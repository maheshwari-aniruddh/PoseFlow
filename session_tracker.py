"""
Session tracking: rep counting, duration tracking, and progress scoring
"""
import time
from typing import Dict, List, Optional
from collections import deque
import config

class SessionTracker:
    """Tracks reps, durations, and session progress"""
    
    def __init__(self):
        self.current_pose = None
        self.pose_start_time = None
        self.pose_confidence_history = deque(maxlen=30)  # Last 30 frames
        self.rep_count = 0
        self.last_rep_time = None
        self.hold_durations = []  # List of hold durations per pose
        self.pose_entries = []  # List of pose entry/exit events
        self.corrections_count = 0  # Total number of corrections needed
        self.dangerous_corrections = 0  # Critical errors (red)
        self.improvable_corrections = 0  # Improvements needed (yellow)
        self.form_scores = []  # Form accuracy scores (0-100)
        self.session_start_time = time.time()
        self.in_pose = False
        self.pose_target_times = {}  # Track target hold times per pose
        self.pose_hold_ratios = []  # Track hold_time/target_time ratios
    
    def update(self, pose_name: str, confidence: float, form_feedback: Dict, target_hold_time: float = None):
        """
        Update tracking with new pose detection.
        
        Args:
            pose_name: Detected pose name
            confidence: Detection confidence
            form_feedback: Form correction feedback
            target_hold_time: Target hold time for this pose (seconds)
        """
        current_time = time.time()
        
        # Update confidence history
        self.pose_confidence_history.append(confidence)
        
        # Store target hold time for this pose
        if target_hold_time is not None:
            self.pose_target_times[pose_name] = target_hold_time
        
        # Check if entering pose
        if not self.in_pose and confidence >= config.POSE_ENTRY_THRESHOLD:
            self._enter_pose(pose_name, current_time)
        
        # Check if exiting pose
        elif self.in_pose and confidence < config.POSE_EXIT_THRESHOLD:
            self._exit_pose(current_time, form_feedback, target_hold_time)
        
        # Update current pose if in pose
        if self.in_pose:
            self.current_pose = pose_name
            # Count corrections by type
            status = form_feedback.get('overall_status', 'unknown') if form_feedback else 'unknown'
            if status == 'dangerous':
                self.dangerous_corrections += 1
                self.corrections_count += 1
            elif status == 'improvable':
                self.improvable_corrections += 1
                self.corrections_count += 1
            # Track form score (0-100)
            if form_feedback and 'score' in form_feedback:
                self.form_scores.append(form_feedback['score'])
    
    def _enter_pose(self, pose_name: str, current_time: float):
        """Handle pose entry"""
        self.in_pose = True
        self.current_pose = pose_name
        self.pose_start_time = current_time
        self.pose_entries.append({
            'pose': pose_name,
            'start_time': current_time
        })
    
    def _exit_pose(self, current_time: float, form_feedback: Dict, target_hold_time: float = None):
        """Handle pose exit"""
        if self.pose_start_time is None:
            return
        
        hold_duration = current_time - self.pose_start_time
        
        # Only count as rep if held long enough
        if hold_duration >= config.MIN_HOLD_DURATION:
            # Check if enough time has passed since last rep
            if self.last_rep_time is None or (current_time - self.last_rep_time) >= config.REP_COUNT_WINDOW:
                self.rep_count += 1
                self.last_rep_time = current_time
            
            self.hold_durations.append(hold_duration)
            
            # Calculate hold ratio (hold_time / target_time) if target is known
            if target_hold_time and target_hold_time > 0:
                hold_ratio = min(1.0, hold_duration / target_hold_time)  # Cap at 1.0 (100%)
                self.pose_hold_ratios.append(hold_ratio)
            
            # Update last entry
            if self.pose_entries:
                self.pose_entries[-1]['duration'] = hold_duration
                self.pose_entries[-1]['form_score'] = form_feedback.get('score', 0) if form_feedback else 0
                self.pose_entries[-1]['target_hold'] = target_hold_time
                self.pose_entries[-1]['hold_ratio'] = hold_ratio if target_hold_time and target_hold_time > 0 else None
        
        self.in_pose = False
        self.current_pose = None
        self.pose_start_time = None
    
    def get_current_hold_duration(self) -> float:
        """Get current pose hold duration"""
        if self.pose_start_time is None:
            return 0.0
        return time.time() - self.pose_start_time
    
    def get_steadiness(self) -> float:
        """Calculate pose steadiness from confidence history"""
        if len(self.pose_confidence_history) < 5:
            return 0.0
        
        confidences = list(self.pose_confidence_history)
        # Steadiness is inverse of variance
        variance = sum((c - sum(confidences)/len(confidences))**2 for c in confidences) / len(confidences)
        steadiness = max(0, 1.0 - variance * 10)  # Normalize to 0-1
        return steadiness * 100
    
    def get_session_stats(self) -> Dict:
        """Get comprehensive session statistics"""
        session_duration = time.time() - self.session_start_time
        
        avg_hold_duration = sum(self.hold_durations) / len(self.hold_durations) if self.hold_durations else 0
        max_hold_duration = max(self.hold_durations) if self.hold_durations else 0
        avg_form_score = sum(self.form_scores) / len(self.form_scores) if self.form_scores else 0
        
        # Calculate average hold ratio (how well user met target times)
        avg_hold_ratio = sum(self.pose_hold_ratios) / len(self.pose_hold_ratios) if self.pose_hold_ratios else 0.0
        
        # Calculate consistency score (how steady they held poses)
        consistency_score = self.get_steadiness()
        
        # Calculate overall accuracy score (0-100%)
        # Based on form accuracy, hold time completion, and consistency
        accuracy_score = self._calculate_accuracy_score(avg_form_score, avg_hold_ratio, consistency_score)
        
        return {
            'session_duration': session_duration,
            'rep_count': self.rep_count,
            'avg_hold_duration': avg_hold_duration,
            'max_hold_duration': max_hold_duration,
            'avg_hold_ratio': avg_hold_ratio,  # Average of hold_time/target_time
            'avg_form_score': avg_form_score,
            'accuracy_score': accuracy_score,  # Overall accuracy (0-100%)
            'corrections_count': self.corrections_count,
            'dangerous_corrections': self.dangerous_corrections,  # Critical errors (red)
            'improvable_corrections': self.improvable_corrections,  # Improvements (yellow)
            'steadiness': consistency_score,  # Consistency score
            'consistency_score': consistency_score,  # Alias for steadiness
            'pose_entries': len(self.pose_entries)
        }
    
    def _calculate_accuracy_score(self, avg_form_score: float, avg_hold_ratio: float, consistency_score: float) -> float:
        """
        Calculate overall accuracy score (0-100%).
        
        Args:
            avg_form_score: Average form score (0-100)
            avg_hold_ratio: Average hold_time/target_time ratio (0-1)
            consistency_score: Consistency/steadiness score (0-100)
        
        Returns:
            Overall accuracy score (0-100)
        """
        # Weighted components
        form_weight = 0.5  # Form accuracy is most important
        hold_weight = 0.3  # Hold time completion
        consistency_weight = 0.2  # Consistency
        
        # Normalize hold ratio to 0-100
        hold_score = avg_hold_ratio * 100
        
        # Calculate weighted average
        accuracy = (
            avg_form_score * form_weight +
            hold_score * hold_weight +
            consistency_score * consistency_weight
        )
        
        return round(accuracy, 1)
    
    def calculate_progress_score(self) -> float:
        """
        Calculate overall progress score for the session.
        
        Returns:
            Score from 0-100
        """
        stats = self.get_session_stats()
        
        # Use accuracy score as base (already weighted)
        accuracy_score = stats.get('accuracy_score', 0)
        
        # Bonus for completing target hold times
        hold_bonus = stats.get('avg_hold_ratio', 0) * 10  # Up to 10 points bonus
        
        # Penalty for dangerous corrections (safety is important)
        safety_penalty = min(20, stats.get('dangerous_corrections', 0) * 2)  # -2 points per dangerous correction, max -20
        
        # Calculate final score
        progress_score = accuracy_score + hold_bonus - safety_penalty
        
        return max(0, min(100, round(progress_score, 1)))  # Clamp to 0-100
    
    def reset(self):
        """Reset session tracking"""
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

