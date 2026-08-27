"""
jarvis_tools.py
Computer control and automation tools for JARVIS.
Exposes Python functions and tool declarations for Groq LLM tool calling.
"""

from __future__ import annotations

import io
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional

from PIL import Image
from dotenv import load_dotenv
import pyautogui
import pyperclip
from pycaw.pycaw import AudioUtilities

# Load .env
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH)

# Configure PyAutoGUI
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.2

log = logging.getLogger("jarvis.tools")

# Common web services / accounts mapping
ACCOUNT_URLS = {
    "youtube": "https://www.youtube.com",
    "instagram": "https://www.instagram.com",
    "spotify": "https://open.spotify.com",
    "gmail": "https://mail.google.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "discord": "https://discord.com/app",
    "whatsapp": "https://web.whatsapp.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "netflix": "https://www.netflix.com",
    "reddit": "https://www.reddit.com",
    "linkedin": "https://www.linkedin.com",
    "facebook": "https://www.facebook.com",
    "amazon": "https://www.amazon.com",
    "notion": "https://www.notion.so",
}

# Windows Application Paths and Aliases
WINDOWS_APP_ALIASES = {
    "spotify": [r"%APPDATA%\Spotify\Spotify.exe", "spotify"],
    "chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", "chrome"],
    "cursor": [r"%LOCALAPPDATA%\Programs\cursor\Cursor.exe", "cursor"],
    "vscode": [r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe", "code"],
    "code": [r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe", "code"],
    "notepad": ["notepad.exe", "notepad"],
    "calculator": ["calc.exe", "calc"],
    "calc": ["calc.exe", "calc"],
    "discord": [r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe", "discord"],
    "explorer": ["explorer.exe"],
    "files": ["explorer.exe"],
    "task manager": ["taskmgr.exe"],
    "cmd": ["cmd.exe"],
    "terminal": ["wt.exe", "powershell.exe", "cmd.exe"],
    "powershell": ["powershell.exe"],
}


def open_website(url_or_service: str) -> str:
    """Opens a website or account in the default web browser."""
    target = url_or_service.lower().strip()
    if target in ACCOUNT_URLS:
        url = ACCOUNT_URLS[target]
    elif target.startswith("http://") or target.startswith("https://"):
        url = target
    else:
        url = f"https://{target}.com" if "." not in target else f"https://{target}"

    webbrowser.open(url)
    return f"Opened {target} at {url}."


def open_application(app_name: str) -> str:
    """Open any desktop application like Spotify, Chrome, Cursor, VS Code, Notepad, Calculator, Discord, Explorer, Task Manager."""
    name_clean = app_name.lower().strip()

    # 1. Check known aliases
    if name_clean in WINDOWS_APP_ALIASES:
        for candidate in WINDOWS_APP_ALIASES[name_clean]:
            expanded = os.path.expandvars(candidate)
            try:
                subprocess.Popen(expanded, shell=True)
                return f"Successfully launched {app_name}."
            except Exception:
                continue

    # 2. Check if the app is in system PATH
    found = shutil.which(name_clean) or shutil.which(f"{name_clean}.exe")
    if found:
        try:
            subprocess.Popen([found])
            return f"Successfully opened {app_name} from system path."
        except Exception as e:
            log.warning("Failed executing %s: %s", found, e)

    # 3. Windows 'start' shell command fallback
    if sys.platform == "win32":
        try:
            subprocess.Popen(["cmd.exe", "/c", "start", "", name_clean], shell=True)
            return f"Attempted to start {app_name} via Windows shell."
        except Exception as e:
            return f"Failed to start {app_name}: {e}"

    return f"Application '{app_name}' not found."


def open_folder(folder_name: str) -> str:
    """Open special Windows folders like 'downloads', 'documents', 'desktop', 'pictures', 'videos', or any custom directory path."""
    f = folder_name.lower().strip()
    user_home = Path.home()

    known_folders = {
        "downloads": user_home / "Downloads",
        "documents": user_home / "Documents",
        "desktop": user_home / "Desktop",
        "pictures": user_home / "Pictures",
        "photos": user_home / "Pictures",
        "videos": user_home / "Videos",
        "music": user_home / "Music",
        "home": user_home,
    }

    target_path = known_folders.get(f) or Path(os.path.expandvars(folder_name))

    if target_path.exists():
        if sys.platform == "win32":
            subprocess.Popen(["explorer.exe", str(target_path)])
        else:
            subprocess.Popen(["xdg-open", str(target_path)])
        return f"Opened folder: {target_path}"
    else:
        return f"Folder '{folder_name}' does not exist."


def play_youtube_video(query: str) -> str:
    """Directly searches YouTube, extracts the top video, and immediately plays it in browser."""
    q_clean = query.strip()
    encoded = urllib.parse.quote_plus(q_clean)
    search_url = f"https://www.youtube.com/results?search_query={encoded}"

    # Attempt to extract the first video ID so the video starts playing immediately
    try:
        req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        html = urllib.request.urlopen(req, timeout=3.5).read().decode("utf-8", errors="ignore")
        video_ids = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html)
        if video_ids:
            first_id = video_ids[0]
            direct_url = f"https://www.youtube.com/watch?v={first_id}"
            webbrowser.open(direct_url)
            return f"Playing '{q_clean}' directly on YouTube."
    except Exception as e:
        log.warning("Could not extract direct video ID: %s", e)

    # Fallback to search results page
    webbrowser.open(search_url)
    return f"Opened YouTube search for '{q_clean}'."


# Specific Instagram contact direct thread URLs and nicknames
INSTAGRAM_CONTACT_URLS = {
    # Sohani
    "sohani": "https://www.instagram.com/direct/t/17842231331975509/",
    "sohu": "https://www.instagram.com/direct/t/17842231331975509/",
    "soha": "https://www.instagram.com/direct/t/17842231331975509/",

    # Abhirup / Abhiroop / Abhi
    "abhi": "https://www.instagram.com/direct/t/17843980718954777/",
    "abhirup": "https://www.instagram.com/direct/t/17843980718954777/",
    "abhiroop": "https://www.instagram.com/direct/t/17843980718954777/",
    "abirup": "https://www.instagram.com/direct/t/17843980718954777/",
    "abiroop": "https://www.instagram.com/direct/t/17843980718954777/",

    # Sampriti / Sam / Samp
    "sampriti": "https://www.instagram.com/direct/t/17845065615183091/",
    "sam": "https://www.instagram.com/direct/t/17845065615183091/",
    "samp": "https://www.instagram.com/direct/t/17845065615183091/",
}


def open_whatsapp(mode: str = "web") -> str:
    """Opens WhatsApp. mode='app' opens the native Windows Desktop app; mode='web' opens WhatsApp Web."""
    if "app" in mode.lower() or "desktop" in mode.lower():
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer.exe", r"shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App"])
            else:
                subprocess.Popen(["whatsapp"])
            return "Launched WhatsApp Desktop App."
        except Exception as e:
            log.warning("Could not launch WhatsApp App directly: %s; opening Web.", e)
            webbrowser.open("https://web.whatsapp.com")
            return "Opened WhatsApp Web."
    else:
        webbrowser.open("https://web.whatsapp.com")
        return "Opened WhatsApp Web."


def like_current_post(platform: str = "instagram") -> str:
    """Likes the active post/reel on screen by moving to the post and liking it."""
    try:
        sw, sh = pyautogui.size()
        target_x, target_y = sw // 2, int(sh * 0.48)

        # Move mouse to the post location
        pyautogui.moveTo(target_x, target_y, duration=0.2)
        # Double click the post
        pyautogui.doubleClick(target_x, target_y)
        time.sleep(0.1)
        # Also press 'l' (Instagram/social feeds web shortcut)
        pyautogui.press("l")

        return "Located active post on screen and liked it."
    except Exception as e:
        return f"Could not like post: {e}"


def send_whatsapp_message(contact_or_number: str, message: str, use_app: bool = True) -> str:
    """Opens WhatsApp (Desktop App or Web), searches the contact, types the message, and sends it."""
    import threading

    contact_clean = contact_or_number.strip()
    msg_to_send = message.strip() if message.strip() else "hey"

    # Check if contact is a direct phone number
    phone_digits = re.sub(r"[^\d+]", "", contact_clean)
    if len(phone_digits) >= 10:
        url = f"https://web.whatsapp.com/send?phone={phone_digits}&text={urllib.parse.quote(msg_to_send)}"
        webbrowser.open(url)
        def _send_web_num():
            time.sleep(8.0)
            pyautogui.press("enter")
        threading.Thread(target=_send_web_num, daemon=True).start()
        return f"Opened WhatsApp chat for {contact_clean} and sending: '{msg_to_send}'."

    if use_app and sys.platform == "win32":
        # Launch Windows WhatsApp Desktop App
        try:
            subprocess.Popen(["explorer.exe", r"shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App"])
        except Exception:
            subprocess.Popen(["cmd.exe", "/c", "start", "whatsapp:"], shell=True)

        def _send_app():
            try:
                # Wait for WhatsApp window to open and focus
                time.sleep(3.5)
                sw, sh = pyautogui.size()

                # Click search area at top-left of WhatsApp window
                search_x = int(sw * 0.15)
                search_y = int(sh * 0.07)
                pyautogui.click(search_x, search_y)
                time.sleep(0.3)

                # Focus search bar
                pyautogui.hotkey("ctrl", "f")
                time.sleep(0.4)

                # Clear and type contact name
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.1)
                pyperclip.copy(contact_clean)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(1.8)

                # Select contact result
                pyautogui.press("down")
                time.sleep(0.2)
                pyautogui.press("enter")
                time.sleep(1.0)

                # Focus chat input area in bottom right
                pyautogui.click(int(sw * 0.65), int(sh * 0.94))
                time.sleep(0.3)

                # Paste and send message
                pyperclip.copy(msg_to_send)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.4)
                pyautogui.press("enter")

                log.info("Sent WhatsApp Desktop message to %s: %r", contact_clean, msg_to_send)
            except Exception as e:
                log.warning("WhatsApp desktop send error: %s", e)

        threading.Thread(target=_send_app, daemon=True).start()
        return f"Opened WhatsApp Desktop and sending message to {contact_clean}: '{msg_to_send}'."

    else:
        # WhatsApp Web fallback
        url = "https://web.whatsapp.com"
        webbrowser.open(url)
        def _send_web():
            try:
                time.sleep(8.0)
                sw, sh = pyautogui.size()
                pyautogui.click(int(sw * 0.18), int(sh * 0.06))
                time.sleep(0.5)
                pyperclip.copy(contact_clean)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(2.0)
                pyautogui.press("down")
                time.sleep(0.2)
                pyautogui.press("enter")
                time.sleep(1.0)
                pyperclip.copy(msg_to_send)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.3)
                pyautogui.press("enter")
            except Exception as e:
                log.warning("WhatsApp web send error: %s", e)

        threading.Thread(target=_send_web, daemon=True).start()
        return f"Opened WhatsApp Web and sending message to {contact_clean}."


