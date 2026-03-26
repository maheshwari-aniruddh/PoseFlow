import os
import json
import random
from typing import List, Dict, Optional
import config
class YogaProgram:
    def __init__(self):
        self.programs = {}
        self.load_programs()
    def load_programs(self):
        self.programs['beginner'] = {
            'name': 'Beginner Flow',
            'description': 'Easy standing poses - Tree Pose first!',
            'poses': [
                'Tree_Pose_or_Vrksasana_',
                'Standing_Forward_Bend_pose_or_Uttanasana_',
                'Warrior_I_Pose_or_Virabhadrasana_I_',
                'Warrior_II_Pose_or_Virabhadrasana_II_',
            ],
            'hold_times': [20, 15, 20, 20],
        }
        self.programs['morning'] = {
            'name': 'Morning Energizer',
            'description': 'Easy standing poses - Tree Pose first!',
            'poses': [
                'Tree_Pose_or_Vrksasana_',
                'Standing_Forward_Bend_pose_or_Uttanasana_',
                'Warrior_I_Pose_or_Virabhadrasana_I_',
                'Warrior_II_Pose_or_Virabhadrasana_II_',
            ],
            'hold_times': [20, 15, 20, 20],
        }
        self.programs['flexibility'] = {
            'name': 'Standing Balance',
            'description': 'Easy standing balance - Tree Pose first!',
            'poses': [
                'Tree_Pose_or_Vrksasana_',
                'Standing_Forward_Bend_pose_or_Uttanasana_',
                'Lord_of_the_Dance_Pose_or_Natarajasana_',
                'Tree_Pose_or_Vrksasana_',
            ],
            'hold_times': [20, 15, 20, 20],
        }
        self.programs['custom'] = {
            'name': 'Easy Standing Flow',
            'description': 'All easy standing poses - Tree Pose first!',
            'poses': [
                'Tree_Pose_or_Vrksasana_',
                'Standing_Forward_Bend_pose_or_Uttanasana_',
                'Warrior_I_Pose_or_Virabhadrasana_I_',
                'Warrior_II_Pose_or_Virabhadrasana_II_',
                'Tree_Pose_or_Vrksasana_',
            ],
            'hold_times': [20, 15, 20, 20, 20],
        }
        self.programs['test_all'] = {
            'name': 'Complete Pose Test',
            'description': 'Test all selected poses - Tree Pose first!',
            'poses': [
                'Tree_Pose_or_Vrksasana_',
                'Boat_Pose_or_Paripurna_Navasana_',
                'Bound_Angle_Pose_or_Baddha_Konasana_',
                'Cat_Cow_Pose_or_Marjaryasana_',
                'Chair_Pose_or_Utkatasana_',
                'Corpse_Pose_or_Savasana_',
                'Dolphin_Plank_Pose_or_Makara_Adho_Mukha_Svanasana_',
                'Extended_Puppy_Pose_or_Uttana_Shishosana_',
                'Extended_Revolved_Side_Angle_Pose_or_Utthita_Parsvakonasana_',
                'Four-Limbed_Staff_Pose_or_Chaturanga_Dandasana_',
                'Garland_Pose_or_Malasana_',
                'Gate_Pose_or_Parighasana_',
                'Happy_Baby_Pose_or_Ananda_Balasana_',
                'Locust_Pose_or_Salabhasana_',
                'Low_Lunge_pose_or_Anjaneyasana_',
                'Sitting pose 1 (normal)',
                'Staff_Pose_or_Dandasana_',
                'Plank_Pose_or_Kumbhakasana_',
                'Supta_Baddha_Konasana_',
                'viparita_virabhadrasana_or_reverse_warrior_pose',
                'Virasana_or_Vajrasana',
                'Warrior_I_Pose_or_Virabhadrasana_I_',
                'Warrior_II_Pose_or_Virabhadrasana_II_',
                'Wind_Relieving_pose_or_Pawanmuktasana',
            ],
            'hold_times': [15] * 24,
        }
    def get_program(self, program_name: str) -> Optional[Dict]:
        return self.programs.get(program_name)
    def list_programs(self) -> List[str]:
        return list(self.programs.keys())
    def get_pose_image_path(self, pose_name: str) -> Optional[str]:
        def normalize(s: str) -> str:
            return s.lower().replace('_', ' ').replace('-', ' ').replace('(', '').replace(')', '').strip()
        for split in ['train', 'valid', 'test']:
            pose_dir = os.path.join(config.DATASET_ROOT, split, pose_name)
            if os.path.exists(pose_dir):
                image_files = [f for f in os.listdir(pose_dir)
                              if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                if image_files:
                    return os.path.join(pose_dir, image_files[0])
        normalized_pose = normalize(pose_name)
        for split in ['train', 'valid', 'test']:
            split_dir = os.path.join(config.DATASET_ROOT, split)
            if not os.path.exists(split_dir):
                continue
            for folder in os.listdir(split_dir):
                folder_path = os.path.join(split_dir, folder)
                if not os.path.isdir(folder_path):
                    continue
                if normalize(folder) == normalized_pose or normalized_pose in normalize(folder) or normalize(folder) in normalized_pose:
                    image_files = [f for f in os.listdir(folder_path)
                                  if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                    if image_files:
                        return os.path.join(folder_path, image_files[0])
        return None