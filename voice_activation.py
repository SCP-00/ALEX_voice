#!/usr/bin/env python3
"""
Alex Voice — Voice Activation Module
======================================
Wake word detection + active listening loop + AEC (Acoustic Echo Cancellation).

Wake words:
  - Spanish:   "Oye Alex"     → opens Conversation mode (ES) + greets in Spanish
  - English:   "Hey Alan"     → opens Conversation mode (EN) + greets in English
  - Japanese:  "Oie Alexis san" → opens Conversation mode (JA) + greets in Japanese

AEC Strategy:
  - Mute microphone while TTS is playing (already implemented in frontend)
  - Use echo cancellation + noise suppression constraints in getUserMedia
  - Add 500ms buffer after TTS before re-enabling mic (already implemented)
  - Voice activity detection (VAD) to filter out non-speech

Architecture:
  This module runs as a background thread. It listens to the microphone
  continuously and detects wake words using speech_recognition (offline).
  When a wake word is detected, it:
    1. Sends a greeting to the appropriate server
    2. Opens the browser
    3. Enters active listening mode (continuous ASR)

Dependencies:
    pip install speechrecognition pyaudio pyttsx3
"""

import os
import sys
import time
import threading
import webbrowser
import json
import urllib.request
from pathlib import Path

# ── Config ──
PROJECT_ROOT = Path(__file__).parent.resolve()
MENU_URL = "http://localhost:5000"
CONV_URL = "http://localhost:3001"

# Wake words per language
WAKE_WORDS = {
    "es": ["oye alex", "hola alex", "alex"],
    "en": ["hey alan", "hello alan", "alan"],
    "ja": ["oie alexis san", "oie alexis", "alexis san", "alexis"],
}

# Greetings per language (sent to the LLM after wake word detection)
GREETINGS = {
    "es": "¡Hola Alex! Soy Alex Voice. ¿En qué puedo ayudarte hoy?",
    "en": "Hey Alan! I'm Alex Voice. How can I help you today?",
    "ja": "おい、アレクシスさん！アレクシスボイスです。何かお手伝いしましょうか？",
}