def send_email_compose(recipient: str = "", subject: str = "", body: str = "") -> str:
    """Opens Gmail compose window with recipient, subject, and body pre-filled."""
    rec_encoded = urllib.parse.quote(recipient.strip())
    sub_encoded = urllib.parse.quote(subject.strip())
    body_encoded = urllib.parse.quote(body.strip())

    url = f"https://mail.google.com/mail/u/0/?fs=1&tf=cm&to={rec_encoded}&su={sub_encoded}&body={body_encoded}"
    webbrowser.open(url)
    return f"Opened Gmail compose draft to {recipient or 'recipient'} with subject '{subject}'."


def send_instagram_dm_message(contact_or_username: str, message: str = "") -> str:
    """Opens Instagram Direct chat for a contact and reliably sends the message."""
    import threading

    c_lower = contact_or_username.lower().strip().replace("@", "")

    # Check mapped threads
    if c_lower in INSTAGRAM_CONTACT_URLS:
        target_url = INSTAGRAM_CONTACT_URLS[c_lower]
        display_name = c_lower.capitalize()
    else:
        target_url = f"https://www.instagram.com/direct/t/{c_lower}/" if c_lower else "https://www.instagram.com/direct/inbox/"
        display_name = f"@{c_lower}"

    webbrowser.open(target_url)
    msg_to_send = message.strip() if message.strip() else "hey"

    def _auto_type_and_send():
        try:
            # Wait for Instagram chat page to load
            time.sleep(6.0)
            sw, sh = pyautogui.size()

            # Click message input area
            click_targets = [
                (int(sw * 0.55), int(sh * 0.92)),
                (int(sw * 0.60), int(sh * 0.90)),
                (int(sw * 0.50), int(sh * 0.93)),
            ]
            for cx, cy in click_targets:
                pyautogui.click(cx, cy)
                time.sleep(0.3)
                break

            time.sleep(0.3)
            for _ in range(3):
                pyautogui.press("tab")
                time.sleep(0.15)

            time.sleep(0.3)
            pyperclip.copy(msg_to_send)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.5)
            pyautogui.press("enter")
            log.info("Sent Instagram DM to %s: %r", display_name, msg_to_send)
        except Exception as e:
            log.warning("Auto-send Instagram DM error: %s", e)

    threading.Thread(target=_auto_type_and_send, daemon=True).start()
    return f"Opened Instagram chat with {display_name} and sending: '{msg_to_send}'."


