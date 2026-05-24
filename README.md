# J.A.R.V.I.S. — Jarvis 2.0 (macOS v2.0.4)

> **Jarvis 2.0 v2.0.4** is a complete redesign of the original [jarvis-voice-assistant](https://github.com/Black-Shadowcat/jarvis-voice-assistant) (v2.x).  
> It replaces the browser-based Web Speech API with **local Whisper STT** on Apple MLX, and uses a **native Tauri app** instead of Chrome Kiosk (86% less memory).  
> Production-ready with **3 independent microservices** (Core, Audio, Dashboard) for reliability and scalability.
>
> Built by Matthias Schreiber with [Claude Code](https://claude.ai/code). No support provided. Personal use only.

---

## What Changed vs. v2.x

| Old JARVIS (v2.x) | Jarvis 2.0 (v2.0.4) |
|---|---|
| Web Speech API (Chrome) | mlx-whisper large-v3 (local, Apple Silicon) |
| Chrome microphone permission | pynput + sounddevice (system-level) |
| No wake word | Wake word **"Jarvis"** (say "Jarvis, …") |
| F19 PTT only | F19 PTT **+** Wake Word |
| Port 8340 | Port **8340** |
| Chrome `--kiosk` (400–600 MB) | **Native Tauri App** (~66 MB, WKWebView) |
| Cmd+Shift+J launch | Cmd+Shift+J → Tauri via LaunchAgent |

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
- **Native Tauri App** — Replaces Chrome Kiosk. ~66 MB vs. 480 MB (86% less memory), no Chrome required. Chrome fallback still available via `USE_TAURI=0`.
- **Native App Bundle** — `/Applications/Jarvis.app` for manual start from Dock or Finder.
- **launchd Autostart** — Server, speech input, and session launch on login.

---

## Architecture (v2.0.4: Tauri Native + Service Isolation)

```
You (speak "Jarvis, ...")
        ↓
speech_input.py
  RMS-VAD detects voice onset
  → HUD: listen_open (blue ring immediately)
  → mlx-whisper large-v3 (local)
  → "jarvis" in text? → send to jarvis-core
        ↓
┌────────────────────────────────────────────────┐
│  jarvis-core (FastAPI, Port 8340)              │
│  ├─ Orchestration & LLM (Claude Haiku)        │
│  ├─ Browser Control (Playwright)              │
│  ├─ Screen Vision (Claude Vision)             │
│  ├─ Action Execution & Routing                │
│  └─ HTTP proxies to audio & ha services      │
└────────────────────────────────────────────────┘
        ↓                           ↓
   ┌─────────────┐      ┌──────────────────┐
   │ jarvis-audio│      │  jarvis-ha       │
   │Port 8341    │      │  Port 8342       │
   ├─ElevenLabs  │      ├─Mail (AppleScript)
   │  TTS        │      ├─Reminders        │
   │─Text        │      ├─Obsidian Inbox   │
   │  Processing │      ├─Weather (API)    │
   │─Chunking &  │      ├─Calendar (HA)    │
   │  Synthesis  │      └─Lights (HA)      │
   └─────────────┘      └──────────────────┘
        ↓
Audio chunks → Tauri (native WKWebView) → You
                [Chrome fallback: USE_TAURI=0]
```

| Component | Technology | Purpose |
|---|---|---|
| **Frontend (Primary)** | Tauri 2 + WKWebView (~66 MB) | Native macOS app, fullscreen 1920×1200 |
| **Frontend (Fallback)** | Chrome `--kiosk` (`USE_TAURI=0`) | Legacy fallback, always available |
| **Health Monitor** | `/health` endpoint | Service status, logs, speech diagnostics |
| Wake Word + PTT | mlx-whisper large-v3 + pynput | Voice-to-text, local |
| **jarvis-core** | FastAPI (Python 3.11), Port 8340 | LLM orchestration + action routing |
| **jarvis-audio** | FastAPI microservice, Port 8341 | TTS synthesis (ElevenLabs) |
| **jarvis-ha** | FastAPI microservice, Port 8342 | Dashboard data + Home Assistant |
| Brain | Claude Haiku (Anthropic) | Thinking, deciding, responding |
| Voice | ElevenLabs TTS (eleven_turbo_v2_5) | Natural German speech |
| Browser Control | Playwright | Real browser automation |
| Screen Vision | Claude Vision + Pillow | Screenshot analysis |
| Reminders/Mail | AppleScript | macOS-native task access |
| Auto-start | launchd (7 KeepAlive agents) | Core + audio + ha + speech + session + wake + supervisor |
| Wake handling | wake-monitor.py → /api/wake | Post-sleep reactivation |

---

## Prerequisites

- **macOS 14+** (Apple Silicon, tested on M4)
- **Python 3.11** via Homebrew (`/opt/homebrew/bin/python3.11`)
- **Rust + Cargo** (for Tauri build, installed automatically if missing — see Quick Start)
- **Google Chrome** (optional — legacy fallback only, not required for normal use)
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
   git clone https://github.com/Black-Shadowcat/Jarvis-2.0.git Jarvis-2.0
   cd Jarvis-2.0
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

4. **Install and load LaunchAgents:**
   ```bash
   bash ~/Jarvis-2.0/scripts/setup-plists.sh
   ```

5. The Tauri app opens automatically. If not: `bash ~/Jarvis-2.0/scripts/launch-session.sh`
   (Chrome fallback: `USE_TAURI=0 bash ~/Jarvis-2.0/scripts/launch-session.sh`)

---

## Manual Start

**Option A — Hotkey** (recommended): `Cmd+Shift+J` → starts Tauri automatically

**Option B — Terminal:**
```bash
bash ~/Jarvis-2.0/scripts/launch-session.sh       # Tauri (default)
USE_TAURI=0 bash ~/Jarvis-2.0/scripts/launch-session.sh  # Chrome (fallback)
```

**Option C — App Bundle:**
```
Double-click: /Applications/Jarvis.app
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
│   ├── handbuch.html      # User manual DE (/handbuch)
│   ├── handbuch-en.html   # User manual EN (/handbuch-en)
│   └── i18n/
│       ├── de.json        # German UI labels
│       └── en.json        # English UI labels
├── docs/
│   ├── SERVICE_SPECS.md       # Microservice API contracts & specs
│   ├── MICROPHONE_SETUP.md    # Microphone calibration guide
│   └── icon-source/           # Icon source files + update process
│       ├── JARVIS_source_1254x1254.png  # Original AI-generated source
│       ├── generate_icon_konzept_a.py   # Programmatic generator (numpy+PIL)
│       └── README.md          # Icon update process documentation
├── services/
│   ├── jarvis-audio/           # Port 8341 — TTS Microservice
│   │   ├── main.py
│   │   └── requirements.txt
│   └── jarvis-ha/              # Port 8342 — Dashboard & HA Microservice
│       ├── main.py
│       └── requirements.txt
├── launchagents/
│   ├── com.jarvis.v2.server.plist      # jarvis-core autostart
│   ├── com.jarvis.v2.audio.plist       # jarvis-audio autostart
│   ├── com.jarvis.v2.ha.plist          # jarvis-ha autostart
│   ├── com.jarvis.v2.speech.plist      # Speech input autostart
│   ├── com.jarvis.v2.session.plist     # Browser session autostart
│   ├── com.jarvis.v2.wake.plist        # Wake-from-sleep handler
│   └── com.jarvis.v2.supervisor.plist  # Health supervisor
├── src-tauri/             # Tauri native app (Rust)
│   ├── src/lib.rs         # IPC bridge (get_status, get_version, send_chat)
│   ├── icons/             # App icon (all sizes, generated by cargo tauri icon)
│   ├── tauri.conf.json    # Tauri config (devUrl → http://localhost:8340)
│   └── Cargo.toml
└── scripts/
    ├── launch-session.sh  # Starts Tauri (default) or Chrome (USE_TAURI=0)
    └── wake-monitor.py    # Wake-from-sleep → /api/wake
```

---

## launchd Agents (7 Services)

All agents in `~/Library/LaunchAgents/` — auto-restart on crash:

| Agent | Port | Purpose |
|---|---|---|
| `com.jarvis.v2.server.plist` | 8340 | **jarvis-core** — LLM Brain + Orchestration |
| `com.jarvis.v2.audio.plist` | 8341 | **jarvis-audio** — TTS Synthesis |
| `com.jarvis.v2.ha.plist` | 8342 | **jarvis-ha** — Dashboard + Home Assistant |
| `com.jarvis.v2.speech.plist` | — | **speech_input.py** — Wake word + F19 PTT |
| `com.jarvis.v2.session.plist` | — | **Tauri App** — Native UI (Chrome fallback via `USE_TAURI=0`) |
| `com.jarvis.v2.wake.plist` | — | **wake-monitor.py** — Wake-from-sleep detection |
| `com.jarvis.v2.supervisor.plist` | — | **supervisor.py** — Health Monitor (30s checks) |

```bash
# Reload a service
launchctl unload ~/Library/LaunchAgents/com.jarvis.v2.server.plist
launchctl load   ~/Library/LaunchAgents/com.jarvis.v2.server.plist

# Logs (real-time)
tail -f ~/Library/Logs/jarvis-v2/server.log
tail -f ~/Library/Logs/jarvis-v2/audio.log
tail -f ~/Library/Logs/jarvis-v2/ha.log
tail -f ~/Library/Logs/jarvis-v2/speech.log
tail -f ~/Library/Logs/jarvis-v2/supervisor.log
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Server not responding | `pkill -f "server.py"` — launchd restarts automatically |
| Wake word not working | Check `~/Library/Logs/jarvis-v2/speech.log` |
| Tauri won't open | Run `bash ~/Jarvis-2.0/scripts/launch-session.sh` — builds binary on first run |
| Chrome fallback | `USE_TAURI=0 bash ~/Jarvis-2.0/scripts/launch-session.sh` |
| Microphone permission | System Settings → Privacy → Accessibility → allow Terminal |
| Reminders not showing | Check `~/Library/Logs/jarvis-v2/server.log` |
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
