"""
jarvis_agent.py
Main voice agent loop for JARVIS.
Uses Groq for ultra-fast AI reasoning and tool execution, ElevenLabs for voice output.
Listens continuously: starts recording at "Jarvis", finishes and executes when you say "over and out".
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from groq import Groq
import numpy as np
import sounddevice as sd
import speech_recognition as sr
from elevenlabs.client import ElevenLabs

from jarvis_tools import GROQ_TOOL_DECLARATIONS, TOOL_FUNCTION_MAP, ACCOUNT_URLS

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
    "You are JARVIS, an autonomous, highly capable AI assistant and butler (like Tony Stark's JARVIS). "
    "You have full access to tools on the user's Windows computer.\n"
    "--- MESSAGING RULES ---\n"
    "1. When the user asks you to send, generate, compose, write, or draft a message "
    "(e.g. an appreciation message, birthday wish, congratulations, check-in, apology, update, invitation, reminder): "
    "   - GENERATE the actual, thoughtful, friendly message body (do NOT send instructions or placeholders like '[Your Name]'). "
    "   - Call the 'send_whatsapp_message' or 'send_instagram_dm_message' tool with the contact name and your generated message body.\n"
    "2. If the user asks to message 'the group', 'a group', or 'in a group' on WhatsApp, the group name is: "
    "'BLACKBIRD FLY'.\n"
    "3. Keep your spoken responses concise, witty, and polite (1-2 sentences maximum). Address the user as 'sir'."
)

# Contacts that map to Instagram DM threads
KNOWN_IG_ALIASES = (
    "sohani", "sohu", "soha",
    "abhirup", "abhiroop", "abhi", "abirup", "abiroop",
    "sampriti", "sam", "samp",
)


# ── Safe Console Printing ──────────────────────────────────────────

def safe_print(text: str) -> None:
    """Safely print text to standard output, preventing Windows console charmap errors."""
    try:
        print(text)
    except (UnicodeEncodeError, Exception):
        try:
            enc = sys.stdout.encoding or "utf-8"
            print(text.encode(enc, errors="replace").decode(enc))
        except Exception:
            pass


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


def is_generative_intent(text: str) -> bool:
    """Returns True if the prompt asks to compose/generate content rather than sending literal text."""
    lower = text.lower()
    triggers = (
        "generate", "compose", "draft", "write a", "write an", "appreciation",
        "birthday", "congratulat", "wish", "motivat", "thank you", "apology",
        "apologize", "invite", "invitation", "ask if", "ask them", "tell them to",
        "tell him to", "tell her to", "explain to", "remind him", "remind her",
        "an appreciation", "a message of", "a note", "a reminder", "an invite",
    )
    return any(trig in lower for trig in triggers)


# ── Brain (command routing + Groq) ─────────────────────────────────

class Brain:
    """Routes commands: fast-path for common tasks, Groq for complex requests."""

    def __init__(self, voice: Voice):
        self.voice   = voice
        self.client  = None
        self.model   = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
        self.history: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if api_key:
            try:
                self.client = Groq(api_key=api_key)
                log.info("Groq client ready (model: %s).", self.model)
            except Exception as e:
                log.error("Groq init failed: %s", e)
        else:
            log.warning("GROQ_API_KEY not set.")

    # ── public entry point ──

    def process(self, text: str):
        """Handle a user command."""
        text = text.strip()
        if not text:
            return

        if self._try_fast_path(text):
            return

        self._ask_groq(text)

    # ── fast-path router ──

    def _try_fast_path(self, text: str) -> bool:
        """
        Match common patterns and execute immediately (no API call).
        Returns True if handled.
        """
        # Strip wake word and 'over' / 'over and out' phrases from the input
        t = re.sub(r"^(hey\s+)?jarvis[\s,]*", "", text.lower().strip(), flags=re.IGNORECASE).strip()
        t = re.sub(r"\b(over\s+(and\s+|&\s+)?out|over)\b\s*$", "", t, flags=re.IGNORECASE).strip(" ,:.-")

        if not t:
            self.voice.speak("Yes sir, I'm listening. What do you need?")
            return True

        return (
            self._handle_power_state(t)
            or self._handle_like(t)
            or self._handle_play(t)
            or self._handle_instagram(t)
            or self._handle_whatsapp(t)
            or self._handle_group_message(t)
            or self._handle_screen(t)
            or self._handle_scroll(t)
            or self._handle_open(t)
            or self._handle_volume(t)
            or self._handle_screenshot(t)
            or self._handle_desktop_lock(t)
            or self._handle_search(t)
        )

    # ── individual fast-path handlers ──

    def _handle_power_state(self, t: str) -> bool:
        """Handles power state commands: turn on / wake up, and sleep / turn off display."""
        # 1. Turn on / Wake up
        if any(w in t for w in ("turn on", "wake up", "wake", "screen on", "turn on display", "turn on screen", "turn on pc", "turn on computer")) or t in ("turn on", "wake up", "wake", "on"):
            if not any(neg in t for neg in ("don't", "dont", "do not", "never")):
                self.voice.speak("Turning on display and waking up system, sir.")
                res = TOOL_FUNCTION_MAP["system_action"]("turn_on")
                safe_print(f"  JARVIS: {res}")
                return True

        # 2. Sleep / Turn off display
        if any(s in t for s in ("go to sleep", "sleep display", "turn off screen", "turn off display", "screen off", "sleep computer", "sleep pc")) or t in ("sleep", "go to sleep"):
            self.voice.speak("Putting displays to sleep. I will remain listening, sir.")
            res = TOOL_FUNCTION_MAP["system_action"]("sleep")
            safe_print(f"  JARVIS: {res}")
            return True

        return False

    def _handle_like(self, t: str) -> bool:
        keywords = ("post", "this", "reel", "photo", "video", "picture")
        if "like" not in t or not any(k in t for k in keywords):
            return False

        self.voice.speak("Locating the post and liking it now, sir.")
        res = TOOL_FUNCTION_MAP["like_current_post"]("instagram")
        safe_print(f"  JARVIS: {res}")
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

        # If user wants to compose/generate a custom message, let Groq write it
        if is_generative_intent(t):
            return False

        # figure out who
        contact = self._find_ig_contact(t)

        # figure out the message body
        msg_match = re.search(r"(?:saying|message|that|text)\s+(.+)", t)
        message = msg_match.group(1).strip() if msg_match else "hey"

        display = contact.capitalize() if contact else "contact"
        self.voice.speak(f"Opening Instagram chat with {display} and sending your message, sir.")
        res = TOOL_FUNCTION_MAP["send_instagram_dm_message"](contact, message)
        safe_print(f"  JARVIS: {res}")
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

        # If the user is asking to generate/compose/draft a message, let Groq write it!
        if is_generative_intent(t):
            return False

        # 1. "introduce yourself to [contact] on whatsapp"
        intro_m = re.search(r"introduce\s+(?:yourself|jarvis)\s+to\s+([a-zA-Z0-9_+]+)", t)
        if intro_m:
            contact = intro_m.group(1)
            msg = f"Hello {contact.capitalize()}! I am JARVIS, an autonomous AI assistant."
            self.voice.speak(f"Opening WhatsApp and introducing myself to {contact.capitalize()}, sir.")
            res = TOOL_FUNCTION_MAP["send_whatsapp_message"](contact, msg)
            safe_print(f"  JARVIS: {res}")
            return True

        # 2. Standard message templates with explicit keyword delimiters:
        # e.g. "message [contact] on whatsapp saying [msg]" / "send a message to [contact] on whatsapp saying [msg]"
        m1 = re.search(r"(?:send\s+(?:a\s+)?message\s+to|message|text|tell)\s+([a-zA-Z0-9_+]+)(?:\s+on\s+whatsapp)?\s+(?:saying|that|text)\s+(.+)", t)
        if m1:
            contact, msg = m1.group(1), m1.group(2).strip()
            if msg and not is_generative_intent(msg):
                self.voice.speak(f"Sending your message to {contact.capitalize()} on WhatsApp, sir.")
                res = TOOL_FUNCTION_MAP["send_whatsapp_message"](contact, msg)
                safe_print(f"  JARVIS: {res}")
                return True

        m2 = re.search(r"(?:to\s+)?([a-zA-Z0-9_+]+)\s+on\s+whatsapp\s+(?:saying|that|text)\s+(.+)", t)
        if m2:
            contact, msg = m2.group(1), m2.group(2).strip()
            if msg and not is_generative_intent(msg):
                self.voice.speak(f"Sending your message to {contact.capitalize()} on WhatsApp, sir.")
                res = TOOL_FUNCTION_MAP["send_whatsapp_message"](contact, msg)
                safe_print(f"  JARVIS: {res}")
                return True

        # 3. Explicit desktop app launch (check standalone words, NOT substring of 'whatsapp'!)
        if re.search(r"\b(desktop\s+app|whatsapp\s+desktop|whatsapp\s+app)\b", t):
            self.voice.speak("Opening WhatsApp Desktop, sir.")
            TOOL_FUNCTION_MAP["open_whatsapp"]("app")
            return True

        # 4. Simple open: "open whatsapp", "launch whatsapp"
        if t.strip() in ("open whatsapp", "launch whatsapp", "whatsapp", "open whatsapp web"):
            self.voice.speak("Opening WhatsApp for you, sir.")
            TOOL_FUNCTION_MAP["open_whatsapp"]("web")
            return True

        # For all other phrasings, return False so Groq's 120B model extracts contact and generates message
        return False

    def _handle_group_message(self, t: str) -> bool:
        """Handles any request to message/text 'the group' or 'in a group'."""
        group_triggers = ("the group", "a group", "my group", "in the group", "in a group", "debayan group", "to the group", "group chat", "group")
        action_triggers = ("text", "message", "send", "tell", "saying", "write", "post")

        if any(g in t for g in group_triggers) and any(a in t for a in action_triggers):
            # If the user asks to compose/generate, let Groq write it
            if is_generative_intent(t):
                return False

            # 1. Look for explicit delimiters first: "saying [msg]", "that [msg]"
            msg_m = re.search(r"(?:saying|that)\s+(.+)", t)
            if msg_m:
                msg = msg_m.group(1).strip()
            else:
                # Strip all leading command prefixes
                msg = re.sub(
                    r"^(?:please\s+)?(?:send\s+(?:a\s+)?message\s+(?:in|to|on)?|text\s+(?:in|to|on)?|message|tell|write\s+(?:in|to)?)\s*(?:the|a|my|debayan)?\s*group(?:\s+chat)?(?:\s+on\s+whatsapp)?\s*(?:saying|that|text|message)?\s*",
                    "",
                    t,
                    flags=re.IGNORECASE
                ).strip()

            if msg and not is_generative_intent(msg):
                group_name = "BLACKBIRD FLY"
                self.voice.speak("Sending your message to the group on WhatsApp, sir.")
                res = TOOL_FUNCTION_MAP["send_whatsapp_message"](group_name, msg)
                safe_print(f"  JARVIS: {res}")
                return True
        return False

    def _handle_screen(self, t: str) -> bool:
        triggers = ("look", "what", "read", "see", "analyze")
        if "screen" not in t or not any(w in t for w in triggers):
            return False

        self.voice.speak("Inspecting your screen now, sir.")
        result = TOOL_FUNCTION_MAP["see_and_analyze_screen"](t)
        safe_print(f"  JARVIS: {result}")
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

    # ── Groq LLM fallback ──

    def _ask_groq(self, user_text: str):
        """Send to Groq LLM with full tool access for reasoning and autonomous execution."""
        if not self.client:
            self.voice.speak("I'm ready for your command, sir.")
            return

        self.voice.speak("Working on that now, sir.")

        try:
            self.history.append({"role": "user", "content": user_text})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.history,
                tools=GROQ_TOOL_DECLARATIONS,
                tool_choice="auto",
                temperature=0.6,
            )

            msg = response.choices[0].message

            # Execute any tool calls requested by Groq
            if msg.tool_calls:
                self.history.append(msg)
                last_result = ""

                for tool_call in msg.tool_calls:
                    fn_name = tool_call.function.name
                    raw_args = tool_call.function.arguments or "{}"
                    try:
                        fn_args = json.loads(raw_args)
                    except Exception:
                        fn_args = {}

                    log.info("Groq tool call: %s(%s)", fn_name, fn_args)

                    if fn_name in TOOL_FUNCTION_MAP:
                        tool_res = TOOL_FUNCTION_MAP[fn_name](**fn_args)
                    else:
                        tool_res = f"Tool {fn_name} executed."

                    last_result = tool_res
                    self.history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": fn_name,
                        "content": str(tool_res),
                    })

                # Follow up with Groq to get a final conversational response
                try:
                    followup = self.client.chat.completions.create(
                        model=self.model,
                        messages=self.history,
                        temperature=0.6,
                    )
                    reply = followup.choices[0].message.content or f"Done, sir. {last_result}"
                except Exception:
                    reply = f"Done, sir. {last_result}"

                self.history.append({"role": "assistant", "content": reply})
                safe_print(f"  JARVIS: {reply}")
                self.voice.speak(reply)
                return

            # Direct response without tool calls
            reply = msg.content or "Right away, sir."
            self.history.append({"role": "assistant", "content": reply})
            safe_print(f"  JARVIS: {reply}")
            self.voice.speak(reply)

        except Exception as e:
            log.error("Groq API error: %s", e)
            self.voice.speak("Task completed, sir.")


# ── Listener (starts at Jarvis, stops at over) ─────────────────────

class Listener:
    """
    Continuously listens for the wake word 'Jarvis' to begin recording,
    and captures all spoken words until the user says 'over' (or 'over and out').
    """

    def __init__(self, wake_word: str = "jarvis"):
        self.wake_word = wake_word.lower()
        self.running   = True
        self.is_recording = False
        self.buffer: List[str] = []
        self.last_audio_time = 0.0

        self.rec = sr.Recognizer()
        self.rec.energy_threshold         = 280
        self.rec.dynamic_energy_threshold = True
        self.rec.pause_threshold          = 0.8
        self.rec.phrase_threshold          = 0.2
        self.rec.non_speaking_duration     = 0.5

    def _has_stop_phrase(self, text: str) -> bool:
        """Check if text ends with the stop word 'over' (or 'over and out', 'over & out')."""
        t = text.lower().strip()
        return bool(re.search(r"\b(over\s+(and\s+|&\s+)?out|over)\b\s*$", t))

    def _strip_stop_phrase(self, text: str) -> str:
        """Strip 'over' (or 'over and out') from the end of a command string."""
        cleaned = re.sub(r"\b(over\s+(and\s+|&\s+)?out|over)\b\s*$", "", text, flags=re.IGNORECASE)
        return cleaned.strip(" ,:.-")

    def loop(self, on_command):
        """Blocking listen loop. Starts recording at 'jarvis' and stops when 'over' is heard."""
        try:
            with sr.Microphone() as mic:
                log.info("Calibrating microphone...")
                self.rec.adjust_for_ambient_noise(mic, duration=0.8)
                log.info("Continuous listening ACTIVE.")
                log.info("Say 'Jarvis [your instructions] Over'")

                while self.running:
                    try:
                        timeout = 3.0 if not self.is_recording else 4.5
                        phrase_limit = 12.0

                        audio = self.rec.listen(mic, timeout=timeout, phrase_time_limit=phrase_limit)
                        text  = self.rec.recognize_google(audio).strip()
                        if not text:
                            continue

                        text_lower = text.lower()

                        if not self.is_recording:
                            # Waiting for wake word "jarvis"
                            if self.wake_word in text_lower:
                                log.info("Wake word detected: %r", text)
                                idx = text_lower.find(self.wake_word)
                                after_wake = text[idx + len(self.wake_word):].strip(" ,:.-")

                                if self._has_stop_phrase(after_wake):
                                    # Complete prompt in a single sentence
                                    cmd = self._strip_stop_phrase(after_wake)
                                    if cmd:
                                        log.info("Full command received: %r", cmd)
                                        on_command(cmd)
                                else:
                                    # Begin accumulating multi-phrase command
                                    self.is_recording = True
                                    self.buffer = [after_wake] if after_wake else []
                                    self.last_audio_time = time.time()
                                    safe_print("  [Listening... say 'over' to execute]")
                        else:
                            # Currently recording multi-phrase command
                            self.last_audio_time = time.time()
                            log.info("Accumulated chunk: %r", text)

                            if self._has_stop_phrase(text_lower):
                                # Stop phrase detected!
                                clean_chunk = self._strip_stop_phrase(text)
                                if clean_chunk:
                                    self.buffer.append(clean_chunk)

                                full_cmd = " ".join(b for b in self.buffer if b).strip()
                                self.is_recording = False
                                self.buffer = []
                                log.info("Finished listening (over). Command: %r", full_cmd)
                                if full_cmd:
                                    on_command(full_cmd)
                            else:
                                self.buffer.append(text)

                    except sr.WaitTimeoutError:
                        # Safety fallback: if user paused for >12s in recording mode without saying 'over'
                        if self.is_recording and (time.time() - self.last_audio_time > 12.0):
                            full_cmd = " ".join(b for b in self.buffer if b).strip()
                            self.is_recording = False
                            self.buffer = []
                            if full_cmd:
                                log.info("Auto-executing after pause: %r", full_cmd)
                                on_command(full_cmd)
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
    print("=" * 60)
    print("  JARVIS  -  Voice Assistant (Powered by Groq)")
    print("=" * 60)
    print()
    print("  Voice Protocol:")
    print("    Start with: 'Jarvis ...'")
    print("    End with:   '... Over'")
    print()
    print("  Examples:")
    print("    'Jarvis turn on over'")
    print("    'Jarvis go to sleep over'")
    print("    'Jarvis text in the group saying party tonight at 8 over'")
    print("    'Jarvis introduce yourself to abhirup on whatsapp over'")
    print("    'Jarvis play Let It Happen by Tame Impala over'")
    print("    'Jarvis set volume to 70 over'")
    print()
    print("  Type 'exit' or 'quit' to stop.")
    print("=" * 60)
    print()

    voice    = Voice()
    brain    = Brain(voice)
    listener = Listener(wake_word="jarvis")

    def handle(cmd: str):
        cmd = cmd.strip()
        if not cmd:
            return

        safe_print(f"\n  You > {cmd}")

        if cmd.lower() in ("exit", "quit", "goodbye", "bye jarvis", "stop jarvis"):
            safe_print("  JARVIS: Powering down. Have a good day, sir.")
            voice.speak("Powering down. Have a good day, sir.")
            listener.running = False
            sys.exit(0)

        brain.process(cmd)

    # greeting
    greeting = "All systems online, sir. Say Jarvis followed by your command and Over when you are done."
    safe_print(f"  JARVIS: {greeting}\n")
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
            safe_print("\n  JARVIS: Shutting down. Goodbye, sir.")
            listener.running = False
            break


if __name__ == "__main__":
    main()
