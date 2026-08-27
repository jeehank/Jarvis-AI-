"""
Jarvis Supercharged Interactive Voice AI Agent
3-Phase Spoken Feedback, Audio Booster (Louder Voice), Gemini Multimodal Screen Vision, Messaging & PC Control.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
You have full access to tools on the user's Windows computer to perform actions like:
- Liking active posts/reels on screen (Instagram, YouTube, X)
- Sending messages on WhatsApp, Gmail compose, or Instagram DMs
- Viewing and analyzing the user's screen with vision
- Opening any websites/accounts, desktop applications, folders
- Controlling volume, typing text, scrolling, pressing hotkeys, playing YouTube videos/music, and taking screenshots.

Guidelines:
1. When asked to perform computer tasks, always use the appropriate tool.
2. Keep your spoken responses concise, witty, elegant, and natural (1-2 sentences maximum).
3. Address the user respectfully as 'sir' or by context.
"""


class JarvisVoice:
    """Handles Text-To-Speech output using ElevenLabs with optimized low latency and Audio Boost."""

    def __init__(self) -> None:
        self.api_key: str = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
        self.voice_id: str = (os.environ.get("ELEVENLABS_VOICE_ID") or "JBFqnCBsd6RMkjVDRZzb").strip()
        self.model_id: str = (os.environ.get("ELEVENLABS_MODEL_ID") or "eleven_turbo_v2_5").strip()
        self.output_format: str = (os.environ.get("ELEVENLABS_OUTPUT_FORMAT") or "pcm_24000").strip()
        self.pcm_rate: int = 24000
        # Volume boost multiplier (1.7x gain with soft peak limiter)
        self.volume_boost: float = float(os.environ.get("JARVIS_VOLUME_BOOST", "1.7"))
        self.client: Optional[ElevenLabs] = None
        if self.api_key:
            try:
                self.client = ElevenLabs(api_key=self.api_key)
            except Exception as e:
                log.warning("Could not initialize ElevenLabs client: %s", e)

    def speak(self, text: str, block: bool = True) -> None:
        """Speak text out loud using ElevenLabs with volume gain boost."""
        if not text or not text.strip():
            return
        log.info("JARVIS speaking: %r", text)

        if not self.client:
            log.warning("ElevenLabs client not configured; skipping voice output.")
            return

        def _play():
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

                # Apply Audio Gain Boost & Peak Limiter for louder, richer voice
                pcm_boosted = pcm_f * self.volume_boost
                pcm_boosted = np.clip(pcm_boosted, -0.98, 0.98)

                sd.play(pcm_boosted, self.pcm_rate)
                sd.wait()
            except Exception as e:
                log.error("TTS playback error: %s", e)

        if block:
            _play()
        else:
            threading.Thread(target=_play, daemon=True).start()


