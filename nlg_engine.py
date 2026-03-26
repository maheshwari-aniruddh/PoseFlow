from typing import Dict, List, Tuple, Optional
from collections import deque
import random
import time
class NLGEngine:
    BODY_REGIONS = {
        'legs': ['left_knee', 'right_knee', 'left_hip', 'right_hip'],
        'front_leg': ['left_knee', 'left_hip'],
        'back_leg': ['right_knee', 'right_hip'],
        'arms': ['left_elbow', 'right_elbow', 'shoulder_left', 'shoulder_right'],
        'torso': ['spine_left', 'spine_right'],
        'upper_body': ['spine_left', 'spine_right', 'shoulder_left', 'shoulder_right'],
        'lower_body': ['left_knee', 'right_knee', 'left_hip', 'right_hip'],
    }
    PRAISE_PHRASES = [
        "Great job!",
        "Looking good!",
        "Nice work!",
        "You're doing well!",
        "Excellent progress!",
        "Keep it up!",
        "You've got this!",
        "Well done!",
        "That's better!",
        "Much improved!",
    ]
    ENCOURAGEMENT_PHRASES = [
        "Keep going!",
        "You're almost there!",
        "Just a little more!",
        "You've got this!",
        "Keep breathing!",
        "Stay strong!",
        "You're doing great!",
        "Almost perfect!",
    ]
    CORRECTION_TEMPLATES = {
        'legs': {
            'dangerous': [
                "Your legs need more alignment. {action} to protect your knees.",
                "Let's fix your leg position. {action} for better support.",
            ],
            'improvable': [
                "Your stance is good! {action} for even better alignment.",
                "Nice leg position! Try {action} to refine it.",
            ],
        },
        'front_leg': {
            'dangerous': [
                "Your front leg needs adjustment. {action} to prevent strain.",
                "Let's align your front leg. {action} for safety.",
            ],
            'improvable': [
                "Good front leg position! {action} to perfect it.",
                "Your front leg is close! {action} for better form.",
            ],
        },
        'back_leg': {
            'dangerous': [
                "Your back leg needs attention. {action} to avoid injury.",
                "Let's fix your back leg. {action} for proper alignment.",
            ],
            'improvable': [
                "Your back leg looks good! {action} to improve it further.",
                "Nice back leg! {action} for better stability.",
            ],
        },
        'arms': {
            'dangerous': [
                "Your arms need adjustment. {action} to protect your shoulders.",
                "Let's align your arms. {action} for better form.",
            ],
            'improvable': [
                "Your arms are looking good! {action} to refine them.",
                "Nice arm position! {action} for perfect alignment.",
            ],
        },
        'torso': {
            'dangerous': [
                "Your torso needs alignment. {action} to protect your spine.",
                "Let's straighten your torso. {action} for safety.",
            ],
            'improvable': [
                "Your posture is good! {action} to perfect it.",
                "Nice torso alignment! {action} for even better form.",
            ],
        },
        'upper_body': {
            'dangerous': [
                "Your upper body needs adjustment. {action} to avoid strain.",
                "Let's align your upper body. {action} for better posture.",
            ],
            'improvable': [
                "Your upper body looks good! {action} to refine it.",
                "Nice upper body position! {action} for perfect alignment.",
            ],
        },
    }
    def __init__(self, max_history: int = 20):
        self.correction_history = deque(maxlen=max_history)
        self.last_correction_time = {}
        self.improvement_tracking = {}
        self.correction_cooldown = 15.0
        self.last_feedback_time = 0.0
        self.feedback_cooldown = 10.0
        self.current_feedback = None
        self.feedback_start_time = 0.0
        self.feedback_duration = 8.0
        self.spoken_corrections = set()
    def group_angles_by_region(self, angle_feedback: Dict) -> Dict[str, List[Tuple[str, Dict]]]:
        region_groups = {}
        for angle_name, feedback in angle_feedback.items():
            if feedback.get('status') == 'correct':
                continue
            assigned = False
            for region, angles in self.BODY_REGIONS.items():
                if angle_name in angles:
                    if region not in region_groups:
                        region_groups[region] = []
                    region_groups[region].append((angle_name, feedback))
                    assigned = True
            if not assigned:
                if 'other' not in region_groups:
                    region_groups['other'] = []
                region_groups['other'].append((angle_name, feedback))
        return region_groups
    def prioritize_regions(self, region_groups: Dict[str, List[Tuple[str, Dict]]]) -> List[Tuple[str, List[Tuple[str, Dict]]]]:
        prioritized = []
        for region, angles in region_groups.items():
            dangerous_count = sum(1 for _, fb in angles if fb.get('status') == 'dangerous')
            max_weighted_dev = max((fb.get('weighted_deviation', 0) for _, fb in angles), default=0)
            priority = 0
            if dangerous_count > 0:
                priority += 1000
            region_priority = {
                'torso': 100,
                'upper_body': 90,
                'legs': 80,
                'front_leg': 75,
                'back_leg': 75,
                'arms': 60,
                'lower_body': 70,
                'other': 50,
            }
            priority += region_priority.get(region, 50)
            priority += max_weighted_dev * 10
            prioritized.append((priority, region, angles))
        prioritized.sort(reverse=True, key=lambda x: x[0])
        return [(region, angles) for _, region, angles in prioritized]
    def generate_action_phrase(self, angles_in_region: List[Tuple[str, Dict]]) -> str:
        if not angles_in_region:
            return ""
        angle_names = [name for name, _ in angles_in_region]
        region_name = ""
        has_knee = any('knee' in name for name in angle_names)
        has_hip = any('hip' in name for name in angle_names)
        has_elbow = any('elbow' in name for name in angle_names)
        has_spine = any('spine' in name for name in angle_names)
        if has_knee and has_hip:
            if 'left' in angle_names[0]:
                region_name = "front leg"
            else:
                region_name = "back leg"
        elif has_elbow:
            region_name = "arms"
        elif has_spine:
            region_name = "torso"
        elif has_knee:
            region_name = "legs"
        elif has_hip:
            region_name = "hips"
        else:
            region_name = "body"
        most_critical = max(angles_in_region, key=lambda x: x[1].get('weighted_deviation', 0))
        angle_name, feedback = most_critical
        current = feedback.get('current', 0)
        target = feedback.get('target', 0)
        diff = abs(current - target)
        if diff > 25:
            amount = "a lot"
        elif diff > 15:
            amount = "quite a bit"
        elif diff > 8:
            amount = "a bit"
        else:
            amount = "just a little"
        if 'knee' in angle_name:
            if current > target:
                return f"straighten your {region_name} {amount}"
            else:
                return f"bend your {region_name} {amount} more"
        elif 'hip' in angle_name:
            if current > target:
                return f"lower your {region_name} {amount}"
            else:
                return f"raise your {region_name} {amount} more"
        elif 'elbow' in angle_name:
            if current > target:
                return f"straighten your {region_name} {amount}"
            else:
                return f"bend your {region_name} {amount} more"
        elif 'spine' in angle_name or 'shoulder' in angle_name:
            if current > target:
                return f"straighten your {region_name} {amount}"
            else:
                return f"round your {region_name} {amount} more"
        else:
            return f"adjust your {region_name} {amount}"
    def should_repeat_correction(self, region: str, action: str) -> bool:
        correction_key = f"{region}:{action}"
        current_time = time.time()
        if self.current_feedback is not None:
            time_since_feedback_start = current_time - self.feedback_start_time
            if time_since_feedback_start < self.feedback_duration:
                return False
        time_since_last_feedback = current_time - self.last_feedback_time
        if time_since_last_feedback < self.feedback_cooldown:
            return False
        if correction_key in self.last_correction_time:
            time_since = current_time - self.last_correction_time[correction_key]
            if time_since < self.correction_cooldown:
                return False
        self.last_correction_time[correction_key] = current_time
        self.last_feedback_time = current_time
        self.current_feedback = correction_key
        self.feedback_start_time = current_time
        return True
    def generate_corrections(self, angle_feedback: Dict, max_corrections: int = 2) -> List[str]:
        if not angle_feedback:
            return []
        region_groups = self.group_angles_by_region(angle_feedback)
        if not region_groups:
            return []
        prioritized_regions = self.prioritize_regions(region_groups)
        corrections = []
        corrections_given = 0
        for region, angles_in_region in prioritized_regions:
            if corrections_given >= max_corrections:
                break
            has_dangerous = any(fb.get('status') == 'dangerous' for _, fb in angles_in_region)
            severity = 'dangerous' if has_dangerous else 'improvable'
            action = self.generate_action_phrase(angles_in_region)
            if not self.should_repeat_correction(region, action):
                continue
            correction_key = f"{region}:{action}"
            if correction_key in self.spoken_corrections:
                continue
            templates = self.CORRECTION_TEMPLATES.get(region,
                self.CORRECTION_TEMPLATES.get('legs', {}))
            if severity in templates:
                template = random.choice(templates[severity])
            else:
                if severity == 'dangerous':
                    template = "Your {region} needs adjustment. {action} to avoid strain."
                else:
                    template = "Your {region} looks good! {action} to refine it."
                template = template.replace('{region}', region.replace('_', ' '))
            correction_text = template.format(action=action)
            praise_start = random.choice(self.PRAISE_PHRASES)
            encouragement_end = random.choice(self.ENCOURAGEMENT_PHRASES)
            full_message = f"{praise_start} {correction_text} {encouragement_end}"
            if full_message.strip() in self.spoken_corrections:
                continue
            corrections.append(full_message)
            corrections_given += 1
            self.spoken_corrections.add(correction_key)
            self.spoken_corrections.add(full_message.strip())
            self.correction_history.append({
                'region': region,
                'action': action,
                'time': time.time(),
                'message': full_message
            })
        return corrections
    def generate_summary_feedback(self, form_feedback: Dict) -> str:
        status = form_feedback.get('overall_status', 'unknown')
        score = form_feedback.get('score', 0)
        if status == 'correct':
            return random.choice([
                "✅ Perfect form! You're holding it beautifully!",
                "✅ Excellent alignment! Keep it steady!",
                "✅ Great posture! You've got it!",
                "✅ Perfect! Your form looks amazing!",
            ])
        elif status == 'improvable':
            return random.choice([
                "💡 Good form! Just a few small adjustments needed.",
                "💡 You're close! Minor tweaks will perfect it.",
                "💡 Nice work! Small refinements coming up.",
            ])
        else:
            return random.choice([
                "⚠️ Let's adjust your form for safety.",
                "⚠️ Important corrections needed to protect your body.",
                "⚠️ We need to fix a few things for proper alignment.",
            ])
    def reset(self):
        self.correction_history.clear()
        self.last_correction_time.clear()
        self.improvement_tracking.clear()
        self.current_feedback = None
        self.feedback_start_time = 0.0
        self.spoken_corrections.clear()