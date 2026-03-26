import os
import json
import numpy as np
from tqdm import tqdm
from typing import Dict, List
import cv2
from pose_detector import PoseDetector
from utils.angles import calculate_joint_angles
import config
class TemplateGenerator:
    def __init__(self):
        self.detector = PoseDetector()
    def process_pose_images(self, pose_dir: str) -> List[Dict[str, float]]:
        angle_list = []
        image_files = [f for f in os.listdir(pose_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        for img_file in tqdm(image_files, desc=f"Processing {os.path.basename(pose_dir)}"):
            img_path = os.path.join(pose_dir, img_file)
            try:
                image = cv2.imread(img_path)
                if image is None:
                    continue
                keypoints = self.detector.detect_pose(image)
                if keypoints is None:
                    continue
                confidence = np.mean(keypoints[:, 2])
                if confidence < 0.5:
                    continue
                visible_keypoints = np.sum(keypoints[:, 2] > 0.3)
                if visible_keypoints < 12:
                    continue
                angles = calculate_joint_angles(keypoints)
                if len(angles) > 0:
                    angle_list.append(angles)
            except Exception as e:
                if len(angle_list) == 0 and image_files.index(img_file) < 3:
                    pass
                continue
        return angle_list
    def generate_template(self, angle_list: List[Dict[str, float]], tolerance: float = 10.0) -> Dict:
        if not angle_list:
            return {}
        all_angle_names = set()
        for angles in angle_list:
            all_angle_names.update(angles.keys())
        template = {}
        for angle_name in all_angle_names:
            values = [angles[angle_name] for angles in angle_list if angle_name in angles]
            if not values:
                continue
            values = np.array(values)
            q1 = np.percentile(values, 25)
            q3 = np.percentile(values, 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            filtered_values = values[(values >= lower_bound) & (values <= upper_bound)]
            if len(filtered_values) < len(values) * 0.5:
                filtered_values = values
            median = np.median(filtered_values)
            mean = np.mean(filtered_values)
            std = np.std(filtered_values)
            iqr_tolerance = 1.5 * iqr
            std_tolerance = std
            angle_tolerance = float(max(min(iqr_tolerance, std_tolerance * 1.2), tolerance * 0.6))
            target = float(median)
            range_tolerance = angle_tolerance * 0.8
            template[angle_name] = {
                'target': target,
                'tolerance': angle_tolerance,
                'min': float(median - range_tolerance),
                'max': float(median + range_tolerance),
                'mean': float(mean),
                'std': float(std),
                'iqr': float(iqr),
                'q1': float(q1),
                'q3': float(q3),
                'sample_count': len(filtered_values)
            }
        return template
    def generate_all_templates(self, output_dir: str = None):
        if output_dir is None:
            output_dir = config.TEMPLATES_DIR
        os.makedirs(output_dir, exist_ok=True)
        templates = {}
        pose_progress = tqdm(config.TOP_POSES, desc="Generating templates", unit="pose", position=0, leave=True)
        for pose_name in pose_progress:
            pose_progress.set_description(f"Processing: {pose_name[:40]}...")
            pose_dir = None
            for split in ['train', 'valid', 'test']:
                split_dir = os.path.join(config.DATASET_ROOT, split)
                potential_dir = os.path.join(split_dir, pose_name)
                if os.path.exists(potential_dir):
                    pose_dir = potential_dir
                    break
            if pose_dir is None:
                pose_progress.write(f"⚠ Warning: Could not find directory for pose {pose_name}")
                continue
            angle_list = self.process_pose_images(pose_dir)
            if not angle_list:
                pose_progress.write(f"⚠ Warning: No valid angles extracted for {pose_name}")
                continue
            template = self.generate_template(angle_list)
            templates[pose_name] = template
            template_file = os.path.join(output_dir, f"{pose_name.replace(' ', '_').replace('/', '_')}.json")
            with open(template_file, 'w') as f:
                json.dump(template, f, indent=2)
            pose_progress.set_postfix({
                'angles': len(template),
                'images': len(angle_list)
            })
        pose_progress.close()
        print("\n💾 Saving combined templates...")
        combined_file = os.path.join(output_dir, "all_templates.json")
        with open(combined_file, 'w') as f:
            json.dump(templates, f, indent=2)
        print(f"✅ All templates saved to {output_dir}")
        print(f"📊 Generated {len(templates)} templates")
        return templates
if __name__ == "__main__":
    generator = TemplateGenerator()
    generator.generate_all_templates()