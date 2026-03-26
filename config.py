import os
DATASET_ROOT = "archive (2)"
TRAIN_DIR = os.path.join(DATASET_ROOT, "train")
VALID_DIR = os.path.join(DATASET_ROOT, "valid")
TEST_DIR = os.path.join(DATASET_ROOT, "test")
MEDIAPIPE_MODEL_PATH = "pose_landmarker_full.task"
MEDIAPIPE_MODEL_DIR = "."
TEMPLATES_DIR = "templates"
MODELS_DIR = "models"
OUTPUT_DIR = "output"
TOP_POSES = [
    "Boat_Pose_or_Paripurna_Navasana_",
    "Bound_Angle_Pose_or_Baddha_Konasana_",
    "Cat_Cow_Pose_or_Marjaryasana_",
    "Chair_Pose_or_Utkatasana_",
    "Corpse_Pose_or_Savasana_",
    "Dolphin_Plank_Pose_or_Makara_Adho_Mukha_Svanasana_",
    "Extended_Puppy_Pose_or_Uttana_Shishosana_",
    "Extended_Revolved_Side_Angle_Pose_or_Utthita_Parsvakonasana_",
    "Four-Limbed_Staff_Pose_or_Chaturanga_Dandasana_",
    "Garland_Pose_or_Malasana_",
    "Gate_Pose_or_Parighasana_",
    "Happy_Baby_Pose_or_Ananda_Balasana_",
    "Locust_Pose_or_Salabhasana_",
    "Low_Lunge_pose_or_Anjaneyasana_",
    "Sitting pose 1 (normal)",
    "Staff_Pose_or_Dandasana_",
    "Plank_Pose_or_Kumbhakasana_",
    "Supta_Baddha_Konasana_",
    "Tree_Pose_or_Vrksasana_",
    "viparita_virabhadrasana_or_reverse_warrior_pose",
    "Virasana_or_Vajrasana",
    "Warrior_I_Pose_or_Virabhadrasana_I_",
    "Warrior_II_Pose_or_Virabhadrasana_II_",
    "Wind_Relieving_pose_or_Pawanmuktasana",
]
KEYPOINT_NAMES = [
    'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
    'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
    'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
    'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
]
KEYPOINT_INDICES = {name: idx for idx, name in enumerate(KEYPOINT_NAMES)}
ANGLE_TOLERANCE = {
    'dangerous': 15.0,
    'improvable': 7.0,
    'correct': 3.0
}
POSE_CONFIDENCE_THRESHOLD = 0.2
POSE_ENTRY_THRESHOLD = 0.3
POSE_EXIT_THRESHOLD = 0.15
POSE_SIMILARITY_THRESHOLD = 0.2
MIN_HOLD_DURATION = 1.0
REP_COUNT_WINDOW = 2.0