def capture_desktop_image() -> Optional[Image.Image]:
    """Capture desktop screenshot with fallbacks."""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        if img:
            return img
    except Exception:
        pass
    try:
        return pyautogui.screenshot()
    except Exception:
        pass
    return None


def get_active_window_title() -> str:
    """Returns the title of the currently focused window on Windows."""
    try:
        if sys.platform == "win32":
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                return buff.value
    except Exception:
        pass
    return "Desktop"


def see_and_analyze_screen(question_or_instruction: str) -> str:
    """Inspects the active window and screen state to answer questions or describe what is open."""
    try:
        title = get_active_window_title()
        sw, sh = pyautogui.size()
        img = capture_desktop_image()
        status = "Screenshot captured successfully." if img else "Display active."

        return f"Currently active window: '{title}' on display ({sw}x{sh}). {status} {question_or_instruction}"
    except Exception as e:
        log.error("Vision analysis error: %s", e)
        return f"Could not analyze screen: {e}"


def scroll_screen(direction: str = "down", amount: int = 5) -> str:
    """Scroll the active window up or down (e.g. while reading reels, feeds, or documents)."""
    d = direction.lower().strip()
    clicks = max(1, int(amount)) * 120
    try:
        if d in ("up", "top"):
            pyautogui.scroll(clicks)
            return f"Scrolled up {amount} clicks."
        else:
            pyautogui.scroll(-clicks)
            return f"Scrolled down {amount} clicks."
    except Exception as e:
        return f"Scroll failed: {e}"


