"""
Jarvis Computer Control & Multimodal Tools
Exposes Python functions and tool declarations for LLM function calling and screen vision.
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
import webbrowser
from pathlib import Path
from typing import Optional

from PIL import Image
from dotenv import load_dotenv
import pyautogui
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
    "amazon": "https://www.amazon.com",
    "reddit": "https://www.reddit.com",
    "linkedin": "https://www.linkedin.com",
}


def open_website(url_or_service: str) -> str:
    """Open any website, social media, or account URL (e.g. YouTube, Instagram, Gmail, GitHub, Spotify, Discord, Netflix)."""
    clean = url_or_service.strip().lower()

    # Check predefined accounts / websites
    if clean in ACCOUNT_URLS:
        target_url = ACCOUNT_URLS[clean]
        webbrowser.open(target_url)
        return f"Opened {clean.capitalize()} in your browser."

    # Direct URL
    target_url = url_or_service.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = f"https://{target_url}"
    try:
        webbrowser.open(target_url)
        return f"Opened {target_url} in your browser."
    except Exception as e:
        return f"Failed to open {url_or_service}: {e}"


def open_application(app_name: str) -> str:
    """Open any desktop application like Spotify, Chrome, Cursor, VS Code, Notepad, Calculator, Discord, Explorer, Task Manager."""
    app_lower = app_name.lower().strip()
    log.info("Opening application: %s", app_name)

    # Windows built-in apps
    win_apps = {
        "spotify": "spotify:",
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "cmd": "cmd.exe",
        "terminal": "wt.exe",
        "explorer": "explorer.exe",
        "task manager": "taskmgr.exe",
        "taskmgr": "taskmgr.exe",
        "paint": "mspaint.exe",
        "whatsapp": "whatsapp:",
    }

    if app_lower in win_apps:
        target = win_apps[app_lower]
        try:
            if sys.platform == "win32":
                os.startfile(target)
            else:
                subprocess.Popen([target])
            return f"Launched {app_name}."
        except Exception as e:
            return f"Failed to launch {app_name}: {e}"

    # Cursor / VS Code
    if "cursor" in app_lower:
        local = os.environ.get("LOCALAPPDATA", "")
        for sub in ("Programs\\cursor\\Cursor.exe", "Programs\\Cursor\\Cursor.exe"):
            p = os.path.join(local, *sub.split("\\"))
            if os.path.isfile(p):
                subprocess.Popen([p])
                return "Launched Cursor IDE."
        if shutil.which("cursor"):
            subprocess.Popen(["cursor"])
            return "Launched Cursor IDE."

    if "code" in app_lower or "vscode" in app_lower or "vs code" in app_lower:
        if shutil.which("code"):
            subprocess.Popen(["code"])
            return "Launched Visual Studio Code."

    # Chrome
    if "chrome" in app_lower or "browser" in app_lower:
        for base in (
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
        ):
            if not base:
                continue
            p = os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")
            if os.path.isfile(p):
                subprocess.Popen([p])
                return "Launched Google Chrome."

    # Generic startfile attempt
    try:
        if sys.platform == "win32":
            os.startfile(app_name)
            return f"Started {app_name}."
    except Exception:
        pass

    return f"Could not find an application named '{app_name}'."


def open_folder(folder_name: str) -> str:
    """Open special Windows folders like 'downloads', 'documents', 'desktop', 'pictures', 'videos', or any custom directory path."""
    f = folder_name.lower().strip()
    user_home = Path.home()

    special_folders = {
        "downloads": user_home / "Downloads",
        "documents": user_home / "Documents",
        "desktop": user_home / "Desktop",
        "pictures": user_home / "Pictures",
        "videos": user_home / "Videos",
        "music": user_home / "Music",
        "home": user_home,
    }

    target = special_folders.get(f) or Path(folder_name).expanduser()
    if target.exists():
        if sys.platform == "win32":
            os.startfile(str(target))
        else:
            subprocess.Popen(["xdg-open", str(target)])
        return f"Opened folder {target}."
    return f"Folder '{folder_name}' not found."


def play_youtube_video(query: str) -> str:
    """Directly search, open, and start playing the top matching video or song on YouTube."""
    import urllib.request
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


def like_current_post(platform: str = "instagram") -> str:
    """Likes the post, reel, or video currently visible on screen (Instagram, YouTube, Twitter/X)."""
    p = platform.lower().strip()
    try:
        # Instagram like action: 'L' keyboard shortcut + double click center of screen
        if "insta" in p:
            # 1. Press 'l' key (Instagram web shortcut to like focused post)
            pyautogui.press("l")
            # 2. Also double click near center where post/reel is displayed
            sw, sh = pyautogui.size()
            cx, cy = sw // 2, sh // 2
            pyautogui.doubleClick(cx, cy)
            return "Liked the active Instagram post."

        elif "x" in p or "twitter" in p:
            pyautogui.press("l")
            return "Liked the active post on X."

        elif "youtube" in p:
            # YouTube like button shortcut or coordinate
            pyautogui.press("i")
            return "Interacted with YouTube video."

        else:
            # Generic double click
            sw, sh = pyautogui.size()
            pyautogui.doubleClick(sw // 2, sh // 2)
            return "Liked the active post."

    except Exception as e:
        return f"Could not like post: {e}"


def send_whatsapp_message(contact_or_number: str, message: str) -> str:
    """Opens WhatsApp and prepares or sends a message to a contact or phone number."""
    contact_clean = contact_or_number.strip()
    msg_encoded = urllib.parse.quote(message.strip())

    # Check if contact is a phone number (digits only or starts with +)
    phone_digits = re.sub(r"[^\d+]", "", contact_clean)
    if len(phone_digits) >= 10:
        url = f"https://web.whatsapp.com/send?phone={phone_digits}&text={msg_encoded}"
        webbrowser.open(url)
        return f"Opened WhatsApp chat for {contact_clean} with your message."

    # Contact Name: Open WhatsApp Web / App
    url = f"https://web.whatsapp.com/send?text={msg_encoded}"
    webbrowser.open(url)
    return f"Opened WhatsApp with your message for {contact_clean}."


def send_email_compose(recipient: str = "", subject: str = "", body: str = "") -> str:
    """Opens Gmail compose window with recipient, subject, and body pre-filled."""
    rec_encoded = urllib.parse.quote(recipient.strip())
    sub_encoded = urllib.parse.quote(subject.strip())
    body_encoded = urllib.parse.quote(body.strip())
    
    url = f"https://mail.google.com/mail/u/0/?fs=1&tf=cm&to={rec_encoded}&su={sub_encoded}&body={body_encoded}"
    webbrowser.open(url)
    return f"Opened Gmail compose draft to {recipient or 'recipient'} with subject '{subject}'."


def send_instagram_dm(username: str, message: str = "") -> str:
    """Opens Instagram direct message chat with a user."""
    u_clean = username.strip().replace("@", "")
    url = f"https://www.instagram.com/direct/t/{u_clean}/" if u_clean else "https://www.instagram.com/direct/inbox/"
    webbrowser.open(url)
    return f"Opened Instagram Direct Message for @{u_clean}."


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


def see_and_analyze_screen(question_or_instruction: str) -> str:
    """Takes a live screenshot and uses Gemini Vision to see what is on screen and answer questions or describe it."""
    try:
        from google import genai
        from google.genai import types
        gemini_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
        if not gemini_key:
            return "Gemini API key is required to view screen."

        img = capture_desktop_image()
        if not img:
            return "Could not capture active screen."

        img.thumbnail((1280, 720))
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="JPEG", quality=80)
        img_bytes = img_byte_arr.getvalue()

        client = genai.Client(api_key=gemini_key)
        prompt = f"Look at this live screenshot of the user's computer screen. Answer concisely: {question_or_instruction}"

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                prompt
            ]
        )
        return response.text or "I inspected your screen, sir."
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
    """Set the system master audio volume from 0 to 100 percent."""
    level = max(0, min(100, int(level_percent)))
    if sys.platform == "win32":
        try:
            spk = AudioUtilities.GetSpeakers()
            vol = spk.EndpointVolume
            vol.SetMasterVolumeLevelScalar(level / 100.0, None)
            return f"System volume set to {level}%."
        except Exception as e:
            return f"Could not set volume: {e}"
    return f"Volume control not supported on {sys.platform}."


def get_system_volume() -> str:
    """Get the current system master volume percentage."""
    if sys.platform == "win32":
        try:
            spk = AudioUtilities.GetSpeakers()
            vol = spk.EndpointVolume
            current = int(round(vol.GetMasterVolumeLevelScalar() * 100))
            return f"Current master volume is {current}%."
        except Exception as e:
            return f"Could not query volume: {e}"
    return "Volume query not supported."


def take_screenshot(filename: str = "") -> str:
    """Take a screenshot of the computer screen and save it."""
    try:
        cache_dir = Path(__file__).resolve().parent / ".cache" / "screenshots"
        cache_dir.mkdir(parents=True, exist_ok=True)
        if not filename:
            filename = f"screenshot_{int(time.time())}.png"
        if not filename.endswith(".png"):
            filename += ".png"
        filepath = cache_dir / filename
        pyautogui.screenshot(str(filepath))
        return f"Screenshot saved to {filepath}."
    except Exception as e:
        return f"Failed to capture screenshot: {e}"


def press_keyboard_keys(hotkey: str) -> str:
    """Press keyboard keys or combinations (e.g. 'ctrl+c', 'ctrl+v', 'alt+tab', 'enter', 'space', 'esc', 'win+d')."""
    keys = [k.strip().lower() for k in hotkey.split("+")]
    try:
        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)
        return f"Pressed '{hotkey}'."
    except Exception as e:
        return f"Failed to press '{hotkey}': {e}"


def type_keyboard_text(text: str, press_enter: bool = False) -> str:
    """Type arbitrary text on the keyboard into the currently focused window."""
    try:
        pyautogui.write(text, interval=0.02)
        if press_enter:
            pyautogui.press("enter")
        return f"Typed: '{text}'."
    except Exception as e:
        return f"Failed to type text: {e}"


def system_action(action: str) -> str:
    """Perform system actions: 'lock' (lock PC), 'sleep', 'minimize_all' (show desktop), 'mute', 'unmute', 'toggle_mute'."""
    act = action.lower().strip()
    if sys.platform == "win32":
        if act == "lock":
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return "PC locked."
        elif act in ("minimize_all", "show_desktop"):
            pyautogui.hotkey("win", "d")
            return "Showing desktop."
        elif act in ("mute", "unmute", "toggle_mute"):
            try:
                spk = AudioUtilities.GetSpeakers()
                vol = spk.EndpointVolume
                current_mute = vol.GetMute()
                vol.SetMute(not current_mute, None)
                return "Muted audio." if not current_mute else "Unmuted audio."
            except Exception as e:
                return f"Failed to toggle mute: {e}"
    return f"Action '{action}' is not supported."


# Tool registry definitions for Gemini Function Calling
JARVIS_TOOL_DECLARATIONS = [
    {
        "name": "open_website",
        "description": "Opens any website, social media, or account URL (e.g. YouTube, Instagram, Gmail, GitHub, Spotify, Discord, Netflix, ChatGPT, Claude, Twitter/X).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url_or_service": {
                    "type": "STRING",
                    "description": "The website name or URL, e.g. 'instagram', 'youtube', 'gmail', 'github', or 'https://example.com'."
                }
            },
            "required": ["url_or_service"]
        }
    },
    {
        "name": "open_application",
        "description": "Opens a desktop application on the computer like Spotify, Chrome, Cursor, VS Code, Notepad, Calculator, Task Manager, etc.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "The name of the application to open, e.g. 'Spotify', 'Cursor', 'Notepad', 'Chrome'."
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "open_folder",
        "description": "Opens Windows folders like 'downloads', 'documents', 'desktop', 'pictures', 'videos', or any custom path.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "folder_name": {
                    "type": "STRING",
                    "description": "The name or path of the folder, e.g. 'downloads', 'documents', 'desktop'."
                }
            },
            "required": ["folder_name"]
        }
    },
    {
        "name": "play_youtube_video",
        "description": "Directly searches, opens, and starts playing a specific song, music track, or video on YouTube.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "The song title, artist, or video search query (e.g. 'Let It Happen Tame Impala')."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "like_current_post",
        "description": "Likes the active post, reel, photo, or video currently visible on screen (on Instagram, Twitter/X, YouTube).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "platform": {
                    "type": "STRING",
                    "description": "The platform name, e.g. 'instagram', 'x', 'youtube'."
                }
            }
        }
    },
    {
        "name": "send_whatsapp_message",
        "description": "Opens WhatsApp and starts a chat or prepares a message for a specific contact or phone number.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "contact_or_number": {
                    "type": "STRING",
                    "description": "The contact name or phone number."
                },
                "message": {
                    "type": "STRING",
                    "description": "The message text to send."
                }
            },
            "required": ["contact_or_number", "message"]
        }
    },
    {
        "name": "send_email_compose",
        "description": "Opens Gmail compose draft with recipient, subject line, and body message pre-filled.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "recipient": {
                    "type": "STRING",
                    "description": "The recipient email address or name."
                },
                "subject": {
                    "type": "STRING",
                    "description": "The email subject line."
                },
                "body": {
                    "type": "STRING",
                    "description": "The email body text."
                }
            }
        }
    },
    {
        "name": "send_instagram_dm",
        "description": "Opens Instagram Direct Message chat with a specific user.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "username": {
                    "type": "STRING",
                    "description": "The Instagram username without @."
                },
                "message": {
                    "type": "STRING",
                    "description": "Optional message text."
                }
            },
            "required": ["username"]
        }
    },
    {
        "name": "see_and_analyze_screen",
        "description": "Looks at the live computer screen using Gemini Vision to answer questions about what is displayed, read content, or inspect UI.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "question_or_instruction": {
                    "type": "STRING",
                    "description": "What to look for or analyze on screen."
                }
            },
            "required": ["question_or_instruction"]
        }
    },
    {
        "name": "scroll_screen",
        "description": "Scrolls the active window up or down (useful for feeds, Instagram, articles).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "direction": {
                    "type": "STRING",
                    "description": "'up' or 'down'."
                },
                "amount": {
                    "type": "INTEGER",
                    "description": "How much to scroll (default 5)."
                }
            }
        }
    },
    {
        "name": "search_google",
        "description": "Searches Google for real-time information or questions.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "The search query to look up on Google."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "set_system_volume",
        "description": "Sets the computer master audio volume level as a percentage from 0 to 100.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "level_percent": {
                    "type": "INTEGER",
                    "description": "Volume level percentage between 0 and 100."
                }
            },
            "required": ["level_percent"]
        }
    },
    {
        "name": "get_system_volume",
        "description": "Queries the current computer master audio volume level percentage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "take_screenshot",
        "description": "Takes a screenshot of the user's computer screen and saves it.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "filename": {
                    "type": "STRING",
                    "description": "Optional name for the screenshot file."
                }
            }
        }
    },
    {
        "name": "press_keyboard_keys",
        "description": "Presses keyboard keys or key combinations (e.g. 'ctrl+c', 'ctrl+v', 'alt+tab', 'enter', 'space', 'esc', 'win+d').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "hotkey": {
                    "type": "STRING",
                    "description": "The key or combination to press, e.g. 'enter', 'ctrl+w', 'alt+tab', 'win+d'."
                }
            },
            "required": ["hotkey"]
        }
    },
    {
        "name": "type_keyboard_text",
        "description": "Types arbitrary text on the keyboard into the currently focused window.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text": {
                    "type": "STRING",
                    "description": "The text to type."
                },
                "press_enter": {
                    "type": "BOOLEAN",
                    "description": "Whether to press Enter after typing."
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "system_action",
        "description": "Performs system level operations like locking the computer, minimizing all windows, or muting sound.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "One of: 'lock', 'minimize_all', 'mute', 'unmute', 'toggle_mute'."
                }
            },
            "required": ["action"]
        }
    }
]

TOOL_FUNCTION_MAP = {
    "open_website": open_website,
    "open_application": open_application,
    "open_folder": open_folder,
    "play_youtube_video": play_youtube_video,
    "like_current_post": like_current_post,
    "send_whatsapp_message": send_whatsapp_message,
    "send_email_compose": send_email_compose,
    "send_instagram_dm": send_instagram_dm,
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
