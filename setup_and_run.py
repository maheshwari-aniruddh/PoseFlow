import os
import sys
from tqdm import tqdm
from template_generator import TemplateGenerator
from pose_classifier import PoseClassifier
import config
def check_dataset():
    if not os.path.exists(config.DATASET_ROOT):
        print(f"❌ Dataset not found at: {config.DATASET_ROOT}")
        print("   Please download the dataset first!")
        print("   See DOWNLOAD_DATASET.md for instructions")
        return False
    train_dir = config.TRAIN_DIR
    if not os.path.exists(train_dir):
        print(f"❌ Train directory not found: {train_dir}")
        return False
    missing = []
    for pose in config.TOP_POSES:
        pose_path = os.path.join(train_dir, pose)
        if not os.path.exists(pose_path):
            missing.append(pose)
    if missing:
        print(f"❌ Missing {len(missing)} poses:")
        for pose in missing[:5]:
            print(f"   - {pose}")
        return False
    print(f"✅ Dataset found: {len(config.TOP_POSES)} poses available")
    return True
def setup_templates():
    print("\n" + "="*60)
    print("📐 [1/2] Generating Angle Templates")
    print("="*60)
    print(f"📋 Processing {len(config.TOP_POSES)} poses...")
    generator = TemplateGenerator()
    generator.generate_all_templates()
    print("✅ Templates generated!")
    return True
def setup_classifier():
    print("\n" + "="*60)
    print("🤖 [2/2] Training Pose Classifier")
    print("="*60)
    print(f"📋 Training on {len(config.TOP_POSES)} poses...")
    classifier = PoseClassifier()
    classifier.train()
    print("\n💾 Saving classifier...")
    classifier_path = os.path.join(config.MODELS_DIR, "pose_classifier.pkl")
    os.makedirs(config.MODELS_DIR, exist_ok=True)
    classifier.save(classifier_path)
    print(f"✅ Classifier saved to {classifier_path}")
    return True
def run_app(program_name="test_all", camera_id=0):
    print("\n" + "="*60)
    print("🧘 Starting YogaBuddy App")
    print("="*60)
    from guided_session import GuidedSession
    try:
        session = GuidedSession()
        session.run_guided_session(program_name, camera_id)
    except KeyboardInterrupt:
        print("\n\n👋 Session ended. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
def main():
    print("="*60)
    print("🧘 YogaBuddy - Complete Setup & Run")
    print("="*60)
    print("\n📁 [0/3] Checking dataset...")
    if not check_dataset():
        sys.exit(1)
    if not os.path.exists(config.TEMPLATES_DIR) or len(os.listdir(config.TEMPLATES_DIR)) < len(config.TOP_POSES):
        if not setup_templates():
            print("❌ Template generation failed!")
            sys.exit(1)
    else:
        print("\n✅ Templates already exist, skipping generation...")
    classifier_path = os.path.join(config.MODELS_DIR, "pose_classifier.pkl")
    if not os.path.exists(classifier_path):
        if not setup_classifier():
            print("❌ Classifier training failed!")
            sys.exit(1)
    else:
        print("\n✅ Classifier already exists, skipping training...")
    print("\n" + "="*60)
    print("✅ Setup Complete!")
    print("="*60)
    program_name = sys.argv[1] if len(sys.argv) > 1 else "test_all"
    try:
        camera_id = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    except ValueError:
        camera_id = 0
    print(f"\n🚀 Starting app with program: {program_name}, camera: {camera_id}")
    print("   (Press 'q' to quit, RIGHT ARROW to skip pose)\n")
    run_app(program_name, camera_id)
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Setup interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()