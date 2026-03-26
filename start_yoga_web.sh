#!/bin/bash

# Start Yoga API Server for Web App
echo "============================================================"
echo "🧘 Starting Yoga API Server for Web App"
echo "============================================================"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Check if TTS backend is running
if ! curl -s http://localhost:5001/health > /dev/null 2>&1; then
    echo "⚠️  TTS backend not running. Starting it..."
    cd tts_test
    python3 backend.py > /tmp/yoga_tts_backend.log 2>&1 &
    cd ..
    sleep 2
fi

echo ""
echo "🚀 Starting Yoga API Server..."
echo "============================================================"
echo "📡 API: http://localhost:5002"
echo "🔌 WebSocket: ws://localhost:5002"
echo ""
echo "Press Ctrl+C to stop"
echo "============================================================"
echo ""

# Start API server
python3 yoga_api_server.py

