#!/bin/bash
# Start both backend and frontend servers in one terminal

cd "$(dirname "$0")"

echo "🚀 Starting Deepgram TTS Website..."
echo "📁 Directory: $(pwd)"
echo ""

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "✅ Dependencies installed!"
echo ""

# Start backend in background
echo "🔊 Starting backend server (port 5001)..."
python3 backend.py &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Start frontend in background
echo "🌐 Starting frontend server (port 8000)..."
python3 -m http.server 8000 &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo "✅ Both servers are running!"
echo "=========================================="
echo "📡 Backend:  http://localhost:5001"
echo "🌐 Frontend: http://localhost:8000"
echo ""
echo "👉 Open http://localhost:8000 in your browser"
echo ""
echo "Press Ctrl+C to stop both servers"
echo "=========================================="
echo ""

# Wait for user interrupt
trap "echo ''; echo '🛑 Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

# Keep script running
wait

