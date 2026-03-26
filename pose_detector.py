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
    MEDIAPIPE_DRAWING_AVAILABLE = False
    solutions = None
    landmark_pb2 = None
import config
class PoseDetector:
    def __init__(self, model_path: str = None):
        if model_path is None:
            model_path = config.MEDIAPIPE_MODEL_PATH
        self.mediapipe_to_common = {
            'nose': 0,
            'left_eye': 2,
            'right_eye': 5,
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
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image_rgb.shape[:2]
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        detection_result = self.detector.detect(mp_image)
        if not detection_result.pose_landmarks or len(detection_result.pose_landmarks) == 0:
            return None
        landmarks = detection_result.pose_landmarks[0]
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
        return keypoints
    def detect_and_draw_pose(self, image: np.ndarray) -> Tuple[Optional[np.ndarray], np.ndarray]:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image_rgb.shape[:2]
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        detection_result = self.detector.detect(mp_image)
        keypoints = None
        if detection_result.pose_landmarks and len(detection_result.pose_landmarks) > 0:
            landmarks = detection_result.pose_landmarks[0]
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
        annotated_image = image.copy()
        if detection_result.pose_landmarks and len(detection_result.pose_landmarks) > 0:
            annotated_image = self._draw_pose_manual(annotated_image, detection_result.pose_landmarks[0], h, w)
        return keypoints, annotated_image
    def _draw_pose_manual(self, image: np.ndarray, landmarks, h: int, w: int) -> np.ndarray:
        output = image.copy()
        connections = [
            (0, 1), (1, 2), (2, 3), (3, 7),
            (0, 4), (4, 5), (5, 6), (6, 8),
            (9, 10),
            (11, 12),
            (11, 13), (13, 15),
            (12, 14), (14, 16),
            (11, 23), (12, 24),
            (23, 24),
            (23, 25), (25, 27),
            (24, 26), (26, 28),
            (27, 29), (27, 31),
            (28, 30), (28, 32),
        ]
        for start_idx, end_idx in connections:
            if start_idx < len(landmarks) and end_idx < len(landmarks):
                start_lm = landmarks[start_idx]
                end_lm = landmarks[end_idx]
                if start_lm.visibility > 0.2 and end_lm.visibility > 0.2:
                    start_pt = (int(start_lm.x * w), int(start_lm.y * h))
                    end_pt = (int(end_lm.x * w), int(end_lm.y * h))
                    cv2.line(output, start_pt, end_pt, (0, 0, 0), 4)
                    cv2.line(output, start_pt, end_pt, (0, 255, 0), 3)
        for i, lm in enumerate(landmarks):
            if lm.visibility > 0.2:
                x, y = int(lm.x * w), int(lm.y * h)
                cv2.circle(output, (x, y), 8, (0, 0, 0), 3)
                cv2.circle(output, (x, y), 6, (0, 0, 255), -1)
                cv2.circle(output, (x, y), 3, (255, 255, 255), -1)
        return output
    def get_pose_confidence(self, keypoints: np.ndarray) -> float:
        if keypoints is None:
            return 0.0
        return float(np.mean(keypoints[:, 2]))