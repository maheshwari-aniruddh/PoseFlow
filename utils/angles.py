"""
Joint angle calculation utilities
Based on MediaPipe pose angle calculations
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
import config

def calculate_angle(point1: np.ndarray, point2: np.ndarray, point3: np.ndarray) -> float:
    """
    Calculate the angle between three points (point2 is the vertex).
    
    Args:
        point1: First point [x, y]
        point2: Vertex point [x, y]
        point3: Third point [x, y]
    
    Returns:
        Angle in degrees (0-180)
    """
    # Convert to numpy arrays
    p1 = np.array(point1)
    p2 = np.array(point2)
    p3 = np.array(point3)
    
    # Calculate vectors
    v1 = p1 - p2
    v2 = p3 - p2
    
    # Calculate angle using dot product
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle = np.arccos(cos_angle)
    
    return np.degrees(angle)

def extract_keypoint(keypoints: np.ndarray, name: str) -> Optional[np.ndarray]:
    """
    Extract a keypoint by name from keypoints array.
    
    Args:
        keypoints: Array of shape [17, 3] (x, y, confidence)
        name: Keypoint name
    
    Returns:
        [x, y, confidence] or None if not found
    """
    if name not in config.KEYPOINT_INDICES:
        return None
    idx = config.KEYPOINT_INDICES[name]
    return keypoints[idx]

def calculate_joint_angles(keypoints: np.ndarray, return_confidence: bool = False) -> Dict:
    """
    Calculate all relevant joint angles from MediaPipe pose keypoints.
    
    Args:
        keypoints: Array of shape [17, 3] (x, y, confidence)
        return_confidence: If True, also return confidence scores for each angle
    
    Returns:
        Dictionary of angle names to angle values in degrees
        If return_confidence=True, returns {'angles': {...}, 'confidences': {...}}
    """
    angles = {}
    confidences = {}
    
    # Helper to get keypoint coordinates and confidence
    def get_coords(name: str) -> Tuple[Optional[np.ndarray], float]:
        kp = extract_keypoint(keypoints, name)
        if kp is None or kp[2] < config.POSE_CONFIDENCE_THRESHOLD:
            return None, 0.0
        return kp[:2], float(kp[2])
    
    # Left elbow angle
    left_shoulder, ls_conf = get_coords('left_shoulder')
    left_elbow, le_conf = get_coords('left_elbow')
    left_wrist, lw_conf = get_coords('left_wrist')
    if all(p is not None for p in [left_shoulder, left_elbow, left_wrist]):
        angles['left_elbow'] = calculate_angle(left_shoulder, left_elbow, left_wrist)
        confidences['left_elbow'] = min(ls_conf, le_conf, lw_conf)  # Use minimum confidence
    
    # Right elbow angle
    right_shoulder, rs_conf = get_coords('right_shoulder')
    right_elbow, re_conf = get_coords('right_elbow')
    right_wrist, rw_conf = get_coords('right_wrist')
    if all(p is not None for p in [right_shoulder, right_elbow, right_wrist]):
        angles['right_elbow'] = calculate_angle(right_shoulder, right_elbow, right_wrist)
        confidences['right_elbow'] = min(rs_conf, re_conf, rw_conf)
    
    # Left knee angle
    left_hip, lh_conf = get_coords('left_hip')
    left_knee, lk_conf = get_coords('left_knee')
    left_ankle, la_conf = get_coords('left_ankle')
    if all(p is not None for p in [left_hip, left_knee, left_ankle]):
        angles['left_knee'] = calculate_angle(left_hip, left_knee, left_ankle)
        confidences['left_knee'] = min(lh_conf, lk_conf, la_conf)
    
    # Right knee angle
    right_hip, rh_conf = get_coords('right_hip')
    right_knee, rk_conf = get_coords('right_knee')
    right_ankle, ra_conf = get_coords('right_ankle')
    if all(p is not None for p in [right_hip, right_knee, right_ankle]):
        angles['right_knee'] = calculate_angle(right_hip, right_knee, right_ankle)
        confidences['right_knee'] = min(rh_conf, rk_conf, ra_conf)
    
    # Left hip angle (hip-shoulder-knee)
    if all(p is not None for p in [left_shoulder, left_hip, left_knee]):
        angles['left_hip'] = calculate_angle(left_shoulder, left_hip, left_knee)
        confidences['left_hip'] = min(ls_conf, lh_conf, lk_conf)
    
    # Right hip angle
    if all(p is not None for p in [right_shoulder, right_hip, right_knee]):
        angles['right_hip'] = calculate_angle(right_shoulder, right_hip, right_knee)
        confidences['right_hip'] = min(rs_conf, rh_conf, rk_conf)
    
    # Shoulder angle (left_shoulder-right_shoulder-left_hip)
    if all(p is not None for p in [left_shoulder, right_shoulder, left_hip]):
        angles['shoulder_left'] = calculate_angle(left_shoulder, right_shoulder, left_hip)
        confidences['shoulder_left'] = min(ls_conf, rs_conf, lh_conf)
    
    # Spine angle (shoulder-hip-knee vertical alignment)
    if left_shoulder is not None and left_hip is not None and left_knee is not None:
        angles['spine_left'] = calculate_angle(left_shoulder, left_hip, left_knee)
        confidences['spine_left'] = min(ls_conf, lh_conf, lk_conf)
    
    if right_shoulder is not None and right_hip is not None and right_knee is not None:
        angles['spine_right'] = calculate_angle(right_shoulder, right_hip, right_knee)
        confidences['spine_right'] = min(rs_conf, rh_conf, rk_conf)
    
    if return_confidence:
        return {'angles': angles, 'confidences': confidences}
    return angles

def get_angle_features(keypoints: np.ndarray) -> np.ndarray:
    """
    Extract angle features as a vector for classification.
    
    Args:
        keypoints: Array of shape [17, 3]
    
    Returns:
        Feature vector of angles
    """
    angle_data = calculate_joint_angles(keypoints, return_confidence=False)
    # When return_confidence=False, it returns just the angles dict directly
    angles = angle_data
    
    # Standard angle features in a fixed order
    feature_order = [
        'left_elbow', 'right_elbow',
        'left_knee', 'right_knee',
        'left_hip', 'right_hip',
        'shoulder_left', 'spine_left', 'spine_right'
    ]
    
    features = []
    for angle_name in feature_order:
        features.append(angles.get(angle_name, 0.0))
    
    return np.array(features, dtype=np.float32)

