# Jarvis — Voice-Controlled PC Assistant

A voice-activated AI assistant for Windows that listens for the wake word **"Jarvis"** and can control your computer, send messages, play music, read your screen, and more.

Built with Python, Google Gemini, and ElevenLabs TTS.

## What It Can Do

| Category | Examples |
| --- | --- |
| **Play music** | "Jarvis, play Let It Happen by Tame Impala" |
| **Open apps & sites** | "Jarvis, open Instagram" / "Jarvis, open Spotify" |
| **Screen vision** | "Jarvis, what's on my screen?" / "Jarvis, read my screen" |
| **Like posts** | "Jarvis, like this post" (uses screen vision to find and click) |
| **WhatsApp messages** | "Jarvis, message Alex on WhatsApp saying I'll be late" |
| **Instagram DMs** | "Jarvis, message Sohani on Instagram saying hey" |
| **Email** | "Jarvis, email john@example.com about the meeting" |
| **Volume control** | "Jarvis, set volume to 70" / "Jarvis, mute" |
| **Screenshots** | "Jarvis, take a screenshot" |
| **Google search** | "Jarvis, search for Python tutorials" |
| **System controls** | "Jarvis, lock PC" / "Jarvis, show desktop" |

## Project Structure

```
jarvis/
  jarvis_agent.py    # Main voice agent (start here)
  jarvis_tools.py    # All PC control tools (clicks, volume, messaging, vision)
  jarvis.py          # Original clap-listener (legacy, not needed for voice agent)
  .env               # API keys (not committed)
  requirements.txt   # Python dependencies
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a `.env` file

```env
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id
GEMINI_API_KEY=your_gemini_api_key
```

| Variable | Required | Purpose |
| --- | --- | --- |
| `ELEVENLABS_API_KEY` | Yes | ElevenLabs API key for voice output |
| `ELEVENLABS_VOICE_ID` | Yes | Which voice to use (find in ElevenLabs dashboard) |
| `GEMINI_API_KEY` | Yes | Google Gemini API key for AI reasoning and tool calling |
| `ELEVENLABS_MODEL_ID` | No | TTS model (default: `eleven_turbo_v2_5`) |
| `ELEVENLABS_OUTPUT_FORMAT` | No | Audio format (default: `pcm_24000`) |
| `JARVIS_VOLUME_BOOST` | No | Voice volume multiplier (default: `1.7`) |

### 3. Run

```bash
python jarvis_agent.py
```

Jarvis will greet you and start listening. Say **"Jarvis"** followed by your command.

You can also type commands directly in the terminal.

## How It Works

1. **Listener** — Continuously listens to your microphone using `SpeechRecognition`. Only activates when it hears "Jarvis".

2. **Fast-path router** — Common commands (play music, open apps, volume, etc.) are matched instantly with pattern matching. No API call needed, so they're fast.

3. **Gemini fallback** — Anything the fast-path doesn't catch gets sent to Google Gemini with access to all tools. Gemini decides which tool to call and responds.

4. **Voice output** — Responses are spoken aloud using ElevenLabs with a volume boost for clarity.

## Instagram DM Contacts

Jarvis recognizes these nicknames for Instagram DMs:

| Say this | Opens chat with |
| --- | --- |
| Sohani, Sohu, Soha | Sohani's DM thread |
| Abhirup, Abhiroop, Abhi | Abhirup's DM thread |
| Sampriti, Sam, Samp | Sampriti's DM thread |

Add more contacts by editing `INSTAGRAM_CONTACT_URLS` in `jarvis_tools.py`.

## Troubleshooting

- **Mic not working**: Check that your default mic is set correctly in Windows Sound Settings.
- **No voice output**: Make sure `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` are set in `.env`.
- **Slow responses**: The fast-path handles most commands instantly. If Jarvis is slow, it's likely hitting the Gemini API — check your network.
- **WhatsApp/Instagram messages not sending**: These use screen automation (`pyautogui`). Make sure the app window is visible and not blocked by other windows.

## Requirements

- Python 3.10+
- Windows 10/11
- Working microphone
- Internet connection (for Gemini API and ElevenLabs)
