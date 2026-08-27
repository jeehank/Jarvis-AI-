# Desktop clap → Jarvis-style welcome

Python script that listens to your default microphone and runs a **double-clap** welcome flow (Spotify, Chrome windows, ElevenLabs voice, Cursor). See constants at the top of `jarvis.py` for behavior and tuning.

## Setup

From this project directory:

```bash
python -m pip install -r requirements.txt
```

## Environment variables

The script loads a **`.env` file** in the same folder as `jarvis.py` (via `python-dotenv`). You can also set variables in the shell.

### Required (ElevenLabs welcome line)

| Variable | Purpose |
| -------- | ------- |
| `ELEVENLABS_API_KEY` | API key from [ElevenLabs](https://elevenlabs.io). |
| `ELEVENLABS_VOICE_ID` | Voice ID from the ElevenLabs app (My Voices / library). |

Without these, the welcome speech is skipped (other actions may still run).

### Optional

| Variable | Purpose |
| -------- | ------- |
| `ELEVENLABS_MODEL_ID` | TTS model (default in code: `eleven_multilingual_v2`). |
| `ELEVENLABS_OUTPUT_FORMAT` | e.g. `pcm_24000` (must match playback expectations). |
| `ELEVENLABS_PCM_SAMPLE_RATE` | Override PCM sample rate if it differs from the format name. |
| `JARVIS_WELCOME_CACHE_DIR` | Custom folder for cached welcome WAV (default: `.cache/jarvis_welcome/` under the project). |
| `JARVIS_INPUT_DEVICE` | Optional mic override: **integer** index or **substring** of the device name. If unset, the script uses the Windows default; when that mic is silent, it auto-picks the loudest working input. List devices: `python -c "import sounddevice as sd; print(sd.query_devices())"`. |
| `YOUTUBE_URL` | URL opened for YouTube in Chrome (default: `https://www.youtube.com`). |
| `INSTAGRAM_URL` | URL opened for Instagram in Chrome (default: `https://www.instagram.com`). |
| `CHROME_NEW_WINDOW_WAIT_S` | Seconds to wait for a new Chrome window on Windows (default `25`). |
| `CHROME_WINDOW_WIDTH` / `CHROME_WINDOW_HEIGHT` | Windowed Chrome size when not fullscreen. |

Example `.env`:

```env
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here
```

## Run

```bash
python jarvis.py
```

Allow the microphone if Windows prompts you. Stop with **Ctrl+C**.

## Tuning

Edit the constants at the top of `jarvis.py`:

| Constant      | Effect                                                            |
| ------------- | ----------------------------------------------------------------- |
| `SPIKE_RATIO` | Increase if you get false triggers; decrease if claps are missed. |
| `COOLDOWN_S`  | Minimum time between two logged claps.                            |
| `BLOCK_MS`    | Larger = slightly less CPU, a bit less precise timing.            |
| `MIN_RMS`     | Floor on how loud a block must be (helps in very quiet rooms).  |
| `SAMPLE_RATE` | Try `48000` if your device does not like `44100`.                 |

## Troubleshooting

- **Wrong or quiet mic:** On startup the script probes your default Windows input. If it is silent, it **auto-selects** the loudest working mic. To force a specific device, set `JARVIS_INPUT_DEVICE` in `.env` (index or name substring from `sounddevice.query_devices()`).
- **PortAudio / audio errors:** Update audio drivers or try another `SAMPLE_RATE`.
- **No reaction to claps:** Lower `SPIKE_RATIO` slightly or speak/clap closer to the mic.
- **Spam logs:** Raise `SPIKE_RATIO` or `COOLDOWN_S`.
- **No welcome speech:** Set `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` in `.env` and restart the terminal so variables load.