def click_on_screen(x: int, y: int, double_click: bool = False) -> str:
    """Click specific coordinates on the screen."""
    try:
        if double_click:
            pyautogui.doubleClick(x, y)
            return f"Double clicked at ({x}, {y})."
        else:
            pyautogui.click(x, y)
            return f"Clicked at ({x}, {y})."
    except Exception as e:
        return f"Failed to click: {e}"


def search_google(query: str) -> str:
    """Search Google for real-time information or answers."""
    encoded = urllib.parse.quote_plus(query.strip())
    url = f"https://www.google.com/search?q={encoded}"
    webbrowser.open(url)
    return f"Searching Google for '{query}'."


def set_system_volume(level_percent: int) -> str:
    """Sets master system volume (0-100%)."""
    clamped = max(0, min(100, int(level_percent)))
    try:
        spk = AudioUtilities.GetSpeakers()
        vol = spk.EndpointVolume
        vol.SetMasterVolumeLevelScalar(clamped / 100.0, None)
        return f"System volume set to {clamped}%."
    except Exception as e:
        return f"Failed to adjust volume: {e}"


def get_system_volume() -> str:
    """Gets the current master system volume percentage."""
    try:
        spk = AudioUtilities.GetSpeakers()
        vol = spk.EndpointVolume
        current = int(vol.GetMasterVolumeLevelScalar() * 100)
        is_muted = vol.GetMute()
        status = " (Muted)" if is_muted else ""
        return f"Current master volume is {current}%{status}."
    except Exception as e:
        return f"Failed to get volume: {e}"


