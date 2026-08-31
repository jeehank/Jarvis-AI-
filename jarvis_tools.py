"""
jarvis_tools.py
Computer control and automation tools for JARVIS.
Exposes Python functions and tool declarations for Groq LLM tool calling.
"""

from __future__ import annotations

import datetime
import io
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional

import requests
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


def search_and_launch_app(app_name: str) -> str:
    """Searches for an application using the Windows taskbar search bar and opens the closest result."""
    target = app_name.strip()
    if not target:
        return "Please specify an application name to search."

    try:
        # 1. Trigger Windows Search via Win+S
        pyautogui.hotkey("win", "s")
        time.sleep(0.4)

        # 2. Type the target application name
        pyperclip.copy(target)
        pyautogui.hotkey("ctrl", "v")

        # 3. Give Windows search indexing time to resolve the closest result
        time.sleep(0.9)

        # 4. Press Enter to launch the best match
        pyautogui.press("enter")
        return f"Searched for '{target}' on taskbar search and opened the closest match."
    except Exception as e:
        log.error("search_and_launch_app error: %s", e)
        return f"Failed searching for '{target}' in search bar: {e}"


def open_application(app_name: str) -> str:
    """Open any desktop application like Spotify, Chrome, Cursor, VS Code, Notepad, Calculator, Roblox, Discord, Explorer, Task Manager."""
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

    # 3. Windows taskbar search fallback (handles Roblox, Windows Store apps, Custom apps)
    if sys.platform == "win32":
        return search_and_launch_app(app_name)

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


# WhatsApp Contact and Group Aliases
WHATSAPP_CONTACT_ALIASES = {
    "group": "BLACKBIRD FLY",
    "the group": "BLACKBIRD FLY",
    "a group": "BLACKBIRD FLY",
    "my group": "BLACKBIRD FLY",
    "debayan group": "BLACKBIRD FLY",
    "debayan": "BLACKBIRD FLY",
    "debayan pathak": "BLACKBIRD FLY",
    "england group": "BLACKBIRD FLY",
}


def send_whatsapp_message(contact_or_number: str, message: str, use_app: bool = True) -> str:
    """Opens WhatsApp (Desktop App or Web), searches the contact or group, types the message, and sends it."""
    import threading

    raw_contact = contact_or_number.strip()
    contact_lower = raw_contact.lower().strip()

    # Map aliases (e.g. 'the group', 'group') to the full group name
    contact_clean = WHATSAPP_CONTACT_ALIASES.get(contact_lower, raw_contact)
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
                # 1. Wait for WhatsApp window to open and take focus
                time.sleep(3.5)

                # 2. Focus search bar via Ctrl+F (standard WhatsApp keyboard shortcut)
                pyautogui.hotkey("ctrl", "f")
                time.sleep(0.4)

                # 3. Clear existing search and paste contact name
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.1)
                pyperclip.copy(contact_clean)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(2.0)

                # 4. Move down from search into the first contact result and open chat
                pyautogui.press("down")
                time.sleep(0.2)
                pyautogui.press("enter")
                time.sleep(1.2)

                # 5. Paste message into the chat message box
                pyperclip.copy(msg_to_send)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.4)

                # 6. Send message with Enter
                pyautogui.press("enter")
                time.sleep(0.3)
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

                # Click search bar
                pyautogui.click(int(sw * 0.18), int(sh * 0.06))
                time.sleep(0.4)
                pyperclip.copy(contact_clean)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(2.0)

                # Click first search result
                pyautogui.click(int(sw * 0.18), int(sh * 0.18))
                time.sleep(0.3)
                pyautogui.press("enter")
                time.sleep(1.2)

                # Click message bar
                pyautogui.click(int(sw * 0.55), int(sh * 0.92))
                time.sleep(0.3)

                # Paste message and send
                pyperclip.copy(msg_to_send)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.4)
                pyautogui.press("enter")
            except Exception as e:
                log.warning("WhatsApp web send error: %s", e)

        threading.Thread(target=_send_web, daemon=True).start()
        return f"Opened WhatsApp Web and sending message to {contact_clean}."