class JarvisBrain:
    """Handles conversation, Fast-Path Router, and Gemini Multimodal LLM function calling."""

    def __init__(self, voice: JarvisVoice) -> None:
        self.voice: JarvisVoice = voice
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

    def process_command(self, user_text: str) -> None:
        """Process user command with 3-Phase Flow (Pre-Ack -> Action -> Post-Confirmation)."""
        clean_text = user_text.strip()
        if not clean_text:
            return

        # 1. Fast-Path Router for instant execution
        fast_handled = self._fast_path_router(clean_text)
        if fast_handled:
            return

        # 2. Complex / AI Reasoning Flow with Gemini
        self._process_gemini_3phase(clean_text)

    def _fast_path_router(self, text: str) -> bool:
        """Instant zero-latency command parser with 3-Phase Spoken Feedback."""
        t = text.lower().strip()
        t_clean = re.sub(r"^(hey\s+)?jarvis[\s,]*", "", t, flags=re.IGNORECASE).strip()
        if not t_clean:
            self.voice.speak("Yes sir, I'm online. How may I help you?")
            return True

        # Like Post: "like this post", "like this", "like reel", "like post"
        if "like" in t_clean and ("post" in t_clean or "this" in t_clean or "reel" in t_clean or "photo" in t_clean or "video" in t_clean or "picture" in t_clean):
            # Phase 1: Pre-Ack
            self.voice.speak("Locating the post on your screen and liking it now, sir.")
            # Phase 2: Action with Vision & Mouse Movement
            res = TOOL_FUNCTION_MAP["like_current_post"]("instagram")
            # Phase 3: Post-Ack
            print(f"JARVIS: {res}\n")
            self.voice.speak("Done, sir. Post located and liked.")
            return True

        # Play Music: "play [song]"
        if t_clean.startswith("play "):
            song_query = t_clean[5:].strip()
            if song_query:
                # Phase 1: Pre-Ack
                self.voice.speak(f"Playing {song_query.title()} for you now, sir.")
                # Phase 2: Action
                TOOL_FUNCTION_MAP["play_youtube_video"](song_query)
                return True

        # Instagram Direct with Contacts (Sohani, Abhirup, Abhiroop, Sampriti, or username)
        if "instagram" in t_clean and any(c in t_clean for c in ("sohani", "abhirup", "abhiroop", "sampriti", "message", "dm", "send", "chat")):
            contact = ""
            for c in ("sohani", "abhirup", "abhiroop", "sampriti"):
                if c in t_clean:
                    contact = c
                    break
            if not contact:
                m_user = re.search(r"(?:to\s+|dm\s+)?@?([a-zA-Z0-9_.]+)", t_clean)
                contact = m_user.group(1) if m_user else ""

            msg_match = re.search(r"(?:saying|message|that|text)\s+(.+)", t_clean)
            message_text = msg_match.group(1).strip() if msg_match else "hey im jarvis"

            self.voice.speak(f"Opening Instagram chat with {contact.capitalize() if contact else 'contact'} and sending your message, sir.")
            res = TOOL_FUNCTION_MAP["send_instagram_dm_message"](contact, message_text)
            print(f"JARVIS: {res}\n")
            return True

        # WhatsApp: App vs Web vs Send Message
        if "whatsapp" in t_clean:
            if "app" in t_clean or "desktop" in t_clean or "application" in t_clean:
                self.voice.speak("Opening WhatsApp Desktop Application for you now, sir.")
                TOOL_FUNCTION_MAP["open_whatsapp"]("app")
                return True
            match = re.search(r"(?:to\s+)?([a-zA-Z0-9_+]+)\s+(?:saying|message|that)\s+(.+)", t_clean)
            if match:
                contact, msg = match.group(1), match.group(2)
                self.voice.speak(f"Opening WhatsApp chat for {contact} with your message, sir.")
                TOOL_FUNCTION_MAP["send_whatsapp_message"](contact, msg)
                return True
            else:
                self.voice.speak("Opening WhatsApp for you now, sir.")
                TOOL_FUNCTION_MAP["open_whatsapp"]("web")
                return True

        # Screen Vision: "what is on my screen", "look at my screen", "read my screen"
        if "screen" in t_clean and ("look" in t_clean or "what" in t_clean or "read" in t_clean or "see" in t_clean or "analyze" in t_clean):
            self.voice.speak("Looking at your screen right now, sir.")
            result = TOOL_FUNCTION_MAP["see_and_analyze_screen"](t_clean)
            print(f"JARVIS: {result}\n")
            self.voice.speak(result)
            return True

        # Scroll Screen: "scroll down", "scroll up"
        if "scroll" in t_clean:
            dir_scroll = "up" if "up" in t_clean else "down"
            TOOL_FUNCTION_MAP["scroll_screen"](dir_scroll, 6)
            return True

        # Open Apps / Sites
        if t_clean.startswith("open "):
            target = t_clean[5:].replace("my ", "").replace("the ", "").strip()
            self.voice.speak(f"Opening {target.title()} for you, sir.")
            if target in ACCOUNT_URLS or any(k in target for k in ACCOUNT_URLS):
                for k in ACCOUNT_URLS:
                    if k in target:
                        TOOL_FUNCTION_MAP["open_website"](k)
                        return True
            if target in ("downloads", "documents", "desktop", "pictures", "videos", "music"):
                TOOL_FUNCTION_MAP["open_folder"](target)
                return True
            TOOL_FUNCTION_MAP["open_application"](target)
            return True

        # Volume
        if "volume" in t_clean:
            digits = re.findall(r"\d+", t_clean)
            if digits:
                vol_num = int(digits[0])
                TOOL_FUNCTION_MAP["set_system_volume"](vol_num)
                self.voice.speak(f"Volume set to {vol_num}%, sir.")
                return True
            if "up" in t_clean or "increase" in t_clean or "higher" in t_clean:
                TOOL_FUNCTION_MAP["set_system_volume"](85)
                self.voice.speak("Turning volume up to 85%, sir.")
                return True
            if "down" in t_clean or "decrease" in t_clean or "lower" in t_clean:
                TOOL_FUNCTION_MAP["set_system_volume"](30)
                self.voice.speak("Lowered volume to 30%, sir.")
                return True
            if "mute" in t_clean:
                TOOL_FUNCTION_MAP["system_action"]("mute")
                self.voice.speak("Muted audio, sir.")
                return True
            if "unmute" in t_clean:
                TOOL_FUNCTION_MAP["system_action"]("unmute")
                self.voice.speak("Unmuted audio, sir.")
                return True

        # Screenshot
        if "screenshot" in t_clean:
            self.voice.speak("Taking screenshot now, sir.")
            TOOL_FUNCTION_MAP["take_screenshot"]()
            self.voice.speak("Screenshot captured and saved, sir.")
            return True

        # Show desktop / Lock PC
        if "show desktop" in t_clean or "minimize all" in t_clean:
            TOOL_FUNCTION_MAP["system_action"]("minimize_all")
            self.voice.speak("Showing desktop, sir.")
            return True
        if "lock pc" in t_clean or "lock computer" in t_clean:
            self.voice.speak("Locking your workstation now, sir.")
            TOOL_FUNCTION_MAP["system_action"]("lock")
            return True

        # Google Search
        if t_clean.startswith("search ") or t_clean.startswith("google "):
            q = re.sub(r"^(search|google)(\s+for)?\s+", "", t_clean).strip()
            if q:
                self.voice.speak(f"Searching Google for {q}, sir.")
                TOOL_FUNCTION_MAP["search_google"](q)
                return True

        return False

    def _process_gemini_3phase(self, user_text: str) -> None:
        """3-Phase Processing with Gemini 3.6 Flash."""
        if not self.client:
            self.voice.speak("I am ready for your command, sir.")
            return

        # Phase 1: Pre-Ack
        self.voice.speak("Looking into that for you now, sir.")

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

            # Phase 2: Action / Model call
            response = self.client.models.generate_content(
                model="gemini-3.6-flash",
                contents=self.chat_history,
                config=config,
            )

            # Tool calling execution
            if response.function_calls:
                for call in response.function_calls:
                    fn_name = call.name
                    fn_args: Dict[str, Any] = call.args or {}
                    log.info("JARVIS executing tool: %s(%s)", fn_name, fn_args)

                    if fn_name in TOOL_FUNCTION_MAP:
                        tool_result = TOOL_FUNCTION_MAP[fn_name](**fn_args)
                    else:
                        tool_result = f"Tool {fn_name} completed."

                if response.candidates:
                    self.chat_history.append(response.candidates[0].content)

                # Phase 3: Post-Ack Confirmation
                final_text = f"Done, sir. {tool_result}"
                print(f"JARVIS: {final_text}\n")
                self.voice.speak(final_text)
                return

            reply_text = response.text or "Right away, sir."
            if response.candidates:
                self.chat_history.append(response.candidates[0].content)

            # Phase 3: Speak final answer
            print(f"JARVIS: {reply_text}\n")
            self.voice.speak(reply_text)

        except Exception as e:
            log.error("Gemini API error: %s", e)
            self.voice.speak("Task completed, sir.")


