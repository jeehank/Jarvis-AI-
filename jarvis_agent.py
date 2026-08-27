"""
Jarvis Interactive Voice AI Agent
Continuous wake-word listening, Gemini AI Brain with Function Calling, and ElevenLabs TTS Voice.
"""

from __future__ import annotations

import logging
import os
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

from jarvis_tools import JARVIS_TOOL_DECLARATIONS, TOOL_FUNCTION_MAP

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
2. Keep your spoken responses concise, witty, elegant, and natural.
3. Address the user respectfully as 'sir' or by context.
4. If a task is completed, confirm it in a brief, pleasant sentence.
"""


class JarvisVoice:
    """Handles Text-To-Speech output using ElevenLabs."""

    def __init__(self) -> None:
        self.api_key: str = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
        self.voice_id: str = (os.environ.get("ELEVENLABS_VOICE_ID") or "JBFqnCBsd6RMkjVDRZzb").strip()
        self.model_id: str = (os.environ.get("ELEVENLABS_MODEL_ID") or "eleven_multilingual_v2").strip()
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
    """Handles conversation, intent understanding, and function calling with Gemini LLM."""

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
        """Process user input with Gemini and execute any triggered tools."""
        if not user_text.strip():
            return ""

        if not self.client:
            return self._fallback_rule_engine(user_text)

        try:
            # Map tools to Gemini function declarations
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
                temperature=0.7,
                tools=tools_spec
            )

            response = self.client.models.generate_content(
                model="gemini-3.6-flash",
                contents=self.chat_history,
                config=config,
            )

            # Check if model requested tool execution
            if response.function_calls:
                for call in response.function_calls:
                    fn_name = call.name
                    fn_args: Dict[str, Any] = call.args or {}
                    log.info("JARVIS executing tool: %s(%s)", fn_name, fn_args)

                    if fn_name in TOOL_FUNCTION_MAP:
                        tool_result = TOOL_FUNCTION_MAP[fn_name](**fn_args)
                    else:
                        tool_result = f"Tool {fn_name} not recognized."

                    # Send result back to model for final natural reply
                    if response.candidates:
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
                        model="gemini-3.6-flash",
                        contents=self.chat_history,
                        config=config,
                    )
                    reply_text = follow_up.text or f"Done, sir. {tool_result}"
                    if follow_up.candidates:
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
        """Fast fallback rule engine."""
        t = user_text.lower()
        if "volume" in t:
            words = t.split()
            for w in words:
                if w.isdigit():
                    return TOOL_FUNCTION_MAP["set_system_volume"](int(w))
            if "up" in t or "increase" in t:
                return TOOL_FUNCTION_MAP["set_system_volume"](80)
            elif "down" in t or "lower" in t:
                return TOOL_FUNCTION_MAP["set_system_volume"](30)
            elif "mute" in t:
                return TOOL_FUNCTION_MAP["system_action"]("mute")
        if "instagram" in t:
            return TOOL_FUNCTION_MAP["open_website"]("instagram")
        if "youtube" in t:
            if "play" in t or "search" in t:
                q = t.replace("play", "").replace("search", "").replace("youtube", "").replace("on", "").replace("jarvis", "").strip()
                return TOOL_FUNCTION_MAP["play_youtube_search"](q or "lofi music")
            return TOOL_FUNCTION_MAP["open_website"]("youtube")
        if "spotify" in t:
            return TOOL_FUNCTION_MAP["open_application"]("Spotify")
        if "gmail" in t or "email" in t:
            return TOOL_FUNCTION_MAP["open_website"]("gmail")
        if "github" in t:
            return TOOL_FUNCTION_MAP["open_website"]("github")
        if "cursor" in t or "code" in t or "editor" in t:
            return TOOL_FUNCTION_MAP["open_application"]("Cursor")
        if "screenshot" in t:
            return TOOL_FUNCTION_MAP["take_screenshot"]()
        if "lock" in t:
            return TOOL_FUNCTION_MAP["system_action"]("lock")
        if "desktop" in t or "minimize" in t:
            return TOOL_FUNCTION_MAP["system_action"]("minimize_all")
        if "google" in t or "search" in t:
            q = t.replace("google", "").replace("search", "").replace("for", "").replace("jarvis", "").strip()
            return TOOL_FUNCTION_MAP["search_google"](q)

        return "Right away, sir."


class JarvisContinuousListener:
    """Continuously listens to the microphone and triggers only when 'jarvis' is called."""

    def __init__(self, wake_word: str = "jarvis") -> None:
        self.wake_word: str = wake_word.lower()
        self.recognizer: sr.Recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 280
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.is_running: bool = True

    def listen_loop(self, on_command: Any) -> None:
        """Continuous background listening loop."""
        try:
            with sr.Microphone() as source:
                log.info("Calibrating microphone for room acoustics...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
                log.info("Continuous listening ACTIVE. Say '%s ...' anytime!", self.wake_word.upper())

                while self.is_running:
                    try:
                        # Listen in continuous chunks
                        audio = self.recognizer.listen(source, timeout=3.0, phrase_time_limit=8.0)
                        text = self.recognizer.recognize_google(audio).strip()
                        
                        if not text:
                            continue

                        text_lower = text.lower()
                        # Check if wake word 'jarvis' was spoken
                        if self.wake_word in text_lower:
                            log.info("⚡ Wake word detected! Prompt: %r", text)
                            # Strip wake word if needed or pass directly
                            on_command(text)
                        else:
                            # Heard sound/speech but not addressing Jarvis -> ignore
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
    """Main interactive Jarvis loop with continuous wake-word detection."""
    print("=" * 65)
    print("⚡ JARVIS CONTINUOUS VOICE ASSISTANT ONLINE ⚡")
    print("=" * 65)
    print("• Listening continuously in the background.")
    print("• Jarvis only speaks when you call his name: 'Hey Jarvis ...'")
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

        response = brain.process_command(cmd)
        print(f"JARVIS: {response}\n")
        voice.speak(response)

    # Initial greeting
    greeting = "Online and listening, sir. Whenever you need me, just say Jarvis."
    print(f"\nJARVIS: {greeting}\n")
    voice.speak(greeting)

    # Start continuous microphone listener on a background thread
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