def call_on_whatsapp(contact_or_number: str, video: bool = False) -> str:
    """Opens WhatsApp Desktop, searches for a contact, and initiates a voice or video call.
    Navigates to the chat, maximizes the window, and clicks the Voice/Video Call button in the chat header.
    """
    import threading

    raw_contact = contact_or_number.strip()
    contact_lower = raw_contact.lower().strip()
    contact_clean = WHATSAPP_CONTACT_ALIASES.get(contact_lower, raw_contact)
    call_type = "video" if video else "voice"

    if sys.platform != "win32":
        return "WhatsApp calling is only supported on Windows with WhatsApp Desktop."

    # Launch WhatsApp Desktop app
    try:
        subprocess.Popen(["explorer.exe", r"shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App"])
    except Exception:
        try:
            subprocess.Popen(["cmd.exe", "/c", "start", "whatsapp:"], shell=True)
        except Exception as e:
            return f"Could not launch WhatsApp Desktop: {e}"

    def _make_call():
        try:
            # 1. Wait for WhatsApp window to open and take focus
            time.sleep(3.5)

            # Maximize window so header call button coordinates are completely predictable
            try:
                pyautogui.hotkey("win", "up")
                time.sleep(0.5)
            except Exception:
                pass

            # 2. Focus search bar via Ctrl+F
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.4)

            # 3. Clear existing search and paste contact name
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyperclip.copy(contact_clean)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(2.0)

            # 4. Move down to the first search result and open the chat
            pyautogui.press("down")
            time.sleep(0.2)
            pyautogui.press("enter")
            time.sleep(1.8)

            # 5. Locate and click the Call button in the top right chat header
            sw, sh = pyautogui.size()
            if video:
                # Video call icon is ~145px from right margin in chat header
                target_x = max(100, sw - 145)
                target_y = int(sh * 0.055) if sh > 800 else 58
            else:
                # Voice call icon is ~100px from right margin in chat header
                target_x = max(100, sw - 100)
                target_y = int(sh * 0.055) if sh > 800 else 58

            log.info("Clicking WhatsApp %s call button at (%d, %d)", call_type, target_x, target_y)
            pyautogui.moveTo(target_x, target_y, duration=0.3)
            time.sleep(0.1)
            pyautogui.click(target_x, target_y)
            time.sleep(0.3)

            # 6. Also send fallback shortcut
            if video:
                pyautogui.hotkey("ctrl", "shift", "v")
            else:
                pyautogui.hotkey("ctrl", "shift", "c")

            log.info("Initiated %s call to %s on WhatsApp Desktop.", call_type, contact_clean)
        except Exception as e:
            log.warning("WhatsApp %s call error: %s", call_type, e)

    threading.Thread(target=_make_call, daemon=True).start()
    return f"Opening WhatsApp Desktop and starting a {call_type} call with {contact_clean}."


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
    """Performs system actions: 'turn_on', 'sleep', 'lock', 'minimize_all', 'mute', 'unmute', 'toggle_mute', 'shutdown', 'restart', 'abort_shutdown'."""
    act = action.lower().strip()
    if act in ("turn_on", "wake", "wake_up", "screen_on", "turn_on_screen", "turn_on_display", "display_on"):
        if sys.platform == "win32":
            import ctypes
            # Send monitor power ON message
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, -1)
            # Wiggle mouse and press shift to wake any sleeping screen
            pyautogui.moveRel(1, 1)
            pyautogui.moveRel(-1, -1)
            pyautogui.press("shift")
            return "Turned on display and woke up workstation."
        return "Turn on command only supported on Windows."
    elif act in ("sleep", "sleep_display", "turn_off_screen", "screen_off", "display_off"):
        if sys.platform == "win32":
            import ctypes
            # Send monitor power OFF / standby message
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
            return "Turned off display into sleep mode. Jarvis remains listening."
        return "Sleep display command only supported on Windows."
    elif act == "lock":
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
    elif act in ("shutdown", "power_off", "turn_off_pc", "turn_off_computer"):
        return shutdown_computer(delay_seconds=5)
    elif act in ("restart", "reboot", "restart_pc", "restart_computer"):
        return restart_computer(delay_seconds=5)
    elif act in ("abort_shutdown", "cancel_shutdown", "stop_shutdown"):
        return abort_shutdown()
    return f"Action '{action}' is not supported."


KNOWN_TAB_SERVICES = (
    "youtube", "instagram", "spotify", "gmail", "github", "discord",
    "whatsapp", "twitter", "chatgpt", "claude", "netflix", "reddit",
    "linkedin", "facebook", "amazon", "notion", "google", "teams", "roblox"
)


