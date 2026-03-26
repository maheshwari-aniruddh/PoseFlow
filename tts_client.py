"""
TTS Client for speaking feedback out loud
"""
import requests
import time
from typing import Optional
import threading

class TTSClient:
    """Client for Deepgram TTS backend"""
    
    def __init__(self, backend_url: str = "http://localhost:5001/speak", voice: str = "arcas"):
        """
        Initialize TTS client with Arcas (deep male voice).
        
        Args:
            backend_url: URL of the TTS backend server
            voice: Default voice to use (arcas = deep male voice)
        """
        self.backend_url = backend_url
        self.voice = voice
        self.last_speak_time = 0.0
        self.speak_cooldown = 3.0  # Minimum seconds between speaking
        self.current_audio = None
        self.speaking = False
    
    def speak(self, text: str, voice: Optional[str] = None, force: bool = False) -> bool:
        """
        Speak text using TTS backend.
        
        Args:
            text: Text to speak
            voice: Voice to use (defaults to self.voice)
            force: Force speaking even if cooldown hasn't passed
        
        Returns:
            True if successful, False otherwise
        """
        if not text or not text.strip():
            return False
        
        # Check cooldown
        current_time = time.time()
        if not force and (current_time - self.last_speak_time) < self.speak_cooldown:
            return False
        
        # Don't interrupt if already speaking
        if self.speaking:
            return False
        
        voice_to_use = voice or self.voice
        
        # Speak in background thread to not block
        def _speak_thread():
            try:
                self.speaking = True
                self.last_speak_time = time.time()
                
                response = requests.post(
                    self.backend_url,
                    json={'text': text, 'voice': voice_to_use},
                    timeout=30
                )
                
                if response.status_code == 200:
                    # Get audio and play it
                    import io
                    from pydub import AudioSegment
                    from pydub.playback import play
                    
                    audio_data = response.content
                    audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
                    play(audio)
                else:
                    print(f"TTS Error: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"TTS Error: {e}")
            finally:
                self.speaking = False
        
        # Start in background thread
        thread = threading.Thread(target=_speak_thread, daemon=True)
        thread.start()
        
        return True
    
    def speak_simple(self, text: str, voice: Optional[str] = None) -> bool:
        """
        Simple speak method using subprocess (no pydub dependency).
        
        Args:
            text: Text to speak
            voice: Voice to use
        
        Returns:
            True if successful
        """
        if not text or not text.strip():
            return False
        
        # Check cooldown
        current_time = time.time()
        if (current_time - self.last_speak_time) < self.speak_cooldown:
            return False
        
        if self.speaking:
            return False
        
        voice_to_use = voice or self.voice
        
        def _speak_thread():
            try:
                self.speaking = True
                self.last_speak_time = time.time()
                
                response = requests.post(
                    self.backend_url,
                    json={'text': text, 'voice': voice_to_use},
                    timeout=30
                )
                
                if response.status_code == 200:
                    # Save to temp file and play with system player
                    import tempfile
                    import subprocess
                    import os
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                        f.write(response.content)
                        temp_path = f.name
                    
                    # Play with system audio player
                    try:
                        if os.name == 'nt':  # Windows
                            os.startfile(temp_path)
                        elif os.name == 'posix':  # macOS/Linux
                            subprocess.Popen(['afplay', temp_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except:
                        pass
                    
                    # Clean up after a delay
                    def cleanup():
                        time.sleep(5)
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
                    threading.Thread(target=cleanup, daemon=True).start()
                else:
                    print(f"TTS Error: {response.status_code}")
            except Exception as e:
                print(f"TTS Error: {e}")
            finally:
                self.speaking = False
        
        thread = threading.Thread(target=_speak_thread, daemon=True)
        thread.start()
        
        return True

