# PoseFlow Core ML

This repository contains the core machine learning and real-time pose detection logic for the PoseFlow project.

## Features
- **Real-Time Pose Detection**: Powered by MediaPipe.
- **Pose Classification**: KNN-based classifier trained on the Yoga-82 dataset.
- **Form Correction**: Real-time feedback logic (Joint angle analysis).
- **Session Tracking**: Duration and scoring metrics.
- **API Server**: Flask-based server for real-time communication.

## Structure
- `pose_detector.py`: MediaPipe integration.
- `pose_classifier.py`: Pose classification logic.
- `form_corrector.py`: Real-time feedback.
- `session_tracker.py`: Progress tracking.
- `yoga_api_server.py`: Backend API and WebSocket server.
- `utils/`: Calculation utilities and angles.
- `models/`: Trained models for pose classification.

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Download `pose_landmarker_full.task` and place it in the root.
3. Run the API server:
   ```bash
   python yoga_api_server.py
   ```