def close_browser_tab(tab_name_or_keyword: str = "current") -> str:
    """Specifically closes a browser tab by title or keyword across Chrome, Edge, Brave, Firefox, Opera, etc., or closes current active tab."""
    raw = (tab_name_or_keyword or "").lower().strip()

    # 1. Determine if the user intends to close the current active tab
    current_tab_triggers = (
        "current", "this", "this tab", "active", "active tab", "tab i have open",
        "tab that is open", "i have open", "open right now", "open tab", "the tab",
        "current tab", "here", "right now", "it"
    )

    is_current_tab = False
    if not raw or raw in current_tab_triggers:
        is_current_tab = True
    elif not any(re.search(rf"\b{s}\b", raw) for s in KNOWN_TAB_SERVICES) and any(trig in raw for trig in current_tab_triggers):
        is_current_tab = True

    try:
        import ctypes
        import comtypes
        import comtypes.client

        user32 = ctypes.windll.user32
        hDesk = user32.OpenInputDesktop(0, False, 0x01FF)

        hwnds = []
        def enum_desk_proc(hwnd, lParam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    hwnds.append((hwnd, title))
            return True

        DESKTOPENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.c_void_p)
        cb = DESKTOPENUMPROC(enum_desk_proc)
        user32.EnumDesktopWindows(hDesk, cb, 0)

        # Fast-path for current / active tab
        if is_current_tab:
            fg_hwnd = user32.GetForegroundWindow()
            fg_len = user32.GetWindowTextLengthW(fg_hwnd)
            fg_title = ""
            if fg_len > 0:
                buff = ctypes.create_unicode_buffer(fg_len + 1)
                user32.GetWindowTextW(fg_hwnd, buff, fg_len + 1)
                fg_title = buff.value

            if any(b in fg_title.lower() for b in ["chrome", "edge", "brave", "firefox", "opera"]):
                pyautogui.hotkey("ctrl", "w")
                return f"Closed the current active tab."

            for hwnd, title in hwnds:
                if any(b in title.lower() for b in ["chrome", "edge", "brave", "firefox", "opera"]):
                    user32.ShowWindow(hwnd, 9)
                    user32.SetForegroundWindow(hwnd)
                    time.sleep(0.15)
                    pyautogui.hotkey("ctrl", "w")
                    return f"Closed the current active tab in {title}."

            pyautogui.hotkey("ctrl", "w")
            return "Closed the active tab."

        # Extract clean keyword from raw phrase
        clean_kw = raw
        for s in KNOWN_TAB_SERVICES:
            if re.search(rf"\b{s}\b", raw):
                clean_kw = s
                break
        else:
            clean_kw = re.sub(r"^(?:please\s+)?close\s+(?:the\s+)?", "", clean_kw, flags=re.IGNORECASE)
            clean_kw = re.sub(r"\b(on|in)\s+(?:my\s+)?(chrome|edge|brave|firefox|opera|browser)\b", "", clean_kw, flags=re.IGNORECASE)
            clean_kw = re.sub(r"\b(tab|tabs|that|i have open|have open|open right now|right now|right|currently|for me|my|the|active|current|this)\b", "", clean_kw, flags=re.IGNORECASE)
            clean_kw = clean_kw.strip(" ,:.-")

        if not clean_kw:
            clean_kw = raw

        comtypes.CoInitialize()
        try:
            from comtypes.gen import UIAutomationClient
        except Exception:
            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen import UIAutomationClient

        uia = comtypes.client.CreateObject(UIAutomationClient.CUIAutomation)
        tab_cond = uia.CreatePropertyCondition(UIAutomationClient.UIA_ControlTypePropertyId, UIAutomationClient.UIA_TabItemControlTypeId)
        btn_cond = uia.CreatePropertyCondition(UIAutomationClient.UIA_ControlTypePropertyId, UIAutomationClient.UIA_ButtonControlTypeId)

        for hwnd, win_title in hwnds:
            if any(b in win_title.lower() for b in ["chrome", "edge", "brave", "firefox", "opera", "browser"]):
                try:
                    win_elem = uia.ElementFromHandle(hwnd)
                    tabs = win_elem.FindAll(UIAutomationClient.TreeScope_Descendants, tab_cond)
                    for i in range(tabs.Length):
                        t = tabs.GetElement(i)
                        t_name = (t.CurrentName or "").lower()
                        if clean_kw in t_name or any(w in t_name for w in clean_kw.split() if len(w) > 2):
                            # 1. Try finding and invoking Close button inside tab item
                            buttons = t.FindAll(UIAutomationClient.TreeScope_Descendants, btn_cond)
                            for b_idx in range(buttons.Length):
                                btn = buttons.GetElement(b_idx)
                                b_name = (btn.CurrentName or "").lower()
                                if "close" in b_name or b_name == "" or "tab" in b_name:
                                    try:
                                        pat = btn.GetCurrentPattern(UIAutomationClient.UIA_InvokePatternId)
                                        if pat:
                                            inv = pat.QueryInterface(UIAutomationClient.IUIAutomationInvokePattern)
                                            inv.Invoke()
                                            return f"Closed the {clean_kw.capitalize()} tab."
                                    except Exception:
                                        pass

                            # 2. Fallback: Select tab, bring window to front, send Ctrl+W
                            try:
                                sel_pat = t.GetCurrentPattern(UIAutomationClient.UIA_SelectionItemPatternId)
                                if sel_pat:
                                    sel = sel_pat.QueryInterface(UIAutomationClient.IUIAutomationSelectionItemPattern)
                                    sel.Select()
                                    time.sleep(0.1)
                                    user32.SetForegroundWindow(hwnd)
                                    time.sleep(0.1)
                                    pyautogui.hotkey("ctrl", "w")
                                    return f"Closed the {clean_kw.capitalize()} tab."
                            except Exception:
                                pass
                except Exception:
                    continue

        # If not found inside tabs, check if an entire window title matches
        for hwnd, win_title in hwnds:
            if clean_kw in win_title.lower() and any(b in win_title.lower() for b in ["chrome", "edge", "brave", "firefox", "opera"]):
                try:
                    user32.SetForegroundWindow(hwnd)
                    time.sleep(0.1)
                    pyautogui.hotkey("ctrl", "w")
                    return f"Closed {clean_kw.capitalize()} tab/window."
                except Exception:
                    pass

        return f"Could not find an open browser tab matching '{clean_kw}'."
    except Exception as e:
        log.error("close_browser_tab error: %s", e)
        return f"Error closing tab: {e}"


