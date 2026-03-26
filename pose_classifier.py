"""
Pose classifier using KNN on joint angle features
"""
import os
import numpy as np
import pickle
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import cv2
from pose_detector import PoseDetector
from utils.angles import get_angle_features
import config

class PoseClassifier:
    """KNN-based pose classifier using joint angle features"""
    
    def __init__(self, n_neighbors: int = 5):
        self.n_neighbors = n_neighbors
        self.classifier = None
        self.scaler = StandardScaler()
        self.pose_labels = []
        self.label_to_pose = {}
        self.pose_to_label = {}
    
    def prepare_training_data(self):
        """
        Prepare training data from dataset.
        
        Returns:
            X: Feature matrix
            y: Label vector
        """
        X = []
        y = []
        
        detector = PoseDetector()
        
        # Overall progress bar for poses
        pose_progress = tqdm(enumerate(config.TOP_POSES), total=len(config.TOP_POSES), 
                            desc="Processing poses", unit="pose", position=0, leave=True)
        
        for pose_idx, pose_name in pose_progress:
            pose_progress.set_description(f"Processing: {pose_name[:40]}...")
            
            # Find pose directory
            pose_dir = None
            for split in ['train', 'valid']:
                split_dir = os.path.join(config.DATASET_ROOT, split)
                potential_dir = os.path.join(split_dir, pose_name)
                if os.path.exists(potential_dir):
                    pose_dir = potential_dir
                    break
            
            if pose_dir is None:
                pose_progress.write(f"⚠ Warning: Could not find directory for pose {pose_name}")
                continue
            
            # Process images
            image_files = [f for f in os.listdir(pose_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            image_files = image_files[:100]  # Limit to 100 per pose for speed
            
            valid_samples = 0
            for img_file in tqdm(image_files, desc=f"  {pose_name[:30]}", 
                                leave=False, position=1, unit="img"):
                img_path = os.path.join(pose_dir, img_file)
                try:
                    image = cv2.imread(img_path)
                    if image is None:
                        continue
                    
                    keypoints = detector.detect_pose(image)
                    if keypoints is None:
                        continue
                    
                    confidence = np.mean(keypoints[:, 2])
                    if confidence < config.POSE_CONFIDENCE_THRESHOLD:
                        continue
                    
                    # Extract features
                    features = get_angle_features(keypoints)
                    
                    # Check if features are valid (not all zeros)
                    if np.any(features > 0):
                        X.append(features)
                        y.append(pose_idx)
                        valid_samples += 1
                
                except Exception as e:
                    # Silently skip errors during batch processing
                    # but log if we're getting too many failures
                    if len(X) == 0 and valid_samples == 0 and len(image_files) > 10:
                        # Only log if we've processed several images with no success
                        pass
                    continue
            
            pose_progress.set_postfix({'samples': valid_samples, 'total': len(X)})
        
        pose_progress.close()
        
        return np.array(X), np.array(y)
    
    def train(self, X: np.ndarray = None, y: np.ndarray = None):
        """
        Train the classifier.
        
        Args:
            X: Feature matrix (if None, will prepare from dataset)
            y: Label vector (if None, will prepare from dataset)
        """
        if X is None or y is None:
            print("📊 Preparing training data...")
            X, y = self.prepare_training_data()
        
        if len(X) == 0:
            raise ValueError(
                "No training data available. This could mean:\n"
                "- Pose detection is failing for all images\n"
                "- Images don't contain detectable poses\n"
                "- Model input format is incorrect\n"
                "Check that MediaPipe Pose Landmarker model is working correctly."
            )
        
        print(f"\n🎯 Training on {len(X)} samples from {len(np.unique(y))} poses")
        
        # Create label mappings
        unique_labels = np.unique(y)
        self.pose_labels = [config.TOP_POSES[int(label)] for label in unique_labels]
        self.label_to_pose = {int(label): config.TOP_POSES[int(label)] for label in unique_labels}
        self.pose_to_label = {pose: label for label, pose in self.label_to_pose.items()}
        
        # Scale features
        print("⚙️  Scaling features...")
        X_scaled = self.scaler.fit_transform(X)
        
        # Train classifier
        print("🤖 Training KNN classifier...")
        self.classifier = KNeighborsClassifier(n_neighbors=self.n_neighbors, weights='distance')
        self.classifier.fit(X_scaled, y)
        
        print("✅ Training complete!")
    
    def predict(self, keypoints: np.ndarray) -> tuple:
        """
        Predict pose from keypoints.
        
        Args:
            keypoints: Keypoints array [17, 3]
        
        Returns:
            Tuple of (pose_name, confidence)
        """
        if self.classifier is None:
            print("❌ CLASSIFIER ERROR: Classifier not trained!")
            raise ValueError("Classifier not trained. Call train() first.")
        
        print(f"🔍 CLASSIFIER.predict() called - classifier exists: {self.classifier is not None}")
        
        # Extract features
        features = get_angle_features(keypoints)
        print(f"📊 Features extracted: shape={features.shape}")
        features = features.reshape(1, -1)
        
        # Scale
        features_scaled = self.scaler.transform(features)
        print(f"📏 Features scaled: shape={features_scaled.shape}")
        
        # Predict
        label = self.classifier.predict(features_scaled)[0]
        probabilities = self.classifier.predict_proba(features_scaled)[0]
        confidence = probabilities[label]
        
        pose_name = self.label_to_pose[label]
        print(f"✅ CLASSIFIER RESULT: pose='{pose_name}', confidence={confidence:.3f}, label={label}")
        
        return pose_name, float(confidence)
    
    def save(self, filepath: str):
        """Save classifier to file"""
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump({
                'classifier': self.classifier,
                'scaler': self.scaler,
                'pose_labels': self.pose_labels,
                'label_to_pose': self.label_to_pose,
                'pose_to_label': self.pose_to_label,
                'n_neighbors': self.n_neighbors
            }, f)
    
    def load(self, filepath: str):
        """Load classifier from file"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.classifier = data['classifier']
            self.scaler = data['scaler']
            self.pose_labels = data['pose_labels']
            self.label_to_pose = data['label_to_pose']
            self.pose_to_label = data['pose_to_label']
            self.n_neighbors = data['n_neighbors']

if __name__ == "__main__":
    classifier = PoseClassifier()
    classifier.train()
    os.makedirs(config.MODELS_DIR, exist_ok=True)
    classifier.save(os.path.join(config.MODELS_DIR, "pose_classifier.pkl"))
    print("Classifier saved!")