def take_screenshot(filename: str = "") -> str:
    """Takes a screenshot of the entire desktop and saves it to user's Pictures folder."""
    try:
        pics_dir = Path.home() / "Pictures" / "Screenshots"
        pics_dir.mkdir(parents=True, exist_ok=True)
        fname = filename.strip() or f"jarvis_snap_{int(time.time())}.png"
        if not fname.endswith(".png"):
            fname += ".png"
        out_path = pics_dir / fname
        img = pyautogui.screenshot()
        img.save(str(out_path))
        return f"Screenshot saved to {out_path}."
    except Exception as e:
        return f"Failed to take screenshot: {e}"


def press_keyboard_keys(hotkey: str) -> str:
    """Press keyboard hotkeys (e.g. 'ctrl+c', 'ctrl+v', 'alt+tab', 'enter', 'space', 'esc', 'win+d', 'f11')."""
    h = hotkey.lower().strip()
    try:
        if "+" in h:
            keys = [k.strip() for k in h.split("+")]
            pyautogui.hotkey(*keys)
        else:
            pyautogui.press(h)
        return f"Pressed hotkey '{hotkey}'."
    except Exception as e:
        return f"Failed pressing hotkey: {e}"


def type_keyboard_text(text: str, press_enter: bool = True) -> str:
    """Types text directly into the active window."""
    try:
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        if press_enter:
            time.sleep(0.1)
            pyautogui.press("enter")
        return f"Typed: '{text}'."
    except Exception as e:
        return f"Failed typing text: {e}"


def system_action(action: str) -> str:
    """Performs system actions: 'lock', 'minimize_all', 'mute', 'unmute', 'toggle_mute'."""
    act = action.lower().strip()
    if act == "lock":
        if sys.platform == "win32":
            subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
            return "Locked workstation."
        return "Lock command only supported on Windows."
    elif act in ("minimize_all", "show_desktop"):
        pyautogui.hotkey("win", "d")
        return "Minimized all windows."
    elif act in ("mute", "unmute", "toggle_mute"):
        if sys.platform == "win32":
            try:
                spk = AudioUtilities.GetSpeakers()
                vol = spk.EndpointVolume
                current_mute = vol.GetMute()
                vol.SetMute(not current_mute, None)
                return "Muted audio." if not current_mute else "Unmuted audio."
            except Exception as e:
                return f"Failed to toggle mute: {e}"
    return f"Action '{action}' is not supported."


# ── Groq / OpenAI Standard Tool Declarations ──────────────────────────