def shutdown_computer(delay_seconds: int = 5, force: bool = False) -> str:
    """Safely shuts down the Windows computer."""
    if sys.platform == "win32":
        f_flag = "/f" if force else ""
        subprocess.Popen(f"shutdown /s {f_flag} /t {delay_seconds} /c \"JARVIS: Shutting down system.\"", shell=True)
        return f"System shutdown initiated. Computer will power down in {delay_seconds} seconds."
    return "Shutdown is only supported on Windows."


def restart_computer(delay_seconds: int = 5, force: bool = False) -> str:
    """Safely restarts the Windows computer."""
    if sys.platform == "win32":
        f_flag = "/f" if force else ""
        subprocess.Popen(f"shutdown /r {f_flag} /t {delay_seconds} /c \"JARVIS: Restarting system.\"", shell=True)
        return f"System restart initiated. Computer will reboot in {delay_seconds} seconds."
    return "Restart is only supported on Windows."


def abort_shutdown() -> str:
    """Aborts any scheduled system shutdown or restart."""
    if sys.platform == "win32":
        subprocess.Popen("shutdown /a", shell=True)
        return "Scheduled shutdown or restart has been cancelled."
    return "Abort shutdown is only supported on Windows."


def get_weather(location: str = "Kolkata, West Bengal, India") -> str:
    """Fetches a real-time weather report and forecast for Kolkata, West Bengal, India (or specified location)."""
    WMO_CODES = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snowfall", 73: "Moderate snowfall", 75: "Heavy snowfall",
        80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
    }

    lat, lon, place_name = 22.5726, 88.3639, "Kolkata, West Bengal"
    loc_clean = location.strip()
    if loc_clean and "kolkata" not in loc_clean.lower():
        try:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(loc_clean)}&count=1&language=en&format=json"
            r = requests.get(geo_url, timeout=3.0).json()
            if r.get("results"):
                res = r["results"][0]
                lat, lon = res["latitude"], res["longitude"]
                place_name = f"{res.get('name')}, {res.get('country')}"
        except Exception:
            pass

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
        )
        r = requests.get(url, timeout=4.0).json()
        curr = r["current"]
        temp = curr["temperature_2m"]
        feels_like = curr["apparent_temperature"]
        humidity = curr["relative_humidity_2m"]
        wind = curr["wind_speed_10m"]
        w_code = curr.get("weather_code", 0)
        cond = WMO_CODES.get(w_code, "Clear")
        daily = r.get("daily", {})
        max_t = daily.get("temperature_2m_max", [temp])[0]
        min_t = daily.get("temperature_2m_min", [temp])[0]

        return (
            f"Weather report for {place_name}: It is currently {cond} with a temperature of {temp}°C "
            f"(feels like {feels_like}°C), {humidity}% humidity, and wind speeds of {wind} km/h. "
            f"Today's high is {max_t}°C and low is {min_t}°C."
        )
    except Exception as e:
        log.error("get_weather error: %s", e)
        return f"Unable to fetch weather data right now: {e}"


def get_time(location: str = "Kolkata, West Bengal, India") -> str:
    """Returns current time (12-hour format with AM/PM) and date in Indian Standard Time (IST, UTC+5:30) for Kolkata."""
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    now = datetime.datetime.now(ist)
    time_str = now.strftime("%I:%M %p").lstrip("0")
    date_str = now.strftime("%A, %B %d, %Y")
    return f"It is currently {time_str} on {date_str} in {location}."


