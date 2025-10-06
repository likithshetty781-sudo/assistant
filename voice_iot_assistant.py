import os
import json
import webbrowser
import threading
import requests
from flask import Flask
import speech_recognition as sr
import pyttsx3
import re
import time
import subprocess
import platform
import shutil
import getpass

# --- CONFIG ---
USER = getpass.getuser()
PLATFORM = platform.system()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "YOUR_GEMINI_API_KEY"

# --- Apps dictionary (add more apps as needed) ---
apps = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        fr"C:\Users\{USER}\AppData\Local\Google\Chrome\Application\chrome.exe",
        "chrome.exe"
    ],
    "edge": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "msedge.exe"
    ],
    "vlc": [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        "vlc.exe"
    ],
    "code": [
        fr"C:\Users\{USER}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        "code"
    ],
}

# --- Initialize TTS (Windows SAPI5) ---
def init_tts():
    try:
        engine = pyttsx3.init("sapi5")  # Windows TTS
    except Exception:
        engine = pyttsx3.init()  # fallback

    engine.setProperty("rate", 170)  # speaking speed
    engine.setProperty("volume", 1.0)  # full volume
    voices = engine.getProperty("voices")
    if voices:
        engine.setProperty("voice", voices[0].id)  # use first available voice
    return engine

tts = init_tts()

def speak(text):
    if not text:
        return
    print("Assistant:", text)
    tts.say(text)
    tts.runAndWait()  # always flush before continuing

# --- Voice Assistant Class ---
class VoiceAssistant:
    def __init__(self):
        self.sr = sr.Recognizer()

    def ask_gemini(self, question):
        """Query Gemini AI"""
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {"Content-Type": "application/json", "X-goog-api-key": GEMINI_API_KEY}
        payload = {"contents": [{"parts": [{"text": question}]}]}
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            r.raise_for_status()
            data = r.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return "No response from AI."
            content = candidates[0].get("content", [])
            if isinstance(content, dict):
                content = [content]
            all_text = []
            for item in content:
                parts = item.get("parts", [])
                for part in parts:
                    t = part.get("text")
                    if t:
                        all_text.append(t.strip())
                if "text" in item:
                    all_text.append(item["text"].strip())
            return " ".join(all_text) if all_text else "No response from AI."
        except Exception as e:
            return f"AI query failed: {e}"

    def try_launch(self, candidate):
        """Launch Windows app"""
        try:
            if os.path.isabs(candidate) and os.path.exists(candidate):
                os.startfile(candidate)
                return True
            found = shutil.which(candidate)
            if found:
                subprocess.Popen([found])
                return True
            subprocess.Popen(f'start "" "{candidate}"', shell=True)
            return True
        except Exception:
            return False

    def open_app_by_name(self, app_key):
        candidates = apps.get(app_key)
        if not candidates:
            return False
        if isinstance(candidates, str):
            candidates = [candidates]
        for c in candidates:
            if self.try_launch(c):
                return True
        return False

    def listen_and_handle(self, timeout=10, phrase_time_limit=15):
        try:
            with sr.Microphone() as source:
                self.sr.adjust_for_ambient_noise(source, duration=1)
                print("Listening...")
                speak("Listening...")
                try:
                    audio = self.sr.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                    text = self.sr.recognize_google(audio).lower()
                except sr.WaitTimeoutError:
                    speak("Listening timed out. Please speak again.")
                    return
                except Exception as e:
                    speak(f"Speech error: {e}")
                    return
        except Exception as e:
            speak(f"Microphone error: {e}")
            return

        print("User said:", text)

        # --- Voice commands ---
        if "open google" in text:
            speak("Opening Google")
            webbrowser.open("https://www.google.com")
        elif "open youtube" in text:
            speak("Opening YouTube")
            webbrowser.open("https://www.youtube.com")
        elif text in apps:
            speak(f"Opening {text}")
            if self.open_app_by_name(text):
                speak(f"{text} opened.")
            else:
                speak(f"Failed to open {text}.")
        else:
            speak("Let me think...")
            answer = self.ask_gemini(text)
            speak(answer)

# --- Initialize assistant ---
assistant = VoiceAssistant()

# --- Flask API ---
app = Flask(__name__)

@app.route("/")
def hello():
    return "Voice IoT Assistant API running"

# --- Run voice assistant in main thread, Flask in separate thread ---
def start_flask():
    app.run(host="0.0.0.0", port=5001, debug=False)

if __name__ == "__main__":
    threading.Thread(target=start_flask, daemon=True).start()
    speak("Voice assistant started. Say a command...")
    try:
        while True:
            assistant.listen_and_handle()
    except KeyboardInterrupt:
        speak("Voice assistant stopped.")

