# TTS Backend

Deepgram text-to-speech backend for yoga feedback and meditation narration.

## Quick Start

```bash
cd tts_test
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 backend.py
```

Backend runs on: **http://localhost:5001**

## Usage

The backend provides a `/speak` endpoint that accepts:
- `text`: Text to convert to speech
- `voice`: Voice name (default: "arcas")

Used by:
- Yoga feedback system
- Meditation narration