def show_google_maps_route(destination: str, origin: str = "Kolkata, West Bengal") -> str:
    """Opens Google Maps with full directions pre-filled from origin to destination."""
    dest_clean = destination.strip()
    orig_clean = origin.strip()

    if not orig_clean or orig_clean.lower() in ("my location", "my place", "here", "current location", "from my location", "from my place"):
        orig_clean = "Kolkata, West Bengal"

    orig_enc = urllib.parse.quote_plus(orig_clean)
    dest_enc = urllib.parse.quote_plus(dest_clean)

    maps_url = f"https://www.google.com/maps/dir/{orig_enc}/{dest_enc}"
    webbrowser.open(maps_url)
    return f"Opened Google Maps route from {orig_clean} to {dest_clean}."


def interruptible_sleep(seconds: float, interrupt_event: Optional[threading.Event] = None) -> bool:
    """Sleeps for the given duration in small intervals. Returns False if interrupted, True if completed."""
    if interrupt_event is None:
        time.sleep(seconds)
        return True
    end_time = time.time() + seconds
    while time.time() < end_time:
        if interrupt_event.is_set():
            return False
        time.sleep(min(0.05, max(0.0, end_time - time.time())))
    return not interrupt_event.is_set()


def run_command_in_terminal(command: str, working_dir: str = "", use_taskbar_search: bool = True) -> str:
    """
    Executes a shell/terminal command on the computer.
    Opens the Windows Terminal app using the taskbar search bar and types the command visibly
    character-by-character so the user can watch JARVIS typing and executing it live on screen.
    """
    cmd_clean = command.strip()
    if not cmd_clean:
        return "No command provided to run."

    cwd = working_dir.strip() if working_dir.strip() else os.getcwd()
    try:
        cwd_path = Path(os.path.expandvars(cwd)).resolve()
        if not cwd_path.exists():
            cwd_path = Path.cwd()
    except Exception:
        cwd_path = Path.cwd()

    log.info("Executing terminal command: %r in %s (via_search=%s)", cmd_clean, cwd_path, use_taskbar_search)

    if use_taskbar_search and sys.platform == "win32":
        import threading
        def _type_in_terminal():
            try:
                # 1. Open taskbar searchbar using Win key
                pyautogui.press("win")
                time.sleep(0.4)

                # 2. Type 'terminal' to search for Windows Terminal
                pyautogui.write("terminal", interval=0.03)
                time.sleep(0.6)
                pyautogui.press("enter")
                time.sleep(2.0)

                # 3. If working directory is specified and different, cd into it
                if str(cwd_path) != str(Path.cwd()):
                    cd_cmd = f'cd /d "{cwd_path}"'
                    for char in cd_cmd:
                        pyautogui.write(char)
                        time.sleep(0.015)
                    pyautogui.press("enter")
                    time.sleep(0.3)

                # 4. Type the command visibly into the terminal
                for char in cmd_clean:
                    pyautogui.write(char)
                    time.sleep(0.02)
                time.sleep(0.3)

                # 5. Execute with Enter
                pyautogui.press("enter")
                log.info("Typed and executed in terminal: %r", cmd_clean)
            except Exception as e:
                log.error("Error typing command into terminal: %s", e)

        threading.Thread(target=_type_in_terminal, daemon=True).start()
        return f"Opened Terminal via taskbar search and executed: '{cmd_clean}' in {cwd_path}"

    # Fallback to subprocess execution
    try:
        res = subprocess.run(
            cmd_clean,
            shell=True,
            cwd=str(cwd_path),
            capture_output=True,
            text=True,
            timeout=45
        )
        out = res.stdout.strip()
        err = res.stderr.strip()
        combined = []
        if out:
            combined.append(out)
        if err:
            combined.append(f"Errors/Warnings:\n{err}")

        output_str = "\n".join(combined).strip()
        if not output_str:
            output_str = f"Command executed successfully with return code {res.returncode} (no output)."
        elif len(output_str) > 1500:
            output_str = output_str[:1500] + "\n...[output truncated]"
        return output_str
    except Exception as e:
        return f"Error executing command: {e}"


def execute_system_command(command: str, working_dir: str = "") -> str:
    """
    Executes a shell command silently in the background and returns the complete output/logs.
    """
    cmd_clean = command.strip()
    if not cmd_clean:
        return "No command provided."

    cwd = working_dir.strip() if working_dir.strip() else os.getcwd()
    try:
        cwd_path = Path(os.path.expandvars(cwd)).resolve()
        if not cwd_path.exists():
            cwd_path = Path.cwd()
    except Exception:
        cwd_path = Path.cwd()

    try:
        res = subprocess.run(
            cmd_clean,
            shell=True,
            cwd=str(cwd_path),
            capture_output=True,
            text=True,
            timeout=60
        )
        out = res.stdout.strip()
        err = res.stderr.strip()
        combined = []
        if out:
            combined.append(out)
        if err:
            combined.append(f"Errors/Warnings:\n{err}")
        return "\n".join(combined).strip() or "Command completed with no output."
    except subprocess.TimeoutExpired:
        return "Command timed out after 60 seconds."
    except Exception as e:
        return f"Error executing system command: {e}"


