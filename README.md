# J.A.R.V.I.S. — Jarvis 2.0 (macOS v0.2.0)

> **Jarvis 2.0** replaces the browser-based Web Speech API of the original JARVIS with local Whisper STT running on Apple MLX.
>
> Based on the original idea by [Julian Ivanov](https://github.com/Julian-Ivanov/jarvis-voice-assistant) and jarvis-voice-assistant v2.6.2 by Matthias Schreiber. Built with [Claude Code](https://claude.ai/code). No support provided. Personal use only.

---

## What Changed vs. v2.x

| Old JARVIS (v2.x) | Jarvis 2.0 (v0.1.x) |
|---|---|
| Web Speech API (Chrome) | mlx-whisper large-v3 (local, Apple Silicon) |
| Chrome microphone permission | pynput + sounddevice (system-level) |
| No wake word | Wake word **"Jarvis"** (say "Jarvis, …") |
| F19 PTT only | F19 PTT **+** Wake Word |
| Port 8340 | Port **8340** |
| `--app --start-fullscreen` | `--kiosk` (true kiosk mode) |
| Cmd+Shift+J launch | Automator App + LaunchAgent |

---

> Say **"Jarvis, …"** — Jarvis recognizes your command locally with Whisper, thinks with Claude Haiku, and responds with ElevenLabs TTS. No cloud STT, no browser microphone permission.

---

## Features

- **Wake Word "Jarvis"** — Say "Jarvis, …" to activate. No "Hey" prefix. VAD + Whisper, no external model.
- **F19 Push-to-Talk** — Physical PTT key still works alongside wake word.
- **Local STT** — mlx-whisper large-v3 on Apple MLX. Fully offline, no API key needed.
- **Echo Protection** — Microphone muted while Jarvis speaks. No feedback loops.
- **User Text in Chat** — Every recognized command appears as "Du:" in the chat history.
- **Voice Conversation** — Speak freely in German. Jarvis listens, thinks, responds with voice.
- **Weather & Tasks** — On greeting: current weather + today's open reminders.
- **Apple Reminders** — Read, add, and complete reminders via AppleScript.
- **Apple Mail** — Read unread mails on request.
- **Calendar** — Today and tomorrow's events via Home Assistant CalDAV.
- **Home Assistant Lights** — Control lights by room name with 30+ synonyms.
- **Obsidian Inbox** — Write notes, read notes, mark notes as done — all by voice.
- **Browser Automation** — Playwright controls a real browser: search, open URLs, read page content.
- **Screen Vision** — Screenshot + Claude Vision: "What's on my screen?"
- **RSS News** — Fetch and read RSS articles. Manage feeds via Config UI.
- **Daily Brief Memory System** — Morning/pause/absence/evening briefs with state tracking.
- **Wake-from-Sleep** — Detects screen unlock, delivers contextual brief.
- **Update Badge** — All pages show a badge when a new GitHub release is available.
- **Kiosk Mode** — Chrome opens in true kiosk mode (no browser chrome, full screen).
- **Automator App** — `~/Applications/Jarvis starten.app` for manual start with custom icon.
- **launchd Autostart** — Server, speech input, and session launch on login.

---

## Architecture

```
You (speak "Jarvis, ...")
        ↓
speech_input.py
  RMS-VAD detects voice onset
  → HUD: listen_open (blue ring immediately)
  → mlx-whisper large-v3 (local)
  → "jarvis" in text? → send command to server
        ↓
FastAPI Server (localhost:8340)
  → Claude Haiku (brain)
  → parse_structured_action()
        ↓
    ┌──────────┬──────────────┬────────────────┐
    ↓          ↓              ↓                ↓
ElevenLabs  Playwright    AppleScript    Home Assistant
  TTS        Browser      Reminders/Mail  Light control
    ↓
Audio chunks → Chrome (kiosk) → You
```

| Component | Technology | Purpose |
|---|---|---|
| Wake Word + PTT | mlx-whisper large-v3 + pynput | Voice-to-text, local |
| Server | FastAPI (Python 3.11), Port 8340 | Local orchestration |
| Brain | Claude Haiku (Anthropic) | Thinking, deciding, responding |
| Voice | ElevenLabs TTS (eleven_turbo_v2_5) | Natural German speech |
| Browser Control | Playwright | Real browser automation |
| Screen Vision | Claude Vision + Pillow | Screenshot analysis |
| Smart Home | Home Assistant REST API | Light control |
| Reminders/Mail | AppleScript | macOS-native task access |
| Auto-start | launchd (3 KeepAlive agents) | Server + speech + session on login |
| Wake handling | wake-monitor.py → /api/wake | Post-sleep reactivation |

---

## Prerequisites

- **macOS 14+** (Apple Silicon, tested on M4)
- **Python 3.11** via Homebrew (`/opt/homebrew/bin/python3.11`)
- **Google Chrome**
- **Accessibility permission** for speech_input.py (System Settings → Privacy → Accessibility)
- **Home Assistant** (optional, for lights and CalDAV calendar)

### API Keys Needed

| Service | What For | Link |
|---|---|---|
| Anthropic | Claude Haiku (the brain) | [console.anthropic.com](https://console.anthropic.com) |
| ElevenLabs | Voice (TTS, Starter plan minimum) | [elevenlabs.io](https://elevenlabs.io) |

No STT API key needed — Whisper runs locally on Apple Silicon.

---

## Quick Start

1. **Clone and install:**
   ```bash
   git clone https://github.com/Black-Shadowcat/Jarvis 2.0.git jarvis-v3
   cd jarvis-v3
   /opt/homebrew/bin/python3.11 -m pip install -r requirements.txt
   /opt/homebrew/bin/python3.11 -m playwright install chromium
   ```

2. **Create config:**
   ```bash
   cp config.example.json config.json
   ```

3. **Edit `config.json`** — minimum required:
   ```json
   {
     "anthropic_api_key": "sk-ant-...",
     "elevenlabs_api_key": "sk_...",
     "elevenlabs_voice_id": "YOUR_VOICE_ID",
     "user_name": "Your Name",
     "user_address": "Sir",
     "city": "Your City"
   }
   ```

4. **Load LaunchAgents:**
   ```bash
   launchctl load ~/Library/LaunchAgents/com.jarvis.v2.server.plist
   launchctl load ~/Library/LaunchAgents/com.jarvis.v2.speech.plist
   launchctl load ~/Library/LaunchAgents/com.jarvis.v2.session.plist
   ```

5. Open `http://localhost:8340` if Chrome doesn't open automatically.

---

## Manual Start

**Option A — Automator App** (recommended):
```
Double-click: ~/Applications/Jarvis starten.app
```

**Option B — Terminal:**
```bash
bash ~/jarvis-v3/scripts/launch-session.sh
```

---

## What You Can Say

| Command | What Happens |
|---|---|
| *"Jarvis, guten Morgen"* | Weather + today's tasks |
| *"Jarvis, was steht heute an?"* | Reminders + calendar |
| *"Jarvis, schalte das Wohnzimmerlicht ein"* | HA light control |
| *"Jarvis, suche nach KI-Neuigkeiten"* | Browser opens, searches |
| *"Jarvis, was ist auf meinem Bildschirm?"* | Screenshot + Claude Vision |
| *"Jarvis, schreib eine Notiz: …"* | Obsidian Inbox entry |
| *"Jarvis"* (alone) | Activates, waits for follow-up command |

---

## Project Structure

```
Jarvis 2.0/
├── server.py              # FastAPI backend — brain + action system (Port 8340)
├── speech_input.py        # mlx-whisper STT + wake word + F19 PTT
├── browser_tools.py       # Playwright browser automation
├── screen_capture.py      # Screenshot + Claude Vision
├── version.json           # Single source of truth for version number
├── config.json            # Personal config (gitignored)
├── config.example.json    # Template for new users
├── requirements.txt       # Python dependencies
├── locales/
│   ├── de.json            # German TTS strings
│   └── en.json            # English equivalents
├── systems/
│   └── daily_brief.py     # Daily Brief Memory System
├── data/
│   └── daily_brief_memory.json   # Daily state (gitignored, resets at midnight)
├── frontend/
│   ├── index.html         # Jarvis Dashboard + HUD (kiosk, port 8340)
│   ├── config.html        # Config UI (/config)
│   ├── config.js          # Config UI logic
│   ├── handbuch.html      # User manual (/handbuch)
│   └── i18n/
│       ├── de.json        # German UI labels
│       └── en.json        # English UI labels
├── docs/
│   ├── jarvis.icns        # App icon (all sizes)
│   └── jarvis-icon.png    # App icon (PNG)
├── launchagents/
│   ├── com.jarvis.v2.server.plist   # Server autostart
│   ├── com.jarvis.v2.speech.plist   # Speech input autostart
│   └── com.jarvis.v2.session.plist  # Browser session autostart
└── scripts/
    ├── launch-session.sh  # Starts Chrome in kiosk mode
    └── wake-monitor.py    # Wake-from-sleep → /api/wake
```

---

## launchd Agents

Three agents in `~/Library/LaunchAgents/`:

| Agent | Purpose |
|---|---|
| `com.jarvis.v2.server.plist` | FastAPI server, KeepAlive (auto-restarts on crash) |
| `com.jarvis.v2.speech.plist` | speech_input.py (wake word + F19 PTT), KeepAlive |
| `com.jarvis.v2.session.plist` | Browser session on login (Chrome kiosk mode) |

```bash
# Reload
launchctl unload ~/Library/LaunchAgents/com.jarvis.v2.server.plist
launchctl load   ~/Library/LaunchAgents/com.jarvis.v2.server.plist

# Logs
tail -f ~/Library/Logs/Jarvis 2.0/server.log
tail -f ~/Library/Logs/Jarvis 2.0/speech.log
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Server not responding | `pkill -f "server.py"` — launchd restarts automatically |
| Wake word not working | Check `~/Library/Logs/Jarvis 2.0/speech.log` |
| Chrome won't open | Run `bash ~/jarvis-v3/scripts/launch-session.sh` manually |
| Microphone permission | System Settings → Privacy → Accessibility → allow Terminal |
| Reminders not showing | Check `~/Library/Logs/Jarvis 2.0/server.log` |
| Browser automation fails | Run `playwright install chromium` again |

---

## Tech Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** — Python web framework
- **[mlx-whisper](https://github.com/ml-explore/mlx-examples)** — Local STT on Apple MLX
- **[Claude Haiku](https://anthropic.com)** — AI model (brain)
- **[ElevenLabs](https://elevenlabs.io)** — Natural text-to-speech
- **[Playwright](https://playwright.dev)** — Browser automation
- **[pynput](https://pynput.readthedocs.io/)** — Global keyboard listener (F19 PTT)
- **[sounddevice](https://python-sounddevice.readthedocs.io/)** — Audio capture
- **[Home Assistant](https://www.home-assistant.io/)** — Smart home integration
- **AppleScript** — macOS Reminders & Mail access

---

## Credits

Original idea and Windows implementation by [Julian Ivanov](https://github.com/Julian-Ivanov) — built with [Claude Code](https://claude.ai/code).
Jarvis 2.0 — built by Matthias Schreiber with [Claude Code](https://claude.ai/code).

Inspired by Iron Man's J.A.R.V.I.S. — *"At your service, Sir."*

---

## License

MIT — use it, modify it, build on it.
