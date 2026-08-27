"""
Jarvis Interactive Voice AI Agent
Ultra-low-latency continuous wake-word listening, Fast Intent Dispatcher, Gemini AI Brain, and ElevenLabs TTS Voice.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
import numpy as np
import sounddevice as sd
import speech_recognition as sr
from elevenlabs.client import ElevenLabs

# Load environment variables
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH)

from jarvis_tools import JARVIS_TOOL_DECLARATIONS, TOOL_FUNCTION_MAP, ACCOUNT_URLS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("jarvis.agent")

SYSTEM_PROMPT = """You are JARVIS, an ultra-capable, polite, intelligent AI assistant and butler (like Tony Stark's JARVIS).
You have full access to tools on the user's Windows computer to perform actions like opening websites/accounts, launching desktop apps, controlling volume, typing text, pressing hotkeys, searching the web, playing music/YouTube, opening folders, and taking screenshots.

Guidelines:
1. When asked to perform computer tasks, always use the appropriate tool.
2. Keep your spoken responses concise, witty, elegant, and natural (1-2 sentences maximum).
3. Address the user respectfully as 'sir' or by context.
"""


class JarvisVoice:
    """Handles Text-To-Speech output using ElevenLabs with optimized low latency."""

    def __init__(self) -> None:
        self.api_key: str = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
        self.voice_id: str = (os.environ.get("ELEVENLABS_VOICE_ID") or "JBFqnCBsd6RMkjVDRZzb").strip()
        # Default to turbo for 3x faster response time
        self.model_id: str = (os.environ.get("ELEVENLABS_MODEL_ID") or "eleven_turbo_v2_5").strip()
        self.output_format: str = (os.environ.get("ELEVENLABS_OUTPUT_FORMAT") or "pcm_24000").strip()
        self.pcm_rate: int = 24000
        self.client: Optional[ElevenLabs] = None
        if self.api_key:
            try:
                self.client = ElevenLabs(api_key=self.api_key)
            except Exception as e:
                log.warning("Could not initialize ElevenLabs client: %s", e)

    def speak(self, text: str) -> None:
        """Speak text out loud using ElevenLabs voice synthesis."""
        if not text or not text.strip():
            return
        log.info("JARVIS speaking: %r", text)

        if not self.client:
            log.warning("ElevenLabs client not configured; skipping voice output.")
            return

        try:
            audio_stream = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text.strip(),
                model_id=self.model_id,
                output_format=self.output_format,
            )
            raw = b"".join(audio_stream)
            if not raw:
                return

            pcm_i16 = np.frombuffer(raw, dtype=np.int16)
            pcm_f = pcm_i16.astype(np.float32) / 32768.0
            sd.play(pcm_f, self.pcm_rate)
            sd.wait()
        except Exception as e:
            log.error("TTS playback error: %s", e)


class JarvisBrain:
    """Handles conversation, fast-path intent routing, and Gemini LLM function calling."""

    def __init__(self) -> None:
        self.gemini_key: str = (os.environ.get("GEMINI_API_KEY") or "").strip()
        self.client: Optional[genai.Client] = None
        self.chat_history: List[types.Content] = []
        self._init_client()

    def _init_client(self) -> None:
        if self.gemini_key:
            try:
                self.client = genai.Client(api_key=self.gemini_key)
                log.info("Gemini AI Brain initialized successfully (gemini-3.6-flash).")
            except Exception as e:
                log.error("Failed to initialize Gemini client: %s", e)
        else:
            log.warning("No GEMINI_API_KEY found in .env.")

    def process_command(self, user_text: str) -> str:
        """Process user input with Fast-Path Router for instant execution or Gemini LLM for complex tasks."""
        clean_text = user_text.strip()
        if not clean_text:
            return ""

        # 1. Fast-Path Router: Instant sub-second execution for common PC commands
        fast_result = self._fast_path_router(clean_text)
        if fast_result:
            return fast_result

        # 2. LLM Brain with Gemini for complex conversations & dynamic reasoning
        if self.client:
            return self._process_gemini(clean_text)

        return "I am awaiting instructions, sir."

    def _fast_path_router(self, text: str) -> Optional[str]:
        """Instant zero-latency command parser for common PC tasks."""
        t = text.lower().strip()
        # Remove wake words from query
        t_clean = re.sub(r"^(hey\s+)?jarvis[\s,]*", "", t, flags=re.IGNORECASE).strip()
        if not t_clean:
            return "Yes sir, I'm here. What can I do for you?"

        # Instant Media Play: "play [song name]" or "play [song] by [artist]"
        if t_clean.startswith("play "):
            song_query = t_clean[5:].strip()
            if song_query:
                # Launch playback in background thread immediately so it doesn't block
                threading.Thread(target=TOOL_FUNCTION_MAP["play_youtube_video"], args=(song_query,), daemon=True).start()
                return f"Playing {song_query.title()} for you now, sir."

        # Instant Volume: "set volume to X", "volume X", "turn up/down volume"
        if "volume" in t_clean:
            # Check numbers
            digits = re.findall(r"\d+", t_clean)
            if digits:
                vol_num = int(digits[0])
                TOOL_FUNCTION_MAP["set_system_volume"](vol_num)
                return f"System volume set to {vol_num}%, sir."
            if "up" in t_clean or "increase" in t_clean or "higher" in t_clean:
                TOOL_FUNCTION_MAP["set_system_volume"](85)
                return "Turning volume up to 85%, sir."
            if "down" in t_clean or "decrease" in t_clean or "lower" in t_clean:
                TOOL_FUNCTION_MAP["set_system_volume"](30)
                return "Lowered volume to 30%, sir."
            if "mute" in t_clean:
                TOOL_FUNCTION_MAP["system_action"]("mute")
                return "Audio muted, sir."
            if "unmute" in t_clean:
                TOOL_FUNCTION_MAP["system_action"]("unmute")
                return "Audio unmuted, sir."

        # Instant App / Account Opener: "open [name]"
        if t_clean.startswith("open "):
            target = t_clean[5:].replace("my ", "").replace("the ", "").strip()
            # Check websites/accounts
            if target in ACCOUNT_URLS or any(k in target for k in ACCOUNT_URLS):
                for k in ACCOUNT_URLS:
                    if k in target:
                        TOOL_FUNCTION_MAP["open_website"](k)
                        return f"Opening {k.capitalize()} for you, sir."
            # Check folders
            if target in ("downloads", "documents", "desktop", "pictures", "videos", "music"):
                TOOL_FUNCTION_MAP["open_folder"](target)
                return f"Opening your {target.capitalize()} folder, sir."
            # Check apps
            TOOL_FUNCTION_MAP["open_application"](target)
            return f"Opening {target.title()}, sir."

        # Instant Screenshot
        if "screenshot" in t_clean:
            TOOL_FUNCTION_MAP["take_screenshot"]()
            return "Screenshot captured and saved, sir."

        # Instant Desktop / Lock
        if "show desktop" in t_clean or "minimize all" in t_clean:
            TOOL_FUNCTION_MAP["system_action"]("minimize_all")
            return "Showing desktop, sir."
        if "lock pc" in t_clean or "lock computer" in t_clean:
            TOOL_FUNCTION_MAP["system_action"]("lock")
            return "Locking workstation, sir."

        # Instant Google Search
        if t_clean.startswith("search ") or t_clean.startswith("google "):
            q = re.sub(r"^(search|google)(\s+for)?\s+", "", t_clean).strip()
            if q:
                TOOL_FUNCTION_MAP["search_google"](q)
                return f"Searching Google for {q}, sir."

        return None

    def _process_gemini(self, user_text: str) -> str:
        """Process complex query or multi-step reasoning with Gemini 3.6 Flash."""
        try:
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

            self.chat_history.append(
                types.Content(role="user", parts=[types.Part.from_text(text=user_text)])
            )

            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.6,
                tools=tools_spec
            )

            response = self.client.models.generate_content(
                model="gemini-3.6-flash",
                contents=self.chat_history,
                config=config,
            )

            # Check if tool calling was triggered
            if response.function_calls:
                tool_confirmations = []
                for call in response.function_calls:
                    fn_name = call.name
                    fn_args: Dict[str, Any] = call.args or {}
                    log.info("JARVIS executing tool: %s(%s)", fn_name, fn_args)

                    if fn_name in TOOL_FUNCTION_MAP:
                        tool_result = TOOL_FUNCTION_MAP[fn_name](**fn_args)
                        tool_confirmations.append(tool_result)
                    else:
                        tool_confirmations.append(f"Tool {fn_name} not recognized.")

                if response.candidates:
                    self.chat_history.append(response.candidates[0].content)

                # Format fast confirmation without redundant 2nd LLM roundtrip
                return f"Right away, sir. {' '.join(tool_confirmations)}"

            reply_text = response.text or "Right away, sir."
            if response.candidates:
                self.chat_history.append(response.candidates[0].content)
            return reply_text

        except Exception as e:
            log.error("Gemini API error: %s", e)
            return "I apologize, sir; there was a momentary network interruption."


class JarvisContinuousListener:
    """Continuously listens to the microphone with snappy silence detection."""

    def __init__(self, wake_word: str = "jarvis") -> None:
        self.wake_word: str = wake_word.lower()
        self.recognizer: sr.Recognizer = sr.Recognizer()
        # Tuning for ultra-responsive speech recognition
        self.recognizer.energy_threshold = 260
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.55  # Snappy stop detection
        self.recognizer.phrase_threshold = 0.2
        self.recognizer.non_speaking_duration = 0.4
        self.is_running: bool = True

    def listen_loop(self, on_command: Any) -> None:
        """Continuous background listening loop."""
        try:
            with sr.Microphone() as source:
                log.info("Calibrating microphone for room acoustics...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
                log.info("Continuous listening ACTIVE. Say '%s ...' anytime!", self.wake_word.upper())

                while self.is_running:
                    try:
                        # Listen in short responsive chunks
                        audio = self.recognizer.listen(source, timeout=2.5, phrase_time_limit=7.0)
                        text = self.recognizer.recognize_google(audio).strip()

                        if not text:
                            continue

                        text_lower = text.lower()
                        # Check if wake word 'jarvis' was spoken
                        if self.wake_word in text_lower:
                            log.info("⚡ Wake word detected! Prompt: %r", text)
                            on_command(text)
                        else:
                            log.debug("Heard non-wake speech: %r", text)

                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        continue
                    except Exception as e:
                        log.debug("Listen chunk error: %s", e)
                        continue

        except Exception as e:
            log.error("Microphone initialization error: %s", e)


def run_interactive_jarvis() -> None:
    """Main interactive Jarvis loop."""
    print("=" * 65)
    print("⚡ JARVIS ULTRA-FAST VOICE ASSISTANT ONLINE ⚡")
    print("=" * 65)
    print("• Listening continuously in the background.")
    print("• Say: 'Jarvis, play Let It Happen by Tame Impala'")
    print("• Say: 'Jarvis, open Instagram / Spotify / YouTube'")
    print("• Say: 'Jarvis, set volume to 50%'")
    print("• Type any command directly below at any time.")
    print("• Say or type 'exit' / 'quit' to stop.")
    print("=" * 65)

    voice = JarvisVoice()
    brain = JarvisBrain()
    listener = JarvisContinuousListener(wake_word="jarvis")

    def handle_command(cmd: str) -> None:
        if not cmd.strip():
            return
        print(f"\nYou > {cmd}")

        if cmd.lower() in ("exit", "quit", "goodbye", "bye jarvis", "stop jarvis"):
            farewell = "Powering down systems. Have a wonderful day, sir."
            print(f"JARVIS: {farewell}")
            voice.speak(farewell)
            listener.is_running = False
            sys.exit(0)

        # Process command with instant feedback
        print("⚡ Processing...")
        response = brain.process_command(cmd)
        print(f"JARVIS: {response}\n")
        voice.speak(response)

    # Initial greeting
    greeting = "Online and at your service, sir. Just say Jarvis whenever you need me."
    print(f"\nJARVIS: {greeting}\n")
    voice.speak(greeting)

    # Start continuous microphone listener on background thread
    mic_thread = threading.Thread(
        target=listener.listen_loop,
        args=(handle_command,),
        daemon=True,
    )
    mic_thread.start()

    # Allow keyboard input simultaneously
    while listener.is_running:
        try:
            typed = input().strip()
            if typed:
                handle_command(typed)
        except (KeyboardInterrupt, EOFError):
            print("\nJARVIS: Shutting down. Goodbye, sir.")
            listener.is_running = False
            break


if __name__ == "__main__":
    run_interactive_jarvis()