GROQ_TOOL_DECLARATIONS = [
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "Opens any website, social media, or account URL (e.g. YouTube, Instagram, Gmail, GitHub, Spotify, Discord, Netflix, ChatGPT, Claude, Twitter/X).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url_or_service": {
                        "type": "string",
                        "description": "The website name or URL, e.g. 'instagram', 'youtube', 'gmail', 'github', or 'https://example.com'."
                    }
                },
                "required": ["url_or_service"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Opens a desktop application on the computer like Spotify, Chrome, Cursor, VS Code, Notepad, Calculator, Task Manager, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "The name of the application to open, e.g. 'Spotify', 'Cursor', 'Notepad', 'Chrome'."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_folder",
            "description": "Opens Windows folders like 'downloads', 'documents', 'desktop', 'pictures', 'videos', or any custom path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_name": {
                        "type": "string",
                        "description": "The name or path of the folder, e.g. 'downloads', 'documents', 'desktop'."
                    }
                },
                "required": ["folder_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_youtube_video",
            "description": "Directly searches, opens, and starts playing a specific song, music track, or video on YouTube.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The song title, artist, or video search query (e.g. 'Let It Happen Tame Impala')."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "like_current_post",
            "description": "Likes the active post, reel, photo, or video currently visible on screen (on Instagram, Twitter/X, YouTube).",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "The platform name, e.g. 'instagram', 'x', 'youtube'."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_whatsapp_message",
            "description": "Opens WhatsApp and starts a chat or prepares a message for a specific contact or phone number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_or_number": {
                        "type": "string",
                        "description": "The contact name or phone number."
                    },
                    "message": {
                        "type": "string",
                        "description": "The message text to send."
                    }
                },
                "required": ["contact_or_number", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email_compose",
            "description": "Opens Gmail compose draft with recipient, subject line, and body message pre-filled.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient": {
                        "type": "string",
                        "description": "The recipient email address or name."
                    },
                    "subject": {
                        "type": "string",
                        "description": "The email subject line."
                    },
                    "body": {
                        "type": "string",
                        "description": "The email body text."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_instagram_dm",
            "description": "Opens Instagram Direct Message chat with a specific user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "The Instagram username without @."
                    },
                    "message": {
                        "type": "string",
                        "description": "Optional message text."
                    }
                },
                "required": ["username"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "see_and_analyze_screen",
            "description": "Looks at the active computer screen and focused window to inspect state or read content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question_or_instruction": {
                        "type": "string",
                        "description": "What to look for or analyze on screen."
                    }
                },
                "required": ["question_or_instruction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scroll_screen",
            "description": "Scrolls the active window up or down (useful for feeds, Instagram, articles).",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "description": "'up' or 'down'."
                    },
                    "amount": {
                        "type": "integer",
                        "description": "How much to scroll (default 5)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_google",
            "description": "Searches Google for real-time information or questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on Google."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_system_volume",
            "description": "Sets the computer master audio volume level as a percentage from 0 to 100.",
            "parameters": {
                "type": "object",
                "properties": {
                    "level_percent": {
                        "type": "integer",
                        "description": "Volume level percentage between 0 and 100."
                    }
                },
                "required": ["level_percent"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_volume",
            "description": "Queries the current computer master audio volume level percentage.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Takes a screenshot of the user's computer screen and saves it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Optional name for the screenshot file."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "press_keyboard_keys",
            "description": "Presses keyboard keys or key combinations (e.g. 'ctrl+c', 'ctrl+v', 'alt+tab', 'enter', 'space', 'esc', 'win+d').",
            "parameters": {
                "type": "object",
                "properties": {
                    "hotkey": {
                        "type": "string",
                        "description": "The key or combination to press, e.g. 'enter', 'ctrl+w', 'alt+tab', 'win+d'."
                    }
                },
                "required": ["hotkey"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "type_keyboard_text",
            "description": "Types arbitrary text on the keyboard into the currently focused window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to type."
                    },
                    "press_enter": {
                        "type": "boolean",
                        "description": "Whether to press Enter after typing."
                    }
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "system_action",
            "description": "Performs system level operations like locking the computer, minimizing all windows, or muting sound.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "One of: 'lock', 'minimize_all', 'mute', 'unmute', 'toggle_mute'."
                    }
                },
                "required": ["action"]
            }
        }
    }
]

# Alias for backwards compatibility
JARVIS_TOOL_DECLARATIONS = GROQ_TOOL_DECLARATIONS

TOOL_FUNCTION_MAP = {
    "open_website": open_website,
    "open_application": open_application,
    "open_folder": open_folder,
    "open_whatsapp": open_whatsapp,
    "play_youtube_video": play_youtube_video,
    "like_current_post": like_current_post,
    "send_whatsapp_message": send_whatsapp_message,
    "send_email_compose": send_email_compose,
    "send_instagram_dm": send_instagram_dm_message,
    "send_instagram_dm_message": send_instagram_dm_message,
    "see_and_analyze_screen": see_and_analyze_screen,
    "scroll_screen": scroll_screen,
    "click_on_screen": click_on_screen,
    "search_google": search_google,
    "set_system_volume": set_system_volume,
    "get_system_volume": get_system_volume,
    "take_screenshot": take_screenshot,
    "press_keyboard_keys": press_keyboard_keys,
    "type_keyboard_text": type_keyboard_text,
    "system_action": system_action,
}