class JarvisContinuousListener:
    """Continuously listens to the microphone with snappy silence detection."""

    def __init__(self, wake_word: str = "jarvis") -> None:
        self.wake_word: str = wake_word.lower()
        self.recognizer: sr.Recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 260
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.55
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
                        audio = self.recognizer.listen(source, timeout=2.5, phrase_time_limit=7.0)
                        text = self.recognizer.recognize_google(audio).strip()

                        if not text:
                            continue

                        text_lower = text.lower()
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
    """Main interactive Jarvis loop with 3-Phase Spoken Feedback and Screen Vision."""
    print("=" * 65)
    print("⚡ JARVIS SUPERCHARGED MULTIMODAL ASSISTANT ONLINE ⚡")
    print("=" * 65)
    print("• Listening continuously in the background.")
    print("• Say: 'Jarvis, like this post'")
    print("• Say: 'Jarvis, look at my screen and tell me what this is'")
    print("• Say: 'Jarvis, message Alex on WhatsApp saying I will be there soon'")
    print("• Say: 'Jarvis, email john@example.com about meeting tomorrow'")
    print("• Say: 'Jarvis, play Let It Happen by Tame Impala'")
    print("• Say: 'Jarvis, set volume to 70%' / 'Jarvis, scroll down'")
    print("• Say or type 'exit' / 'quit' to stop.")
    print("=" * 65)

    voice = JarvisVoice()
    brain = JarvisBrain(voice=voice)
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

        brain.process_command(cmd)

    # Initial greeting
    greeting = "All systems online and at full capacity, sir. Just say Jarvis whenever you need me."
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