def _resolve_user_dest(raw_path: str) -> Path:
    """Resolves a destination path, defaulting relative paths to the user's Downloads directory."""
    raw = raw_path.strip()
    expanded = Path(os.path.expandvars(raw))
    if expanded.is_absolute():
        return expanded.resolve()
    downloads_dir = Path.home() / "Downloads"
    return (downloads_dir / expanded).resolve()


def create_file(file_path: str, content: str = "", open_after: bool = False) -> str:
    """
    Creates or overwrites a file with the given text/code content and optional auto-open.
    Relative paths are saved in the user's Downloads folder.
    """
    raw_path = file_path.strip()
    if not raw_path:
        return "Please specify a file path."

    p = _resolve_user_dest(raw_path)

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        
        if p.suffix.lower() == ".xlsx":
            try:
                import openpyxl
                import csv
                import io
                wb = openpyxl.Workbook()
                ws = wb.active
                # Try to parse content as CSV
                reader = csv.reader(io.StringIO(content.strip()))
                for row in reader:
                    ws.append(row)
                wb.save(p)
                msg = f"Successfully created Excel file: {p}"
            except ImportError:
                # Fallback if openpyxl not installed
                p.write_text(content, encoding="utf-8")
                msg = f"Created file {p} (Note: openpyxl missing, written as text)."
        else:
            p.write_text(content, encoding="utf-8")
            msg = f"Successfully created file: {p} ({len(content)} characters written)."

        if open_after:
            try:
                if p.suffix.lower() in (".html", ".htm"):
                    webbrowser.open(p.as_uri())
                elif sys.platform == "win32":
                    os.startfile(str(p))
                msg += " Opened in viewer/browser."
            except Exception as e:
                log.warning("Could not auto-open %s: %s", p, e)
        return msg
    except Exception as e:
        log.error("create_file error: %s", e)
        return f"Failed to create file at {p}: {e}"


def create_folder(folder_path: str) -> str:
    """Creates a new directory in the user's Downloads folder (and any necessary parent directories)."""
    raw = folder_path.strip()
    if not raw:
        return "Please specify a folder path."
    p = _resolve_user_dest(raw)
    try:
        p.mkdir(parents=True, exist_ok=True)
        return f"Successfully created folder: {p}"
    except Exception as e:
        log.error("create_folder error: %s", e)
        return f"Failed to create folder at {p}: {e}"


def create_file_or_folder(path: str, content: str = "", is_folder: bool = False) -> str:
    """Legacy alias: Creates a new file (with specified content) or directory."""
    if is_folder or (not Path(path).suffix and not content):
        return create_folder(path)
    return create_file(path, content)


def create_web_project(
    project_name: str,
    html_code: str,
    css_code: str = "",
    js_code: str = "",
    single_file: bool = False,
    open_in_browser: bool = True
) -> str:
    """
    Creates a complete, playable web application, game, or website directly in the user's Downloads folder.
    Can create either a single self-contained .html file or a clean project folder with index.html, style.css, and script.js.
    Automatically launches the generated game/website in the default browser so the user can immediately play/view it.
    """
    clean_name = re.sub(r"[^\w\-]", "_", project_name.strip()) or "web_project"
    downloads_dir = Path.home() / "Downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)

    try:
        if single_file or (not css_code.strip() and not js_code.strip()):
            # Single self-contained HTML file in Downloads
            file_name = f"{clean_name}.html" if not clean_name.endswith(".html") else clean_name
            target_path = downloads_dir / file_name

            full_html = html_code
            if css_code.strip() and "<style>" not in full_html:
                full_html = full_html.replace("</head>", f"<style>\n{css_code}\n</style>\n</head>") if "</head>" in full_html else f"<style>\n{css_code}\n</style>\n" + full_html
            if js_code.strip() and "<script>" not in full_html:
                full_html = full_html.replace("</body>", f"<script>\n{js_code}\n</script>\n</body>") if "</body>" in full_html else full_html + f"\n<script>\n{js_code}\n</script>"

            target_path.write_text(full_html, encoding="utf-8")
            log.info("Created standalone web app/game in Downloads: %s", target_path)

            if open_in_browser:
                webbrowser.open(target_path.as_uri())

            return f"Successfully created web app/game in Downloads: {target_path}. Opened in browser for you to play/view, sir."

        else:
            # Multi-file folder with index.html, style.css, script.js inside Downloads
            proj_folder = downloads_dir / clean_name
            proj_folder.mkdir(parents=True, exist_ok=True)

            html_file = proj_folder / "index.html"
            css_file = proj_folder / "style.css"
            js_file = proj_folder / "script.js"

            # Ensure HTML links to style.css and script.js if not already present
            processed_html = html_code
            if "style.css" not in processed_html and "</head>" in processed_html:
                processed_html = processed_html.replace("</head>", '<link rel="stylesheet" href="style.css">\n</head>')
            if "script.js" not in processed_html and "</body>" in processed_html:
                processed_html = processed_html.replace("</body>", '<script src="script.js"></script>\n</body>')

            html_file.write_text(processed_html, encoding="utf-8")
            if css_code.strip():
                css_file.write_text(css_code, encoding="utf-8")
            if js_code.strip():
                js_file.write_text(js_code, encoding="utf-8")

            log.info("Created web project in Downloads: %s", proj_folder)

            if open_in_browser:
                webbrowser.open(html_file.as_uri())

            return f"Successfully created web project in Downloads at '{proj_folder}' with index.html, style.css, and script.js. Opened in browser for you, sir."

    except Exception as e:
        log.error("create_web_project error: %s", e)
        return f"Failed creating web project '{project_name}': {e}"


