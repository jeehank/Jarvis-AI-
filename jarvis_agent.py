"""
jarvis_agent.py
Main voice agent loop. Listens for "Jarvis", runs fast-path commands
or falls back to Gemini for complex tasks.
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

from jarvis_tools import JARVIS_TOOL_DECLARATIONS, TOOL_FUNCTION_MAP, ACCOUNT_URLS

# ── Setup ──────────────────────────────────────────────────────────

_ENV = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("jarvis")

SYSTEM_PROMPT = (
    "You are JARVIS, a capable, polite AI assistant (like Tony Stark's JARVIS). "
    "You have tools to control the user's Windows PC: open apps/sites, send messages, "
    "play music, control volume, take screenshots, like posts, read the screen, etc. "
    "Keep spoken responses concise (1-2 sentences). Address the user as 'sir'."
)

# Contacts that map to Instagram DM threads
KNOWN_IG_ALIASES = (
    "sohani", "sohu", "soha",
    "abhirup", "abhiroop", "abhi", "abirup", "abiroop",
    "sampriti", "sam", "samp",
)


# ── Voice (ElevenLabs TTS) ─────────────────────────────────────────

class Voice:
    """Text-to-speech via ElevenLabs with volume boost."""

    def __init__(self):
        self.api_key   = os.getenv("ELEVENLABS_API_KEY", "").strip()
        self.voice_id  = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb").strip()
        self.model_id  = os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5").strip()
        self.out_fmt   = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "pcm_24000").strip()
        self.rate      = 24000
        self.boost     = float(os.getenv("JARVIS_VOLUME_BOOST", "1.7"))
        self.client    = None

        if self.api_key:
            try:
                self.client = ElevenLabs(api_key=self.api_key)
            except Exception as e:
                log.warning("ElevenLabs init failed: %s", e)

    def speak(self, text: str, block: bool = True):
        """Say something out loud. Blocks by default."""
        if not text or not text.strip():
            return
        log.info("Speaking: %s", text.strip()[:80])

        if not self.client:
            log.warning("No ElevenLabs client, skipping TTS.")
            return

        def _play():
            try:
                chunks = self.client.text_to_speech.convert(
                    voice_id=self.voice_id,
                    text=text.strip(),
                    model_id=self.model_id,
                    output_format=self.out_fmt,
                )
                raw = b"".join(chunks)
                if not raw:
                    return

                pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                pcm = np.clip(pcm * self.boost, -0.98, 0.98)
                sd.play(pcm, self.rate)
                sd.wait()
            except Exception as e:
                log.error("TTS playback error: %s", e)

        if block:
            _play()
        else:
            threading.Thread(target=_play, daemon=True).start()


# ── Brain (command routing + Gemini) ───────────────────────────────

class Brain:
    """Routes commands: fast-path for common tasks, Gemini for everything else."""

    def __init__(self, voice: Voice):
        self.voice   = voice
        self.client  = None
        self.history: List[types.Content] = []

        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if api_key:
            try:
                self.client = genai.Client(api_key=api_key)
                log.info("Gemini client ready.")
            except Exception as e:
                log.error("Gemini init failed: %s", e)
        else:
            log.warning("GEMINI_API_KEY not set.")

    # ── public entry point ──

    def process(self, text: str):
        """Handle a user command."""
        text = text.strip()
        if not text:
            return

        if self._try_fast_path(text):
            return

        self._ask_gemini(text)

    # ── fast-path router ──

    def _try_fast_path(self, text: str) -> bool:
        """
        Match common patterns and execute immediately (no API call).
        Returns True if handled.
        """
        t = re.sub(r"^(hey\s+)?jarvis[\s,]*", "", text.lower().strip(), flags=re.IGNORECASE).strip()

        if not t:
            self.voice.speak("Yes sir, I'm here. What do you need?")
            return True

        return (
            self._handle_like(t)
            or self._handle_play(t)
            or self._handle_instagram(t)
            or self._handle_whatsapp(t)
            or self._handle_screen(t)
            or self._handle_scroll(t)
            or self._handle_open(t)
            or self._handle_volume(t)
            or self._handle_screenshot(t)
            or self._handle_desktop_lock(t)
            or self._handle_search(t)
        )

    # ── individual fast-path handlers ──

    def _handle_like(self, t: str) -> bool:
        keywords = ("post", "this", "reel", "photo", "video", "picture")
        if "like" not in t or not any(k in t for k in keywords):
            return False

        self.voice.speak("Locating the post and liking it now, sir.")
        res = TOOL_FUNCTION_MAP["like_current_post"]("instagram")
        print(f"  JARVIS: {res}")
        self.voice.speak("Done, sir. Post liked.")
        return True

    def _handle_play(self, t: str) -> bool:
        if not t.startswith("play "):
            return False

        song = t[5:].strip()
        if not song:
            return False

        self.voice.speak(f"Playing {song.title()} for you, sir.")
        TOOL_FUNCTION_MAP["play_youtube_video"](song)
        return True

    def _handle_instagram(self, t: str) -> bool:
        trigger_words = ("message", "dm", "send", "chat")
        has_contact = any(c in t for c in KNOWN_IG_ALIASES)
        has_action  = any(w in t for w in trigger_words)

        if "instagram" not in t or not (has_contact or has_action):
            return False

        # figure out who
        contact = self._find_ig_contact(t)

        # figure out the message body
        msg_match = re.search(r"(?:saying|message|that|text)\s+(.+)", t)
        message = msg_match.group(1).strip() if msg_match else "hey"

        display = contact.capitalize() if contact else "contact"
        self.voice.speak(f"Opening Instagram chat with {display} and sending your message, sir.")
        res = TOOL_FUNCTION_MAP["send_instagram_dm_message"](contact, message)
        print(f"  JARVIS: {res}")
        return True

    def _find_ig_contact(self, t: str) -> str:
        """Try to match a known alias in the text."""
        # exact word boundary first
        for name in KNOWN_IG_ALIASES:
            if re.search(rf"\b{name}\b", t):
                return name
        # substring fallback
        for name in KNOWN_IG_ALIASES:
            if name in t:
                return name
        # raw username fallback
        m = re.search(r"(?:to\s+|dm\s+)?@?([a-zA-Z0-9_.]+)", t)
        return m.group(1) if m else ""

    def _handle_whatsapp(self, t: str) -> bool:
        if "whatsapp" not in t:
            return False

        # explicit desktop app
        if any(w in t for w in ("app", "desktop", "application")):
            self.voice.speak("Opening WhatsApp Desktop, sir.")
            TOOL_FUNCTION_MAP["open_whatsapp"]("app")
            return True

        # send a message
        m = re.search(r"(?:to\s+)?([a-zA-Z0-9_+]+)\s+(?:saying|message|that)\s+(.+)", t)
        if m:
            contact, msg = m.group(1), m.group(2)
            self.voice.speak(f"Sending your message to {contact} on WhatsApp, sir.")
            TOOL_FUNCTION_MAP["send_whatsapp_message"](contact, msg)
            return True

        # just open it
        self.voice.speak("Opening WhatsApp for you, sir.")
        TOOL_FUNCTION_MAP["open_whatsapp"]("web")
        return True

    def _handle_screen(self, t: str) -> bool:
        triggers = ("look", "what", "read", "see", "analyze")
        if "screen" not in t or not any(w in t for w in triggers):
            return False

        self.voice.speak("Looking at your screen now, sir.")
        result = TOOL_FUNCTION_MAP["see_and_analyze_screen"](t)
        print(f"  JARVIS: {result}")
        self.voice.speak(result)
        return True

    def _handle_scroll(self, t: str) -> bool:
        if "scroll" not in t:
            return False
        direction = "up" if "up" in t else "down"
        TOOL_FUNCTION_MAP["scroll_screen"](direction, 6)
        return True

    def _handle_open(self, t: str) -> bool:
        if not t.startswith("open "):
            return False

        target = t[5:].replace("my ", "").replace("the ", "").strip()
        self.voice.speak(f"Opening {target.title()}, sir.")

        # check known websites
        for key in ACCOUNT_URLS:
            if key in target:
                TOOL_FUNCTION_MAP["open_website"](key)
                return True

        # check common folders
        folders = ("downloads", "documents", "desktop", "pictures", "videos", "music")
        if target in folders:
            TOOL_FUNCTION_MAP["open_folder"](target)
            return True

        # fall back to app launcher
        TOOL_FUNCTION_MAP["open_application"](target)
        return True

    def _handle_volume(self, t: str) -> bool:
        if "volume" not in t:
            return False

        nums = re.findall(r"\d+", t)
        if nums:
            level = int(nums[0])
            TOOL_FUNCTION_MAP["set_system_volume"](level)
            self.voice.speak(f"Volume set to {level}%, sir.")
            return True

        if any(w in t for w in ("up", "increase", "higher")):
            TOOL_FUNCTION_MAP["set_system_volume"](85)
            self.voice.speak("Volume up to 85%, sir.")
            return True
        if any(w in t for w in ("down", "decrease", "lower")):
            TOOL_FUNCTION_MAP["set_system_volume"](30)
            self.voice.speak("Volume down to 30%, sir.")
            return True
        if "mute" in t:
            TOOL_FUNCTION_MAP["system_action"]("mute")
            self.voice.speak("Muted, sir.")
            return True
        if "unmute" in t:
            TOOL_FUNCTION_MAP["system_action"]("unmute")
            self.voice.speak("Unmuted, sir.")
            return True

        return False

    def _handle_screenshot(self, t: str) -> bool:
        if "screenshot" not in t:
            return False
        self.voice.speak("Taking a screenshot, sir.")
        TOOL_FUNCTION_MAP["take_screenshot"]()
        self.voice.speak("Screenshot saved, sir.")
        return True

    def _handle_desktop_lock(self, t: str) -> bool:
        if "show desktop" in t or "minimize all" in t:
            TOOL_FUNCTION_MAP["system_action"]("minimize_all")
            self.voice.speak("Showing desktop, sir.")
            return True
        if "lock pc" in t or "lock computer" in t:
            self.voice.speak("Locking your PC, sir.")
            TOOL_FUNCTION_MAP["system_action"]("lock")
            return True
        return False

    def _handle_search(self, t: str) -> bool:
        if not (t.startswith("search ") or t.startswith("google ")):
            return False
        query = re.sub(r"^(search|google)(\s+for)?\s+", "", t).strip()
        if not query:
            return False
        self.voice.speak(f"Searching for {query}, sir.")
        TOOL_FUNCTION_MAP["search_google"](query)
        return True

    # ── Gemini fallback ──

    def _ask_gemini(self, user_text: str):
        """Send to Gemini with tool access for complex requests."""
        if not self.client:
            self.voice.speak("I'm ready for your command, sir.")
            return

        self.voice.speak("Working on that now, sir.")

        try:
            tools = [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=d["name"],
                            description=d["description"],
                            parameters=d["parameters"],
                        )
                        for d in JARVIS_TOOL_DECLARATIONS
                    ]
                )
            ]

            self.history.append(
                types.Content(role="user", parts=[types.Part.from_text(text=user_text)])
            )

            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.6,
                tools=tools,
            )

            response = self.client.models.generate_content(
                model="gemini-3.6-flash",
                contents=self.history,
                config=config,
            )

            # execute any tool calls the model requested
            if response.function_calls:
                result = ""
                for call in response.function_calls:
                    fn = call.name
                    args = call.args or {}
                    log.info("Tool call: %s(%s)", fn, args)

                    if fn in TOOL_FUNCTION_MAP:
                        result = TOOL_FUNCTION_MAP[fn](**args)
                    else:
                        result = f"Tool {fn} completed."

                if response.candidates:
                    self.history.append(response.candidates[0].content)

                reply = f"Done, sir. {result}"
                print(f"  JARVIS: {reply}")
                self.voice.speak(reply)
                return

            # plain text reply
            reply = response.text or "Right away, sir."
            if response.candidates:
                self.history.append(response.candidates[0].content)

            print(f"  JARVIS: {reply}")
            self.voice.speak(reply)

        except Exception as e:
            log.error("Gemini error: %s", e)
            self.voice.speak("Task completed, sir.")


# ── Listener (always-on mic) ──────────────────────────────────────

class Listener:
    """Continuously listens to the mic for the wake word."""

    def __init__(self, wake_word: str = "jarvis"):
        self.wake_word = wake_word.lower()
        self.running   = True

        self.rec = sr.Recognizer()
        self.rec.energy_threshold         = 260
        self.rec.dynamic_energy_threshold = True
        self.rec.pause_threshold          = 0.55
        self.rec.phrase_threshold          = 0.2
        self.rec.non_speaking_duration     = 0.4

    def loop(self, on_command):
        """Blocking listen loop. Calls on_command(text) when wake word is heard."""
        try:
            with sr.Microphone() as mic:
                log.info("Calibrating mic...")
                self.rec.adjust_for_ambient_noise(mic, duration=0.8)
                log.info("Listening. Say '%s' to activate.", self.wake_word)

                while self.running:
                    try:
                        audio = self.rec.listen(mic, timeout=2.5, phrase_time_limit=7.0)
                        text  = self.rec.recognize_google(audio).strip()
                        if not text:
                            continue

                        if self.wake_word in text.lower():
                            log.info("Wake word detected: %r", text)
                            on_command(text)

                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        continue
                    except Exception as e:
                        log.debug("Listen error: %s", e)
                        continue

        except Exception as e:
            log.error("Mic init error: %s", e)


# ── Main ──────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 55)
    print("  JARVIS  -  Voice Assistant")
    print("=" * 55)
    print()
    print("  Commands you can try:")
    print("    'Jarvis, play Let It Happen by Tame Impala'")
    print("    'Jarvis, like this post'")
    print("    'Jarvis, look at my screen'")
    print("    'Jarvis, message Alex on WhatsApp saying I'm on my way'")
    print("    'Jarvis, set volume to 70'")
    print("    'Jarvis, open Instagram'")
    print()
    print("  Type 'exit' or 'quit' to stop.")
    print("=" * 55)
    print()

    voice    = Voice()
    brain    = Brain(voice)
    listener = Listener(wake_word="jarvis")

    def handle(cmd: str):
        cmd = cmd.strip()
        if not cmd:
            return

        print(f"\n  You > {cmd}")

        if cmd.lower() in ("exit", "quit", "goodbye", "bye jarvis", "stop jarvis"):
            print("  JARVIS: Powering down. Have a good day, sir.")
            voice.speak("Powering down. Have a good day, sir.")
            listener.running = False
            sys.exit(0)

        brain.process(cmd)

    # greeting
    greeting = "All systems online, sir. Say Jarvis whenever you need me."
    print(f"  JARVIS: {greeting}\n")
    voice.speak(greeting)

    # mic listener on background thread
    threading.Thread(target=listener.loop, args=(handle,), daemon=True).start()

    # also accept typed input
    while listener.running:
        try:
            typed = input().strip()
            if typed:
                handle(typed)
        except (KeyboardInterrupt, EOFError):
            print("\n  JARVIS: Shutting down. Goodbye, sir.")
            listener.running = False
            break


if __name__ == "__main__":
    main()
