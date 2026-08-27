"""
Jarvis Computer Control Tools
Exposes Python functions and tool declarations for LLM function calling.
"""

from __future__ import annotations

import os
import sys
import time
import shutil
import logging
import subprocess
import webbrowser
from pathlib import Path

log = logging.getLogger("jarvis.tools")


def open_application(app_name: str) -> str:
    """Open a desktop application such as Spotify, Chrome, Cursor, VS Code, Notepad, Calculator, Discord, etc."""
    app_lower = app_name.lower().strip()
    log.info("Opening application: %s", app_name)
    
    # Common application mappings on Windows
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
            return f"Successfully launched {app_name}."
        except Exception as e:
            return f"Failed to launch {app_name}: {e}"

    # Check for Cursor / VS Code
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

    # Check Chrome
    if "chrome" in app_lower or "browser" in app_lower:
        for base in (
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
        ):
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

    return f"Could not find an executable or shortcut for {app_name}."


def open_website(url: str, site_name: str = "") -> str:
    """Open a URL or popular website (e.g. YouTube, Instagram, GitHub, Spotify, Netflix, Reddit)."""
    url_clean = url.strip()
    if not url_clean.startswith(("http://", "https://")):
        url_clean = f"https://{url_clean}"
    try:
        webbrowser.open(url_clean)
        display_name = site_name or url_clean
        return f"Opened {display_name} in your browser."
    except Exception as e:
        return f"Error opening {url}: {e}"


def play_youtube_search(query: str) -> str:
    """Search and play a video or music track on YouTube."""
    import urllib.parse
    encoded = urllib.parse.quote_plus(query.strip())
    url = f"https://www.youtube.com/results?search_query={encoded}"
    webbrowser.open(url)
    return f"Searching YouTube for '{query}'."


def search_google(query: str) -> str:
    """Search Google for information or an answer."""
    import urllib.parse
    encoded = urllib.parse.quote_plus(query.strip())
    url = f"https://www.google.com/search?q={encoded}"
    webbrowser.open(url)
    return f"Opened Google search for '{query}'."


def set_system_volume(level_percent: int) -> str:
    """Set the system master volume (0 to 100 percent)."""
    level = max(0, min(100, int(level_percent)))
    if sys.platform == "win32":
        try:
            from pycaw.pycaw import AudioUtilities
            spk = AudioUtilities.GetSpeakers()
            vol = spk.EndpointVolume
            vol.SetMasterVolumeLevelScalar(level / 100.0, None)
            return f"System volume set to {level}%."
        except Exception as e:
            log.warning("pycaw volume adjustment failed: %s", e)
            return f"Could not set volume: {e}"
    return f"Volume control not supported on {sys.platform}."


def get_system_volume() -> str:
    """Get the current system master volume percentage."""
    if sys.platform == "win32":
        try:
            from pycaw.pycaw import AudioUtilities
            spk = AudioUtilities.GetSpeakers()
            vol = spk.EndpointVolume
            current = int(round(vol.GetMasterVolumeLevelScalar() * 100))
            return f"Current master volume is {current}%."
        except Exception as e:
            return f"Could not query volume: {e}"
    return "Volume query not supported."


def take_screenshot(filename: str = "") -> str:
    """Take a screenshot of the primary screen and save it."""
    try:
        import pyautogui
        cache_dir = Path(__file__).resolve().parent / ".cache" / "screenshots"
        cache_dir.mkdir(parents=True, exist_ok=True)
        if not filename:
            filename = f"screenshot_{int(time.time())}.png"
        if not filename.endswith(".png"):
            filename += ".png"
        filepath = cache_dir / filename
        pyautogui.screenshot(str(filepath))
        return f"Screenshot captured and saved to {filepath}."
    except Exception as e:
        return f"Failed to capture screenshot: {e}"


def system_action(action: str) -> str:
    """Perform system actions: 'lock' (lock PC), 'sleep', 'minimize_all' (show desktop), 'mute', 'unmute'."""
    act = action.lower().strip()
    if sys.platform == "win32":
        if act == "lock":
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return "PC locked."
        elif act in ("minimize_all", "show_desktop"):
            import pyautogui
            pyautogui.hotkey("win", "d")
            return "Showing desktop."
        elif act in ("mute", "unmute", "toggle_mute"):
            try:
                from pycaw.pycaw import AudioUtilities
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
        "name": "open_application",
        "description": "Opens a desktop application on the computer like Spotify, Chrome, Cursor, VS Code, Notepad, Calculator, etc.",
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
        "name": "open_website",
        "description": "Opens any website or URL in the default web browser (e.g. YouTube, Instagram, GitHub, Reddit, Spotify).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {
                    "type": "STRING",
                    "description": "The URL or website domain to open, e.g. 'https://www.youtube.com' or 'instagram.com'."
                },
                "site_name": {
                    "type": "STRING",
                    "description": "Optional friendly name of the site."
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "play_youtube_search",
        "description": "Searches and plays a specific song, music, or video on YouTube.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "The song title, artist, or video search query."
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
    "open_application": open_application,
    "open_website": open_website,
    "play_youtube_search": play_youtube_search,
    "search_google": search_google,
    "set_system_volume": set_system_volume,
    "get_system_volume": get_system_volume,
    "take_screenshot": take_screenshot,
    "system_action": system_action,
}
