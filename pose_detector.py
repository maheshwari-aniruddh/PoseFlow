"""
MediaPipe Pose Landmarker pose detector
"""
import numpy as np
import cv2
from typing import Tuple, Optional, Dict
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
try:
    from mediapipe import solutions
    from mediapipe.framework.formats import landmark_pb2
    MEDIAPIPE_DRAWING_AVAILABLE = True
except ImportError:
    # Fallback if solutions module not available
    MEDIAPIPE_DRAWING_AVAILABLE = False
    solutions = None
    landmark_pb2 = None
import config

class PoseDetector:
    """MediaPipe Pose Landmarker detector for real-time pose estimation"""
    
    def __init__(self, model_path: str = None):
        """
        Initialize MediaPipe pose detector.
        
        Args:
            model_path: Path to MediaPipe pose_landmarker_full.task file
        """
        if model_path is None:
            model_path = config.MEDIAPIPE_MODEL_PATH
        
        # MediaPipe Pose Landmarker has 33 keypoints (indices 0-32)
        # Map to 17 keypoints for compatibility with existing code
        # Using MediaPipe Pose landmark indices (standard MediaPipe pose landmark order)
        self.mediapipe_to_common = {
            'nose': 0,
            'left_eye': 2,  # LEFT_EYE_INNER
            'right_eye': 5,  # RIGHT_EYE_INNER
            'left_ear': 7,
            'right_ear': 8,
            'left_shoulder': 11,
            'right_shoulder': 12,
            'left_elbow': 13,
            'right_elbow': 14,
            'left_wrist': 15,
            'right_wrist': 16,
            'left_hip': 23,
            'right_hip': 24,
            'left_knee': 25,
            'right_knee': 26,
            'left_ankle': 27,
            'right_ankle': 28
        }
        
        # Initialize MediaPipe Pose Landmarker
        try:
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.PoseLandmarkerOptions(
                base_options=base_options,
                output_segmentation_masks=False,
                min_pose_detection_confidence=0.5,
                min_pose_presence_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.detector = vision.PoseLandmarker.create_from_options(options)
            print(f"✅ MediaPipe Pose Landmarker loaded from {model_path}")
        except Exception as e:
            raise ValueError(f"Failed to load MediaPipe model from {model_path}: {e}")
    
    def detect_pose(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect pose keypoints in image.
        
        Args:
            image: Input image (BGR format from OpenCV)
        
        Returns:
            Keypoints array of shape [17, 3] (x, y, confidence) in original image coordinates
            or None if detection fails
        """
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image_rgb.shape[:2]
        
        # Convert to MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        
        # Detect pose
        detection_result = self.detector.detect(mp_image)
        
        # Check if any pose detected
        if not detection_result.pose_landmarks or len(detection_result.pose_landmarks) == 0:
            return None
        
        # Use first detected pose
        landmarks = detection_result.pose_landmarks[0]
        
        # Convert MediaPipe landmarks (33 keypoints) to common format (17 keypoints)
        keypoints = np.zeros((17, 3), dtype=np.float32)
        
        # Map MediaPipe landmarks to common keypoint indices
        common_keypoint_order = [
            'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
            'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
            'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
            'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
        ]
        
        for idx, keypoint_name in enumerate(common_keypoint_order):
            if keypoint_name in self.mediapipe_to_common:
                mp_idx = self.mediapipe_to_common[keypoint_name]
                if mp_idx < len(landmarks):
                    landmark = landmarks[mp_idx]
                    # MediaPipe coordinates are normalized (0-1), convert to pixel coordinates
                    keypoints[idx, 0] = landmark.x * w  # x coordinate
                    keypoints[idx, 1] = landmark.y * h  # y coordinate
                    keypoints[idx, 2] = landmark.visibility  # visibility/confidence
        
        return keypoints
    
    def detect_and_draw_pose(self, image: np.ndarray) -> Tuple[Optional[np.ndarray], np.ndarray]:
        """
        Detect pose and draw MediaPipe visualization directly on frame.
        
        Args:
            image: Input image (BGR format from OpenCV)
        
        Returns:
            Tuple of (keypoints, annotated_frame)
            - keypoints: Keypoints array [17, 3] or None
            - annotated_frame: Frame with MediaPipe pose visualization drawn
        """
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image_rgb.shape[:2]
        
        # Convert to MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        
        # Detect pose
        detection_result = self.detector.detect(mp_image)
        
        # Get keypoints for processing
        keypoints = None
        if detection_result.pose_landmarks and len(detection_result.pose_landmarks) > 0:
            landmarks = detection_result.pose_landmarks[0]
            
            # Convert MediaPipe landmarks (33 keypoints) to common format (17 keypoints)
            keypoints = np.zeros((17, 3), dtype=np.float32)
            common_keypoint_order = [
                'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
                'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
                'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
                'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
            ]
            
            for idx, keypoint_name in enumerate(common_keypoint_order):
                if keypoint_name in self.mediapipe_to_common:
                    mp_idx = self.mediapipe_to_common[keypoint_name]
                    if mp_idx < len(landmarks):
                        landmark = landmarks[mp_idx]
                        keypoints[idx, 0] = landmark.x * w
                        keypoints[idx, 1] = landmark.y * h
                        keypoints[idx, 2] = landmark.visibility
        
        # Draw MediaPipe pose visualization - USE MANUAL DRAWING FOR RELIABILITY
        annotated_image = image.copy()
        
        if detection_result.pose_landmarks and len(detection_result.pose_landmarks) > 0:
            # Always use manual drawing for more reliable, visible skeleton
            annotated_image = self._draw_pose_manual(annotated_image, detection_result.pose_landmarks[0], h, w)
        
        return keypoints, annotated_image
    
    def _draw_pose_manual(self, image: np.ndarray, landmarks, h: int, w: int) -> np.ndarray:
        """Manual fallback drawing if MediaPipe drawing utils not available - MORE RELIABLE"""
        output = image.copy()
        
        # MediaPipe POSE_CONNECTIONS (33 keypoints) - COMPLETE connections
        connections = [
            # Face/Head
            (0, 1), (1, 2), (2, 3), (3, 7),  # Left eye/ear
            (0, 4), (4, 5), (5, 6), (6, 8),  # Right eye/ear
            # Upper body
            (9, 10),  # Shoulders
            (11, 12),  # Shoulders
            (11, 13), (13, 15),  # Left arm
            (12, 14), (14, 16),  # Right arm
            # Torso
            (11, 23), (12, 24),  # Shoulders to hips
            (23, 24),  # Hips
            # Lower body
            (23, 25), (25, 27),  # Left leg
            (24, 26), (26, 28),  # Right leg
            (27, 29), (27, 31),  # Left foot
            (28, 30), (28, 32),  # Right foot
        ]
        
        # Draw connections with thicker, more visible lines
        for start_idx, end_idx in connections:
            if start_idx < len(landmarks) and end_idx < len(landmarks):
                start_lm = landmarks[start_idx]
                end_lm = landmarks[end_idx]
                # Lower threshold for visibility to show more connections
                if start_lm.visibility > 0.2 and end_lm.visibility > 0.2:
                    start_pt = (int(start_lm.x * w), int(start_lm.y * h))
                    end_pt = (int(end_lm.x * w), int(end_lm.y * h))
                    # Thicker lines with black outline for visibility
                    cv2.line(output, start_pt, end_pt, (0, 0, 0), 4)  # Black outline
                    cv2.line(output, start_pt, end_pt, (0, 255, 0), 3)  # Green line
        
        # Draw landmarks with larger, more visible dots
        for i, lm in enumerate(landmarks):
            if lm.visibility > 0.2:  # Lower threshold
                x, y = int(lm.x * w), int(lm.y * h)
                # Larger, more visible dots
                cv2.circle(output, (x, y), 8, (0, 0, 0), 3)  # Black outline
                cv2.circle(output, (x, y), 6, (0, 0, 255), -1)  # Red fill
                cv2.circle(output, (x, y), 3, (255, 255, 255), -1)  # White center
        
        return output
    
    def get_pose_confidence(self, keypoints: np.ndarray) -> float:
        """
        Calculate overall pose confidence from keypoints.
        
        Args:
            keypoints: Keypoints array [17, 3]
        
        Returns:
            Average confidence score
        """
        if keypoints is None:
            return 0.0
        return float(np.mean(keypoints[:, 2]))