def search_files(query: str, root_dir: str = "", max_results: int = 15) -> str:
    """
    Searches for files or folders matching a query name/pattern across common user locations.
    """
    q = query.strip()
    if not q:
        return "Please provide a search query or filename."

    roots = []
    if root_dir.strip():
        resolved_root = Path(os.path.expandvars(root_dir.strip())).resolve()
        if resolved_root.exists():
            roots.append(resolved_root)

    if not roots:
        user_home = Path.home()
        roots = [
            Path.cwd(),
            user_home / "Desktop",
            user_home / "Documents",
            user_home / "Downloads",
        ]

    results = []
    seen = set()

    for root in roots:
        if not root.exists():
            continue
        try:
            for current_dir, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv", "venv", ".cache", "AppData")]
                try:
                    rel = Path(current_dir).relative_to(root)
                    if len(rel.parts) > 4:
                        dirs.clear()
                        continue
                except Exception:
                    pass

                for f in files:
                    if q.lower() in f.lower():
                        full_path = Path(current_dir) / f
                        if str(full_path) not in seen:
                            seen.add(str(full_path))
                            results.append(str(full_path))
                            if len(results) >= max_results:
                                break
                if len(results) >= max_results:
                    break
        except Exception as e:
            log.warning("Search error in %s: %s", root, e)

    if not results:
        return f"No files found matching '{q}' in common directories."
    return f"Found {len(results)} matches for '{q}':\n" + "\n".join(f"- {r}" for r in results)


