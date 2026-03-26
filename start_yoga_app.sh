#!/bin/bash

# YogaBuddy - Complete Startup Script
# Starts TTS backend and yoga app together

echo "============================================================"
echo "🧘 YogaBuddy - Starting Everything..."
echo "============================================================"

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# Check and install dependencies
echo "📦 Checking dependencies..."
if ! .venv/bin/python -c "import cv2" 2>/dev/null; then
    echo "📥 Installing dependencies (this may take a minute)..."
    
    # Fix numpy/tensorflow compatibility issues
    echo "🔧 Fixing numpy compatibility..."
    .venv/bin/pip uninstall -y tensorflow tensorflow-gpu tensorflow-macos jax jaxlib 2>/dev/null || true
    .venv/bin/pip install --upgrade "numpy<2.0" --quiet
    
    # Install main dependencies
    .venv/bin/pip install -q -r requirements.txt
    echo "✅ Dependencies installed!"
else
    # Still check for numpy/tensorflow issues and fix if needed
    if ! .venv/bin/python -c "import mediapipe" 2>/dev/null; then
        echo "🔧 Fixing numpy/tensorflow compatibility..."
        .venv/bin/pip uninstall -y tensorflow tensorflow-gpu tensorflow-macos jax jaxlib 2>/dev/null || true
        .venv/bin/pip install --upgrade "numpy<2.0" --quiet
        .venv/bin/pip install --upgrade mediapipe --quiet
    fi
    echo "✅ Dependencies already installed"
fi

# Function to kill processes on a port
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        echo "🛑 Killing processes on port $port..."
        kill -9 $pids 2>/dev/null
        sleep 1
    fi
}

# Kill existing processes
echo ""
echo "🧹 Cleaning up existing processes..."
kill_port 5001
kill_port 8000

# Trap Ctrl+C to cleanup
cleanup() {
    echo ""
    echo "🛑 Stopping all services..."
    kill_port 5001
    kill_port 8000
    pkill -f "run_guided.py" 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# Start TTS backend
echo ""
echo "🔊 Starting TTS backend (port 5001)..."
cd tts_test

# Check if TTS venv exists, create if not
if [ ! -d "venv" ]; then
    echo "📦 Creating TTS virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
else
    source venv/bin/activate
fi

# Start backend in background
python3 backend.py > /tmp/yoga_tts_backend.log 2>&1 &
TTS_BACKEND_PID=$!

cd "$SCRIPT_DIR"

# Wait for backend to be ready
echo "⏳ Waiting for TTS backend to start..."
sleep 3

# Check if backend is running
if ! curl -s http://localhost:5001/health > /dev/null 2>&1; then
    echo "⚠️  TTS backend may not be ready, but continuing..."
else
    echo "✅ TTS backend is ready!"
fi

# Get program name and camera ID from arguments
PROGRAM_NAME=${1:-"test_all"}
CAMERA_ID=${2:-0}

echo ""
echo "🧘 Starting yoga app..."
echo "   Program: $PROGRAM_NAME"
echo "   Camera: $CAMERA_ID"
echo ""
echo "============================================================"
echo "✅ Everything is running!"
echo "============================================================"
echo "📡 TTS Backend: http://localhost:5001"
echo "🧘 Yoga App: Running with program '$PROGRAM_NAME'"
echo ""
echo "Press Ctrl+C to stop everything"
echo "============================================================"
echo ""

# Run the yoga app (foreground, so we can see output)
# Use venv Python explicitly
.venv/bin/python run_guided.py "$PROGRAM_NAME" "$CAMERA_ID"

# Cleanup on exit
cleanup