# ── Logging ──
def log_info(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [Voice] [INFO] {msg}")

def log_err(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [Voice] [ERROR] {msg}")

# ── Wake Word Detector ──
class WakeWordDetector:
    """Continuous wake word detection using speech_recognition + Sphinx (offline)."""

    def __init__(self):
        self._running = False
        self._thread = None
        self._listening = False  # active listening mode after wake word
        self._detected_lang = None
        self._recognizer = None
        self._mic = None
        self._lock = threading.Lock()
        self._aec_enabled = True  # acoustic echo cancellation
        self._tts_playing = False  # tracks whether TTS is currently playing

    # ── AEC: mute mic during playback ──
    def set_tts_playing(self, playing):
        """Called by the frontend/server to indicate TTS playback state."""
        with self._lock:
            self._tts_playing = playing

    def is_mic_muted(self):
        """Returns True if mic should be muted (AEC)."""
        with self._lock:
            return self._tts_playing

    def start(self):
        """Start the wake word detection thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._detect_loop, daemon=True)
        self._thread.start()
        log_info("Wake word detection started")
        return True

    def stop(self):
        """Stop wake word detection."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        log_info("Wake word detection stopped")

    def _detect_loop(self):
        """Main detection loop - listens for wake words continuously."""
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            try:
                self._mic = sr.Microphone()
            except (OSError, AttributeError) as e:
                log_err(f"No microphone/audio input available: {e}")
                log_err("This environment appears headless or has no audio hardware.")
                log_err("Run on a desktop with a working ALSA/PulseAudio setup and a microphone.")
                self._running = False
                return

            # Calibrate for ambient noise
            log_info("Calibrating microphone for ambient noise...")
            with self._mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=1)
            log_info("Microphone calibrated")

            while self._running:
                try:
                    # AEC: skip listening if TTS is playing
                    if self.is_mic_muted():
                        time.sleep(0.2)
                        continue

                    # Listen in chunks (2s max)
                    with self._mic as source:
                        audio = self._recognizer.listen(
                            source, timeout=0.5, phrase_time_limit=2
                        )

                    # Try to recognize offline with Sphinx
                    try:
                        text = self._recognizer.recognize_sphinx(audio).lower().strip()
                    except sr.UnknownValueError:
                        continue  # No speech detected
                    except sr.RequestError:
                        continue

                    if not text or len(text) < 3:
                        continue

                    log_info(f"Heard: '{text}'")

                    # Check for wake words
                    detected_lang = self._check_wake_words(text)
                    if detected_lang:
                        self._on_wake_word(detected_lang)
                        break  # Exit loop after wake word

                except sr.WaitTimeoutError:
                    continue  # No speech in timeout window
                except Exception as e:
                    log_err(f"Detection error: {e}")
                    time.sleep(0.5)

        except ImportError:
            log_err(
                "speech_recognition not installed.\n"
                "  Install: pip install speechrecognition pyaudio\n"
                "  For offline wake word detection (recommended):\n"
                "    Ubuntu/Debian: apt install python3-pyaudio portaudio19-dev\n"
                "    Then: pip install pocketsphinx\n"
                "  Or use Google Web Speech API (requires internet):\n"
                "    pip install google-cloud-speech"
            )
        except Exception as e:
            log_err(f"Fatal error: {e}")
            self._running = False

    def _check_wake_words(self, text):
        """Check if the text contains any wake word. Returns language code or None."""
        for lang, words in WAKE_WORDS.items():
            for ww in words:
                if ww in text:
                    log_info(f"Wake word detected: '{ww}' ({lang})")
                    return lang
        return None

    def _on_wake_word(self, lang):
        """Called when a wake word is detected. Opens the mode and sends greeting."""
        log_info(f"🎤 Wake word: {lang.upper()} — activating Alex Voice...")

        # 1. Stop the detection loop (we'll be in active listening mode via the browser)
        self._running = False

        # 2. Start conversation mode via menu
        try:
            req = urllib.request.Request(
                f"{MENU_URL}/api/start/conv",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                if result.get("url"):
                    webbrowser.open(result["url"])

            # 3. Wait for server to be ready (poll /api/stats instead of sleep)
            for attempt in range(20):  # Up to ~40s wait
                try:
                    with urllib.request.urlopen(f"{CONV_URL}/api/stats", timeout=2) as check:
                        break
                except:
                    time.sleep(2)
            greeting = GREETINGS.get(lang, GREETINGS["es"])
            chat_req = urllib.request.Request(
                f"{CONV_URL}/api/chat",
                data=json.dumps({
                    "messages": [
                        {"role": "system", "content": f"You are Alex Voice, a voice assistant. The user just activated you with a wake word. Greet them warmly in {'Spanish' if lang == 'es' else 'English' if lang == 'en' else 'Japanese'}. Keep it brief and friendly."},
                        {"role": "user", "content": greeting}
                    ],
                    "mode": "conversation",
                    "n_predict": 150,
                    "temperature": 0.7,
                    "stream": False,
                }).encode(),
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(chat_req, timeout=30) as resp:
                    chat_data = json.loads(resp.read().decode())
                    content = chat_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if content:
                        log_info(f"🤖 Greeting: {content[:100]}...")
            except Exception as e:
                log_err(f"Greeting failed: {e}")

        except Exception as e:
            log_err(f"Failed to activate: {e}")


# ── Active Listening Loop ──
class ActiveListeningLoop:
    """
    Active listening mode - after wake word, continuously listens
    for voice input and sends it to the conversation server.
    
    Uses VAD (Voice Activity Detection) to filter silence.
    Uses AEC (mute detection) to avoid hearing own output.
    """

    def __init__(self, server_url=CONV_URL):
        self._running = False
        self._server_url = server_url
        self._listening = False

    def start(self):
        """Start active listening loop."""
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            try:
                self._mic = sr.Microphone()
            except (OSError, AttributeError) as e:
                log_err(f"No microphone/audio input available: {e}")
                self._running = False
                return
            self._running = True

            log_info("Active listening loop started")
            log_info("AEC: microphone will be muted during TTS playback")
            log_info("VAD: voice activity detection enabled")

            while self._running:
                try:
                    with self._mic as source:
                        self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
                        audio = self._recognizer.listen(
                            source, timeout=0.3, phrase_time_limit=5
                        )

                    # AEC check is handled by the frontend (mutes mic during playback)
                    # Here we just transcribe and send
                    try:
                        text = self._recognizer.recognize_sphinx(audio).lower().strip()
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError:
                        continue

                    if not text or len(text) < 2:
                        continue

                    log_info(f"🎤 Heard: '{text}'")

                    # Send to conversation server
                    self._send_to_server(text)

                except sr.WaitTimeoutError:
                    continue
                except Exception as e:
                    log_err(f"Listen error: {e}")
                    time.sleep(0.5)

        except ImportError:
            log_err("speech_recognition not installed for active listening")

    def stop(self):
        self._running = False

    def _send_to_server(self, text):
        """Send transcribed text to the conversation server."""
        try:
            req = urllib.request.Request(
                f"{self._server_url}/api/chat",
                data=json.dumps({
                    "messages": [{"role": "user", "content": text}],
                    "mode": "conversation",
                    "n_predict": 256,
                    "temperature": 0.7,
                    "stream": False,
                }).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content:
                    log_info(f"🤖 Response: {content[:100]}...")
        except Exception as e:
            log_err(f"Send failed: {e}")


# ── Dependency Check ──
def check_dependencies():
    """Check if required dependencies are installed. Returns list of missing ones."""
    missing = []
    try:
        import speech_recognition
    except ImportError:
        missing.append("speechrecognition")
    try:
        import pyaudio
    except ImportError:
        missing.append("pyaudio")
    # Check for pocketsphinx (needed for recognize_sphinx offline mode)
    try:
        import pocketsphinx
    except ImportError:
        missing.append("pocketsphinx (or vosk for offline recognition)")
    return missing


def install_instructions():
    """Print install instructions for missing dependencies."""
    print("\n" + "=" * 50)
    print("  Alex Voice — Voice Activation Setup")
    print("=" * 50)
    print("\n  Required dependencies:")
    print("    pip install speechrecognition pyaudio")
    print("\n  For offline wake word detection (recommended):")
    print("    Ubuntu/Debian:")
    print("      apt install python3-pyaudio portaudio19-dev")
    print("      pip install pocketsphinx")
    print("    Or use Vosk (better accuracy, easier install):")
    print("      pip install vosk")
    print("\n  Alternative (Google Web Speech API, requires internet):")
    print("      pip install google-cloud-speech")
    print("\n" + "=" * 50 + "\n")


# ── Main Entry Point ──
def main():
    """Start the voice activation system."""
    # Check dependencies first
    missing = check_dependencies()
    if missing:
        print(f"\n[Voice] ❌ Missing dependencies: {', '.join(missing)}")
        install_instructions()
        return

    print(f"\n{'='*50}")
    print(f"  Alex Voice — Voice Activation Module")
    print(f"  Wake words: Oye Alex (ES) · Hey Alan (EN) · Oie Alexis san (JA)")
    print(f"  AEC: Mic muted during TTS playback + 500ms buffer")
    print(f"  VAD: Voice activity detection enabled")
    print(f"{'='*50}\n")
    print(f"  Say one of the wake words to activate:")
    print(f"    🇪🇸  'Oye Alex' — Conversación en español")
    print(f"    🇬🇧  'Hey Alan' — English conversation")
    print(f"    🇯🇵  'おい、アレクシスさん' — 日本語会話")
    print(f"\n  Press Ctrl+C to stop.\n")

    detector = WakeWordDetector()
    detector.start()

    # Start active listening loop in background (runs after wake word triggers it)
    listener = ActiveListeningLoop()
    
    # Patch: when wake word is detected, start the active listening loop
    original_on_wake = detector._on_wake_word
    
    def patched_on_wake(lang):
        try:
            original_on_wake(lang)
            # Start active listening in a new thread
            t = threading.Thread(target=listener.start, daemon=True)
            t.start()
        except Exception as e:
            log_err(f"Wake word handler failed: {e}")
    
    detector._on_wake_word = patched_on_wake

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Voice] Stopping...")
    finally:
        detector.stop()
        listener.stop()
        print("[Voice] Stopped.")


if __name__ == "__main__":
    main()