def open_file_or_editor(file_path: str, editor: str = "") -> str:
    """
    Opens a file with default program or specified editor (e.g. 'cursor', 'vscode', 'notepad').
    """
    raw_path = file_path.strip()
    if not raw_path:
        return "Please specify a file path to open."

    p = Path(os.path.expandvars(raw_path)).resolve()
    if not p.exists():
        # Check if file exists relative to cwd or user directories
        for cand in [Path.cwd() / raw_path, Path.home() / "Desktop" / raw_path, Path.home() / "Downloads" / raw_path]:
            if cand.exists():
                p = cand
                break
        else:
            return f"File does not exist: {p}"

    editor_clean = editor.lower().strip()
    try:
        if editor_clean in ("cursor", "code", "vscode", "notepad"):
            exec_name = "code" if editor_clean == "vscode" else editor_clean
            subprocess.Popen(f'{exec_name} "{p}"', shell=True)
            return f"Opened {p.name} in {editor.title()}."

        if sys.platform == "win32":
            os.startfile(str(p))
        else:
            subprocess.Popen(["xdg-open", str(p)])
        return f"Opened file: {p.name}"
    except Exception as e:
        log.error("open_file_or_editor error: %s", e)
        return f"Failed opening file {p}: {e}"


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
            "name": "close_browser_tab",
            "description": "Closes a specific browser tab by title or website name (e.g. 'youtube', 'spotify', 'instagram', 'github') no matter which tab is currently active.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tab_name_or_keyword": {
                        "type": "string",
                        "description": "The name or keyword of the tab to close, e.g. 'youtube', 'spotify', 'instagram'."
                    }
                },
                "required": ["tab_name_or_keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_and_launch_app",
            "description": "Searches for an application using the Windows taskbar search bar and opens the closest/best matching result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "The application to search and launch, e.g. 'roblox', 'spotify', 'calculator', 'notepad'."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Opens a desktop application on the computer like Spotify, Chrome, Cursor, VS Code, Notepad, Calculator, Roblox, Task Manager, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "The name of the application to open, e.g. 'Spotify', 'Roblox', 'Cursor', 'Notepad', 'Chrome'."
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
            "name": "open_whatsapp",
            "description": "Opens WhatsApp Desktop App or WhatsApp Web in the default browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": "'app' for native desktop app, 'web' for WhatsApp Web."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_youtube_video",
            "description": "Searches YouTube for a song, music video, or topic and starts playing the top result automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_query": {
                        "type": "string",
                        "description": "Song name, artist, or video title to search and play."
                    }
                },
                "required": ["search_query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Gets the current live weather report and temperature for any city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, e.g. 'Kolkata, West Bengal, India' or 'London'."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Gets current time and date for a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City or timezone, default 'Kolkata, West Bengal, India'."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "show_google_maps_route",
            "description": "Opens Google Maps showing driving/transit route directions from origin to destination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Destination city, address, or landmark (e.g. 'Durgapur')."
                    },
                    "origin": {
                        "type": "string",
                        "description": "Starting location (default 'Kolkata, West Bengal')."
                    }
                },
                "required": ["destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "shutdown_computer",
            "description": "Initiates computer shutdown with countdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_seconds": {
                        "type": "integer",
                        "description": "Seconds before shutdown (default 5)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "restart_computer",
            "description": "Initiates computer restart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_seconds": {
                        "type": "integer",
                        "description": "Seconds before restart (default 5)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "abort_shutdown",
            "description": "Cancels any pending shutdown or restart.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "like_current_post",
            "description": "Likes the active post/reel on screen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "Social platform, e.g. 'instagram'."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_whatsapp_message",
            "description": "Searches for a contact or group on WhatsApp and sends a message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_or_number": {
                        "type": "string",
                        "description": "Contact name, group name ('BLACKBIRD FLY'), or phone number."
                    },
                    "message": {
                        "type": "string",
                        "description": "The message to send."
                    },
                    "use_app": {
                        "type": "boolean",
                        "description": "True to use Desktop App, False for WhatsApp Web."
                    }
                },
                "required": ["contact_or_number", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "call_on_whatsapp",
            "description": "Opens WhatsApp Desktop, searches for a contact, and initiates a voice or video call by clicking the call button in the chat header.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_or_number": {
                        "type": "string",
                        "description": "Contact name or phone number."
                    },
                    "video": {
                        "type": "boolean",
                        "description": "Set to true for a video call, false for a voice call."
                    }
                },
                "required": ["contact_or_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email_compose",
            "description": "Opens Gmail compose window with recipient, subject, and body pre-filled.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_instagram_dm_message",
            "description": "Sends a direct message on Instagram.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact": {
                        "type": "string",
                        "description": "Instagram contact name/username."
                    },
                    "message": {
                        "type": "string",
                        "description": "The message to send."
                    }
                },
                "required": ["contact", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "see_and_analyze_screen",
            "description": "Takes a screenshot and analyzes the current screen visually.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instruction": {"type": "string"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scroll_screen",
            "description": "Scrolls the screen up or down.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["up", "down"]},
                    "amount": {"type": "integer"}
                },
                "required": ["direction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click_on_screen",
            "description": "Clicks at specific screen coordinates or performs double/right click.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "button": {"type": "string", "enum": ["left", "right", "double"]}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_google",
            "description": "Searches Google in the browser for any query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_system_volume",
            "description": "Sets master system volume (0-100).",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer"}
                },
                "required": ["level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_volume",
            "description": "Gets current master system volume.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Takes a screenshot and saves it to disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "save_path": {"type": "string"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "press_keyboard_keys",
            "description": "Presses a keyboard key combination (e.g. 'ctrl+c', 'alt+tab', 'enter').",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["keys"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "type_keyboard_text",
            "description": "Types arbitrary text using the keyboard.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
JARVIS_TOOL_DECLARATIONS = GROQ_TOOL_DECLARATIONS

TOOL_FUNCTION_MAP = {
    "open_website": open_website,
    "close_browser_tab": close_browser_tab,
    "search_and_launch_app": search_and_launch_app,
    "open_application": open_application,
    "open_folder": open_folder,
    "open_whatsapp": open_whatsapp,
    "play_youtube_video": play_youtube_video,
    "get_weather": get_weather,
    "get_time": get_time,
    "show_google_maps_route": show_google_maps_route,
    "shutdown_computer": shutdown_computer,
    "restart_computer": restart_computer,
    "abort_shutdown": abort_shutdown,
    "like_current_post": like_current_post,
    "send_whatsapp_message": send_whatsapp_message,
    "call_on_whatsapp": call_on_whatsapp,
    "send_email_compose": send_email_compose,
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
    "run_terminal_command": run_command_in_terminal,
    "run_command_in_terminal": run_command_in_terminal,
    "execute_system_command": execute_system_command,
    "create_file_or_folder": create_file_or_folder,
    "create_file": create_file,
    "create_folder": create_folder,
    "create_web_project": create_web_project,
    "search_files": search_files,
    "open_file_or_editor": open_file_or_editor,
}
