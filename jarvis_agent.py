"""
Jarvis Interactive Voice AI Agent
Orchestrates Speech-to-Text, Gemini AI Brain with Function Calling, and ElevenLabs TTS Voice.
"""

from __future__ import annotations

import os
import sys
import time
import logging
from pathlib import Path

from dotenv import load_dotenv
import numpy as np
import sounddevice as sd

# Load .env
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

from jarvis_tools import JARVIS_TOOL_DECLARATIONS, TOOL_FUNCTION_MAP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("jarvis.agent")

SYSTEM_PROMPT = """You are JARVIS, an ultra-capable, polite, intelligent AI assistant and butler (like Tony Stark's JARVIS).
You have full access to tools on the user's Windows computer to perform actions like launching apps, controlling volume, searching the web, playing music/YouTube, and taking screenshots.

Guidelines:
1. When asked to perform computer tasks, always use the appropriate tool.
2. Keep your spoken responses concise, witty, elegant, and natural.
3. Address the user respectfully (e.g. 'sir' or by context).
4. If a task is completed, confirm it in a brief, pleasant sentence.
"""


class JarvisVoice:
    def __init__(self):
        self.api_key = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
        self.voice_id = (os.environ.get("ELEVENLABS_VOICE_ID") or "JBFqnCBsd6RMkjVDRZzb").strip()
        self.model_id = (os.environ.get("ELEVENLABS_MODEL_ID") or "eleven_multilingual_v2").strip()
        self.output_format = (os.environ.get("ELEVENLABS_OUTPUT_FORMAT") or "pcm_24000").strip()
        self.pcm_rate = 24000

    def speak(self, text: str) -> None:
        """Speak text out loud using ElevenLabs."""
        if not text or not text.strip():
            return
        log.info("JARVIS speaking: %r", text)
        
        if not self.api_key:
            log.warning("ELEVENLABS_API_KEY is not set in .env; skipping voice output.")
            return

        try:
            from elevenlabs.client import ElevenLabs
            client = ElevenLabs(api_key=self.api_key)
            audio_stream = client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text.strip(),
                model_id=self.model_id,
                output_format=self.output_format,
            )
            raw = b"".join(audio_stream)
            if not raw:
                log.warning("ElevenLabs returned empty audio.")
                return

            pcm_i16 = np.frombuffer(raw, dtype=np.int16)
            pcm_f = pcm_i16.astype(np.float32) / 32768.0
            sd.play(pcm_f, self.pcm_rate)
            sd.wait()
        except Exception as e:
            log.error("TTS playback error: %s", e)


