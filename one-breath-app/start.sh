#!/bin/bash

# PoseFlow App - Startup Script
echo "============================================================"
echo "🌬️  PoseFlow App - Starting..."
echo "============================================================"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo "✅ Dependencies installed!"
fi

echo ""
echo "🚀 Starting development server..."
echo "============================================================"
echo "✅ Server will be available at: http://localhost:8080"
echo ""
echo "Press Ctrl+C to stop"
echo "============================================================"
echo ""

# Start Vite dev server
npm run dev

