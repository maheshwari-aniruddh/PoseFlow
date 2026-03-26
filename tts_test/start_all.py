#!/usr/bin/env python3
"""
Start both backend and frontend servers in one terminal
"""
import subprocess
import sys
import os
import time
import signal

def main():
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("🚀 Starting Deepgram TTS Website...")
    print(f"📁 Directory: {os.getcwd()}")
    print("")
    
    # Create venv if it doesn't exist
    if not os.path.exists("venv"):
        print("📦 Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
    
    # Determine Python executable in venv
    if sys.platform == "win32":
        venv_python = os.path.join("venv", "Scripts", "python.exe")
    else:
        venv_python = os.path.join("venv", "bin", "python3")
    
    # Install dependencies
    print("📥 Installing dependencies...")
    subprocess.run([venv_python, "-m", "pip", "install", "-q", "--upgrade", "pip"], check=True)
    subprocess.run([venv_python, "-m", "pip", "install", "-q", "-r", "requirements.txt"], check=True)
    
    print("")
    print("✅ Dependencies installed!")
    print("")
    
    # Start backend
    print("🔊 Starting backend server (port 5001)...")
    backend = subprocess.Popen([venv_python, "backend.py"])
    
    # Wait a moment for backend to start
    time.sleep(2)
    
    # Start frontend
    print("🌐 Starting frontend server (port 8000)...")
    frontend = subprocess.Popen([sys.executable, "-m", "http.server", "8000"])
    
    print("")
    print("=" * 42)
    print("✅ Both servers are running!")
    print("=" * 42)
    print("📡 Backend:  http://localhost:5001")
    print("🌐 Frontend: http://localhost:8000")
    print("")
    print("👉 Open http://localhost:8000 in your browser")
    print("")
    print("Press Ctrl+C to stop both servers")
    print("=" * 42)
    print("")
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\n🛑 Stopping servers...")
        backend.terminate()
        frontend.terminate()
        backend.wait()
        frontend.wait()
        print("✅ Servers stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Wait for processes
    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()

