# Jarvis — Voice-Controlled PC Assistant

A voice-activated AI assistant for Windows that listens for the wake word **"Jarvis"** and can control your computer, send messages, play music, read your screen, and more.

Powered by Python, **Groq** (Llama / GPT-OSS on ultra-fast LPUs), and ElevenLabs TTS.

## What It Can Do

| Category | Examples |
| --- | --- |
| **Play music** | "Jarvis, play Let It Happen by Tame Impala" |
| **Open apps & sites** | "Jarvis, open Instagram" / "Jarvis, open Spotify" |
| **Screen inspection** | "Jarvis, what's on my screen?" / "Jarvis, read my screen" |
| **Like posts** | "Jarvis, like this post" (focuses and likes current social post/reel) |
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
  jarvis_tools.py    # All PC control tools (clicks, volume, messaging, etc.)
  jarvis.py          # Original clap-listener (legacy, not needed for voice agent)
  .env               # API keys (Groq, ElevenLabs)
  requirements.txt   # Python dependencies
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create or update your `.env` file

```env
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
```

| Variable | Required | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | Yes | Groq API key for ultra-fast AI reasoning and tool calling |
| `GROQ_MODEL` | No | Groq model (default: `openai/gpt-oss-120b` or `qwen/qwen3.8-27b`) |
| `ELEVENLABS_API_KEY` | Yes | ElevenLabs API key for voice output |
| `ELEVENLABS_VOICE_ID` | Yes | Which voice to use (find in ElevenLabs dashboard) |
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

2. **Fast-path router** — Common commands (play music, open apps, volume, Instagram nicknames) are matched instantly with pattern matching without making API calls.

3. **Groq LLM fallback** — Any request not caught by the fast-path is sent to Groq with full tool execution capabilities (running at hundreds of tokens per second).

4. **Voice output** — Responses are spoken aloud using ElevenLabs with audio gain boost.

## Troubleshooting

- **Mic not working**: Check that your default mic is set correctly in Windows Sound Settings.
- **No voice output**: Make sure `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` are set in `.env`.
- **Groq errors**: Ensure `GROQ_API_KEY` is set in `.env`.
- **WhatsApp/Instagram messages not sending**: These use screen automation (`pyautogui`). Make sure the app window is visible and not blocked by other windows.

## Requirements

- Python 3.10+
- Windows 10/11
- Working microphone
- Internet connection (for Groq API and ElevenLabs)
