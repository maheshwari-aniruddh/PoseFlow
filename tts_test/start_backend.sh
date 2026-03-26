#!/bin/bash
# Start the Deepgram TTS backend server

cd "$(dirname "$0")"
echo "🚀 Starting Deepgram TTS Backend..."
echo "📁 Directory: $(pwd)"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Start the server
echo ""
echo "✅ Starting backend server..."
python3 backend.py

