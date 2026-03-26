import requests
import time
from typing import Optional
import threading
class TTSClient:
    def __init__(self, backend_url: str = "http://localhost:5001/speak", voice: str = "arcas"):
        self.backend_url = backend_url
        self.voice = voice
        self.last_speak_time = 0.0
        self.speak_cooldown = 3.0
        self.current_audio = None
        self.speaking = False
    def speak(self, text: str, voice: Optional[str] = None, force: bool = False) -> bool:
        if not text or not text.strip():
            return False
        current_time = time.time()
        if not force and (current_time - self.last_speak_time) < self.speak_cooldown:
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
        thread = threading.Thread(target=_speak_thread, daemon=True)
        thread.start()
        return True
    def speak_simple(self, text: str, voice: Optional[str] = None) -> bool:
        if not text or not text.strip():
            return False
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
                    import tempfile
                    import subprocess
                    import os
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                        f.write(response.content)
                        temp_path = f.name
                    try:
                        if os.name == 'nt':
                            os.startfile(temp_path)
                        elif os.name == 'posix':
                            subprocess.Popen(['afplay', temp_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except:
                        pass
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