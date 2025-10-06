
import os
import json
import webbrowser
import threading
import requests
from dotenv import load_dotenv
from flask import Flask
import speech_recognition as sr
import pyttsx3

# --- Load environment variables ---
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set in .env file")

# --- Initialize TTS ---
tts = pyttsx3.init()

# --- Voice Assistant class ---
class VoiceAssistant:
    def __init__(self):
        self.sr = sr.Recognizer()
        self.tts = tts

    def speak(self, text):
        """Speak text using TTS and print to console"""
        print("Assistant:", text)
        if self.tts:
            self.tts.say(text)
            self.tts.runAndWait()

    def ask_gemini(self, question):
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": GEMINI_API_KEY
        }
        payload = {"contents": [{"parts": [{"text": question}]}]}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            print("DEBUG - Gemini response:", json.dumps(data, indent=2))  # <-- debug

            # Extract text safely
            candidates = data.get("candidates", [])
            if not candidates:
                return "No response from AI"

            content_list = candidates[0].get("content", [])
            if not content_list:
                return "No response from AI"

            # Loop through content to get first text
            for content in content_list:
                parts = content.get("parts", [])
                if parts:
                    for part in parts:
                        text = part.get("text")
                        if text:
                            return text
                elif "text" in content:  # some responses may have text directly
                    return content["text"]

            return "No response from AI"

        except Exception as e:
            return f"AI query failed: {e}"



    def listen_and_handle(self, timeout=10, phrase_time_limit=15):
        """Listen to user via microphone, handle commands or AI queries"""
        if not self.sr:
            self.speak("Speech recognition not available.")
            return

        try:
            with sr.Microphone() as source:
                self.sr.adjust_for_ambient_noise(source, duration=1)
                self.speak("Listening...")
                try:
                    audio = self.sr.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                    text = self.sr.recognize_google(audio).lower()
                except sr.WaitTimeoutError:
                    self.speak("Listening timed out. Please speak again.")
                    return
                except Exception as e:
                    self.speak(f"Speech error: {e}")
                    return
        except Exception as e:
            self.speak(f"Microphone error: {e}")
            return

        print("User said:", text)

        # --- Handle commands ---
        if "open google" in text:
            self.speak("Opening Google")
            webbrowser.open("https://www.google.com")
        elif "open youtube" in text:
            self.speak("Opening YouTube")
            webbrowser.open("https://www.youtube.com")
        else:
            answer = self.ask_gemini(text)
            self.speak(answer)

# --- Initialize assistant ---
assistant = VoiceAssistant()

# --- Continuous voice loop ---
def start_voice_loop():
    assistant.speak("Voice assistant started. Say a command...")
    try:
        while True:
            assistant.listen_and_handle()
    except KeyboardInterrupt:
        assistant.speak("Voice assistant stopped.")

# --- Flask API ---
app = Flask(__name__)

@app.route("/")
def hello():
    return "Voice IoT Assistant API running"

# --- Main entry ---
if __name__ == "__main__":
    # Start voice loop in background thread
    threading.Thread(target=start_voice_loop, daemon=True).start()
    # Start Flask server
    app.run(host="0.0.0.0", port=5001, debug=False)
