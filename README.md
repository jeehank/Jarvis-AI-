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
- *"Jarvis, turn on, over."*
- *"Jarvis, go to sleep, over."*
- *"Jarvis, text in the group saying are we meeting today, over."*
- *"Jarvis, generate an appreciation message and send it to Abhirup on WhatsApp, over."*
- *"Jarvis, play Let It Happen by Tame Impala, over."*
- *"Jarvis, like this post, over."*
- *"Jarvis, set system volume to 75%, over."*
- *"Jarvis, open Instagram, over."*

---

## What It Can Do

| Category | Examples |
| --- | --- |
| **Turn on / Wake up** | "Jarvis, turn on, over" / "Jarvis, wake up, over" *(powers display on and brings workstation active)* |
| **Sleep display** | "Jarvis, go to sleep, over" / "Jarvis, sleep, over" *(puts monitors to sleep while remaining listening)* |
| **Group WhatsApp messages** | "Jarvis, text in the group saying party tonight at 8, over" *(auto-targets `DEBAYAN PATHAK IS GOING TO ENGLAND BABES (BO'O'WOER)`)* |
| **AI-Generated messages** | "Jarvis, generate an appreciation message and send it to Abhirup on WhatsApp, over" |
| **Direct WhatsApp messages** | "Jarvis, message Abhirup on WhatsApp saying are you free to talk, over" |
| **Instagram DMs** | "Jarvis, message Sohani on Instagram saying hey, over" |
| **Play music** | "Jarvis, play Let It Happen by Tame Impala, over" |
| **Like posts** | "Jarvis, like this post, over" (focuses and likes current social post/reel) |
| **Open apps & sites** | "Jarvis, open Instagram, over" / "Jarvis, open Spotify, over" |
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
  jarvis_tools.py    # Automation tools (clicks, typing, WhatsApp, display power, volume, etc.)
  .env               # API keys (Groq, ElevenLabs)
  requirements.txt   # Python dependencies
```

---

## Setup

### 1. Install dependencies

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

## Contact & Group Aliases

### WhatsApp:
- **"the group" / "in the group" / "debayan group"** → `DEBAYAN PATHAK IS GOING TO ENGLAND BABES (BO'O'WOER)`

### Instagram DMs:
- **Sohani, Sohu, Soha** → Sohani's DM thread
- **Abhirup, Abhiroop, Abhi** → Abhirup's DM thread
- **Sampriti, Sam, Samp** → Sampriti's DM thread

---

## Sleep & Turn On Behavior

- **"Jarvis, go to sleep, over"**: Sends a Windows monitor standby signal. Displays power down immediately while Jarvis keeps running in the background and listening for your voice.
- **"Jarvis, turn on, over"** / **"Jarvis, wake up, over"**: Powers on the display, brings the workstation active, and acknowledges your command.
