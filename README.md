# Jarvis — Voice-Controlled PC Assistant

A voice-activated AI assistant for Windows that listens for the wake word **"Jarvis"** and executes actions when you finish with **"over"**.

Powered by Python, **Groq** (running on ultra-fast LPUs), and ElevenLabs TTS.

---

## 🎙️ Voice Protocol

To ensure Jarvis never cuts you off mid-sentence:
1. **Start** your command with **"Jarvis ..."**
2. Speak your full command (you can pause naturally without being interrupted)
3. **End** with **"... Over"**

### Examples:
- *"Jarvis, close YouTube tab, over."*
- *"Jarvis, open Roblox, over."*
- *"Jarvis, create a file called test.py with print hello world, over."*
- *"Jarvis, search for file invoice.pdf, over."*
- *"Jarvis, open file main.py in cursor, over."*
- *"Jarvis, run command dir, over."*
- *"Jarvis, ask opencode to build a full stack flask app, over."*
- *"Jarvis, what is the weather report, over."*
- *"Jarvis, what time is it, over."*
- *"Jarvis, show me the route from my location to Durgapur, over."*
- *"Jarvis, shutdown computer, over."*
- *"Jarvis, restart computer, over."*
- *"Jarvis, turn on, over."*
- *"Jarvis, go to sleep, over."*
- *"Jarvis, text in the group saying are we meeting today, over."*
- *"Jarvis, play Let It Happen by Tame Impala, over."*
- *"Jarvis, like this post, over."*
- *"Jarvis, set system volume to 75%, over."*
- **Emergency Halt**: Just say *"Jarvis stop"* at any moment to immediately abort the ongoing task and silence speech!

---

## What It Can Do

| Category | Examples |
| --- | --- |
| **OpenCode AI Autonomous Coding** | "Jarvis, ask opencode to create a snake game in python, over" *(crafts refined prompt and runs OpenCode CLI in terminal)* |
| **Terminal Command Execution** | "Jarvis, run command dir, over" / "Jarvis, execute command git status, over" *(runs in terminal, captures and speaks output)* |
| **File Management** | "Jarvis, create a file called app.py with print hello, over" / "Jarvis, search for file notes.txt, over" |
| **Open Files in Editors** | "Jarvis, open file main.py in cursor, over" / "Jarvis, open file app.py in vscode, over" |
| **Close Specific Tabs** | "Jarvis, close YouTube tab, over" / "Jarvis, close Spotify tab, over" *(specifically closes that tab via UIAutomation)* |
| **Search Bar App Launch** | "Jarvis, open Roblox, over" / "Jarvis, open Calculator, over" *(searches taskbar search bar and opens closest match)* |
| **Weather & Time (Kolkata)** | "Jarvis, what is the weather report, over" / "Jarvis, what time is it, over" *(live weather & IST time for Kolkata, West Bengal)* |
| **Google Maps Routes** | "Jarvis, show me the route from my location to Durgapur, over" *(opens directions directly pre-filled)* |
| **System Shutdown & Reboot** | "Jarvis, shutdown computer, over" / "Jarvis, restart computer, over" / "Jarvis, cancel shutdown, over" |
| **Emergency Interruption** | "Jarvis stop" *(instantly silences audio and stops running tasks)* |
| **Turn on / Wake up** | "Jarvis, turn on, over" / "Jarvis, wake up, over" *(powers display on and brings workstation active)* |
| **Sleep display** | "Jarvis, go to sleep, over" / "Jarvis, sleep, over" *(puts monitors to sleep while remaining listening)* |
| **Group WhatsApp messages** | "Jarvis, text in the group saying party tonight at 8, over" *(auto-targets `BLACKBIRD FLY`)* |
| **AI-Generated messages** | "Jarvis, generate an appreciation message and send it to Abhirup on WhatsApp, over" |
| **Direct WhatsApp messages** | "Jarvis, message Abhirup on WhatsApp saying are you free to talk, over" |
| **Instagram DMs** | "Jarvis, message Sohani on Instagram saying hey, over" |
| **Play music** | "Jarvis, play Let It Happen by Tame Impala, over" |
| **Like posts** | "Jarvis, like this post, over" (focuses and likes current social post/reel) |
| **Volume control** | "Jarvis, set volume to 70, over" / "Jarvis, mute, over" |
| **Screen inspection** | "Jarvis, what's on my screen?, over" |
| **Email** | "Jarvis, email john@example.com about the meeting, over" |
| **Screenshots** | "Jarvis, take a screenshot, over" |
| **Google search** | "Jarvis, search for Python tutorials, over" |
| **System controls** | "Jarvis, lock PC, over" / "Jarvis, show desktop, over" |

---

## Project Structure

```
jarvis/
  jarvis_agent.py    # Main voice agent loop (start here)
  jarvis_tools.py    # Automation tools (terminal, OpenCode, file tools, clicks, WhatsApp, etc.)
  .env               # API keys (Groq, ElevenLabs)
  requirements.txt   # Python dependencies
```

---

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install OpenCode AI CLI (for autonomous coding in terminal)

Install the global OpenCode CLI using npm:

```bash
npm install -g opencode-ai
```

*(Verify installation by running `opencode.cmd --version`)*

### 3. Configure `.env`

```env
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
```

### 4. Run

```bash
python jarvis_agent.py
```

Say **"Jarvis ... [your command] ... Over"** or type commands directly in the terminal.

---

## OpenCode CLI & Terminal Powers

- When you ask JARVIS to write code, build an application, create scripts, or troubleshoot code, JARVIS formulates an enhanced, high-precision prompt and launches **OpenCode CLI** in an interactive terminal window to execute the job autonomously.
- You can also directly run shell commands (e.g. `dir`, `git status`, `pip list`, `python script.py`), create files/directories, and search for files across your drive.

---

## Sleep & Turn On Behavior

- **"Jarvis, go to sleep, over"**: Sends a Windows monitor standby signal. Displays power down immediately while Jarvis keeps running in the background and listening for your voice.
- **"Jarvis, turn on, over"** / **"Jarvis, wake up, over"**: Powers on the display, brings the workstation active, and acknowledges your command.