class JarvisBrain:
    def __init__(self):
        self.gemini_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
        self.openai_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        self.client = None
        self.chat_history = []
        self._init_client()

    def _init_client(self):
        if self.gemini_key:
            try:
                from google import genai
                from google.genai import types
                self.client = genai.Client(api_key=self.gemini_key)
                log.info("Gemini AI Brain initialized successfully.")
            except ImportError:
                log.warning("google-genai package not installed.")
        elif self.openai_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.openai_key)
                log.info("OpenAI Brain initialized.")
            except ImportError:
                pass
        else:
            log.warning("No GEMINI_API_KEY found in .env. Please set GEMINI_API_KEY for AI intelligence.")

    def process_command(self, user_text: str) -> str:
        """Process user input with AI Brain and execute any requested tools."""
        if not user_text.strip():
            return ""

        # Direct local command fallbacks if no LLM key is configured yet
        if not self.gemini_key and not self.openai_key:
            return self._fallback_rule_engine(user_text)

        if self.gemini_key:
            return self._process_gemini(user_text)
        elif self.openai_key:
            return self._process_openai(user_text)
        return "I am awaiting an AI API key to process complex queries."

    def _process_gemini(self, user_text: str) -> str:
        try:
            from google.genai import types
            
            # Map tools to google-genai function declarations
            tools_spec = [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=t["name"],
                            description=t["description"],
                            parameters=t["parameters"]
                        ) for t in JARVIS_TOOL_DECLARATIONS
                    ]
                )
            ]

            self.chat_history.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))

            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                tools=tools_spec
            )

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=self.chat_history,
                config=config,
            )

            # Check for function calls
            if response.function_calls:
                for call in response.function_calls:
                    fn_name = call.name
                    fn_args = call.args or {}
                    log.info("JARVIS executing tool: %s(%s)", fn_name, fn_args)
                    
                    if fn_name in TOOL_FUNCTION_MAP:
                        tool_result = TOOL_FUNCTION_MAP[fn_name](**fn_args)
                    else:
                        tool_result = f"Tool {fn_name} not recognized."

                    # Return result to model to get final spoken answer
                    self.chat_history.append(response.candidates[0].content)
                    self.chat_history.append(
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_function_response(
                                    name=fn_name,
                                    response={"result": tool_result}
                                )
                            ]
                        )
                    )

                    follow_up = self.client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=self.chat_history,
                        config=config,
                    )
                    reply_text = follow_up.text or f"Done, sir. {tool_result}"
                    self.chat_history.append(follow_up.candidates[0].content)
                    return reply_text

            reply_text = response.text or "Right away, sir."
            if response.candidates:
                self.chat_history.append(response.candidates[0].content)
            return reply_text

        except Exception as e:
            log.error("Gemini API error: %s", e)
            return self._fallback_rule_engine(user_text)

    def _fallback_rule_engine(self, user_text: str) -> str:
        """Fast fallback rule engine when working without an LLM API key."""
        t = user_text.lower()
        if "volume" in t:
            if "up" in t or "increase" in t:
                return TOOL_FUNCTION_MAP["set_system_volume"](80)
            elif "down" in t or "lower" in t:
                return TOOL_FUNCTION_MAP["set_system_volume"](30)
            elif "mute" in t:
                return TOOL_FUNCTION_MAP["system_action"]("mute")
            # Extract number
            words = t.split()
            for w in words:
                if w.isdigit():
                    return TOOL_FUNCTION_MAP["set_system_volume"](int(w))
        if "spotify" in t:
            return TOOL_FUNCTION_MAP["open_application"]("Spotify")
        if "youtube" in t:
            if "play" in t or "search" in t:
                q = t.replace("play", "").replace("search", "").replace("youtube", "").replace("on", "").strip()
                return TOOL_FUNCTION_MAP["play_youtube_search"](q or "lofi music")
            return TOOL_FUNCTION_MAP["open_website"]("https://www.youtube.com", "YouTube")
        if "instagram" in t:
            return TOOL_FUNCTION_MAP["open_website"]("https://www.instagram.com", "Instagram")
        if "cursor" in t or "code" in t or "editor" in t:
            return TOOL_FUNCTION_MAP["open_application"]("Cursor")
        if "screenshot" in t:
            return TOOL_FUNCTION_MAP["take_screenshot"]()
        if "lock" in t:
            return TOOL_FUNCTION_MAP["system_action"]("lock")
        if "desktop" in t or "minimize" in t:
            return TOOL_FUNCTION_MAP["system_action"]("minimize_all")
        if "google" in t or "search" in t:
            q = t.replace("google", "").replace("search", "").replace("for", "").strip()
            return TOOL_FUNCTION_MAP["search_google"](q)
        
        return "I heard you, sir. Add your GEMINI_API_KEY in .env for full conversational intelligence."


class JarvisListener:
    def __init__(self):
        self.recognizer = None
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
        except ImportError:
            log.warning("speech_recognition not installed.")

    def listen_once(self) -> str | None:
        """Capture one spoken phrase from the microphone."""
        if not self.recognizer:
            return None
        import speech_recognition as sr
        try:
            with sr.Microphone() as source:
                log.info("Listening for command...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=6, phrase_time_limit=10)
                log.info("Processing speech...")
                text = self.recognizer.recognize_google(audio)
                log.info("You said: %r", text)
                return text
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception as e:
            log.warning("Microphone capture error: %s", e)
            return None


def run_interactive_jarvis():
    log.info("=" * 60)
    log.info("⚡ JARVIS INTERACTIVE ASSISTANT ACTIVATED ⚡")
    log.info("Commands: Speak into your microphone, or type below.")
    log.info("Say/Type 'exit' or 'quit' to stop.")
    log.info("=" * 60)

    voice = JarvisVoice()
    brain = JarvisBrain()
    listener = JarvisListener()

    # Initial greeting
    greeting = "Online and at your service, sir. How may I assist you today?"
    print(f"\nJARVIS: {greeting}")
    voice.speak(greeting)

    while True:
        try:
            print("\n[Options: Press Enter to speak, or type command directly]")
            user_input = input("You > ").strip()
            
            if not user_input:
                print("🎤 Listening... (Speak now)")
                speech = listener.listen_once()
                if speech:
                    user_input = speech
                else:
                    print("Didn't catch that, sir. Try again.")
                    continue

            if user_input.lower() in ("exit", "quit", "goodbye", "bye jarvis"):
                farewell = "Powering down systems. Have a wonderful day, sir."
                print(f"JARVIS: {farewell}")
                voice.speak(farewell)
                break

            response = brain.process_command(user_input)
            print(f"JARVIS: {response}")
            voice.speak(response)

        except (KeyboardInterrupt, EOFError):
            print("\nJARVIS: Shutting down. Goodbye, sir.")
            break


if __name__ == "__main__":
    run_interactive_jarvis()
