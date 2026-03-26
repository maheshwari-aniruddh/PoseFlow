import json
import os
from typing import Dict, List, Tuple, Optional
from utils.angles import calculate_joint_angles
from nlg_engine import NLGEngine
import config
class FormCorrector:
    def __init__(self, templates_dir: str = None):
        if templates_dir is None:
            templates_dir = config.TEMPLATES_DIR
        self.templates_dir = templates_dir
        self.templates = {}
        self.load_templates()
        self.nlg = NLGEngine()
    def load_templates(self):
        if not os.path.exists(self.templates_dir):
            print(f"Templates directory not found: {self.templates_dir}")
            return
        combined_file = os.path.join(self.templates_dir, "all_templates.json")
        if os.path.exists(combined_file):
            with open(combined_file, 'r') as f:
                self.templates = json.load(f)
        else:
            for filename in os.listdir(self.templates_dir):
                if filename.endswith('.json') and filename != 'all_templates.json':
                    pose_name = filename.replace('.json', '')
                    template_path = os.path.join(self.templates_dir, filename)
                    try:
                        with open(template_path, 'r') as f:
                            self.templates[pose_name] = json.load(f)
                    except Exception as e:
                        print(f"Error loading template {filename}: {e}")
    def get_template(self, pose_name: str) -> Optional[Dict]:
        def normalize_name(name):
            return name.lower().replace('_', ' ').replace('-', ' ').replace('(', '').replace(')', '').replace('or', '').strip()
        normalized_pose = normalize_name(pose_name)
        if pose_name in self.templates:
            return self.templates[pose_name]
        for template_pose in self.templates.keys():
            if normalize_name(template_pose) == normalized_pose:
                return self.templates[template_pose]
        pose_words = set([w for w in normalized_pose.split() if len(w) > 2])
        best_match = None
        best_overlap = 0.0
        for template_pose in self.templates.keys():
            template_normalized = normalize_name(template_pose)
            template_words = set([w for w in template_normalized.split() if len(w) > 2])
            if pose_words and template_words:
                overlap = len(pose_words & template_words) / max(len(pose_words), len(template_words))
                if overlap > best_overlap and overlap >= 0.5:
                    best_overlap = overlap
                    best_match = template_pose
        if best_match:
            return self.templates[best_match]
        for template_pose in self.templates.keys():
            if normalized_pose in normalize_name(template_pose) or normalize_name(template_pose) in normalized_pose:
                return self.templates[template_pose]
        return None
    def check_angle(self, angle_value: float, template: Dict) -> Tuple[str, float]:
        target = template.get('target', 0)
        min_val = template.get('min', target - config.ANGLE_TOLERANCE['improvable'])
        max_val = template.get('max', target + config.ANGLE_TOLERANCE['improvable'])
        tolerance = template.get('tolerance', config.ANGLE_TOLERANCE['improvable'])
        deviation = abs(angle_value - target)
        if deviation <= config.ANGLE_TOLERANCE['correct']:
            return 'correct', deviation
        elif deviation <= config.ANGLE_TOLERANCE['improvable']:
            return 'improvable', deviation
        elif min_val <= angle_value <= max_val:
            return 'improvable', deviation
        else:
            return 'dangerous', deviation
    def correct_form(self, keypoints, pose_name: str) -> Dict:
        angle_data = calculate_joint_angles(keypoints, return_confidence=True)
        current_angles = angle_data['angles']
        angle_confidences = angle_data.get('confidences', {})
        template = self.get_template(pose_name)
        if template is None:
            return {
                'pose': pose_name,
                'has_template': False,
                'feedback': {},
                'overall_status': 'unknown'
            }
        angle_weights = self._get_angle_weights(pose_name)
        feedback = {}
        statuses = []
        weighted_deviations = []
        for angle_name, angle_value in current_angles.items():
            if angle_name not in template:
                continue
            angle_conf = angle_confidences.get(angle_name, 0.5)
            if angle_conf < 0.2:
                continue
            status, deviation = self.check_angle(angle_value, template[angle_name])
            weight = angle_weights.get(angle_name, 1.0)
            weighted_deviation = deviation * weight * angle_conf
            feedback[angle_name] = {
                'status': status,
                'current': angle_value,
                'target': template[angle_name]['target'],
                'deviation': deviation,
                'weighted_deviation': weighted_deviation,
                'confidence': angle_conf,
                'weight': weight,
                'message': self._get_feedback_message(angle_name, status, angle_value, template[angle_name]['target'])
            }
            statuses.append(status)
            weighted_deviations.append(weighted_deviation)
        if 'dangerous' in statuses:
            overall_status = 'dangerous'
        elif 'improvable' in statuses:
            overall_status = 'improvable'
        else:
            overall_status = 'correct'
        avg_weighted_deviation = sum(weighted_deviations) / len(weighted_deviations) if weighted_deviations else 100.0
        nlg_corrections = self.nlg.generate_corrections(feedback, max_corrections=2)
        return {
            'pose': pose_name,
            'has_template': True,
            'feedback': feedback,
            'overall_status': overall_status,
            'score': self._calculate_form_score(statuses),
            'avg_weighted_deviation': avg_weighted_deviation,
            'angle_weights': angle_weights,
            'nlg_corrections': nlg_corrections,
            'nlg_summary': self.nlg.generate_summary_feedback({
                'overall_status': overall_status,
                'score': self._calculate_form_score(statuses)
            })
        }
    def _get_angle_weights(self, pose_name: str) -> Dict[str, float]:
        pose_lower = pose_name.lower()
        weights = {}
        default_weight = 1.0
        important_weight = 2.0
        critical_weight = 3.0
        all_angles = ['left_elbow', 'right_elbow', 'left_knee', 'right_knee',
                     'left_hip', 'right_hip', 'shoulder_left', 'spine_left', 'spine_right']
        for angle in all_angles:
            weights[angle] = default_weight
        if 'child' in pose_lower or 'balasana' in pose_lower:
            weights['left_knee'] = critical_weight
            weights['right_knee'] = critical_weight
            weights['left_hip'] = important_weight
            weights['right_hip'] = important_weight
            weights['spine_left'] = important_weight
            weights['spine_right'] = important_weight
        elif 'forward' in pose_lower or 'uttanasana' in pose_lower:
            weights['spine_left'] = critical_weight
            weights['spine_right'] = critical_weight
            weights['left_hip'] = important_weight
            weights['right_hip'] = important_weight
            weights['left_knee'] = important_weight
            weights['right_knee'] = important_weight
        elif 'camel' in pose_lower or 'ustrasana' in pose_lower:
            weights['left_hip'] = critical_weight
            weights['right_hip'] = critical_weight
            weights['spine_left'] = important_weight
            weights['spine_right'] = important_weight
        elif 'wheel' in pose_lower or 'bow' in pose_lower or 'dhanurasana' in pose_lower:
            weights['left_hip'] = critical_weight
            weights['right_hip'] = critical_weight
            weights['spine_left'] = critical_weight
            weights['spine_right'] = critical_weight
            weights['left_elbow'] = important_weight
            weights['right_elbow'] = important_weight
        elif 'tree' in pose_lower or 'vrksasana' in pose_lower:
            weights['left_hip'] = critical_weight
            weights['right_hip'] = critical_weight
            weights['left_knee'] = critical_weight
            weights['right_knee'] = critical_weight
            weights['spine_left'] = important_weight
            weights['spine_right'] = important_weight
        elif 'dance' in pose_lower or 'natarajasana' in pose_lower:
            weights['left_hip'] = critical_weight
            weights['right_hip'] = critical_weight
            weights['left_knee'] = important_weight
            weights['right_knee'] = important_weight
        elif 'warrior' in pose_lower or 'virabhadrasana' in pose_lower:
            weights['left_hip'] = critical_weight
            weights['right_hip'] = critical_weight
            weights['left_knee'] = critical_weight
            weights['right_knee'] = critical_weight
            weights['spine_left'] = important_weight
            weights['spine_right'] = important_weight
        elif 'headstand' in pose_lower or 'sirsasana' in pose_lower:
            weights['spine_left'] = critical_weight
            weights['spine_right'] = critical_weight
            weights['left_hip'] = important_weight
            weights['right_hip'] = important_weight
        elif 'sitting' in pose_lower or 'virasana' in pose_lower or 'vajrasana' in pose_lower:
            weights['left_hip'] = important_weight
            weights['right_hip'] = important_weight
            weights['left_knee'] = important_weight
            weights['right_knee'] = important_weight
        return weights
    def _get_feedback_message(self, angle_name: str, status: str, current: float, target: float) -> str:
        diff = abs(current - target)
        angle_parts = angle_name.replace('_', ' ').split()
        body_part = angle_parts[0].title()
        joint = angle_parts[1].title() if len(angle_parts) > 1 else ""
        body_part_map = {
            'Left': 'left', 'Right': 'right',
            'Elbow': 'elbow', 'Knee': 'knee', 'Hip': 'hip',
            'Shoulder': 'shoulder', 'Spine': 'spine'
        }
        if 'elbow' in angle_name.lower():
            part_desc = f"{body_part.lower()} arm"
            action_part = "arm"
        elif 'knee' in angle_name.lower():
            part_desc = f"{body_part.lower()} leg"
            action_part = "leg"
        elif 'hip' in angle_name.lower():
            part_desc = f"{body_part.lower()} hip"
            action_part = "hip"
        elif 'shoulder' in angle_name.lower():
            part_desc = f"{body_part.lower()} shoulder"
            action_part = "shoulder"
        elif 'spine' in angle_name.lower():
            part_desc = "your spine"
            action_part = "back"
        else:
            part_desc = angle_name.replace('_', ' ').lower()
            action_part = "body"
        if status == 'correct':
            return f"✅ Great! Your {part_desc} looks perfect!"
        if diff > 25:
            amount = "a lot"
            encouragement = "You're getting there! "
        elif diff > 15:
            amount = "quite a bit"
            encouragement = "Nice progress! "
        elif diff > 8:
            amount = "a bit"
            encouragement = "Almost there! "
        else:
            amount = "just a little"
            encouragement = "You're so close! "
        if 'elbow' in angle_name.lower():
            if current > target:
                direction = f"straighten your {body_part.lower()} arm {amount}"
            else:
                direction = f"bend your {body_part.lower()} arm {amount} more"
        elif 'knee' in angle_name.lower():
            if current > target:
                direction = f"straighten your {body_part.lower()} leg {amount}"
            else:
                direction = f"bend your {body_part.lower()} leg {amount} more"
        elif 'hip' in angle_name.lower():
            if current > target:
                direction = f"lower your {body_part.lower()} hip {amount}"
            else:
                direction = f"raise your {body_part.lower()} hip {amount} more"
        elif 'shoulder' in angle_name.lower():
            if current > target:
                direction = f"relax your {body_part.lower()} shoulder {amount}"
            else:
                direction = f"engage your {body_part.lower()} shoulder {amount} more"
        elif 'spine' in angle_name.lower():
            if current > target:
                direction = f"straighten your back {amount}"
            else:
                direction = f"round your back {amount} more"
        else:
            if current > target:
                direction = f"adjust your {part_desc} {amount}"
            else:
                direction = f"adjust your {part_desc} {amount} more"
        if status == 'improvable':
            return f"💡 {encouragement}Try to {direction}"
        else:
            return f"⚠️ Please {direction} to avoid strain"
    def _calculate_form_score(self, statuses: List[str]) -> float:
        if not statuses:
            return 0.0
        correct_count = statuses.count('correct')
        improvable_count = statuses.count('improvable')
        dangerous_count = statuses.count('dangerous')
        total = len(statuses)
        score = (correct_count * 1.0 + improvable_count * 0.6 + dangerous_count * 0.2) / total * 100
        return round(score, 1)