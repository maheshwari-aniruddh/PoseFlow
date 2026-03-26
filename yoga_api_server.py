
"""
Yoga API Server - Connects web app to yoga ML system
"""
import asyncio
import json
import os
import cv2
import numpy as np
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from guided_session import GuidedSession
import threading
import time

def make_json_serializable(obj):
    """Convert numpy types and other non-JSON types to JSON-serializable types"""
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, (np.floating, float)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    elif obj is None:
        return None
    else:
        return str(obj)

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global session state
yoga_session = None
camera = None
session_thread = None
is_running = False

def create_custom_program(poses, hold_times):
    """Create a custom program from poses and hold times"""
    return {
        'name': 'Personalized Plan',
        'description': 'Your custom yoga plan',
        'poses': poses,
        'hold_times': hold_times,
    }

def run_yoga_session(poses, hold_times, camera_id=0):
    """Run yoga session in background thread"""
    global yoga_session, camera, is_running
    
    try:
        # Initialize session first - MUST work for pose detection
        print("🔧 Initializing yoga session with MediaPipe...")
        try:
            yoga_session = GuidedSession()
            print("✅ GuidedSession created successfully")
            # Create custom program and add to program manager
            program = create_custom_program(poses, hold_times)
            yoga_session.program_manager.programs['custom_web'] = program
            print("✅ Program created and added")
            # Start the program
            yoga_session.start_program('custom_web')
            print("✅ Program started")
            print("✅ Yoga session initialized with pose detection")
            if hasattr(yoga_session, 'detector') and yoga_session.detector:
                print("✅ MediaPipe detector is available")
            else:
                print("❌ WARNING: MediaPipe detector not available!")
        except Exception as session_error:
            print(f"❌ CRITICAL ERROR: Could not initialize pose detection: {session_error}")
            import traceback
            traceback.print_exc()
            print("❌ Session will NOT work without pose detection - aborting")
            socketio.emit('error', {'message': f'Failed to initialize pose detection: {str(session_error)}'})
            return
        
        # Open camera
        print(f"📷 Opening camera {camera_id} (OpenCV backend)...")
        print("⚠️ Note: This is separate from browser camera - backend needs its own camera access")
        camera = cv2.VideoCapture(camera_id)
        if not camera.isOpened():
            print("❌ CRITICAL: Failed to open camera with OpenCV")
            print("❌ This might be because:")
            print("   1. Camera is already in use by another app")
            print("   2. Camera permissions not granted to Python/terminal")
            print("   3. Camera index 0 is incorrect (try 1 or 2)")
            socketio.emit('error', {'message': 'Failed to open camera - check backend terminal'})
            return
        
        print("✅ Camera opened successfully!")
        print("📷 Setting camera properties to 1080p...")
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        
        # Verify camera is actually working
        test_ret, test_frame = camera.read()
        if not test_ret or test_frame is None:
            print("❌ CRITICAL: Camera opened but cannot read frames!")
            socketio.emit('error', {'message': 'Camera opened but cannot read frames'})
            return
        print(f"✅ Camera test frame read: {test_frame.shape if test_frame is not None else 'None'}")
        
        print("✅ Camera ready, starting session loop...")
        print("📡 Sending first frame immediately...")
        is_running = True
        last_update_time = 0  # Start at 0 so first frame is sent immediately
        last_video_time = 0   # Separate timer for video frames - start at 0 to send immediately
        
        # Main loop - wrapped in comprehensive error handling
        frame_count = 0
        while is_running:
            try:
                ret, frame = camera.read()
                if not ret:
                    print(f"❌ Failed to read frame #{frame_count}")
                    break
                frame_count += 1
                if frame_count == 1:
                    print(f"✅ First frame read successfully: {frame.shape}")
                elif frame_count == 2:
                    print(f"✅ Second frame read, starting to send frames...")
                
                # Process frame - MUST process for pose detection
                result = {}
                debug_info = {}
                try:
                    result = yoga_session.process_frame(frame)
                    # Extract debug info from result
                    debug_info = result.get('debug_info', {}) if isinstance(result, dict) else {}
                    if frame_count <= 5:
                        print(f"✅ Frame {frame_count} processed: has_keypoints={result.get('keypoints') is not None}, debug_keys={list(debug_info.keys())}")
                except Exception as e:
                    print(f"❌ Error processing frame {frame_count}: {e}")
                    import traceback
                    traceback.print_exc()
                    result = {}
                    debug_info = {}
                
                # Ensure result is a dict
                if not isinstance(result, dict):
                    print(f"Warning: result is not a dict, it's {type(result)}")
                    result = {}
                
                # Use MediaPipe's built-in visualization FIRST to draw pose
                frame_with_mediapipe = frame.copy()
                keypoints = None
                try:
                    # Get MediaPipe detection and draw directly using MediaPipe's native visualization
                    if hasattr(yoga_session, 'detector') and yoga_session.detector:
                        keypoints, frame_with_mediapipe = yoga_session.detector.detect_and_draw_pose(frame)
                        if keypoints is not None:
                            visible_count = np.sum(keypoints[:, 2] > 0.2) if len(keypoints.shape) > 1 else 0
                            if frame_count <= 10:
                                print(f"✅ MediaPipe frame {frame_count}: {visible_count} keypoints visible, frame shape: {frame_with_mediapipe.shape}")
                        else:
                            if frame_count <= 5:
                                print(f"⚠️ MediaPipe frame {frame_count}: No keypoints detected")
                    else:
                        print(f"❌ CRITICAL: MediaPipe detector not available in yoga_session! Frame {frame_count}")
                except Exception as e:
                    print(f"❌ Error in MediaPipe visualization frame {frame_count}: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Initialize frame_with_viz early (will be updated later if pose_info exists)
                frame_with_viz = frame_with_mediapipe.copy()
                
                # Get current pose info - with error handling
                pose_info = None
                try:
                    pose_info = yoga_session.get_current_pose()
                except Exception as e:
                    pose_info = None
                
                # Ensure pose_info is a dict, not a string or None
                if pose_info is not None:
                    if not isinstance(pose_info, dict):
                        print(f"Warning: pose_info is not a dict, it's {type(pose_info)}: {pose_info}")
                        pose_info = None
                
                # ALWAYS draw visualization on frame (keypoints and skeleton) - SAFELY
                keypoints = result.get('keypoints') if isinstance(result, dict) else None
                
                # Debug: Log keypoint detection
                if keypoints is not None:
                    if isinstance(keypoints, np.ndarray):
                        visible_count = np.sum(keypoints[:, 2] > 0.2) if len(keypoints.shape) > 1 else 0
                        if visible_count > 0:
                            print(f"✅ Detected {visible_count}/17 keypoints - drawing visualization")
                
                # Get session state for drawing (only if session exists)
                pose_name = ''
                hold_time = 20
                if yoga_session and pose_info and isinstance(pose_info, dict):
                    pose_name = str(pose_info.get('name', ''))
                    hold_time_val = pose_info.get('target_hold', 20)
                    if isinstance(hold_time_val, (int, float)):
                        hold_time = int(hold_time_val)
                
                # Get form status safely
                form_status = 'unknown'
                form_feedback = result.get('form_feedback') if isinstance(result, dict) else None
                if form_feedback and isinstance(form_feedback, dict):
                    form_status = str(form_feedback.get('overall_status', 'unknown'))
                else:
                    # Fallback to smoothed_form_status
                    form_status = str(result.get('smoothed_form_status', 'unknown')) if isinstance(result, dict) else 'unknown'
                
                # Ensure keypoints is valid (array/list, not string)
                if keypoints is not None:
                    if isinstance(keypoints, str):
                        print(f"Warning: keypoints is a string, not array: {keypoints[:50]}")
                        keypoints = None
                    elif not isinstance(keypoints, (list, np.ndarray)):
                        print(f"Warning: keypoints is wrong type: {type(keypoints)}")
                        keypoints = None
                    elif isinstance(keypoints, np.ndarray) and len(keypoints.shape) < 2:
                        print(f"Warning: keypoints array has wrong shape: {keypoints.shape}")
                        keypoints = None
                
                # Initialize session_state with defaults
                session_state = {
                    'keypoints': keypoints,  # Can be None if no detection
                    'current_pose_index': yoga_session.current_pose_index,
                    'current_pose': pose_name,
                    'hold_time': hold_time,
                    'elapsed_time': 0,
                    'in_pose': yoga_session.in_pose,
                    'form_status': form_status,
                    'pose_image': None,  # Will be set if available
                }
                
                # ALWAYS try to draw - even if no keypoints, draw the frame
                try:
                    # Get pose image path from dataset (only if session exists)
                    pose_image_base64 = None
                    if yoga_session and pose_name:
                        try:
                            pose_image_path = yoga_session.program_manager.get_pose_image_path(pose_name)
                            if pose_image_path and os.path.exists(pose_image_path):
                                with open(pose_image_path, 'rb') as f:
                                    image_data = f.read()
                                    pose_image_base64 = base64.b64encode(image_data).decode('utf-8')
                        except Exception as e:
                            pass
                    
                    # Update session_state with pose image
                    session_state['pose_image'] = pose_image_base64
                    
                    # Use MediaPipe visualization as base, then add timer/text overlays
                    try:
                        # Start with MediaPipe visualization (already has dots and skeleton)
                        frame_with_viz = frame_with_mediapipe.copy()
                        # Add timer and text overlays on top (but don't redraw keypoints)
                        frame_with_viz = yoga_session.draw_guided_feedback(frame_with_viz, session_state, skip_keypoints=True)
                        if frame_count <= 10:
                            print(f"✅ Frame {frame_count} visualization complete: shape={frame_with_viz.shape}, has MediaPipe overlay")
                    except Exception as e:
                        print(f"❌ Error in draw_guided_feedback frame {frame_count}: {e}")
                        import traceback
                        traceback.print_exc()
                        # Fallback: use MediaPipe frame
                        frame_with_viz = frame_with_mediapipe
                    
                    # Update keypoints in result for processing
                    if 'keypoints' in locals() and keypoints is not None:
                        result['keypoints'] = keypoints
                except Exception as e:
                    # Fallback: use raw frame
                    frame_with_viz = frame.copy()
                
                # Calculate elapsed time - RESET to 0 when pose is broken
                if yoga_session.in_pose and yoga_session.hold_start_time is not None:
                    # Timer is RUNNING - calculate current elapsed
                    current_elapsed = time.time() - yoga_session.hold_start_time
                    total_elapsed = yoga_session.accumulated_hold_time + current_elapsed
                    session_state['elapsed_time'] = int(round(total_elapsed))
                else:
                    # Timer is RESET - show 0 (restart exercise step when pose is broken)
                    session_state['elapsed_time'] = 0
                
                # Send updates every 100ms (10 FPS for data, 30 FPS for video)
                current_time = time.time()
                send_data_update = (current_time - last_update_time >= 0.1)
                send_video_only = (current_time - last_video_time >= 0.033)  # 30 FPS for video (separate timer)
                
                # Always send debug info if available (even if no pose_info yet)
                if debug_info and send_data_update:
                    try:
                        # Convert all values to JSON-serializable types
                        debug_info_serializable = {}
                        for key, value in debug_info.items():
                            if isinstance(value, bool):
                                debug_info_serializable[key] = bool(value)
                            elif isinstance(value, (int, float, str)):
                                debug_info_serializable[key] = value
                            elif value is None:
                                debug_info_serializable[key] = None
                            else:
                                debug_info_serializable[key] = str(value)
                        
                        socketio.emit('debug_update', {
                            'debugInfo': debug_info_serializable,
                        })
                    except Exception as e:
                        print(f"Error emitting debug_update: {e}")
                        import traceback
                        traceback.print_exc()
                
                # ALWAYS encode and send frame for video - at 30 FPS (regardless of pose_info)
                # Send IMMEDIATELY on first frame, then at 30 FPS
                frame_base64 = None
                # Always send first 3 frames immediately, then at 30 FPS
                should_send_video = (frame_count <= 3) or send_video_only
                if should_send_video:
                    try:
                        _, buffer = cv2.imencode('.jpg', frame_with_viz, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        if buffer is not None and len(buffer) > 0:
                            frame_base64 = base64.b64encode(buffer).decode('utf-8')
                            # ALWAYS send video frame immediately (regardless of pose_info)
                            try:
                                socketio.emit('video_frame', {
                                    'frame': frame_base64,
                                })
                                if not hasattr(run_yoga_session, '_video_frame_count'):
                                    run_yoga_session._video_frame_count = 0
                                run_yoga_session._video_frame_count += 1
                                if run_yoga_session._video_frame_count <= 15:
                                    print(f"📹 Sent video_frame #{run_yoga_session._video_frame_count} (frame {frame_count}): {len(frame_base64)} chars")
                                elif run_yoga_session._video_frame_count == 16:
                                    print(f"📹 Video frames streaming... (continuing silently)")
                                if frame_count <= 3:
                                    last_video_time = 0  # Force next frames to send immediately
                                else:
                                    last_video_time = current_time
                            except Exception as emit_error:
                                print(f"❌ Error emitting video_frame: {emit_error}")
                                import traceback
                                traceback.print_exc()
                        else:
                            print("❌ Failed to encode frame buffer")
                    except Exception as e:
                        print(f"❌ Error encoding/sending video frame: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Always send session_update with pose info (even if pose_info is None, send what we have)
                if send_data_update:
                    try:
                        # Determine pose status - check smoothed_form_status first, then form_feedback
                        pose_status = "unknown"
                        form_feedback = None
                        
                        # Safely get form_feedback from result
                        if isinstance(result, dict):
                            form_feedback = result.get('form_feedback')
                        
                        # Check smoothed_form_status from result
                        smoothed_status = ''
                        if isinstance(result, dict):
                            smoothed_status = str(result.get('smoothed_form_status', ''))
                        
                        if smoothed_status == 'correct':
                            pose_status = "correct"
                        elif smoothed_status == 'improvable':
                            pose_status = "improvable"
                        elif smoothed_status == 'dangerous':
                            pose_status = "wrong"
                        # Fallback to form_feedback overall_status if smoothed_status not available
                        elif form_feedback and isinstance(form_feedback, dict):
                            overall_status = str(form_feedback.get('overall_status', ''))
                            if overall_status == 'correct':
                                pose_status = "correct"
                            elif overall_status == 'improvable':
                                pose_status = "improvable"
                            elif overall_status == 'dangerous':
                                pose_status = "wrong"
                        
                        # Get feedback - safely access form_feedback
                        feedback = ""
                        if form_feedback and isinstance(form_feedback, dict):
                            nlg_corrections = form_feedback.get('nlg_corrections', [])
                            if nlg_corrections and isinstance(nlg_corrections, list) and len(nlg_corrections) > 0:
                                first_correction = nlg_corrections[0]
                                if isinstance(first_correction, dict):
                                    feedback = str(first_correction.get('message', ''))
                    except Exception as e:
                        print(f"Error determining pose status: {e}")
                        pose_status = "unknown"
                        feedback = ""
                    
                    # Get pose image path from dataset (reuse from session_state if available)
                    pose_image_base64 = session_state.get('pose_image') if 'pose_image' in session_state else None
                    
                    # Use the monotonic elapsed_time from session_state (calculated above)
                    # This ensures consistency - we already calculated it with monotonic logic
                    elapsed = session_state.get('elapsed_time', 0)
                    
                    # Use the frame_base64 we already encoded above (if available)
                    # If not available, encode it now
                    if frame_base64 is None:
                        try:
                            _, buffer = cv2.imencode('.jpg', frame_with_viz, [cv2.IMWRITE_JPEG_QUALITY, 85])
                            if buffer is None or len(buffer) == 0:
                                print("❌ ERROR: Failed to encode frame!")
                                frame_base64 = None
                            else:
                                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                                if len(frame_base64) == 0:
                                    print("❌ ERROR: Empty base64 frame!")
                        except Exception as e:
                            print(f"❌ ERROR encoding frame: {e}")
                            import traceback
                            traceback.print_exc()
                            frame_base64 = None
                    
                    try:
                        # Get hold time from pose_info (use target_hold, not hold_time)
                        # Safely extract values from pose_info
                        pose_name = ''
                        hold_time = 20
                        if pose_info and isinstance(pose_info, dict):
                            pose_name = pose_info.get('name', '')
                            hold_time = pose_info.get('target_hold', 20)
                        
                        # Get real-time session statistics from tracker - SAFELY
                        stats = {}
                        progress_score = 0
                        try:
                            if yoga_session and hasattr(yoga_session, 'tracker') and yoga_session.tracker:
                                stats_result = yoga_session.tracker.get_session_stats()
                                if isinstance(stats_result, dict):
                                    stats = stats_result
                                progress_score_result = yoga_session.tracker.calculate_progress_score()
                                if isinstance(progress_score_result, (int, float)):
                                    progress_score = progress_score_result
                        except Exception as e:
                            print(f"Error getting stats: {e}")
                            stats = {}
                            progress_score = 0
                        
                        # Ensure all values are JSON serializable
                        # Check if pose is complete and auto-advance (only if session exists)
                        pose_complete = result.get('pose_complete', False) if isinstance(result, dict) else False
                        if pose_complete and yoga_session.current_pose_index < len(yoga_session.current_program['poses']) - 1:
                            # Auto-advance to next pose after 2 seconds
                            import time as time_module
                            if not hasattr(yoga_session, '_pose_complete_time'):
                                yoga_session._pose_complete_time = time_module.time()
                            elif time_module.time() - yoga_session._pose_complete_time >= 2.0:
                                print(f"✅ Pose complete! Auto-advancing to next pose...")
                                yoga_session.next_pose()
                                yoga_session._pose_complete_time = None
                                # Reset elapsed time for new pose
                                if hasattr(yoga_session, '_last_elapsed_time'):
                                    yoga_session._last_elapsed_time = 0
                        
                        # Ensure we have a frame_base64 (encode if not already done)
                        if frame_base64 is None:
                            try:
                                _, buffer = cv2.imencode('.jpg', frame_with_viz, [cv2.IMWRITE_JPEG_QUALITY, 85])
                                if buffer is not None and len(buffer) > 0:
                                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                            except Exception as e:
                                print(f"❌ Error encoding frame for session_update: {e}")
                                frame_base64 = None
                        
                        # Always send video frame if available
                        if frame_base64:
                            if not hasattr(run_yoga_session, '_session_update_count'):
                                run_yoga_session._session_update_count = 0
                            run_yoga_session._session_update_count += 1
                            if run_yoga_session._session_update_count <= 3:
                                print(f"📹 Sending session_update with videoFrame: {len(frame_base64)} chars")
                        
                        # Emit session_update with video frame and dataset pose reference image
                        socketio.emit('session_update', {
                            'currentPoseIndex': int(yoga_session.current_pose_index),
                            'currentPose': str(pose_name) if pose_name else '',
                            'holdTime': int(hold_time),
                            'elapsedTime': int(elapsed),
                            'isInPose': bool(yoga_session.in_pose),  # Explicitly convert to Python bool
                            'poseStatus': str(pose_status) if pose_status else 'unknown',
                            'feedback': str(feedback) if feedback else '',
                            'poseComplete': bool(pose_complete),  # Add pose completion status
                            'videoFrame': frame_base64 if frame_base64 else None,  # Add video frame (only if encoded successfully)
                            'video_frame': frame_base64 if frame_base64 else None,  # Also send with underscore for compatibility
                            'poseImage': pose_image_base64,  # Dataset reference image for current pose
                            'pose_image': pose_image_base64,  # Underscore variant for compatibility
                            'debugInfo': make_json_serializable(debug_info) if debug_info else {},  # Convert all types to JSON-serializable
                            # Real statistics from model output - all safely accessed
                            'statistics': {
                                'accuracyScore': float(stats.get('accuracy_score', 0)) if isinstance(stats, dict) else 0,
                                'progressScore': float(progress_score) if isinstance(progress_score, (int, float)) else 0,
                                'repCount': int(stats.get('rep_count', 0)) if isinstance(stats, dict) else 0,
                                'avgHoldDuration': round(float(stats.get('avg_hold_duration', 0)), 1) if isinstance(stats, dict) else 0.0,
                                'maxHoldDuration': round(float(stats.get('max_hold_duration', 0)), 1) if isinstance(stats, dict) else 0.0,
                                'avgHoldRatio': round(float(stats.get('avg_hold_ratio', 0)) * 100, 1) if isinstance(stats, dict) else 0.0,
                                'avgFormScore': round(float(stats.get('avg_form_score', 0)), 1) if isinstance(stats, dict) else 0.0,
                                'correctionsCount': int(stats.get('corrections_count', 0)) if isinstance(stats, dict) else 0,
                                'dangerousCorrections': int(stats.get('dangerous_corrections', 0)) if isinstance(stats, dict) else 0,
                                'improvableCorrections': int(stats.get('improvable_corrections', 0)) if isinstance(stats, dict) else 0,
                                'consistencyScore': round(float(stats.get('consistency_score', 0)), 1) if isinstance(stats, dict) else 0.0,
                                'sessionDuration': round(float(stats.get('session_duration', 0)), 1) if isinstance(stats, dict) else 0.0,
                                'poseEntries': int(stats.get('pose_entries', 0)) if isinstance(stats, dict) else 0,
                            }
                        })
                        last_update_time = current_time
                    except Exception as e:
                        print(f"Error emitting session_update: {e}")
                        import traceback
                        traceback.print_exc()
                # Video frames are now sent above in the send_video_only section
                # This ensures frames are sent immediately even when no pose is detected
                
                # Small delay to prevent overwhelming
                time.sleep(0.033)  # ~30 FPS
            except Exception as e:
                print(f"Error in main loop iteration: {e}")
                import traceback
                traceback.print_exc()
                # Continue to next iteration instead of crashing
                time.sleep(0.033)
                continue
        
    except Exception as e:
        socketio.emit('error', {'message': str(e)})
        print(f"Session error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if camera:
            camera.release()
        is_running = False

@app.route('/start-session', methods=['POST'])
def start_session():
    """Start a new yoga session"""
    global yoga_session, session_thread, is_running, camera
    
    print("📥 Received start-session request")
    
    # Stop any existing session first
    if is_running:
        print("⚠️ Stopping existing session before starting new one...")
        is_running = False
        if camera:
            try:
                camera.release()
            except:
                pass
        camera = None
        # Wait a bit for thread to finish
        if session_thread and session_thread.is_alive():
            import time
            time.sleep(1)
    
    data = request.json
    if not data:
        print("❌ No data provided")
        return jsonify({'error': 'No data provided', 'message': 'No data provided'}), 400
    
    plan = data.get('plan', {})
    poses = plan.get('poses', [])
    hold_times = plan.get('hold_times', [])
    camera_id = data.get('camera_id', 0)
    
    if not poses or not hold_times:
        print(f"❌ Invalid plan: poses={len(poses) if poses else 0}, hold_times={len(hold_times) if hold_times else 0}")
        return jsonify({'error': 'Invalid plan', 'message': 'Invalid plan: poses or hold_times missing'}), 400
    
    # Start session in background thread
    try:
        print(f"🚀 Starting session thread with {len(poses)} poses using camera {camera_id}...")
        session_thread = threading.Thread(
            target=run_yoga_session,
            args=(poses, hold_times, camera_id),
            daemon=True
        )
        session_thread.start()
        print(f"✅ Session thread started, returning response")
        return jsonify({'status': 'started', 'message': 'Session started successfully'})
    except Exception as e:
        print(f"❌ Error starting session: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'message': f'Failed to start session: {str(e)}'}), 500

@app.route('/stop-session', methods=['POST'])
def stop_session():
    """Stop the current session"""
    global is_running, yoga_session, camera
    
    is_running = False
    
    # Get final statistics before stopping - SAFELY
    final_stats = None
    if yoga_session and hasattr(yoga_session, 'tracker') and yoga_session.tracker:
        try:
            stats_result = yoga_session.tracker.get_session_stats()
            progress_score_result = yoga_session.tracker.calculate_progress_score()
            
            # Ensure stats is a dict
            if isinstance(stats_result, dict):
                stats = stats_result
            else:
                stats = {}
            
            # Ensure progress_score is a number
            if isinstance(progress_score_result, (int, float)):
                progress_score = progress_score_result
            else:
                progress_score = 0
            
            final_stats = {
                'accuracyScore': float(stats.get('accuracy_score', 0)),
                'progressScore': float(progress_score),
                'repCount': int(stats.get('rep_count', 0)),
                'avgHoldDuration': round(float(stats.get('avg_hold_duration', 0)), 1),
                'maxHoldDuration': round(float(stats.get('max_hold_duration', 0)), 1),
                'avgHoldRatio': round(float(stats.get('avg_hold_ratio', 0)) * 100, 1),
                'avgFormScore': round(float(stats.get('avg_form_score', 0)), 1),
                'correctionsCount': int(stats.get('corrections_count', 0)),
                'dangerousCorrections': int(stats.get('dangerous_corrections', 0)),
                'improvableCorrections': int(stats.get('improvable_corrections', 0)),
                'consistencyScore': round(float(stats.get('consistency_score', 0)), 1),
                'sessionDuration': round(float(stats.get('session_duration', 0)), 1),
                'poseEntries': int(stats.get('pose_entries', 0)),
            }
        except Exception as e:
            print(f"Error getting final statistics: {e}")
            import traceback
            traceback.print_exc()
    
    if camera:
        camera.release()
        camera = None
    
    return jsonify({'status': 'stopped', 'finalStatistics': final_stats})

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'Yoga API Server',
        'session_running': is_running
    })

@app.route('/list-cameras', methods=['GET'])
def list_cameras():
    """List available cameras"""
    try:
        available = []
        camera_info = []
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    available.append(i)
                    camera_info.append({
                        'id': i,
                        'width': width,
                        'height': height,
                        'name': f'Camera {i}'
                    })
                cap.release()
        return jsonify({
            'cameras': camera_info,
            'available': available
        })
    except Exception as e:
        print(f"Error listing cameras: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'cameras': [], 'available': []}), 500

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    print("✅ Client connected via Socket.IO WebSocket")
    print(f"📡 Socket.IO connection established - ready to send video frames")
    emit('connected', {'status': 'connected', 'message': 'Socket.IO connection established'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    print("Client disconnected")

@socketio.on('next_pose')
def handle_next_pose():
    """Handle next pose command - SKIP TO NEXT POSE"""
    global yoga_session
    if yoga_session and hasattr(yoga_session, 'next_pose'):
        try:
            yoga_session.next_pose()
            print("➡️  Moving to next pose...")
            
            # Emit pose change event to frontend
            pose_info = yoga_session.get_current_pose()
            if pose_info and isinstance(pose_info, dict):
                socketio.emit('pose_changed', {
                    'currentPoseIndex': yoga_session.current_pose_index,
                    'currentPose': pose_info.get('name', ''),
                    'holdTime': pose_info.get('target_hold', 20),
                })
            
            # Check if session complete
            if yoga_session.current_program and yoga_session.current_pose_index >= len(yoga_session.current_program['poses']):
                socketio.emit('session_complete', {'message': 'All poses completed!'})
        except Exception as e:
            print(f"Error moving to next pose: {e}")
            import traceback
            traceback.print_exc()

@socketio.on('end_session')
def handle_end_session():
    """Handle end session command"""
    global is_running
    is_running = False

@socketio.on('pause_session')
def handle_pause_session():
    """Handle pause session command"""
    global yoga_session
    if yoga_session:
        yoga_session.paused = True
        print("⏸️  Session paused")

@socketio.on('resume_session')
def handle_resume_session():
    """Handle resume session command"""
    global yoga_session
    if yoga_session:
        yoga_session.paused = False
        print("▶️  Session resumed")

@socketio.on('repeat_instruction')
def handle_repeat_instruction():
    """Handle repeat instruction command"""
    global yoga_session
    if yoga_session:
        yoga_session.repeat_instruction()
        print("🔊 Repeating instruction...")

if __name__ == '__main__':
    print("=" * 60)
    print("🧘 Yoga API Server Starting...")
    print("=" * 60)
    print("📡 API: http://localhost:5002")
    print("🔌 WebSocket: ws://localhost:5002")
    print("=" * 60)
    try:
        socketio.run(app, host='0.0.0.0', port=5002, debug=False, allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()

