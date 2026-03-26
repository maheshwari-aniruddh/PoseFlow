"""
Guided yoga session with step-by-step instructions
"""
import cv2
import numpy as np
import time
from typing import Dict, Optional
from pose_detector import PoseDetector
from pose_classifier import PoseClassifier
from form_corrector import FormCorrector
from session_tracker import SessionTracker
from yoga_program import YogaProgram
from tts_client import TTSClient
import config
import os

class GuidedSession:
    """Guided yoga session with pose-by-pose instructions"""
    
    def __init__(self, classifier_path: Optional[str] = None, templates_dir: Optional[str] = None):
        """Initialize guided session"""
# Initializing session
        
        self.detector = PoseDetector()
        self.classifier = PoseClassifier()
        self.corrector = FormCorrector(templates_dir)
        self.tracker = SessionTracker()
        self.program_manager = YogaProgram()
        
        # Initialize TTS client for voice feedback (Arcas = deep male voice)
        try:
            self.tts = TTSClient(backend_url="http://localhost:5001/speak", voice="arcas")
            pass  # TTS initialized
        except Exception as e:
            pass  # TTS failed
            self.tts = None
        
        # Track last spoken feedback to avoid repetition
        self.last_spoken_feedback = None
        self.last_spoken_time = 0.0
        self.feedback_speak_cooldown = 30.0  # Minimum seconds between ANY feedback (more patient, was 10.0)
        self.feedback_already_spoken = set()  # Track which feedback has been spoken to avoid repetition
        
        # Track if instructions have been spoken for current pose (only speak once)
        self.instruction_spoken_for_pose = False
        self.current_pose_name_for_instruction = None
        
        # Load classifier
        if classifier_path and os.path.exists(classifier_path):
            self.classifier.load(classifier_path)
        else:
            classifier_path = os.path.join(config.MODELS_DIR, "pose_classifier.pkl")
            if os.path.exists(classifier_path):
                self.classifier.load(classifier_path)
            else:
                raise FileNotFoundError("Classifier not found. Run setup.py first!")
        
        self.current_program = None
        self.current_pose_index = 0
        self.pose_start_time = None
        self.in_pose = False
        self.pose_entered = False
        self.hold_start_time = None
        self.accumulated_hold_time = 0.0  # Total time accumulated for current pose (pauses when exiting)
        self.last_pause_time = None  # When we last paused (exited pose)
        self.paused = False  # Manual pause flag
        
        # Correction logging
        self.corrections_log = []  # Store all corrections during session
        self.corrections_file = None  # File handle for corrections log
        self.session_start_time = None
        
        # Smoothing for pose detection (more responsive - less smoothing)
        self.pose_confidence_history = []  # Track recent combined scores
        self.confidence_history_size = 10  # Average over last 10 frames (more responsive, was 18)
        self.smoothed_score = 0.0  # Exponential moving average
        self.alpha = 0.4  # EMA smoothing factor (0.4 = 40% new, 60% old - more responsive, was 0.25)
        
        # Smooth form status to prevent flickering - MORE RESPONSIVE
        self.form_status_history = []  # Track recent form statuses
        self.form_status_history_size = 12  # Average over last 12 frames (more responsive, was 25)
        self.smoothed_form_status = 'unknown'  # Current smoothed form status
        self.form_status_consistency_required = 8  # Need 8 consistent frames to change status (more responsive, was 15)
        self.current_form_status_count = 0  # Count of consecutive frames with same status
        
        # Color indicator hysteresis - once green, stay green longer
        self.last_color_state = 'unknown'  # Track last color state (green/red)
        self.color_green_frames = 0  # Count frames in green state
        
        # Pose stability - require pose to be detected for N frames before confirming
        # More responsive - reduced from 6 to 2 for easier activation
        self.pose_stability_frames = []  # Track frames where pose matches
        self.stability_required = 3  # Must match for 3 frames before confirming (more stable, was 2)
        
        # Store last pose detection values for debug_info and voice feedback
        self.last_pose_confidence = 0.0
        self.last_angle_similarity = 0.0
        self.last_combined_score = 0.0
        self.last_exact_match = False
        self.last_can_start_timer = False
        self.last_has_template = False
        
        # Session ready
    
    def start_program(self, program_name: str):
        """Start a yoga program"""
        program = self.program_manager.get_program(program_name)
        if not program:
            raise ValueError(f"Program '{program_name}' not found")
        
        self.current_program = program
        self.current_pose_index = 0
        self.in_pose = False
        self.pose_entered = False
        self.accumulated_hold_time = 0.0  # Reset accumulated time for new program
        self.last_pause_time = None
        self.instruction_spoken_for_pose = False  # Reset instruction tracking
        self.current_pose_name_for_instruction = None
        # Reset feedback tracking for new program
        self.feedback_already_spoken.clear()
        self.last_spoken_feedback = None
        self.last_spoken_time = 0.0
        # Reset color state
        self.last_color_state = 'unknown'
        self.color_green_frames = 0
        if hasattr(self, 'pose_wrong_frames'):
            self.pose_wrong_frames = 0
        
        # Initialize corrections log file
        self.corrections_log = []
        self.session_start_time = time.time()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        corrections_filename = os.path.join(config.OUTPUT_DIR, f"corrections_{timestamp}.txt")
        self.corrections_file = open(corrections_filename, 'w', encoding='utf-8')
        self.corrections_file.write(f"🧘 YogaBuddy - Session Corrections Log\n")
        self.corrections_file.write(f"{'='*60}\n")
        self.corrections_file.write(f"Program: {program['name']}\n")
        self.corrections_file.write(f"Description: {program['description']}\n")
        self.corrections_file.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.corrections_file.write(f"{'='*60}\n\n")
        
        # Starting program
    
    def get_current_pose(self) -> Optional[Dict]:
        """Get current pose information"""
        if not self.current_program:
            return None
        
        if self.current_pose_index >= len(self.current_program['poses']):
            return None
        
        pose_name = self.current_program['poses'][self.current_pose_index]
        hold_time = self.program_manager.get_pose_image_path(pose_name)
        
        return {
            'name': pose_name,
            'index': self.current_pose_index,
            'total': len(self.current_program['poses']),
            'target_hold': self.current_program['hold_times'][self.current_pose_index],
            'image_path': hold_time
        }
    
    def process_frame(self, frame: np.ndarray) -> Dict:
        """Process a frame and return session state"""
        # Detect pose
        keypoints = self.detector.detect_pose(frame)
        
        # Check if full body is in frame
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
        distance_status = 'optimal'  # Always allow processing
        distance_msg = "✅ Ready"
        is_optimal_distance = True  # Always true - skip distance check
        
        # Check body visibility - ensure full body is in frame
        body_fully_visible = True
        visibility_message = ""
        
        if keypoints is not None:
            # Check critical body parts for full body visibility - VERY LENIENT thresholds
            # Use lower confidence threshold (0.2 instead of 0.3) for body part detection
            low_threshold = 0.2
            
            # Head: at least nose or one eye/ear visible
            head_visible = (keypoints[0][2] > low_threshold or  # nose
                          keypoints[1][2] > low_threshold or  # left_eye
                          keypoints[2][2] > low_threshold)   # right_eye
            
            # Shoulders: at least one visible
            shoulders_visible = (keypoints[5][2] > low_threshold or  # left_shoulder
                                keypoints[6][2] > low_threshold)      # right_shoulder
            
            # Hips: at least one visible
            hips_visible = (keypoints[11][2] > low_threshold or  # left_hip
                           keypoints[12][2] > low_threshold)    # right_hip
            
            # Knees: at least one visible
            knees_visible = (keypoints[13][2] > low_threshold or  # left_knee
                            keypoints[14][2] > low_threshold)     # right_knee
            
            # Ankles: at least one visible
            ankles_visible = (keypoints[15][2] > low_threshold or  # left_ankle
                             keypoints[16][2] > low_threshold)     # right_ankle
            
            # Check if enough body parts are visible (VERY lenient - need only 2 out of 5)
            visible_parts = sum([head_visible, shoulders_visible, hips_visible, knees_visible, ankles_visible])
            body_fully_visible = visible_parts >= 2  # Very lenient - only need 2 out of 5 parts
            
            # Also check if we have ANY keypoints at all (even lower threshold)
            any_keypoints = any(kp[2] > 0.15 for kp in keypoints if len(kp) > 2)
            if any_keypoints and visible_parts < 2:
                # If we have some keypoints but not enough parts, still try
                body_fully_visible = True
            
            if not body_fully_visible:
                missing_parts = []
                if not head_visible:
                    missing_parts.append("head")
                if not shoulders_visible:
                    missing_parts.append("shoulders")
                if not hips_visible:
                    missing_parts.append("hips")
                if not knees_visible:
                    missing_parts.append("knees")
                if not ankles_visible:
                    missing_parts.append("ankles/feet")
                
                visibility_message = f"⚠️ Move back! Your {', '.join(missing_parts)} are not fully visible. Step back to fit your whole body in frame."
            else:
                visibility_message = "✅ Full body visible"
        
        # Get current pose info
        current_pose_info = self.get_current_pose()
        
        if current_pose_info is None:
            return {
                'status': 'complete',
                'message': '🎉 Program complete!',
                'keypoints': keypoints,
                'distance_status': distance_status,
                'distance_msg': distance_msg
            }
        
        # Classify pose if we have keypoints
        detected_pose = None
        confidence = 0.0
        form_feedback = None
        
        if keypoints is not None:
            confidence = self.detector.get_pose_confidence(keypoints)
            if confidence >= config.POSE_CONFIDENCE_THRESHOLD:
                try:
                    # LENIENT: Always try to classify, even if body not fully visible
                    # This allows detection even with partial body visibility
                    has_template = False
                    detected_pose, pose_confidence = self.classifier.predict(keypoints)
                    confidence = pose_confidence
                    
                    target_pose = current_pose_info['name']
                    
                    # Get form feedback to check angle similarity to target pose
                    # Use detected_pose name for template lookup (it's the actual folder name)
                    form_feedback = self.corrector.correct_form(keypoints, detected_pose)
                    has_template = form_feedback.get('has_template', False)
                    
                    # Debug: Check if template was found
                    if not has_template:
                        # Try with target_pose name as fallback
                        form_feedback_target = self.corrector.correct_form(keypoints, target_pose)
                        if form_feedback_target.get('has_template', False):
                            form_feedback = form_feedback_target
                            has_template = True if form_feedback else False
                    
                    # Only reduce confidence if body not fully visible, but still try
                    if not body_fully_visible:
                        confidence = pose_confidence * 0.8  # Slight reduction, but still try
                    
                    # Calculate weighted angle similarity score if we have a template
                    # STRICT: Require template to exist, otherwise angle_similarity = 0
                    if body_fully_visible and has_template:
                        angle_similarity = 0.0
                        angle_feedback = form_feedback.get('feedback', {})
                        if angle_feedback:
                            # Use weighted average deviation (more accurate)
                            avg_weighted_deviation = form_feedback.get('avg_weighted_deviation', 100.0)
                            
                            # BALANCED: Convert to similarity with reasonable thresholds (tolerable but accurate)
                            # 40° max deviation = 0 similarity, 0° = 1.0 similarity
                            # Tolerable scaling for number of angles
                            num_angles = len(angle_feedback)
                            max_deviation = 40.0 + (num_angles * 2.2)  # Tolerable threshold (slightly more forgiving)
                            angle_similarity = max(0.0, min(1.0, 1.0 - (avg_weighted_deviation / max_deviation)))
                            
                            # More tolerant penalty - only penalize if many angles are wrong
                            correct_count = sum(1 for fb in angle_feedback.values() if fb.get('status') == 'correct')
                            total_count = len(angle_feedback)
                            correct_ratio = correct_count / total_count if total_count > 0 else 0.0
                            
                            # Only boost if most angles are correct (at least 60% - tolerable)
                            if correct_ratio >= 0.60:  # Tolerable threshold
                                # Boost similarity if most critical angles are correct
                                critical_correct = sum(1 for fb in angle_feedback.values() 
                                                     if fb.get('weight', 1.0) >= 2.0 and fb.get('status') == 'correct')
                                total_critical = sum(1 for fb in angle_feedback.values() 
                                                   if fb.get('weight', 1.0) >= 2.0)
                                if total_critical > 0:
                                    critical_ratio = critical_correct / total_critical
                                    # Smaller boost (was 0.2, now 0.1) - be more stable
                                    angle_similarity = min(1.0, angle_similarity + (critical_ratio * 0.1))
                            else:
                                # Moderate penalty - reduce by 20% if less than 60% correct (more tolerable)
                                angle_similarity = angle_similarity * 0.80  # Reduce by 20%
                    else:
                        # No template = can't verify angles = angle_similarity = 0
                        angle_similarity = 0.0
                    
                    # Normalize pose names for comparison (better matching)
                    target_normalized = target_pose.lower().replace('_', ' ').replace('-', ' ').replace('(', '').replace(')', '').replace('or', '').strip()
                    detected_normalized = detected_pose.lower().replace('_', ' ').replace('-', ' ').replace('(', '').replace(')', '').replace('or', '').strip()
                    
                    # Extract key words from pose names
                    target_words = set([w for w in target_normalized.split() if len(w) > 2])
                    detected_words = set([w for w in detected_normalized.split() if len(w) > 2])
                    
                    # Check for word overlap (more lenient matching)
                    word_overlap = len(target_words & detected_words) / max(len(target_words), 1) if target_words else 0.0
                    
                    # Check exact name match OR significant word overlap
                    exact_match = (
                        detected_pose == target_pose or 
                        target_pose in detected_pose or 
                        detected_pose in target_pose or
                        word_overlap >= 0.5  # At least 50% word overlap
                    )
                    
                    # Combined score: 50% classifier confidence + 50% angle similarity
                    # STRICT: Both must be high for pose to be recognized
                    combined_score = (pose_confidence * 0.5) + (angle_similarity * 0.5)
                    
                    # Get form status to ensure angles are actually correct
                    form_status = form_feedback.get('overall_status', 'unknown') if form_feedback else 'unknown'
                    
                    # Smooth form status to prevent flickering - MUCH MORE STABLE
                    if form_feedback:
                        current_form_status = form_feedback.get('overall_status', 'unknown')
                        self.form_status_history.append(current_form_status)
                        if len(self.form_status_history) > self.form_status_history_size:
                            self.form_status_history.pop(0)
                        
                        # Use majority vote for smoothed status (prevents rapid flickering)
                        if len(self.form_status_history) >= 5:
                            status_counts = {}
                            for status in self.form_status_history:
                                status_counts[status] = status_counts.get(status, 0) + 1
                            # Get most common status
                            most_common_status = max(status_counts.items(), key=lambda x: x[1])[0]
                            most_common_count = status_counts[most_common_status]
                            
                            # Require consistency: status must appear in majority of recent frames
                            # AND must be consistent for multiple frames before changing
                            if most_common_status == self.smoothed_form_status:
                                # Same status - increment counter
                                self.current_form_status_count += 1
                            else:
                                # Different status - check if it's consistent enough to change
                                if most_common_count >= (len(self.form_status_history) * 0.6):  # 60% majority
                                    # New status is dominant, but require consistency before switching
                                    if self.current_form_status_count >= self.form_status_consistency_required:
                                        # Been consistent long enough, allow change
                                        self.smoothed_form_status = most_common_status
                                        self.current_form_status_count = 1
                                    else:
                                        # Not consistent enough yet, keep old status
                                        self.current_form_status_count = 0
                                else:
                                    # New status not dominant enough, keep old status
                                    self.current_form_status_count = 0
                        else:
                            # Not enough history yet, use current
                            if current_form_status == self.smoothed_form_status:
                                self.current_form_status_count += 1
                            else:
                                self.smoothed_form_status = current_form_status
                                self.current_form_status_count = 1
                    else:
                        self.smoothed_form_status = 'unknown'
                        self.current_form_status_count = 0
                    
                    # Use smoothed form status for decisions
                    smoothed_status = self.smoothed_form_status
                    
                    # MORE TOLERABLE matching criteria
                    # Require reasonable classifier confidence AND reasonable angle match
                    is_matching_pose = (
                        exact_match and  # Must match (exact or word overlap)
                        has_template and  # Must have template to verify angles
                        pose_confidence >= 0.12 and  # Very tolerant classifier confidence (was 0.20)
                        angle_similarity >= 0.25 and  # Very tolerant angle similarity (was 0.35)
                        combined_score >= 0.20 and  # Very tolerant combined score (was 0.30)
                        smoothed_status != 'dangerous'  # Form must not be dangerous (use smoothed)
                    )
                    
                    # Track combined score for smoothing (both simple average and EMA)
                    self.pose_confidence_history.append(combined_score)
                    if len(self.pose_confidence_history) > self.confidence_history_size:
                        self.pose_confidence_history.pop(0)
                    
                    # Exponential moving average (responds faster to changes, smoother)
                    if self.smoothed_score == 0.0:
                        self.smoothed_score = combined_score
                    else:
                        self.smoothed_score = (self.alpha * combined_score) + ((1 - self.alpha) * self.smoothed_score)
                    
                    # Also calculate simple average for comparison
                    simple_avg = sum(self.pose_confidence_history) / len(self.pose_confidence_history) if self.pose_confidence_history else combined_score
                    
                    # Use the more conservative of the two (prevents false positives)
                    smoothed_score = min(self.smoothed_score, simple_avg)
                    
                    # Start timer if pose is detected with reasonable confidence
                    # Very lenient criteria for starting timer - just need to detect the pose
                    can_start_timer = (
                        exact_match and  # Pose name matches
                        has_template and  # Have template to verify
                        pose_confidence >= 0.10 and  # Very tolerant classifier confidence (was 0.15)
                        (angle_similarity >= 0.18 or combined_score >= 0.18)  # Very tolerant angle match OR combined score (was 0.25)
                    )
                    
                    # Store values as instance variables for use in debug_info and voice feedback
                    self.last_pose_confidence = pose_confidence
                    self.last_angle_similarity = angle_similarity
                    self.last_combined_score = combined_score
                    self.last_exact_match = exact_match
                    self.last_can_start_timer = can_start_timer
                    self.last_has_template = has_template
                    
                    # Determine if we're in pose using balanced thresholds with stability check
                    # Use smoothed score with wide hysteresis gap to prevent flickering
                    # Entry threshold: require both smoothed AND current score to be reasonable (more tolerable)
                    if is_matching_pose and smoothed_score >= 0.20 and combined_score >= 0.20:  # Very tolerable entry (was 0.30)
                        # Track stability - add this frame to stability history
                        self.pose_stability_frames.append(True)
                        if len(self.pose_stability_frames) > self.stability_required:
                            self.pose_stability_frames.pop(0)
                        
                        # Only confirm pose if stable for required frames (prevents false positives)
                        is_stable = len(self.pose_stability_frames) >= self.stability_required
                        
                        if is_stable:
                            # Update tracking
                            if not self.pose_entered:
                                self.pose_entered = True
                                # Resume timer from where we left off - NEVER RESET
                                if self.last_pause_time is not None:
                                    # We were paused, resume timer from accumulated time
                                    self.last_pause_time = None
                                # Start/resume the timer (resume from accumulated time - NEVER RESET)
                                if self.hold_start_time is None:
                                    # Only start if not already running
                                    self.hold_start_time = time.time() - self.accumulated_hold_time
                            
                            # Keep timer running if already started
                            if self.hold_start_time is None and self.accumulated_hold_time > 0:
                                # Resume from accumulated time
                                self.hold_start_time = time.time() - self.accumulated_hold_time
                            
                            self.in_pose = True
                        else:
                            # Not stable yet - reset timer (restart exercise step)
                            if self.in_pose or self.hold_start_time is not None:
                                self.accumulated_hold_time = 0.0
                                self.hold_start_time = None
                            self.in_pose = False  # Don't count as in pose until stable
                    elif can_start_timer:
                        # Start timer even if not perfect match - user is trying to get into pose
                        self.pose_entered = True
                        if self.last_pause_time is not None:
                            self.last_pause_time = None
                        # Start/resume the timer - NEVER RESET, always continue from accumulated time
                        if self.hold_start_time is None:
                            # Only start if not already running
                            if self.accumulated_hold_time > 0:
                                # Resume from accumulated time
                                self.hold_start_time = time.time() - self.accumulated_hold_time
                            else:
                                # First time starting for this pose
                                self.hold_start_time = time.time()
                        self.in_pose = True
                    else:
                        # Not matching well enough
                        # Track instability - add False to stability history
                        self.pose_stability_frames.append(False)
                        if len(self.pose_stability_frames) > self.stability_required:
                            self.pose_stability_frames.pop(0)
                        
                        if self.pose_entered:
                            # Use WIDE hysteresis - need to drop significantly to exit (prevents flickering)
                            # Exit threshold: lower than entry threshold (0.15 gap for stability, but still responsive)
                            # But also exit if form becomes dangerous or angles don't match well
                            # Also require instability for multiple frames (prevents flickering on exit)
                            unstable_frames = sum(1 for x in self.pose_stability_frames if not x)
                            is_unstable = unstable_frames >= self.stability_required  # Need ALL frames unstable (much more tolerant - was 50%)
                            
                            should_exit = (
                                (smoothed_score < 0.05 or  # VERY tolerant - only exit if score drops very low (0.15 gap from 0.20 entry)
                                 combined_score < 0.05 or  # VERY tolerant - only exit if score drops very low (0.15 gap from 0.20 entry)
                                 angle_similarity < 0.08 or  # VERY tolerant - only exit if angles are way off (0.17 gap from 0.25 entry)
                                 smoothed_status == 'dangerous') and  # Form is dangerous (use smoothed)
                                is_unstable  # Must be unstable for multiple frames
                            )
                            if should_exit:
                                # RESET TIMER - Model detected you're not in pose anymore
                                # Reset to 0 - restart the exercise step
                                self.accumulated_hold_time = 0.0
                                self.hold_start_time = None
                                self.last_pause_time = None
                                self.in_pose = False
                                # DON'T reset pose_entered - keep it True so timer can resume
                                # self.pose_entered = False  # REMOVED - keep pose_entered True so timer resumes
                                self.pose_stability_frames = []  # Reset stability tracking
                                # Don't reset history immediately - keep some smoothing
                                # Only reset if we've been out for a while
                                if len(self.pose_confidence_history) > 0:
                                    # Keep last few frames for smoother re-entry
                                    self.pose_confidence_history = self.pose_confidence_history[-5:]
                                # Don't reset smoothed_score completely - keep some memory
                                self.smoothed_score = max(0.0, self.smoothed_score * 0.5)  # Decay slowly
                            else:
                                # Still close enough, keep tracking (tolerance for small movements)
                                # Keep timer running - don't pause for minor fluctuations
                                self.in_pose = True
                                # Ensure timer is still running
                                if self.hold_start_time is None and self.accumulated_hold_time > 0:
                                    self.hold_start_time = time.time() - self.accumulated_hold_time
                        else:
                            # Not in pose - RESET timer (restart exercise step)
                            if self.in_pose or self.hold_start_time is not None:
                                # Reset timer to 0 - restart the exercise
                                self.accumulated_hold_time = 0.0
                                self.hold_start_time = None
                            
                            self.in_pose = False
                            # Reset stability if we're not even close (more tolerant)
                            if smoothed_score < 0.05:
                                self.pose_stability_frames = []
                except Exception as e:
                    pass
        
        # CRITICAL: Reset timer if we're not in pose (restart exercise step)
        # This must happen BEFORE calculating current_hold to prevent timer from continuing
        if not self.in_pose and (self.hold_start_time is not None or self.accumulated_hold_time > 0):
            # IMMEDIATELY reset timer to 0 - restart the exercise step
            self.accumulated_hold_time = 0.0
            self.hold_start_time = None
        
        # Calculate hold time (accumulated + current session)
        current_hold = self.accumulated_hold_time
        if self.hold_start_time:
            current_hold += (time.time() - self.hold_start_time)
        
        # ONLY log timer information - count up when in pose
        if self.in_pose and self.hold_start_time is not None:
            # Timer is running - log every second
            elapsed_seconds = int(current_hold)
            if not hasattr(self, '_last_logged_second'):
                self._last_logged_second = -1
            if elapsed_seconds != self._last_logged_second:
                self._last_logged_second = elapsed_seconds
                print(f"⏱️  {elapsed_seconds}s")
        
        # Check if pose is complete
        target_hold = current_pose_info['target_hold']
        pose_complete = current_hold >= target_hold and self.in_pose
        
        # Update session tracker with current pose info
        if detected_pose and form_feedback:
            self.tracker.update(
                detected_pose, 
                confidence, 
                form_feedback,
                target_hold_time=target_hold
            )
        
        # Calculate debug info FIRST so we can use it for voice feedback
        # Store values calculated during pose detection (they're in local scope, need to extract)
        debug_info = {}
        # Always include basic info
        debug_info = {
            'body_fully_visible': body_fully_visible,
            'stability_frames': len(self.pose_stability_frames),
            'stability_required': self.stability_required,
            'smoothed_score': round(self.smoothed_score, 3),
        }
        
        # Use stored pose detection values (calculated during pose detection above)
        if detected_pose is not None:
            try:
                target_pose = current_pose_info['name']
                # Use stored values from pose detection
                pose_confidence = self.last_pose_confidence
                angle_similarity = self.last_angle_similarity
                combined_score = self.last_combined_score
                exact_match = self.last_exact_match
                can_start_timer = self.last_can_start_timer
                has_template = self.last_has_template
                
                # Update debug info with pose-specific data
                debug_info.update({
                    'detected_pose': detected_pose,
                    'target_pose': target_pose,
                    'pose_confidence': round(pose_confidence, 3),
                    'angle_similarity': round(angle_similarity, 3),
                    'combined_score': round(combined_score, 3),
                    'has_template': has_template,
                    'exact_match': exact_match,
                    'can_start_timer': can_start_timer,
                    'is_matching_pose': (
                        exact_match and
                        has_template and
                        pose_confidence >= 0.12 and
                        angle_similarity >= 0.25 and
                        combined_score >= 0.20
                    ),
                })
            except Exception as e:
                debug_info.update({'error': str(e)})
        else:
            # No pose detected - reset stored values and show basic info
            self.last_pose_confidence = 0.0
            self.last_angle_similarity = 0.0
            self.last_combined_score = 0.0
            self.last_exact_match = False
            self.last_can_start_timer = False
            self.last_has_template = False
            
            debug_info.update({
                'detected_pose': None,
                'target_pose': current_pose_info['name'] if current_pose_info else None,
                'pose_confidence': 0.0,
                'angle_similarity': 0.0,
                'combined_score': 0.0,
                'has_template': False,
                'exact_match': False,
                'can_start_timer': False,
                'is_matching_pose': False,
            })
        
        # Generate instruction message - pass debug_info for voice feedback
        instruction = self._generate_instruction(
            current_pose_info, 
            is_optimal_distance,
            distance_msg,
            detected_pose,
            confidence,
            form_feedback,
            current_hold,
            target_hold,
            pose_complete,
            body_fully_visible,
            visibility_message,
            debug_info  # Pass debug_info so voice feedback uses actual detection values
        )
        
        return {
            'status': 'in_progress',
            'current_pose': current_pose_info,
            'keypoints': keypoints,
            'detected_pose': detected_pose,
            'confidence': confidence,
            'form_feedback': form_feedback,
            'smoothed_form_status': self.smoothed_form_status,  # Include smoothed status
            'distance_status': distance_status,
            'distance_msg': distance_msg,
            'is_optimal_distance': is_optimal_distance,
            'in_pose': self.in_pose,
            'current_hold': current_hold,
            'target_hold': target_hold,
            'pose_complete': pose_complete,
            'instruction': instruction,
            'body_fully_visible': body_fully_visible,
            'visibility_message': visibility_message,
            'debug_info': debug_info  # Add debug info
        }
    
    def _generate_instruction(self, pose_info, is_optimal_distance, distance_msg, 
                             detected_pose, confidence, form_feedback, 
                             current_hold, target_hold, pose_complete,
                             body_fully_visible=True, visibility_message="", debug_info=None) -> str:
        """Generate step-by-step instruction message with clear guidance"""
        pose_name = pose_info['name'].replace('_', ' ').replace('or', '|')
        target_pose = pose_info['name']
        
        # Add visibility message at the top if body not fully visible
        visibility_prefix = ""
        if not body_fully_visible and visibility_message:
            visibility_prefix = f"{visibility_message}\n\n"
        
        # Step 1: Pose detection - speak instruction ONCE per pose
        if not detected_pose:
            # Only speak instruction once per pose (unless repeat button pressed)
            pose_changed = (self.current_pose_name_for_instruction != target_pose)
            if pose_changed:
                self.instruction_spoken_for_pose = False
                self.current_pose_name_for_instruction = target_pose
            
            if self.tts and not self.instruction_spoken_for_pose:
                instruction = f"Get into {pose_name.replace('_', ' ')}. Hold for {int(target_hold)} seconds."
                self.tts.speak_simple(instruction, voice="arcas")
                self.instruction_spoken_for_pose = True
                self.last_spoken_time = time.time()
            return f"Hold for {target_hold}s"
        
        # Step 2: Check if pose is similar (even if not exact match)
        target_normalized = target_pose.lower().replace('_', ' ').replace('-', ' ').replace('(', '').replace(')', '')
        detected_normalized = detected_pose.lower().replace('_', ' ').replace('-', ' ').replace('(', '').replace(')', '')
        target_words = set(target_normalized.split())
        detected_words = set(detected_normalized.split())
        word_overlap = len(target_words & detected_words) / max(len(target_words), 1)
        
        # If pose is similar but not exact, still give form feedback
        is_similar = (word_overlap > 0.3 or 
                     target_normalized in detected_normalized or 
                     detected_normalized in target_normalized)
        
        # Step 3: Voice feedback based on DEBUG VALUES (not form feedback)
        # Use debug_info to determine if pose is correct
        if debug_info:
            exact_match = debug_info.get('exact_match', False)
            pose_confidence = debug_info.get('pose_confidence', 0.0)
            angle_similarity = debug_info.get('angle_similarity', 0.0)
            can_start_timer = debug_info.get('can_start_timer', False)
            has_template = debug_info.get('has_template', False)
            
            # Only say "wrong pose" if debug values clearly show wrong pose
            # If exact_match is True OR can_start_timer is True, pose is correct
            if exact_match or can_start_timer:
                # Pose is correct - don't say anything wrong
                # Only speak if form needs adjustment (but not "wrong pose")
                pass
            elif detected_pose and not exact_match and pose_confidence < 0.05:
                # REALLY wrong pose - very low confidence and not exact match (only speak if very wrong)
                if self.tts and (time.time() - self.last_spoken_time) >= self.feedback_speak_cooldown:
                    correction = f"Please move to {pose_name.replace('_', ' ')}."
                    self.tts.speak_simple(correction, voice="arcas")
                    self.last_spoken_time = time.time()
                    pass  # Voice feedback
            # Don't speak for angle adjustments - too frequent and annoying
            # Only speak positive feedback very rarely
            elif can_start_timer and self.in_pose:
                # Pose is good - only speak positive feedback very rarely (encouragement)
                if self.tts and (time.time() - self.last_spoken_time) > 60.0:  # Only every 60 seconds
                    feedback = "Great job. Keep holding."
                    self.tts.speak_simple(feedback, voice="arcas")
                    self.last_spoken_time = time.time()
                    pass  # Voice encouragement
        
        # Step 4: Similar pose or almost there - form feedback will be spoken in Step 5
        if not self.in_pose or (is_similar and not self.in_pose):
            return f"{current_hold:.1f}s / {target_hold}s"
        
        # Step 5: In the pose - show timer and feedback
        # Calculate remaining time
        remaining = max(0, target_hold - current_hold)
        progress_pct = min(100, (current_hold / target_hold) * 100)
        
        # Voice feedback based on DEBUG VALUES (not form_feedback status)
        # Only speak if debug_info shows the pose is actually wrong
        if debug_info:
            exact_match = debug_info.get('exact_match', False)
            pose_confidence = debug_info.get('pose_confidence', 0.0)
            angle_similarity = debug_info.get('angle_similarity', 0.0)
            can_start_timer = debug_info.get('can_start_timer', False)
            
            # If can_start_timer is True, pose is correct - don't say wrong pose
            if can_start_timer or exact_match:
                # Pose is correct - only give positive feedback very rarely (encouragement)
                if form_feedback and form_feedback.get('has_template'):
                    status = form_feedback.get('overall_status', 'unknown')
                    # Only speak if form is perfect AND it's been a long time (encouragement, not constant)
                    if status == 'correct' and self.tts and (time.time() - self.last_spoken_time) > 60.0:
                        feedback_text = "Excellent form. Keep going."
                        self.tts.speak_simple(feedback_text, voice="arcas")
                        self.last_spoken_time = time.time()
                        pass  # Voice feedback
        
        # Build detailed feedback message using advanced NLG (for display, not voice)
        if form_feedback and form_feedback.get('has_template'):
            status = form_feedback.get('overall_status', 'unknown')
            
            # Use advanced NLG corrections if available (grouped by body regions, 1-2 at a time)
            nlg_corrections = form_feedback.get('nlg_corrections', [])
            nlg_summary = form_feedback.get('nlg_summary', '')
            
            # Prepare feedback text for TTS (remove emojis and formatting)
            # BUT: Only speak if debug values show pose is actually wrong
            if status == 'correct':
                feedback_text = "Perfect form! Keep holding."
                # DEBUG: Print feedback (but don't speak - already handled above)
                pass  # Status feedback
            elif nlg_corrections:
                # Only speak the MOST WRONG feedback (highest deviation, not danger-based)
                angle_feedback = form_feedback.get('feedback', {})
                
                # Find the angle with HIGHEST DEVIATION (most wrong)
                most_critical = None
                max_deviation = 0
                max_weighted_deviation = 0
                critical_status = None
                critical_angle_name = None
                
                # Find the angle with the highest deviation (most wrong)
                if angle_feedback:
                    for angle_name, angle_info in angle_feedback.items():
                        deviation = angle_info.get('deviation', 0)
                        weighted_deviation = angle_info.get('weighted_deviation', 0)
                        angle_status = angle_info.get('status', 'improvable')
                        
                        # Only consider if deviation is significant (>= 15 degrees)
                        if deviation >= 15.0 and angle_status != 'correct':
                            # Use weighted deviation as primary, then regular deviation
                            if weighted_deviation > max_weighted_deviation or (weighted_deviation == max_weighted_deviation and deviation > max_deviation):
                                max_weighted_deviation = weighted_deviation
                                max_deviation = deviation
                                critical_angle_name = angle_name
                                critical_status = angle_status
                
                # Find corresponding NLG correction for the most wrong angle
                if critical_angle_name:
                    # Try to match the angle name to an NLG correction
                    for corr in nlg_corrections:
                        # Match by angle name or message content
                        if (critical_angle_name.lower() in corr.lower() or 
                            angle_feedback[critical_angle_name].get('message', '').lower() in corr.lower()):
                            most_critical = corr
                            break
                    
                    # If no match found, use first NLG correction (it should be prioritized)
                    if not most_critical and nlg_corrections:
                        most_critical = nlg_corrections[0]
                
                # Only speak if we have a critical correction AND it hasn't been spoken before
                if most_critical:
                    feedback_text = most_critical.replace("💡", "").replace("⚠️", "").replace("✅", "").strip()
                    
                    # DEBUG: Print feedback with status
                    status_emoji = "🟡" if critical_status == 'improvable' else "🔴" if critical_status == 'dangerous' else "⚪"
                    pass  # Critical feedback
                    if nlg_corrections:
                        pass  # NLG corrections
                    
                    # Log NLG corrections to file
                    if self.corrections_file:
                        current_pose = self.get_current_pose()
                        pose_name = current_pose['name'] if current_pose else "Unknown"
                        timestamp = time.strftime("%H:%M:%S")
                        self.corrections_file.write(f"[{timestamp}] {pose_name}\n")
                        for correction in nlg_corrections:
                            self.corrections_file.write(f"  {correction}\n")
                        self.corrections_file.flush()  # Write immediately
                    
                    # SPEAK FEEDBACK OUT LOUD - BUT ONLY IF DEBUG VALUES SHOW POSE IS WRONG
                    if debug_info:
                        exact_match = debug_info.get('exact_match', False)
                        can_start_timer = debug_info.get('can_start_timer', False)
                        pose_confidence = debug_info.get('pose_confidence', 0.0)
                        
                        # Only speak if pose is REALLY wrong AND form is dangerous (important feedback only)
                        # Only speak for dangerous corrections, not minor improvements
                        if (not exact_match and not can_start_timer and pose_confidence < 0.05 and 
                            critical_status == 'dangerous'):  # Only speak for dangerous corrections
                            feedback_key = f"{status}:{feedback_text[:50]}"  # Create unique key
                            if self.tts and feedback_key not in self.feedback_already_spoken:
                                current_time = time.time()
                                if (current_time - self.last_spoken_time) >= self.feedback_speak_cooldown:
                                    self.tts.speak_simple(feedback_text, voice="arcas")
                                    self.feedback_already_spoken.add(feedback_key)
                                    self.last_spoken_feedback = feedback_text
                                    self.last_spoken_time = current_time
                                    pass  # Voice correction
                        else:
                            pass  # Minor correction
                    else:
                        pass  # No debug_info
                else:
                    # No critical feedback to speak - just print
                    feedback_text = " ".join([c.replace("💡", "").replace("⚠️", "").replace("✅", "").strip() for c in nlg_corrections])
                    status_emoji = "🟡" if status == 'improvable' else "🔴" if status == 'dangerous' else "⚪"
                    pass  # Non-critical feedback
            else:
                # Fallback to basic feedback
                angle_feedback = form_feedback.get('feedback', {})
                if angle_feedback:
                    # Only get the MOST CRITICAL feedback (highest deviation, >= 15 degrees)
                    sorted_feedback = sorted(
                        angle_feedback.items(),
                        key=lambda x: x[1].get('deviation', 0),
                        reverse=True
                    )
                    
                    # Filter to only significant deviations (>= 15 degrees) or dangerous status
                    critical_feedback = []
                    for angle_name, angle_info in sorted_feedback:
                        deviation = angle_info.get('deviation', 0)
                        angle_status = angle_info.get('status', 'improvable')
                        # Only include if deviation >= 15 degrees OR dangerous status
                        if (deviation >= 15.0 or angle_status == 'dangerous') and angle_status != 'correct':
                            critical_feedback.append((angle_name, angle_info))
                            if len(critical_feedback) >= 1:  # Only take the top 1 most critical
                                break
                    
                    if critical_feedback:
                        # Get the most critical one
                        angle_name, angle_info = critical_feedback[0]
                        msg = angle_info.get('message', '')
                        feedback_text = msg.replace("💡", "").replace("⚠️", "").replace("✅", "").strip()
                        
                        # DEBUG: Print feedback
                        status_emoji = "🟡" if angle_info.get('status') == 'improvable' else "🔴" if angle_info.get('status') == 'dangerous' else "⚪"
                        pass  # Angle feedback
                        
                        # SPEAK FEEDBACK OUT LOUD - BUT ONLY IF DEBUG VALUES SHOW POSE IS WRONG
                        if debug_info:
                            exact_match = debug_info.get('exact_match', False)
                            can_start_timer = debug_info.get('can_start_timer', False)
                            pose_confidence = debug_info.get('pose_confidence', 0.0)
                            
                            # Only speak if pose is REALLY wrong AND form is dangerous (important only)
                            angle_status = angle_info.get('status', 'improvable')
                            if (not exact_match and not can_start_timer and pose_confidence < 0.05 and 
                                angle_status == 'dangerous'):  # Only speak for dangerous corrections
                                feedback_key = f"{angle_info.get('status')}:{feedback_text[:50]}"
                                if self.tts and feedback_key not in self.feedback_already_spoken:
                                    current_time = time.time()
                                    if (current_time - self.last_spoken_time) >= self.feedback_speak_cooldown:
                                        self.tts.speak_simple(feedback_text, voice="arcas")
                                        self.feedback_already_spoken.add(feedback_key)
                                        self.last_spoken_feedback = feedback_text
                                        self.last_spoken_time = current_time
                                        pass  # Voice correction
                            else:
                                pass  # Minor correction
                        else:
                            # No debug_info - skip speaking to avoid false corrections
                            pass
                    else:
                        # No critical feedback - don't speak, just print
                        feedback_text = "Small adjustments needed (not spoken - not critical enough)"
                        print(f"🟡 [{status.upper()}] {feedback_text}")
                else:
                    feedback_text = "Adjust your form"
                    print(f"⚪ [UNKNOWN] {feedback_text}")
        else:
            feedback_text = "Good form! Hold steady."
            print(f"🟢 [CORRECT] {feedback_text}")
        
        # Store feedback text for display (but we won't display it - only speak it)
        feedback_msg = ""  # Empty - we don't show text, only speak
        
        # Main instruction - ONLY TIMER (no text feedback, that's spoken)
        if pose_complete:
            # Speak completion message (only once)
            if self.tts and not hasattr(self, '_completion_spoken'):
                completion_msg = f"{pose_name.replace('_', ' ')} complete! Great job."
                self.tts.speak_simple(completion_msg, voice="arcas")
                self._completion_spoken = True
                self.last_spoken_time = time.time()
            
            # Return only timer (no text feedback)
            return f"{current_hold:.1f}s / {target_hold}s"
        else:
            # Return only timer (no text feedback - all feedback is spoken)
            timer_msg = f"{current_hold:.1f}s / {target_hold}s"
            if remaining > 0:
                timer_msg += f"\n{remaining:.1f}s remaining"
            
            return timer_msg
    
    def next_pose(self):
        """Move to next pose - RESET ALL STATE AND FORCE NEW POSE DETECTION"""
        if self.current_program:
            # Stop current timer completely (save any time before moving to next pose)
            if self.hold_start_time is not None:
                # Save any accumulated time before stopping
                self.accumulated_hold_time = time.time() - self.hold_start_time + self.accumulated_hold_time
                self.hold_start_time = None
            
            # Reset elapsed time tracking for new pose
            if hasattr(self, '_last_elapsed_time'):
                self._last_elapsed_time = 0
            
            # Reset completion flag for new pose
            if hasattr(self, '_completion_spoken'):
                self._completion_spoken = False
            
            # Move to next pose
            self.current_pose_index += 1
            
            # FORCE RESET ALL POSE DETECTION STATE - Model will search for new pose
            self.in_pose = False
            self.pose_entered = False
            self.pose_stability_frames = []  # Clear stability tracking
            self.pose_confidence_history = []  # Clear confidence history
            self.smoothed_score = 0.0  # Reset smoothed score
            self.last_pose_name = None  # Clear last detected pose
            
            # ONLY reset timer when moving to NEXT pose (not during same pose)
            self.accumulated_hold_time = 0.0
            self.last_pause_time = None
            
            # Reset NLG engine for new pose (clear correction history)
            self.corrector.nlg.reset()
            
            # Reset instruction tracking for new pose
            self.instruction_spoken_for_pose = False
            self.current_pose_name_for_instruction = None
            
            # Reset feedback tracking for new pose
            self.feedback_already_spoken.clear()
            self.last_spoken_feedback = None
            self.last_spoken_time = 0.0
            
            # Reset color state for new pose
            if hasattr(self, 'pose_wrong_frames'):
                self.pose_wrong_frames = 0
            if hasattr(self, 'last_color_state'):
                self.last_color_state = None
            
            # Reset form status history
            if hasattr(self, 'form_status_history'):
                self.form_status_history = []
            
            # Moved to next pose
    
    def repeat_instruction(self):
        """Manually repeat the current pose instruction"""
        if self.current_program and self.current_pose_index < len(self.current_program['poses']):
            pose_name = self.current_program['poses'][self.current_pose_index]
            target_hold = self.current_program['hold_times'][self.current_pose_index]
            if self.tts:
                instruction = f"Get into {pose_name.replace('_', ' ')}. Hold for {int(target_hold)} seconds."
                self.tts.speak_simple(instruction, voice="arcas")
                # Repeating instruction
    
    def draw_guided_feedback(self, frame: np.ndarray, session_state: Dict, skip_keypoints: bool = False) -> np.ndarray:
        """Draw guided feedback on frame with large, readable text"""
        output = frame.copy()
        h, w = output.shape[:2]
        
        # Draw keypoints and skeleton connections (skip if MediaPipe already drew them)
        if not skip_keypoints:
            keypoints = session_state.get('keypoints')
            if keypoints is not None:
                # Ensure keypoints is a numpy array
                if not isinstance(keypoints, np.ndarray):
                    if isinstance(keypoints, list):
                        keypoints = np.array(keypoints, dtype=np.float32)
                    else:
                        keypoints = None
            
            if keypoints is not None and len(keypoints) > 0:
                # Define COMPLETE skeleton connections - ALL connections between keypoints
                    # This creates a full skeleton visualization connecting EVERY dot
                    skeleton_connections = [
                    # HEAD CONNECTIONS - Connect all head keypoints
                    (0, 1), (0, 2),      # nose to left_eye, nose to right_eye
                    (1, 3), (2, 4),      # left_eye to left_ear, right_eye to right_ear
                    (0, 5), (0, 6),      # nose to left_shoulder, nose to right_shoulder
                    
                    # UPPER BODY CONNECTIONS - Complete arm chains
                    (5, 6),              # left_shoulder to right_shoulder (chest)
                    (5, 7),              # left_shoulder to left_elbow
                    (7, 9),              # left_elbow to left_wrist
                    (6, 8),              # right_shoulder to right_elbow
                    (8, 10),             # right_elbow to right_wrist
                    
                    # TORSO CONNECTIONS - Connect shoulders to hips
                    (5, 11),             # left_shoulder to left_hip
                    (6, 12),             # right_shoulder to right_hip
                    (11, 12),            # left_hip to right_hip (pelvis)
                    
                    # LOWER BODY CONNECTIONS - Complete leg chains
                    (11, 13),            # left_hip to left_knee
                    (13, 15),            # left_knee to left_ankle
                    (12, 14),            # right_hip to right_knee
                    (14, 16),            # right_knee to right_ankle
                    ]
                    
                    # DRAW ALL SKELETON LINES FIRST (behind the keypoints for better visibility)
                    # This ensures every keypoint is connected to form a complete skeleton
                    for start_idx, end_idx in skeleton_connections:
                        if (start_idx < len(keypoints) and end_idx < len(keypoints)):
                            start_kp = keypoints[start_idx]
                            end_kp = keypoints[end_idx]
                            
                            # Only draw if both keypoints are visible (with lower threshold for skeleton)
                            if (start_kp[2] > 0.2 and end_kp[2] > 0.2):  # Lower threshold to show more connections
                                start_pt = (int(start_kp[0]), int(start_kp[1]))
                                end_pt = (int(end_kp[0]), int(end_kp[1]))
                                
                                # Determine line color based on body part for visual clarity
                                if start_idx in [0, 1, 2, 3, 4]:  # Head connections
                                    line_color = (255, 150, 255)  # Bright magenta
                                elif start_idx in [5, 6, 7, 8, 9, 10]:  # Upper body/arms
                                    line_color = (150, 255, 150)  # Bright green
                                elif start_idx in [11, 12, 13, 14, 15, 16]:  # Lower body/legs
                                    line_color = (150, 150, 255)  # Bright blue
                                else:
                                    line_color = (255, 255, 255)  # White
                                
                                # Draw thinner lines for cleaner look
                                # Black outline first (thinner)
                                cv2.line(output, start_pt, end_pt, (0, 0, 0), 3)  # Thinner outline (was 8)
                                # Colored line on top (thinner)
                                cv2.line(output, start_pt, end_pt, line_color, 2)  # Thinner line (was 6)
                    
                    # Keypoint colors for different body parts
                    keypoint_colors = {
                    # Head
                    0: (255, 0, 255),    # nose - magenta
                    1: (255, 100, 255),  # left_eye - light magenta
                    2: (255, 100, 255),  # right_eye - light magenta
                    3: (200, 0, 200),    # left_ear - purple
                    4: (200, 0, 200),    # right_ear - purple
                    # Upper body
                    5: (0, 255, 0),      # left_shoulder - green
                    6: (0, 255, 0),      # right_shoulder - green
                    7: (255, 255, 0),    # left_elbow - cyan
                    8: (255, 255, 0),    # right_elbow - cyan
                    9: (0, 255, 255),    # left_wrist - yellow
                    10: (0, 255, 255),   # right_wrist - yellow
                    # Lower body
                    11: (255, 0, 0),     # left_hip - blue
                    12: (255, 0, 0),     # right_hip - blue
                    13: (0, 165, 255),  # left_knee - orange
                    14: (0, 165, 255),  # right_knee - orange
                    15: (0, 0, 255),     # left_ankle - red
                    16: (0, 0, 255),    # right_ankle - red
                    }
                    
                    # DRAW KEYPOINTS AFTER LINES (so dots appear on top)
                    for i, (x, y, conf) in enumerate(keypoints):
                        if conf > config.POSE_CONFIDENCE_THRESHOLD:
                            x_int, y_int = int(x), int(y)
                            
                            # Get color for this keypoint
                            color = keypoint_colors.get(i, (255, 255, 255))  # Default white
                            
                            # Draw smaller circles for cleaner look
                            radius = 8  # Smaller (was 15)
                            thickness = -1  # Filled
                            
                            # Draw outer ring (black for contrast) - thinner
                            cv2.circle(output, (x_int, y_int), radius + 2, (0, 0, 0), 2)  # Thinner (was 4)
                            # Draw main circle
                            cv2.circle(output, (x_int, y_int), radius, color, thickness)
                            # Draw inner dot - smaller
                            cv2.circle(output, (x_int, y_int), 3, (255, 255, 255), -1)  # Smaller (was 6)
        
        # Draw ONLY TIMER (centered, large)
        instruction = session_state.get('instruction', '')
        if instruction:
            # Extract only timer lines (lines with numbers and "s" or "remaining")
            timer_lines = [line for line in instruction.split('\n') if ('s /' in line or 'remaining' in line or 'Hold for' in line)]
            
            if timer_lines:
                y_offset = h // 2  # Center vertically
                base_font_scale = max(1.2, h / 400)  # Large timer
                
                for line in timer_lines:
                    if line.strip():
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        font_scale = base_font_scale
                        thickness = 4
                        
                        (text_w, text_h), baseline = cv2.getTextSize(line, font, font_scale, thickness)
                        x = (w - text_w) // 2
                        
                        # Draw WHITE background
                        padding = 30
                        overlay = output.copy()
                        cv2.rectangle(overlay, (x - padding, y_offset - text_h - padding), 
                                     (x + text_w + padding, y_offset + padding), (255, 255, 255), -1)
                        cv2.addWeighted(overlay, 0.95, output, 0.05, 0, output)
                        
                        # Draw black border
                        cv2.rectangle(output, (x - padding, y_offset - text_h - padding), 
                                     (x + text_w + padding, y_offset + padding), (0, 0, 0), 4)
                        
                        # Draw timer text in BLACK
                        cv2.putText(output, line, (x, y_offset), font, font_scale, (0, 0, 0), thickness)
                        
                        y_offset += text_h + 40
        
        # Draw pose info (top left) - Simple, minimal
        current_pose = session_state.get('current_pose')
        current_pose_index = session_state.get('current_pose_index', 0)
        
        # Handle current_pose - it might be a string (pose name) or dict
        if current_pose:
            if isinstance(current_pose, dict):
                pose_index = current_pose.get('index', current_pose_index)
                pose_total = current_pose.get('total', 0)
                info_text = f"Pose {pose_index + 1}/{pose_total}"
            else:
                # Just show the pose name if it's a string
                info_text = str(current_pose).replace('_', ' ')
            
            font_scale = max(0.6, h / 800)
            thickness = 2
            (text_w, text_h), _ = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
            
            # Draw simple white background
            overlay = output.copy()
            cv2.rectangle(overlay, (10, 10), (10 + text_w + 20, 10 + text_h + 20), (255, 255, 255), -1)
            cv2.addWeighted(overlay, 0.9, output, 0.1, 0, output)
            cv2.rectangle(output, (10, 10), (10 + text_w + 20, 10 + text_h + 20), (0, 0, 0), 2)
            cv2.putText(output, info_text, (20, text_h + 25), cv2.FONT_HERSHEY_SIMPLEX, 
                      font_scale, (0, 0, 0), thickness)
        
        # Draw POSE IMAGE (top right) - Show reference image for current pose
        if current_pose:
            # Handle both string and dict formats
            if isinstance(current_pose, dict):
                pose_name = current_pose.get('name', '')
            else:
                pose_name = str(current_pose)
            pose_image_path = self.program_manager.get_pose_image_path(pose_name)
            
            if pose_image_path and os.path.exists(pose_image_path):
                try:
                    pose_img = cv2.imread(pose_image_path)
                    if pose_img is not None:
                        # Resize to fit in top right corner
                        img_height = 200
                        img_width = int(pose_img.shape[1] * (img_height / pose_img.shape[0]))
                        pose_img_resized = cv2.resize(pose_img, (img_width, img_height))
                        
                        # Position in top right
                        x_offset = w - img_width - 20
                        y_offset = 10
                        
                        # Draw white background
                        overlay = output.copy()
                        cv2.rectangle(overlay, (x_offset - 10, y_offset - 10), 
                                     (x_offset + img_width + 10, y_offset + img_height + 10), 
                                     (255, 255, 255), -1)
                        cv2.addWeighted(overlay, 0.9, output, 0.1, 0, output)
                        
                        # Draw border
                        cv2.rectangle(output, (x_offset - 10, y_offset - 10), 
                                     (x_offset + img_width + 10, y_offset + img_height + 10), 
                                     (0, 0, 0), 2)
                        
                        # Place image
                        output[y_offset:y_offset + img_height, x_offset:x_offset + img_width] = pose_img_resized
                except Exception as e:
                    pass  # Silently fail if image can't be loaded
        
        # Draw SIMPLE COLOR INDICATOR (bottom center) - Green if correct pose, Red if wrong
        form_feedback = session_state.get('form_feedback')
        in_pose = session_state.get('in_pose', False)
        detected_pose = session_state.get('detected_pose')
        
        if form_feedback and current_pose:
            status = session_state.get('smoothed_form_status', form_feedback.get('overall_status', 'unknown'))
            # Handle both string and dict formats
            if isinstance(current_pose, dict):
                target_pose = current_pose.get('name', '')
            else:
                target_pose = str(current_pose)
            
            # Check if doing the correct pose
            pose_correct = (in_pose and detected_pose and 
                          (detected_pose == target_pose or 
                           detected_pose.lower().replace('_', ' ') in target_pose.lower().replace('_', ' ') or
                           target_pose.lower().replace('_', ' ') in detected_pose.lower().replace('_', ' ')))
            
            # Simple color indicator - LARGE circle at bottom center
            # WITH HYSTERESIS: Once green, stay green longer (don't switch to red easily)
            indicator_size = 80  # Large circle
            indicator_x = w // 2
            indicator_y = h - 100
            
            # Determine desired color based on pose and status
            if pose_correct:
                # GREEN if correct pose (yellow/improvable also shows as green)
                desired_color = (0, 255, 0)  # Green
            else:
                # RED if wrong pose
                desired_color = (0, 0, 255)  # Red
            
            # Apply hysteresis: if we were green, require more evidence to switch to red
            if self.last_color_state == 'green' and desired_color == (0, 0, 255):
                # Was green, now wants red - require pose to be wrong for multiple frames
                if not hasattr(self, 'pose_wrong_frames'):
                    self.pose_wrong_frames = 0
                if not pose_correct:
                    self.pose_wrong_frames += 1
                    # Require 15 frames of wrong pose before switching to red (more stable)
                    if self.pose_wrong_frames < 15:
                        color = (0, 255, 0)  # Keep green
                    else:
                        color = (0, 0, 255)  # Switch to red
                        self.last_color_state = 'red'
                        self.pose_wrong_frames = 0
                else:
                    # Pose is correct again, reset counter
                    self.pose_wrong_frames = 0
                    color = desired_color
                    if color == (0, 255, 0):
                        self.last_color_state = 'green'
                        self.color_green_frames += 1
            else:
                # Normal transition or was red
                color = desired_color
                if color == (0, 255, 0):
                    self.last_color_state = 'green'
                    self.color_green_frames += 1
                    if hasattr(self, 'pose_wrong_frames'):
                        self.pose_wrong_frames = 0
                else:
                    self.last_color_state = 'red'
                    if hasattr(self, 'pose_wrong_frames'):
                        self.pose_wrong_frames = 0
            
            # Draw large colored circle
            cv2.circle(output, (indicator_x, indicator_y), indicator_size, color, -1)
            cv2.circle(output, (indicator_x, indicator_y), indicator_size, (0, 0, 0), 5)  # Black border
            
            # Draw "Press R to repeat" hint (small, bottom left)
            hint_text = "Press 'R' to repeat instruction"
            hint_font_scale = 0.5
            hint_thickness = 1
            (hint_w, hint_h), _ = cv2.getTextSize(hint_text, cv2.FONT_HERSHEY_SIMPLEX, hint_font_scale, hint_thickness)
            hint_x = 20
            hint_y = h - 20
            
            # White background for hint
            overlay_hint = output.copy()
            cv2.rectangle(overlay_hint, (hint_x - 5, hint_y - hint_h - 5), 
                         (hint_x + hint_w + 5, hint_y + 5), (255, 255, 255), -1)
            cv2.addWeighted(overlay_hint, 0.8, output, 0.2, 0, output)
            
            # Draw hint text
            cv2.putText(output, hint_text, (hint_x, hint_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, hint_font_scale, (0, 0, 0), hint_thickness)
        
        return output
    
    def run_guided_session(self, program_name: str, camera_id: int = None):
        """Run a guided yoga session"""
        # Start program
        self.start_program(program_name)
        
        # Setup camera
        if camera_id is None:
            cameras = self.list_cameras()
            if not cameras:
                pass  # No cameras
                return
            camera_id = cameras[0] if len(cameras) == 1 else int(input(f"Select camera {cameras}: "))
        
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            pass  # Camera error
            return
        
        # Set camera to higher resolution for larger window
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        
        # Create resizable window
        cv2.namedWindow('YogaBuddy - Guided Session', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('YogaBuddy - Guided Session', 1920, 1080)
        
        # Camera ready
        # Controls available
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame
            session_state = self.process_frame(frame)
            
            # Check if program complete
            if session_state['status'] == 'complete':
                pass  # Program complete
                self._close_corrections_file()
                break
            
            # Auto-advance if pose complete
            if session_state.get('pose_complete'):
                time.sleep(2)  # Show completion for 2 seconds
                self.next_pose()
                if self.current_pose_index >= len(self.current_program['poses']):
                    pass  # Program complete
                    self._close_corrections_file()
                    break
            
            # Draw feedback
            output = self.draw_guided_feedback(frame, session_state)
            
            # Display
            cv2.imshow('YogaBuddy - Guided Session', output)
            
            key = cv2.waitKey(1)
            
            # Quit
            if key == ord('q') or key == 27:  # 'q' or ESC
                self._close_corrections_file()
                break
            
            # Repeat instruction - 'r' key
            elif key == ord('r'):
                self.repeat_instruction()
            
            # Next pose - 'n' key
            elif key == ord('n'):
                self.next_pose()
                pass  # Moving to next pose
            
            # Handle arrow keys - they come as special codes
            # Check without masking first (arrow keys are > 255)
            elif key != -1:
                # Right arrow key codes vary by system
                # macOS/Linux: often 83 or 65363, Windows: 77 or 2555904
                if key == 83 or key == 65363 or (key & 0xFF) == 83:
                    self.next_pose()
                    pass  # Moving to next pose
                # Also check masked version
                elif (key & 0xFF) == 77:  # Windows right arrow
                    self.next_pose()
                    pass  # Moving to next pose
        
        cap.release()
        cv2.destroyAllWindows()
        
        # Close corrections file if still open
        self._close_corrections_file()
        
        # Print summary with enhanced metrics
        # Session summary
        stats = self.tracker.get_session_stats()
        
        # Display key metrics
        # Session stats removed - console only shows timer
        pass
    
    def _close_corrections_file(self):
        """Close the corrections log file and write summary"""
        if self.corrections_file:
            # Write summary
            self.corrections_file.write(f"\n{'='*60}\n")
            self.corrections_file.write(f"Session Ended: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            if self.session_start_time:
                duration = time.time() - self.session_start_time
                self.corrections_file.write(f"Duration: {duration:.1f} seconds\n")
            stats = self.tracker.get_session_stats()
            self.corrections_file.write(f"Total Corrections: {stats['corrections_count']}\n")
            self.corrections_file.write(f"Critical Errors: {stats.get('dangerous_corrections', 0)}\n")
            self.corrections_file.write(f"Improvements: {stats.get('improvable_corrections', 0)}\n")
            self.corrections_file.write(f"Final Score: {self.tracker.calculate_progress_score():.1f}/100\n")
            self.corrections_file.write(f"{'='*60}\n")
            self.corrections_file.close()
            self.corrections_file = None
            pass  # Corrections log saved
    
    def list_cameras(self):
        """List available cameras"""
        available = []
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available.append(i)
                cap.release()
        return available

