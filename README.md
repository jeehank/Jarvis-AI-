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
- *"Jarvis, call Debayan on WhatsApp, over."*
- *"Jarvis, create a snake game, over."*
- *"Jarvis, build a portfolio website for me, over."*
- *"Jarvis, run command dir, over."*
- *"Jarvis, close YouTube tab, over."*
- *"Jarvis, open Roblox, over."*
- *"Jarvis, create a file called test.py containing print('hello world'), over."*
- *"Jarvis, search for file invoice.pdf, over."*
- *"Jarvis, open file main.py in cursor, over."*
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
| **WhatsApp Calling** | "Jarvis, call Debayan on WhatsApp, over" / "Jarvis, make a video call to Sam on WhatsApp, over" *(navigates chat and clicks Call button in header)* |
| **Autonomous Game & Website Coding** | "Jarvis, create a snake game, over" / "Jarvis, build a flappy bird game, over" *(codes full HTML5/CSS/JS and opens in browser to play immediately)* |
| **Live Visible Terminal Typing** | "Jarvis, run command dir, over" / "Jarvis, in terminal run pip list, over" *(opens Windows Terminal via Taskbar search and types command visibly live)* |
| **File & Project Management** | "Jarvis, create a file called app.py with print hello, over" / "Jarvis, search for file notes.txt, over" |
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
  jarvis_tools.py    # Automation tools (terminal typing, web/game creation, file tools, clicks, WhatsApp, etc.)
  .env               # API keys (Groq, ElevenLabs)
  requirements.txt   # Python dependencies
  projects/          # Generated web apps and games
```

---

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure `.env`

```env
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
```

### 3. Run

```bash
python jarvis_agent.py
```

Say **"Jarvis ... [your command] ... Over"** or type commands directly in the terminal.

---

## Autonomous Web & Game Creation

- When you ask JARVIS to build a website or game (e.g. *"Jarvis, create a snake game over"* or *"Jarvis, build a calculator website over"*), JARVIS writes full, beautiful, production-ready HTML5, CSS3, and JavaScript code.
- Files are saved in the `projects/` directory and immediately opened in your default web browser so you can test and play them on the spot!

---

## Live Visible Terminal Execution

- When you instruct JARVIS to run terminal commands (e.g. *"Jarvis, run command dir over"*), JARVIS accesses the Windows Taskbar searchbar, opens the Windows Terminal app, and visibly types out each command live on screen so you can watch what it is executing in real-time.

---

## Sleep & Turn On Behavior

- **"Jarvis, go to sleep, over"**: Sends a Windows monitor standby signal. Displays power down immediately while Jarvis keeps running in the background and listening for your voice.
- **"Jarvis, turn on, over"** / **"Jarvis, wake up, over"**: Powers on the display, brings the workstation active, and acknowledges your command.


