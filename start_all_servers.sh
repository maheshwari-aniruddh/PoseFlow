#!/bin/bash

# Start All Servers for OneBreath App
echo "============================================================"
echo "🚀 Starting All Servers for OneBreath"
echo "============================================================"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
lsof -ti:5000,5001,5002,5003,8080 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

# Start TTS Backend
echo ""
echo "🔊 [1/3] Starting TTS Backend (port 5001)..."
cd "$SCRIPT_DIR/tts_test"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
python3 backend.py > /tmp/yoga_tts_backend.log 2>&1 &
TTS_PID=$!
cd "$SCRIPT_DIR"
sleep 2

# Start Yoga API Server
echo "🧘 [2/3] Starting Yoga API Server (port 5002)..."
source .venv/bin/activate 2>/dev/null || python3 -m venv .venv && source .venv/bin/activate
pip install -q Flask Flask-CORS Flask-SocketIO python-socketio 2>/dev/null
python3 yoga_api_server.py > /tmp/yoga_api_server.log 2>&1 &
YOGA_PID=$!
sleep 3

# Start Web App
echo "🌐 [3/3] Starting Web App (port 5003)..."
cd "$SCRIPT_DIR/one-breath-app"
if [ ! -d "node_modules" ]; then
    npm install --silent
fi
npm run dev > /tmp/onebreath_app.log 2>&1 &
WEB_PID=$!
cd "$SCRIPT_DIR"
sleep 3

echo ""
echo "============================================================"
echo "✅ All Servers Started!"
echo "============================================================"
echo ""
echo "🌐 Web App: http://localhost:5003"
echo "📡 TTS Backend: http://localhost:5001"
echo "🧘 Yoga API: http://localhost:5002"
echo ""
echo "👉 Open http://localhost:5003 in your browser"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "============================================================"
echo ""

# Wait for user interrupt
trap "echo ''; echo '🛑 Stopping all servers...'; kill $TTS_PID $YOGA_PID $WEB_PID 2>/dev/null; exit" INT TERM

# Keep script running
wait

