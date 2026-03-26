"""
Generate angle templates from dataset for form correction
"""
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
    """Generate angle templates from Yoga-82 dataset"""
    
    def __init__(self):
        self.detector = PoseDetector()
    
    def process_pose_images(self, pose_dir: str) -> List[Dict[str, float]]:
        """
        Process all images for a pose and extract angles.
        
        Args:
            pose_dir: Directory containing images for a pose
        
        Returns:
            List of angle dictionaries
        """
        angle_list = []
        image_files = [f for f in os.listdir(pose_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        for img_file in tqdm(image_files, desc=f"Processing {os.path.basename(pose_dir)}"):
            img_path = os.path.join(pose_dir, img_file)
            try:
                # Load image
                image = cv2.imread(img_path)
                if image is None:
                    continue
                
                # Detect pose
                keypoints = self.detector.detect_pose(image)
                if keypoints is None:
                    continue
                
                # Check confidence - use higher threshold for template generation
                # We want only high-quality poses for accurate templates
                confidence = np.mean(keypoints[:, 2])
                if confidence < 0.5:  # Higher threshold for template generation
                    continue
                
                # Check that we have enough visible keypoints (at least 12 out of 17)
                visible_keypoints = np.sum(keypoints[:, 2] > 0.3)
                if visible_keypoints < 12:
                    continue
                
                # Calculate angles
                angles = calculate_joint_angles(keypoints)
                if len(angles) > 0:
                    angle_list.append(angles)
            
            except Exception as e:
                # Suppress individual image errors to avoid cluttering output
                # Only show first few errors as examples
                if len(angle_list) == 0 and image_files.index(img_file) < 3:
                    # Show first few errors to help debug
                    pass
                continue
        
        return angle_list
    
    def generate_template(self, angle_list: List[Dict[str, float]], tolerance: float = 10.0) -> Dict:
        """
        Generate angle template from list of angle measurements with improved accuracy.
        Uses IQR (Interquartile Range) to filter outliers and create tighter, more accurate ranges.
        
        Args:
            angle_list: List of angle dictionaries
            tolerance: Default minimum tolerance in degrees
        
        Returns:
            Template dictionary with angle ranges
        """
        if not angle_list:
            return {}
        
        # Get all angle names
        all_angle_names = set()
        for angles in angle_list:
            all_angle_names.update(angles.keys())
        
        template = {}
        
        for angle_name in all_angle_names:
            # Collect all values for this angle
            values = [angles[angle_name] for angles in angle_list if angle_name in angles]
            
            if not values:
                continue
            
            # Convert to numpy array
            values = np.array(values)
            
            # Filter outliers using IQR (Interquartile Range) method
            # This removes poses that are clearly wrong/atypical
            q1 = np.percentile(values, 25)
            q3 = np.percentile(values, 75)
            iqr = q3 - q1
            
            # Only keep values within 1.5 * IQR (standard outlier detection)
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            filtered_values = values[(values >= lower_bound) & (values <= upper_bound)]
            
            # If filtering removed too many values (>50%), use original
            if len(filtered_values) < len(values) * 0.5:
                filtered_values = values
            
            # Calculate statistics on filtered data
            median = np.median(filtered_values)
            mean = np.mean(filtered_values)
            std = np.std(filtered_values)
            
            # Use tighter tolerance: 1.5 * IQR or std, whichever is smaller
            # This creates more accurate reference ranges
            iqr_tolerance = 1.5 * iqr
            std_tolerance = std
            
            # Use the smaller of IQR-based or std-based tolerance for tighter ranges
            # But ensure minimum tolerance for stability
            angle_tolerance = float(max(min(iqr_tolerance, std_tolerance * 1.2), tolerance * 0.6))
            
            # Use median as target (more robust than mean)
            target = float(median)
            
            # Create tighter range: use 1.0 * tolerance instead of full std
            # This makes the "correct" range smaller and more accurate
            range_tolerance = angle_tolerance * 0.8  # 80% of tolerance for min/max range
            
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
        """
        Generate templates for all poses in TOP_POSES.
        
        Args:
            output_dir: Output directory for templates
        """
        if output_dir is None:
            output_dir = config.TEMPLATES_DIR
        
        os.makedirs(output_dir, exist_ok=True)
        
        templates = {}
        
        # Progress bar for overall template generation
        pose_progress = tqdm(config.TOP_POSES, desc="Generating templates", unit="pose", position=0, leave=True)
        
        for pose_name in pose_progress:
            pose_progress.set_description(f"Processing: {pose_name[:40]}...")
            
            # Try to find pose directory
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
            
            # Process images
            angle_list = self.process_pose_images(pose_dir)
            
            if not angle_list:
                pose_progress.write(f"⚠ Warning: No valid angles extracted for {pose_name}")
                continue
            
            # Generate template
            template = self.generate_template(angle_list)
            templates[pose_name] = template
            
            # Save individual template
            template_file = os.path.join(output_dir, f"{pose_name.replace(' ', '_').replace('/', '_')}.json")
            with open(template_file, 'w') as f:
                json.dump(template, f, indent=2)
            
            pose_progress.set_postfix({
                'angles': len(template),
                'images': len(angle_list)
            })
        
        pose_progress.close()
        
        # Save combined template
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

