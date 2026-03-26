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
    def __init__(self, classifier_path: Optional[str] = None, templates_dir: Optional[str] = None):
        self.detector = PoseDetector()
        self.classifier = PoseClassifier()
        self.corrector = FormCorrector(templates_dir)
        self.tracker = SessionTracker()
        self.program_manager = YogaProgram()
        try:
            self.tts = TTSClient(backend_url="http://localhost:5001/speak", voice="arcas")
            pass
        except Exception as e:
            pass
            self.tts = None
        self.last_spoken_feedback = None
        self.last_spoken_time = 0.0
        self.feedback_speak_cooldown = 30.0
        self.feedback_already_spoken = set()
        self.instruction_spoken_for_pose = False
        self.current_pose_name_for_instruction = None
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
        self.accumulated_hold_time = 0.0
        self.last_pause_time = None
        self.paused = False
        self.corrections_log = []
        self.corrections_file = None
        self.session_start_time = None
        self.pose_confidence_history = []
        self.confidence_history_size = 10
        self.smoothed_score = 0.0
        self.alpha = 0.4
        self.form_status_history = []
        self.form_status_history_size = 12
        self.smoothed_form_status = 'unknown'
        self.form_status_consistency_required = 8
        self.current_form_status_count = 0
        self.last_color_state = 'unknown'
        self.color_green_frames = 0
        self.pose_stability_frames = []
        self.stability_required = 3
        self.last_pose_confidence = 0.0
        self.last_angle_similarity = 0.0
        self.last_combined_score = 0.0
        self.last_exact_match = False
        self.last_can_start_timer = False
        self.last_has_template = False
    def start_program(self, program_name: str):
        program = self.program_manager.get_program(program_name)
        if not program:
            raise ValueError(f"Program '{program_name}' not found")
        self.current_program = program
        self.current_pose_index = 0
        self.in_pose = False
        self.pose_entered = False
        self.accumulated_hold_time = 0.0
        self.last_pause_time = None
        self.instruction_spoken_for_pose = False
        self.current_pose_name_for_instruction = None
        self.feedback_already_spoken.clear()
        self.last_spoken_feedback = None
        self.last_spoken_time = 0.0
        self.last_color_state = 'unknown'
        self.color_green_frames = 0
        if hasattr(self, 'pose_wrong_frames'):
            self.pose_wrong_frames = 0
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
    def get_current_pose(self) -> Optional[Dict]:
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
        keypoints = self.detector.detect_pose(frame)
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
        distance_status = 'optimal'
        distance_msg = "✅ Ready"
        is_optimal_distance = True
        body_fully_visible = True
        visibility_message = ""
        if keypoints is not None:
            low_threshold = 0.2
            head_visible = (keypoints[0][2] > low_threshold or
                          keypoints[1][2] > low_threshold or
                          keypoints[2][2] > low_threshold)
            shoulders_visible = (keypoints[5][2] > low_threshold or
                                keypoints[6][2] > low_threshold)
            hips_visible = (keypoints[11][2] > low_threshold or
                           keypoints[12][2] > low_threshold)
            knees_visible = (keypoints[13][2] > low_threshold or
                            keypoints[14][2] > low_threshold)
            ankles_visible = (keypoints[15][2] > low_threshold or
                             keypoints[16][2] > low_threshold)
            visible_parts = sum([head_visible, shoulders_visible, hips_visible, knees_visible, ankles_visible])
            body_fully_visible = visible_parts >= 2
            any_keypoints = any(kp[2] > 0.15 for kp in keypoints if len(kp) > 2)
            if any_keypoints and visible_parts < 2:
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
        current_pose_info = self.get_current_pose()
        if current_pose_info is None:
            return {
                'status': 'complete',
                'message': '🎉 Program complete!',
                'keypoints': keypoints,
                'distance_status': distance_status,
                'distance_msg': distance_msg
            }
        detected_pose = None
        confidence = 0.0
        form_feedback = None
        if keypoints is not None:
            confidence = self.detector.get_pose_confidence(keypoints)
            if confidence >= config.POSE_CONFIDENCE_THRESHOLD:
                try:
                    has_template = False
                    detected_pose, pose_confidence = self.classifier.predict(keypoints)
                    confidence = pose_confidence
                    target_pose = current_pose_info['name']
                    form_feedback = self.corrector.correct_form(keypoints, detected_pose)
                    has_template = form_feedback.get('has_template', False)
                    if not has_template:
                        form_feedback_target = self.corrector.correct_form(keypoints, target_pose)
                        if form_feedback_target.get('has_template', False):
                            form_feedback = form_feedback_target
                            has_template = True if form_feedback else False
                    if not body_fully_visible:
                        confidence = pose_confidence * 0.8
                    if body_fully_visible and has_template:
                        angle_similarity = 0.0
                        angle_feedback = form_feedback.get('feedback', {})
                        if angle_feedback:
                            avg_weighted_deviation = form_feedback.get('avg_weighted_deviation', 100.0)
                            num_angles = len(angle_feedback)
                            max_deviation = 40.0 + (num_angles * 2.2)
                            angle_similarity = max(0.0, min(1.0, 1.0 - (avg_weighted_deviation / max_deviation)))
                            correct_count = sum(1 for fb in angle_feedback.values() if fb.get('status') == 'correct')
                            total_count = len(angle_feedback)
                            correct_ratio = correct_count / total_count if total_count > 0 else 0.0
                            if correct_ratio >= 0.60:
                                critical_correct = sum(1 for fb in angle_feedback.values()
                                                     if fb.get('weight', 1.0) >= 2.0 and fb.get('status') == 'correct')
                                total_critical = sum(1 for fb in angle_feedback.values()
                                                   if fb.get('weight', 1.0) >= 2.0)
                                if total_critical > 0:
                                    critical_ratio = critical_correct / total_critical
                                    angle_similarity = min(1.0, angle_similarity + (critical_ratio * 0.1))
                            else:
                                angle_similarity = angle_similarity * 0.80
                    else:
                        angle_similarity = 0.0
                    target_normalized = target_pose.lower().replace('_', ' ').replace('-', ' ').replace('(', '').replace(')', '').replace('or', '').strip()
                    detected_normalized = detected_pose.lower().replace('_', ' ').replace('-', ' ').replace('(', '').replace(')', '').replace('or', '').strip()
                    target_words = set([w for w in target_normalized.split() if len(w) > 2])
                    detected_words = set([w for w in detected_normalized.split() if len(w) > 2])
                    word_overlap = len(target_words & detected_words) / max(len(target_words), 1) if target_words else 0.0
                    exact_match = (
                        detected_pose == target_pose or
                        target_pose in detected_pose or
                        detected_pose in target_pose or
                        word_overlap >= 0.5
                    )
                    combined_score = (pose_confidence * 0.5) + (angle_similarity * 0.5)
                    form_status = form_feedback.get('overall_status', 'unknown') if form_feedback else 'unknown'
                    if form_feedback:
                        current_form_status = form_feedback.get('overall_status', 'unknown')
                        self.form_status_history.append(current_form_status)
                        if len(self.form_status_history) > self.form_status_history_size:
                            self.form_status_history.pop(0)
                        if len(self.form_status_history) >= 5:
                            status_counts = {}
                            for status in self.form_status_history:
                                status_counts[status] = status_counts.get(status, 0) + 1
                            most_common_status = max(status_counts.items(), key=lambda x: x[1])[0]
                            most_common_count = status_counts[most_common_status]
                            if most_common_status == self.smoothed_form_status:
                                self.current_form_status_count += 1
                            else:
                                if most_common_count >= (len(self.form_status_history) * 0.6):
                                    if self.current_form_status_count >= self.form_status_consistency_required:
                                        self.smoothed_form_status = most_common_status
                                        self.current_form_status_count = 1
                                    else:
                                        self.current_form_status_count = 0
                                else:
                                    self.current_form_status_count = 0
                        else:
                            if current_form_status == self.smoothed_form_status:
                                self.current_form_status_count += 1
                            else:
                                self.smoothed_form_status = current_form_status
                                self.current_form_status_count = 1
                    else:
                        self.smoothed_form_status = 'unknown'
                        self.current_form_status_count = 0
                    smoothed_status = self.smoothed_form_status
                    is_matching_pose = (
                        exact_match and
                        has_template and
                        pose_confidence >= 0.12 and
                        angle_similarity >= 0.25 and
                        combined_score >= 0.20 and
                        smoothed_status != 'dangerous'
                    )
                    self.pose_confidence_history.append(combined_score)
                    if len(self.pose_confidence_history) > self.confidence_history_size:
                        self.pose_confidence_history.pop(0)
                    if self.smoothed_score == 0.0:
                        self.smoothed_score = combined_score
                    else:
                        self.smoothed_score = (self.alpha * combined_score) + ((1 - self.alpha) * self.smoothed_score)
                    simple_avg = sum(self.pose_confidence_history) / len(self.pose_confidence_history) if self.pose_confidence_history else combined_score
                    smoothed_score = min(self.smoothed_score, simple_avg)
                    can_start_timer = (
                        exact_match and
                        has_template and
                        pose_confidence >= 0.10 and
                        (angle_similarity >= 0.18 or combined_score >= 0.18)
                    )
                    self.last_pose_confidence = pose_confidence
                    self.last_angle_similarity = angle_similarity
                    self.last_combined_score = combined_score
                    self.last_exact_match = exact_match
                    self.last_can_start_timer = can_start_timer
                    self.last_has_template = has_template
                    if is_matching_pose and smoothed_score >= 0.20 and combined_score >= 0.20:
                        self.pose_stability_frames.append(True)
                        if len(self.pose_stability_frames) > self.stability_required:
                            self.pose_stability_frames.pop(0)
                        is_stable = len(self.pose_stability_frames) >= self.stability_required
                        if is_stable:
                            if not self.pose_entered:
                                self.pose_entered = True
                                if self.last_pause_time is not None:
                                    self.last_pause_time = None
                                if self.hold_start_time is None:
                                    self.hold_start_time = time.time() - self.accumulated_hold_time
                            if self.hold_start_time is None and self.accumulated_hold_time > 0:
                                self.hold_start_time = time.time() - self.accumulated_hold_time
                            self.in_pose = True
                        else:
                            if self.in_pose or self.hold_start_time is not None:
                                self.accumulated_hold_time = 0.0
                                self.hold_start_time = None
                            self.in_pose = False
                    elif can_start_timer:
                        self.pose_entered = True
                        if self.last_pause_time is not None:
                            self.last_pause_time = None
                        if self.hold_start_time is None:
                            if self.accumulated_hold_time > 0:
                                self.hold_start_time = time.time() - self.accumulated_hold_time
                            else:
                                self.hold_start_time = time.time()
                        self.in_pose = True
                    else:
                        self.pose_stability_frames.append(False)
                        if len(self.pose_stability_frames) > self.stability_required:
                            self.pose_stability_frames.pop(0)
                        if self.pose_entered:
                            unstable_frames = sum(1 for x in self.pose_stability_frames if not x)
                            is_unstable = unstable_frames >= self.stability_required
                            should_exit = (
                                (smoothed_score < 0.05 or
                                 combined_score < 0.05 or
                                 angle_similarity < 0.08 or
                                 smoothed_status == 'dangerous') and
                                is_unstable
                            )
                            if should_exit:
                                self.accumulated_hold_time = 0.0
                                self.hold_start_time = None
                                self.last_pause_time = None
                                self.in_pose = False
                                self.pose_stability_frames = []
                                if len(self.pose_confidence_history) > 0:
                                    self.pose_confidence_history = self.pose_confidence_history[-5:]
                                self.smoothed_score = max(0.0, self.smoothed_score * 0.5)
                            else:
                                self.in_pose = True
                                if self.hold_start_time is None and self.accumulated_hold_time > 0:
                                    self.hold_start_time = time.time() - self.accumulated_hold_time
                        else:
                            if self.in_pose or self.hold_start_time is not None:
                                self.accumulated_hold_time = 0.0
                                self.hold_start_time = None
                            self.in_pose = False
                            if smoothed_score < 0.05:
                                self.pose_stability_frames = []
                except Exception as e:
                    pass
        if not self.in_pose and (self.hold_start_time is not None or self.accumulated_hold_time > 0):
            self.accumulated_hold_time = 0.0
            self.hold_start_time = None
        current_hold = self.accumulated_hold_time
        if self.hold_start_time:
            current_hold += (time.time() - self.hold_start_time)
        if self.in_pose and self.hold_start_time is not None:
            elapsed_seconds = int(current_hold)
            if not hasattr(self, '_last_logged_second'):
                self._last_logged_second = -1
            if elapsed_seconds != self._last_logged_second:
                self._last_logged_second = elapsed_seconds
                print(f"⏱️  {elapsed_seconds}s")
        target_hold = current_pose_info['target_hold']
        pose_complete = current_hold >= target_hold and self.in_pose
        if detected_pose and form_feedback:
            self.tracker.update(
                detected_pose,
                confidence,
                form_feedback,
                target_hold_time=target_hold
            )
        debug_info = {}
        debug_info = {
            'body_fully_visible': body_fully_visible,
            'stability_frames': len(self.pose_stability_frames),
            'stability_required': self.stability_required,
            'smoothed_score': round(self.smoothed_score, 3),
        }
        if detected_pose is not None:
            try:
                target_pose = current_pose_info['name']
                pose_confidence = self.last_pose_confidence
                angle_similarity = self.last_angle_similarity
                combined_score = self.last_combined_score
                exact_match = self.last_exact_match
                can_start_timer = self.last_can_start_timer
                has_template = self.last_has_template
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
            debug_info
        )
        return {
            'status': 'in_progress',
            'current_pose': current_pose_info,
            'keypoints': keypoints,
            'detected_pose': detected_pose,
            'confidence': confidence,
            'form_feedback': form_feedback,
            'smoothed_form_status': self.smoothed_form_status,
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
            'debug_info': debug_info
        }
    def _generate_instruction(self, pose_info, is_optimal_distance, distance_msg,
                             detected_pose, confidence, form_feedback,
                             current_hold, target_hold, pose_complete,
                             body_fully_visible=True, visibility_message="", debug_info=None) -> str:
        pose_name = pose_info['name'].replace('_', ' ').replace('or', '|')
        target_pose = pose_info['name']
        visibility_prefix = ""
        if not body_fully_visible and visibility_message:
            visibility_prefix = f"{visibility_message}\n\n"
        if not detected_pose:
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
        target_normalized = target_pose.lower().replace('_', ' ').replace('-', ' ').replace('(', '').replace(')', '')
        detected_normalized = detected_pose.lower().replace('_', ' ').replace('-', ' ').replace('(', '').replace(')', '')
        target_words = set(target_normalized.split())
        detected_words = set(detected_normalized.split())
        word_overlap = len(target_words & detected_words) / max(len(target_words), 1)
        is_similar = (word_overlap > 0.3 or
                     target_normalized in detected_normalized or
                     detected_normalized in target_normalized)
        if debug_info:
            exact_match = debug_info.get('exact_match', False)
            pose_confidence = debug_info.get('pose_confidence', 0.0)
            angle_similarity = debug_info.get('angle_similarity', 0.0)
            can_start_timer = debug_info.get('can_start_timer', False)
            has_template = debug_info.get('has_template', False)
            if exact_match or can_start_timer:
                pass
            elif detected_pose and not exact_match and pose_confidence < 0.05:
                if self.tts and (time.time() - self.last_spoken_time) >= self.feedback_speak_cooldown:
                    correction = f"Please move to {pose_name.replace('_', ' ')}."
                    self.tts.speak_simple(correction, voice="arcas")
                    self.last_spoken_time = time.time()
                    pass
            elif can_start_timer and self.in_pose:
                if self.tts and (time.time() - self.last_spoken_time) > 60.0:
                    feedback = "Great job. Keep holding."
                    self.tts.speak_simple(feedback, voice="arcas")
                    self.last_spoken_time = time.time()
                    pass
        if not self.in_pose or (is_similar and not self.in_pose):
            return f"{current_hold:.1f}s / {target_hold}s"
        remaining = max(0, target_hold - current_hold)
        progress_pct = min(100, (current_hold / target_hold) * 100)
        if debug_info:
            exact_match = debug_info.get('exact_match', False)
            pose_confidence = debug_info.get('pose_confidence', 0.0)
            angle_similarity = debug_info.get('angle_similarity', 0.0)
            can_start_timer = debug_info.get('can_start_timer', False)
            if can_start_timer or exact_match:
                if form_feedback and form_feedback.get('has_template'):
                    status = form_feedback.get('overall_status', 'unknown')
                    if status == 'correct' and self.tts and (time.time() - self.last_spoken_time) > 60.0:
                        feedback_text = "Excellent form. Keep going."
                        self.tts.speak_simple(feedback_text, voice="arcas")
                        self.last_spoken_time = time.time()
                        pass
        if form_feedback and form_feedback.get('has_template'):
            status = form_feedback.get('overall_status', 'unknown')
            nlg_corrections = form_feedback.get('nlg_corrections', [])
            nlg_summary = form_feedback.get('nlg_summary', '')
            if status == 'correct':
                feedback_text = "Perfect form! Keep holding."
                pass
            elif nlg_corrections:
                angle_feedback = form_feedback.get('feedback', {})
                most_critical = None
                max_deviation = 0
                max_weighted_deviation = 0
                critical_status = None
                critical_angle_name = None
                if angle_feedback:
                    for angle_name, angle_info in angle_feedback.items():
                        deviation = angle_info.get('deviation', 0)
                        weighted_deviation = angle_info.get('weighted_deviation', 0)
                        angle_status = angle_info.get('status', 'improvable')
                        if deviation >= 15.0 and angle_status != 'correct':
                            if weighted_deviation > max_weighted_deviation or (weighted_deviation == max_weighted_deviation and deviation > max_deviation):
                                max_weighted_deviation = weighted_deviation
                                max_deviation = deviation
                                critical_angle_name = angle_name
                                critical_status = angle_status
                if critical_angle_name:
                    for corr in nlg_corrections:
                        if (critical_angle_name.lower() in corr.lower() or
                            angle_feedback[critical_angle_name].get('message', '').lower() in corr.lower()):
                            most_critical = corr
                            break
                    if not most_critical and nlg_corrections:
                        most_critical = nlg_corrections[0]
                if most_critical:
                    feedback_text = most_critical.replace("💡", "").replace("⚠️", "").replace("✅", "").strip()
                    status_emoji = "🟡" if critical_status == 'improvable' else "🔴" if critical_status == 'dangerous' else "⚪"
                    pass
                    if nlg_corrections:
                        pass
                    if self.corrections_file:
                        current_pose = self.get_current_pose()
                        pose_name = current_pose['name'] if current_pose else "Unknown"
                        timestamp = time.strftime("%H:%M:%S")
                        self.corrections_file.write(f"[{timestamp}] {pose_name}\n")
                        for correction in nlg_corrections:
                            self.corrections_file.write(f"  {correction}\n")
                        self.corrections_file.flush()
                    if debug_info:
                        exact_match = debug_info.get('exact_match', False)
                        can_start_timer = debug_info.get('can_start_timer', False)
                        pose_confidence = debug_info.get('pose_confidence', 0.0)
                        if (not exact_match and not can_start_timer and pose_confidence < 0.05 and
                            critical_status == 'dangerous'):
                            feedback_key = f"{status}:{feedback_text[:50]}"
                            if self.tts and feedback_key not in self.feedback_already_spoken:
                                current_time = time.time()
                                if (current_time - self.last_spoken_time) >= self.feedback_speak_cooldown:
                                    self.tts.speak_simple(feedback_text, voice="arcas")
                                    self.feedback_already_spoken.add(feedback_key)
                                    self.last_spoken_feedback = feedback_text
                                    self.last_spoken_time = current_time
                                    pass
                        else:
                            pass
                    else:
                        pass
                else:
                    feedback_text = " ".join([c.replace("💡", "").replace("⚠️", "").replace("✅", "").strip() for c in nlg_corrections])
                    status_emoji = "🟡" if status == 'improvable' else "🔴" if status == 'dangerous' else "⚪"
                    pass
            else:
                angle_feedback = form_feedback.get('feedback', {})
                if angle_feedback:
                    sorted_feedback = sorted(
                        angle_feedback.items(),
                        key=lambda x: x[1].get('deviation', 0),
                        reverse=True
                    )
                    critical_feedback = []
                    for angle_name, angle_info in sorted_feedback:
                        deviation = angle_info.get('deviation', 0)
                        angle_status = angle_info.get('status', 'improvable')
                        if (deviation >= 15.0 or angle_status == 'dangerous') and angle_status != 'correct':
                            critical_feedback.append((angle_name, angle_info))
                            if len(critical_feedback) >= 1:
                                break
                    if critical_feedback:
                        angle_name, angle_info = critical_feedback[0]
                        msg = angle_info.get('message', '')
                        feedback_text = msg.replace("💡", "").replace("⚠️", "").replace("✅", "").strip()
                        status_emoji = "🟡" if angle_info.get('status') == 'improvable' else "🔴" if angle_info.get('status') == 'dangerous' else "⚪"
                        pass
                        if debug_info:
                            exact_match = debug_info.get('exact_match', False)
                            can_start_timer = debug_info.get('can_start_timer', False)
                            pose_confidence = debug_info.get('pose_confidence', 0.0)
                            angle_status = angle_info.get('status', 'improvable')
                            if (not exact_match and not can_start_timer and pose_confidence < 0.05 and
                                angle_status == 'dangerous'):
                                feedback_key = f"{angle_info.get('status')}:{feedback_text[:50]}"
                                if self.tts and feedback_key not in self.feedback_already_spoken:
                                    current_time = time.time()
                                    if (current_time - self.last_spoken_time) >= self.feedback_speak_cooldown:
                                        self.tts.speak_simple(feedback_text, voice="arcas")
                                        self.feedback_already_spoken.add(feedback_key)
                                        self.last_spoken_feedback = feedback_text
                                        self.last_spoken_time = current_time
                                        pass
                            else:
                                pass
                        else:
                            pass
                    else:
                        feedback_text = "Small adjustments needed (not spoken - not critical enough)"
                        print(f"🟡 [{status.upper()}] {feedback_text}")
                else:
                    feedback_text = "Adjust your form"
                    print(f"⚪ [UNKNOWN] {feedback_text}")
        else:
            feedback_text = "Good form! Hold steady."
            print(f"🟢 [CORRECT] {feedback_text}")
        feedback_msg = ""
        if pose_complete:
            if self.tts and not hasattr(self, '_completion_spoken'):
                completion_msg = f"{pose_name.replace('_', ' ')} complete! Great job."
                self.tts.speak_simple(completion_msg, voice="arcas")
                self._completion_spoken = True
                self.last_spoken_time = time.time()
            return f"{current_hold:.1f}s / {target_hold}s"
        else:
            timer_msg = f"{current_hold:.1f}s / {target_hold}s"
            if remaining > 0:
                timer_msg += f"\n{remaining:.1f}s remaining"
            return timer_msg
    def next_pose(self):
        if self.current_program:
            if self.hold_start_time is not None:
                self.accumulated_hold_time = time.time() - self.hold_start_time + self.accumulated_hold_time
                self.hold_start_time = None
            if hasattr(self, '_last_elapsed_time'):
                self._last_elapsed_time = 0
            if hasattr(self, '_completion_spoken'):
                self._completion_spoken = False
            self.current_pose_index += 1
            self.in_pose = False
            self.pose_entered = False
            self.pose_stability_frames = []
            self.pose_confidence_history = []
            self.smoothed_score = 0.0
            self.last_pose_name = None
            self.accumulated_hold_time = 0.0
            self.last_pause_time = None
            self.corrector.nlg.reset()
            self.instruction_spoken_for_pose = False
            self.current_pose_name_for_instruction = None
            self.feedback_already_spoken.clear()
            self.last_spoken_feedback = None
            self.last_spoken_time = 0.0
            if hasattr(self, 'pose_wrong_frames'):
                self.pose_wrong_frames = 0
            if hasattr(self, 'last_color_state'):
                self.last_color_state = None
            if hasattr(self, 'form_status_history'):
                self.form_status_history = []
    def repeat_instruction(self):
        if self.current_program and self.current_pose_index < len(self.current_program['poses']):
            pose_name = self.current_program['poses'][self.current_pose_index]
            target_hold = self.current_program['hold_times'][self.current_pose_index]
            if self.tts:
                instruction = f"Get into {pose_name.replace('_', ' ')}. Hold for {int(target_hold)} seconds."
                self.tts.speak_simple(instruction, voice="arcas")
    def draw_guided_feedback(self, frame: np.ndarray, session_state: Dict, skip_keypoints: bool = False) -> np.ndarray:
        output = frame.copy()
        h, w = output.shape[:2]
        if not skip_keypoints:
            keypoints = session_state.get('keypoints')
            if keypoints is not None:
                if not isinstance(keypoints, np.ndarray):
                    if isinstance(keypoints, list):
                        keypoints = np.array(keypoints, dtype=np.float32)
                    else:
                        keypoints = None
            if keypoints is not None and len(keypoints) > 0:
                    skeleton_connections = [
                    (0, 1), (0, 2),
                    (1, 3), (2, 4),
                    (0, 5), (0, 6),
                    (5, 6),
                    (5, 7),
                    (7, 9),
                    (6, 8),
                    (8, 10),
                    (5, 11),
                    (6, 12),
                    (11, 12),
                    (11, 13),
                    (13, 15),
                    (12, 14),
                    (14, 16),
                    ]
                    for start_idx, end_idx in skeleton_connections:
                        if (start_idx < len(keypoints) and end_idx < len(keypoints)):
                            start_kp = keypoints[start_idx]
                            end_kp = keypoints[end_idx]
                            if (start_kp[2] > 0.2 and end_kp[2] > 0.2):
                                start_pt = (int(start_kp[0]), int(start_kp[1]))
                                end_pt = (int(end_kp[0]), int(end_kp[1]))
                                if start_idx in [0, 1, 2, 3, 4]:
                                    line_color = (255, 150, 255)
                                elif start_idx in [5, 6, 7, 8, 9, 10]:
                                    line_color = (150, 255, 150)
                                elif start_idx in [11, 12, 13, 14, 15, 16]:
                                    line_color = (150, 150, 255)
                                else:
                                    line_color = (255, 255, 255)
                                cv2.line(output, start_pt, end_pt, (0, 0, 0), 3)
                                cv2.line(output, start_pt, end_pt, line_color, 2)
                    keypoint_colors = {
                    0: (255, 0, 255),
                    1: (255, 100, 255),
                    2: (255, 100, 255),
                    3: (200, 0, 200),
                    4: (200, 0, 200),
                    5: (0, 255, 0),
                    6: (0, 255, 0),
                    7: (255, 255, 0),
                    8: (255, 255, 0),
                    9: (0, 255, 255),
                    10: (0, 255, 255),
                    11: (255, 0, 0),
                    12: (255, 0, 0),
                    13: (0, 165, 255),
                    14: (0, 165, 255),
                    15: (0, 0, 255),
                    16: (0, 0, 255),
                    }
                    for i, (x, y, conf) in enumerate(keypoints):
                        if conf > config.POSE_CONFIDENCE_THRESHOLD:
                            x_int, y_int = int(x), int(y)
                            color = keypoint_colors.get(i, (255, 255, 255))
                            radius = 8
                            thickness = -1
                            cv2.circle(output, (x_int, y_int), radius + 2, (0, 0, 0), 2)
                            cv2.circle(output, (x_int, y_int), radius, color, thickness)
                            cv2.circle(output, (x_int, y_int), 3, (255, 255, 255), -1)
        instruction = session_state.get('instruction', '')
        if instruction:
            timer_lines = [line for line in instruction.split('\n') if ('s /' in line or 'remaining' in line or 'Hold for' in line)]
            if timer_lines:
                y_offset = h // 2
                base_font_scale = max(1.2, h / 400)
                for line in timer_lines:
                    if line.strip():
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        font_scale = base_font_scale
                        thickness = 4
                        (text_w, text_h), baseline = cv2.getTextSize(line, font, font_scale, thickness)
                        x = (w - text_w) // 2
                        padding = 30
                        overlay = output.copy()
                        cv2.rectangle(overlay, (x - padding, y_offset - text_h - padding),
                                     (x + text_w + padding, y_offset + padding), (255, 255, 255), -1)
                        cv2.addWeighted(overlay, 0.95, output, 0.05, 0, output)
                        cv2.rectangle(output, (x - padding, y_offset - text_h - padding),
                                     (x + text_w + padding, y_offset + padding), (0, 0, 0), 4)
                        cv2.putText(output, line, (x, y_offset), font, font_scale, (0, 0, 0), thickness)
                        y_offset += text_h + 40
        current_pose = session_state.get('current_pose')
        current_pose_index = session_state.get('current_pose_index', 0)
        if current_pose:
            if isinstance(current_pose, dict):
                pose_index = current_pose.get('index', current_pose_index)
                pose_total = current_pose.get('total', 0)
                info_text = f"Pose {pose_index + 1}/{pose_total}"
            else:
                info_text = str(current_pose).replace('_', ' ')
            font_scale = max(0.6, h / 800)
            thickness = 2
            (text_w, text_h), _ = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
            overlay = output.copy()
            cv2.rectangle(overlay, (10, 10), (10 + text_w + 20, 10 + text_h + 20), (255, 255, 255), -1)
            cv2.addWeighted(overlay, 0.9, output, 0.1, 0, output)
            cv2.rectangle(output, (10, 10), (10 + text_w + 20, 10 + text_h + 20), (0, 0, 0), 2)
            cv2.putText(output, info_text, (20, text_h + 25), cv2.FONT_HERSHEY_SIMPLEX,
                      font_scale, (0, 0, 0), thickness)
        if current_pose:
            if isinstance(current_pose, dict):
                pose_name = current_pose.get('name', '')
            else:
                pose_name = str(current_pose)
            pose_image_path = self.program_manager.get_pose_image_path(pose_name)
            if pose_image_path and os.path.exists(pose_image_path):
                try:
                    pose_img = cv2.imread(pose_image_path)
                    if pose_img is not None:
                        img_height = 200
                        img_width = int(pose_img.shape[1] * (img_height / pose_img.shape[0]))
                        pose_img_resized = cv2.resize(pose_img, (img_width, img_height))
                        x_offset = w - img_width - 20
                        y_offset = 10
                        overlay = output.copy()
                        cv2.rectangle(overlay, (x_offset - 10, y_offset - 10),
                                     (x_offset + img_width + 10, y_offset + img_height + 10),
                                     (255, 255, 255), -1)
                        cv2.addWeighted(overlay, 0.9, output, 0.1, 0, output)
                        cv2.rectangle(output, (x_offset - 10, y_offset - 10),
                                     (x_offset + img_width + 10, y_offset + img_height + 10),
                                     (0, 0, 0), 2)
                        output[y_offset:y_offset + img_height, x_offset:x_offset + img_width] = pose_img_resized
                except Exception as e:
                    pass
        form_feedback = session_state.get('form_feedback')
        in_pose = session_state.get('in_pose', False)
        detected_pose = session_state.get('detected_pose')
        if form_feedback and current_pose:
            status = session_state.get('smoothed_form_status', form_feedback.get('overall_status', 'unknown'))
            if isinstance(current_pose, dict):
                target_pose = current_pose.get('name', '')
            else:
                target_pose = str(current_pose)
            pose_correct = (in_pose and detected_pose and
                          (detected_pose == target_pose or
                           detected_pose.lower().replace('_', ' ') in target_pose.lower().replace('_', ' ') or
                           target_pose.lower().replace('_', ' ') in detected_pose.lower().replace('_', ' ')))
            indicator_size = 80
            indicator_x = w // 2
            indicator_y = h - 100
            if pose_correct:
                desired_color = (0, 255, 0)
            else:
                desired_color = (0, 0, 255)
            if self.last_color_state == 'green' and desired_color == (0, 0, 255):
                if not hasattr(self, 'pose_wrong_frames'):
                    self.pose_wrong_frames = 0
                if not pose_correct:
                    self.pose_wrong_frames += 1
                    if self.pose_wrong_frames < 15:
                        color = (0, 255, 0)
                    else:
                        color = (0, 0, 255)
                        self.last_color_state = 'red'
                        self.pose_wrong_frames = 0
                else:
                    self.pose_wrong_frames = 0
                    color = desired_color
                    if color == (0, 255, 0):
                        self.last_color_state = 'green'
                        self.color_green_frames += 1
            else:
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
            cv2.circle(output, (indicator_x, indicator_y), indicator_size, color, -1)
            cv2.circle(output, (indicator_x, indicator_y), indicator_size, (0, 0, 0), 5)
            hint_text = "Press 'R' to repeat instruction"
            hint_font_scale = 0.5
            hint_thickness = 1
            (hint_w, hint_h), _ = cv2.getTextSize(hint_text, cv2.FONT_HERSHEY_SIMPLEX, hint_font_scale, hint_thickness)
            hint_x = 20
            hint_y = h - 20
            overlay_hint = output.copy()
            cv2.rectangle(overlay_hint, (hint_x - 5, hint_y - hint_h - 5),
                         (hint_x + hint_w + 5, hint_y + 5), (255, 255, 255), -1)
            cv2.addWeighted(overlay_hint, 0.8, output, 0.2, 0, output)
            cv2.putText(output, hint_text, (hint_x, hint_y),
                       cv2.FONT_HERSHEY_SIMPLEX, hint_font_scale, (0, 0, 0), hint_thickness)
        return output
    def run_guided_session(self, program_name: str, camera_id: int = None):
        self.start_program(program_name)
        if camera_id is None:
            cameras = self.list_cameras()
            if not cameras:
                pass
                return
            camera_id = cameras[0] if len(cameras) == 1 else int(input(f"Select camera {cameras}: "))
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            pass
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cv2.namedWindow('YogaBuddy - Guided Session', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('YogaBuddy - Guided Session', 1920, 1080)
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            session_state = self.process_frame(frame)
            if session_state['status'] == 'complete':
                pass
                self._close_corrections_file()
                break
            if session_state.get('pose_complete'):
                time.sleep(2)
                self.next_pose()
                if self.current_pose_index >= len(self.current_program['poses']):
                    pass
                    self._close_corrections_file()
                    break
            output = self.draw_guided_feedback(frame, session_state)
            cv2.imshow('YogaBuddy - Guided Session', output)
            key = cv2.waitKey(1)
            if key == ord('q') or key == 27:
                self._close_corrections_file()
                break
            elif key == ord('r'):
                self.repeat_instruction()
            elif key == ord('n'):
                self.next_pose()
                pass
            elif key != -1:
                if key == 83 or key == 65363 or (key & 0xFF) == 83:
                    self.next_pose()
                    pass
                elif (key & 0xFF) == 77:
                    self.next_pose()
                    pass
        cap.release()
        cv2.destroyAllWindows()
        self._close_corrections_file()
        stats = self.tracker.get_session_stats()
        pass
    def _close_corrections_file(self):
        if self.corrections_file:
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
            pass
    def list_cameras(self):
        available = []
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available.append(i)
                cap.release()
        return available