"""
Complete setup and run script for YogaBuddy
- Generates angle templates
- Trains classifier
- Runs the app
"""
import os
import sys
from tqdm import tqdm
from template_generator import TemplateGenerator
from pose_classifier import PoseClassifier
import config

def check_dataset():
    """Check if dataset exists"""
    if not os.path.exists(config.DATASET_ROOT):
        print(f"❌ Dataset not found at: {config.DATASET_ROOT}")
        print("   Please download the dataset first!")
        print("   See DOWNLOAD_DATASET.md for instructions")
        return False
    
    train_dir = config.TRAIN_DIR
    if not os.path.exists(train_dir):
        print(f"❌ Train directory not found: {train_dir}")
        return False
    
    # Check if all poses exist
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
    """Generate angle templates for all poses"""
    print("\n" + "="*60)
    print("📐 [1/2] Generating Angle Templates")
    print("="*60)
    print(f"📋 Processing {len(config.TOP_POSES)} poses...")
    
    generator = TemplateGenerator()
    generator.generate_all_templates()
    
    print("✅ Templates generated!")
    return True

def setup_classifier():
    """Train the pose classifier"""
    print("\n" + "="*60)
    print("🤖 [2/2] Training Pose Classifier")
    print("="*60)
    print(f"📋 Training on {len(config.TOP_POSES)} poses...")
    
    classifier = PoseClassifier()
    classifier.train()
    
    # Save classifier
    print("\n💾 Saving classifier...")
    classifier_path = os.path.join(config.MODELS_DIR, "pose_classifier.pkl")
    os.makedirs(config.MODELS_DIR, exist_ok=True)
    classifier.save(classifier_path)
    print(f"✅ Classifier saved to {classifier_path}")
    
    return True

def run_app(program_name="test_all", camera_id=0):
    """Run the guided yoga session"""
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
    """Main setup and run function"""
    print("="*60)
    print("🧘 YogaBuddy - Complete Setup & Run")
    print("="*60)
    
    # Step 0: Check dataset
    print("\n📁 [0/3] Checking dataset...")
    if not check_dataset():
        sys.exit(1)
    
    # Step 1: Generate templates
    if not os.path.exists(config.TEMPLATES_DIR) or len(os.listdir(config.TEMPLATES_DIR)) < len(config.TOP_POSES):
        if not setup_templates():
            print("❌ Template generation failed!")
            sys.exit(1)
    else:
        print("\n✅ Templates already exist, skipping generation...")
    
    # Step 2: Train classifier
    classifier_path = os.path.join(config.MODELS_DIR, "pose_classifier.pkl")
    if not os.path.exists(classifier_path):
        if not setup_classifier():
            print("❌ Classifier training failed!")
            sys.exit(1)
    else:
        print("\n✅ Classifier already exists, skipping training...")
    
    # Step 3: Run app
    print("\n" + "="*60)
    print("✅ Setup Complete!")
    print("="*60)
    
    # Get program and camera from command line or use defaults
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

