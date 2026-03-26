import time
from typing import Dict, List, Optional
from collections import deque
import config
class SessionTracker:
    def __init__(self):
        self.current_pose = None
        self.pose_start_time = None
        self.pose_confidence_history = deque(maxlen=30)
        self.rep_count = 0
        self.last_rep_time = None
        self.hold_durations = []
        self.pose_entries = []
        self.corrections_count = 0
        self.dangerous_corrections = 0
        self.improvable_corrections = 0
        self.form_scores = []
        self.session_start_time = time.time()
        self.in_pose = False
        self.pose_target_times = {}
        self.pose_hold_ratios = []
    def update(self, pose_name: str, confidence: float, form_feedback: Dict, target_hold_time: float = None):
        current_time = time.time()
        self.pose_confidence_history.append(confidence)
        if target_hold_time is not None:
            self.pose_target_times[pose_name] = target_hold_time
        if not self.in_pose and confidence >= config.POSE_ENTRY_THRESHOLD:
            self._enter_pose(pose_name, current_time)
        elif self.in_pose and confidence < config.POSE_EXIT_THRESHOLD:
            self._exit_pose(current_time, form_feedback, target_hold_time)
        if self.in_pose:
            self.current_pose = pose_name
            status = form_feedback.get('overall_status', 'unknown') if form_feedback else 'unknown'
            if status == 'dangerous':
                self.dangerous_corrections += 1
                self.corrections_count += 1
            elif status == 'improvable':
                self.improvable_corrections += 1
                self.corrections_count += 1
            if form_feedback and 'score' in form_feedback:
                self.form_scores.append(form_feedback['score'])
    def _enter_pose(self, pose_name: str, current_time: float):
        self.in_pose = True
        self.current_pose = pose_name
        self.pose_start_time = current_time
        self.pose_entries.append({
            'pose': pose_name,
            'start_time': current_time
        })
    def _exit_pose(self, current_time: float, form_feedback: Dict, target_hold_time: float = None):
        if self.pose_start_time is None:
            return
        hold_duration = current_time - self.pose_start_time
        if hold_duration >= config.MIN_HOLD_DURATION:
            if self.last_rep_time is None or (current_time - self.last_rep_time) >= config.REP_COUNT_WINDOW:
                self.rep_count += 1
                self.last_rep_time = current_time
            self.hold_durations.append(hold_duration)
            if target_hold_time and target_hold_time > 0:
                hold_ratio = min(1.0, hold_duration / target_hold_time)
                self.pose_hold_ratios.append(hold_ratio)
            if self.pose_entries:
                self.pose_entries[-1]['duration'] = hold_duration
                self.pose_entries[-1]['form_score'] = form_feedback.get('score', 0) if form_feedback else 0
                self.pose_entries[-1]['target_hold'] = target_hold_time
                self.pose_entries[-1]['hold_ratio'] = hold_ratio if target_hold_time and target_hold_time > 0 else None
        self.in_pose = False
        self.current_pose = None
        self.pose_start_time = None
    def get_current_hold_duration(self) -> float:
        if self.pose_start_time is None:
            return 0.0
        return time.time() - self.pose_start_time
    def get_steadiness(self) -> float:
        if len(self.pose_confidence_history) < 5:
            return 0.0
        confidences = list(self.pose_confidence_history)
        variance = sum((c - sum(confidences)/len(confidences))**2 for c in confidences) / len(confidences)
        steadiness = max(0, 1.0 - variance * 10)
        return steadiness * 100
    def get_session_stats(self) -> Dict:
        session_duration = time.time() - self.session_start_time
        avg_hold_duration = sum(self.hold_durations) / len(self.hold_durations) if self.hold_durations else 0
        max_hold_duration = max(self.hold_durations) if self.hold_durations else 0
        avg_form_score = sum(self.form_scores) / len(self.form_scores) if self.form_scores else 0
        avg_hold_ratio = sum(self.pose_hold_ratios) / len(self.pose_hold_ratios) if self.pose_hold_ratios else 0.0
        consistency_score = self.get_steadiness()
        accuracy_score = self._calculate_accuracy_score(avg_form_score, avg_hold_ratio, consistency_score)
        return {
            'session_duration': session_duration,
            'rep_count': self.rep_count,
            'avg_hold_duration': avg_hold_duration,
            'max_hold_duration': max_hold_duration,
            'avg_hold_ratio': avg_hold_ratio,
            'avg_form_score': avg_form_score,
            'accuracy_score': accuracy_score,
            'corrections_count': self.corrections_count,
            'dangerous_corrections': self.dangerous_corrections,
            'improvable_corrections': self.improvable_corrections,
            'steadiness': consistency_score,
            'consistency_score': consistency_score,
            'pose_entries': len(self.pose_entries)
        }
    def _calculate_accuracy_score(self, avg_form_score: float, avg_hold_ratio: float, consistency_score: float) -> float:
        form_weight = 0.5
        hold_weight = 0.3
        consistency_weight = 0.2
        hold_score = avg_hold_ratio * 100
        accuracy = (
            avg_form_score * form_weight +
            hold_score * hold_weight +
            consistency_score * consistency_weight
        )
        return round(accuracy, 1)
    def calculate_progress_score(self) -> float:
        stats = self.get_session_stats()
        accuracy_score = stats.get('accuracy_score', 0)
        hold_bonus = stats.get('avg_hold_ratio', 0) * 10
        safety_penalty = min(20, stats.get('dangerous_corrections', 0) * 2)
        progress_score = accuracy_score + hold_bonus - safety_penalty
        return max(0, min(100, round(progress_score, 1)))
    def reset(self):
        self.current_pose = None
        self.pose_start_time = None
        self.pose_confidence_history.clear()
        self.rep_count = 0
        self.last_rep_time = None
        self.hold_durations = []
        self.pose_entries = []
        self.corrections_count = 0
        self.dangerous_corrections = 0
        self.improvable_corrections = 0
        self.form_scores = []
        self.session_start_time = time.time()
        self.in_pose = False
        self.pose_target_times = {}
        self.pose_hold_ratios = []