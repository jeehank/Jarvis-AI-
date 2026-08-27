# Jarvis — Voice-Controlled PC Assistant

A voice-activated AI assistant for Windows that listens for the wake word **"Jarvis"** and executes actions when you finish with **"over and out"**.

Powered by Python, **Groq** (running on ultra-fast LPUs), and ElevenLabs TTS.

---

## 🎙️ Voice Protocol

To ensure Jarvis never cuts you off mid-sentence:
1. **Start** your command with **"Jarvis ..."**
2. Speak your full command (you can pause naturally without being interrupted)
3. **End** with **"... Over and out"**

### Examples:
- *"Jarvis, text in the group saying are we meeting today, over and out."*
- *"Jarvis, message Abhirup on WhatsApp saying are you free to talk, over and out."*
- *"Jarvis, play Let It Happen by Tame Impala, over and out."*
- *"Jarvis, like this post, over and out."*
- *"Jarvis, set system volume to 75%, over and out."*
- *"Jarvis, open Instagram, over and out."*

---

## What It Can Do

| Category | Examples |
| --- | --- |
| **Group WhatsApp messages** | "Jarvis, text in the group saying party tonight at 8, over and out" *(auto-targets `DEBAYAN PATHAK IS GOING TO ENGLAND BABES (BO'O'WOER)`)* |
| **Direct WhatsApp messages** | "Jarvis, message Abhirup on WhatsApp saying are you free to talk, over and out" |
| **Instagram DMs** | "Jarvis, message Sohani on Instagram saying hey, over and out" |
| **Play music** | "Jarvis, play Let It Happen by Tame Impala, over and out" |
| **Like posts** | "Jarvis, like this post, over and out" (focuses and likes current social post/reel) |
| **Open apps & sites** | "Jarvis, open Instagram, over and out" / "Jarvis, open Spotify, over and out" |
| **Volume control** | "Jarvis, set volume to 70, over and out" / "Jarvis, mute, over and out" |
| **Screen inspection** | "Jarvis, what's on my screen?, over and out" |
| **Email** | "Jarvis, email john@example.com about the meeting, over and out" |
| **Screenshots** | "Jarvis, take a screenshot, over and out" |
| **Google search** | "Jarvis, search for Python tutorials, over and out" |
| **System controls** | "Jarvis, lock PC, over and out" / "Jarvis, show desktop, over and out" |

---

## Project Structure

```
jarvis/
  jarvis_agent.py    # Main voice agent loop (start here)
  jarvis_tools.py    # Automation tools (clicks, typing, WhatsApp, volume, etc.)
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

Say **"Jarvis ... [your command] ... Over and out"** or type commands directly in the terminal.

---

<<<<<<< HEAD
<<<<<<< HEAD
=======
## Instagram DM Contacts
=======
## Contact & Group Aliases
>>>>>>> 8b99233 (group update)

### WhatsApp:
- **"the group" / "in the group" / "debayan group"** → `DEBAYAN PATHAK IS GOING TO ENGLAND BABES (BO'O'WOER)`

<<<<<<< HEAD
| Say this | Opens chat with |
| --- | --- |
| Sohani, Sohu, Soha | Sohani's DM thread |
| Abhirup, Abhiroop, Abhi | Abhirup's DM thread |
| Sampriti, Sam, Samp | Sampriti's DM thread |

---

>>>>>>> 31161a3 (readjusted send whatsapp message function)
## Troubleshooting

- **WhatsApp messaging**: Make sure WhatsApp Desktop (or WhatsApp Web) is open or accessible. Jarvis will search for the contact, select them, and type & send the message.
- **Microphone timing**: You can speak across multiple sentences — Jarvis will keep listening until you say **"over and out"**.
=======
### Instagram DMs:
- **Sohani, Sohu, Soha** → Sohani's DM thread
- **Abhirup, Abhiroop, Abhi** → Abhirup's DM thread
- **Sampriti, Sam, Samp** → Sampriti's DM thread
>>>>>>> 8b99233 (group update)
