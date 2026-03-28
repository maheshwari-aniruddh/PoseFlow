# PoseFLow - Real-Time Yoga Pose Detection & Feedback

A real-time yoga app that provides on-device pose detection, classification, form correction, rep counting, and progress scoring.

## Features

### Yoga App
- **Pose Detection**: MediaPipe Pose Landmarker (30-60 FPS)
- **Pose Classification**: KNN-based classifier trained on Yoga-82 dataset
- **Form Correction**: Real-time feedback (🟢 Green / 🟡 Yellow / 🔴 Red)
- **Rep & Duration Tracking**: Automatic counting
- **Progress Scoring**: Based on form accuracy, hold time, steadiness
- **Text-to-Speech**: Voice feedback using Deepgram TTS (Arcas voice)

### Web App (one-breath-app)
- **Meditation Practices**: Morning, Night, Stress Relief with breathing guidance
- **Yoga Sessions**: Real-time pose detection via WebSocket
- **Personalized Plans**: Based on health level, age, weight
- **Progress Tracking**: Session history and statistics
- **Community Features**: Share progress and connect

## Quick Start

### All-in-One Command

```bash
./start_all_servers.sh
```

This starts:
- TTS Backend (port 5001)
- Yoga API Server (port 5002)  
- Web App (port 8080)

Then open: **http://localhost:8080**

### Manual Setup

1. **Setup Virtual Environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **Download MediaPipe Model:**
Download `pose_landmarker_full.task` from:
https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
Place it in the project root.

3. **Run Setup (if needed):**
```bash
python setup_and_run.py test_all 0
```

### 5. Or Use the Start Script

```bash
./start_yoga_app.sh test_all 0
```

This starts both the TTS backend and the yoga app.

## Manual Setup Steps

### Generate Templates Only

```bash
python -c "from template_generator import TemplateGenerator; TemplateGenerator().generate_all_templates()"
```

### Train Classifier Only

```bash
python -c "from pose_classifier import PoseClassifier; c = PoseClassifier(); c.train(); c.save('models/pose_classifier.pkl')"
```

### Run Guided Session

```bash
python run_guided.py test_all 0
```

## Available Programs

- `test_all` - All 24 poses (15 seconds each)
- `beginner` - Easy standing poses
- `morning` - Morning energizer
- `flexibility` - Standing balance
- `custom` - Easy standing flow

## Controls

- **Q** or **ESC** - Quit
- **RIGHT ARROW (→)** or **N** - Skip to next pose
- **R** - Repeat current instruction

## Supported Poses (24)

The app supports these 24 poses from the Yoga-82 dataset:
- Tree Pose (Vrksasana)
- Warrior I & II
- Boat Pose
- Bound Angle Pose
- Cat-Cow Pose
- Chair Pose
- Corpse Pose
- And 16 more...

See `config.py` for the complete list.

## Project Structure

```
Yogabuddy/
├── config.py                 # Configuration and constants
├── pose_detector.py          # MediaPipe Pose Landmarker detection
├── pose_classifier.py        # KNN pose classifier
├── form_corrector.py         # Form correction feedback
├── session_tracker.py        # Rep/duration tracking & scoring
├── nlg_engine.py             # Natural language feedback generation
├── guided_session.py         # Guided yoga session logic
├── run_guided.py             # Entry point for guided sessions
├── setup_and_run.py          # All-in-one setup script
├── yoga_program.py           # Yoga program definitions
├── tts_client.py             # Text-to-speech client
├── template_generator.py     # Generate angle templates from dataset
├── utils/
│   └── angles.py            # Joint angle calculations
├── templates/               # Generated angle templates (JSON)
├── models/                  # Trained classifier
├── output/                  # Session logs and corrections
├── tts_test/                # TTS test website
│   ├── backend.py           # Flask TTS backend
│   └── index.html           # TTS test frontend
└── one-breath-app/          # React web app
```

## How It Works

1. **Pose Detection**: MediaPipe Pose Landmarker detects 33 keypoints (mapped to 17 for compatibility) in real-time
2. **Feature Extraction**: Joint angles (elbows, knees, hips, spine, shoulders) are calculated
3. **Pose Classification**: KNN classifier matches current pose to trained poses
4. **Form Analysis**: Current angles are compared to template ranges
5. **Feedback**: Visual feedback (color indicator) and audio feedback (TTS) indicate form quality
6. **Tracking**: Reps, durations, and scores are tracked throughout the session

## Configuration

Edit `config.py` to adjust:
- Pose confidence thresholds
- Angle tolerance levels
- Minimum hold duration
- Rep counting window
- Selected poses

## Troubleshooting

### MediaPipe Installation Issues

```bash
# Uninstall TensorFlow if present (not needed)
pip uninstall tensorflow tensorflow-gpu tensorflow-macos -y

# Upgrade numpy
pip install --upgrade "numpy<2.0"

# Install MediaPipe
pip install "mediapipe>=0.10.0"
```

### Protobuf Errors

```bash
pip uninstall tensorflow -y
pip install --force-reinstall "mediapipe>=0.10.0"
```

### Low FPS

- Reduce image processing in `pose_classifier.py`
- Use a smaller webcam resolution
- Close other applications

### Classification Not Working

- Make sure templates were generated successfully
- Check that the classifier was trained (look for `models/pose_classifier.pkl`)
- Try retraining: `python -c "from pose_classifier import PoseClassifier; c = PoseClassifier(); c.train(); c.save('models/pose_classifier.pkl')"`

### TTS Not Working

- Make sure the TTS backend is running: `cd tts_test && python backend.py`
- Check that port 5001 is available
- Verify Deepgram API key in `tts_test/backend.py`

## Dataset

The app uses the Yoga-82 dataset. Place it in the project root as `archive (1) 2/` with `train/`, `test/`, and `valid/` subdirectories.

## License

This project uses the Yoga-82 dataset and MediaPipe Pose Landmarker model. Please refer to their respective licenses.
