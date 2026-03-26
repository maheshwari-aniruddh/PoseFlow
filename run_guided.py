import sys
import cv2
from guided_session import GuidedSession
from yoga_program import YogaProgram
def main():
    print("="*60)
    print("🧘 YogaBuddy - Guided Session")
    print("="*60)
    session = GuidedSession()
    program_manager = YogaProgram()
    print("\n📋 Available Programs:")
    programs = program_manager.list_programs()
    for i, prog_name in enumerate(programs):
        prog = program_manager.get_program(prog_name)
        print(f"  {i+1}. {prog['name']} - {prog['description']}")
    if len(sys.argv) > 1:
        program_name = sys.argv[1]
    else:
        try:
            choice = input(f"\nSelect program (1-{len(programs)}) or name: ").strip()
            if choice.isdigit():
                program_name = programs[int(choice) - 1]
            else:
                program_name = choice
        except (ValueError, IndexError, KeyboardInterrupt):
            print("Using default: beginner")
            program_name = 'beginner'
    camera_id = None
    if len(sys.argv) > 2:
        try:
            camera_id = int(sys.argv[2])
            print(f"Using camera {camera_id} from command line")
        except ValueError:
            pass
    if camera_id is None:
        print("\n📹 Scanning for cameras...")
        available_cameras = session.list_cameras()
        if not available_cameras:
            print("❌ No cameras found!")
            return
        if len(available_cameras) == 1:
            camera_id = available_cameras[0]
            print(f"✅ Using camera {camera_id}")
        else:
            print(f"\n📹 Available cameras: {available_cameras}")
            for cam_id in available_cameras:
                cap = cv2.VideoCapture(cam_id)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                        print(f"  Camera {cam_id}: {int(width)}x{int(height)}")
                    cap.release()
            try:
                choice = input(f"\nSelect camera ({available_cameras[0]}-{available_cameras[-1]}): ").strip()
                camera_id = int(choice)
                if camera_id not in available_cameras:
                    print(f"⚠ Warning: Camera {camera_id} may not work, trying anyway...")
            except (ValueError, KeyboardInterrupt):
                camera_id = available_cameras[0]
                print(f"Using default camera {camera_id}")
    try:
        session.run_guided_session(program_name, camera_id)
    except KeyboardInterrupt:
        print("\n\n👋 Session interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
if __name__ == "__main__":
    main()