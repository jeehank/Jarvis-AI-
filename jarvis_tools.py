"""
Jarvis Computer Control Tools
Exposes Python functions and tool declarations for LLM function calling.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path

import pyautogui
from pycaw.pycaw import AudioUtilities

# Configure PyAutoGUI fail-safe
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

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
    "twitter": "https://x.com",
    "x": "https://x.com",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "whatsapp": "https://web.whatsapp.com",
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
    import re
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
    """Type arbitrary text on the keyboard as if the user typed it."""
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
    "search_google": search_google,
    "set_system_volume": set_system_volume,
    "get_system_volume": get_system_volume,
    "take_screenshot": take_screenshot,
    "press_keyboard_keys": press_keyboard_keys,
    "type_keyboard_text": type_keyboard_text,
    "system_action": system_action,
}
