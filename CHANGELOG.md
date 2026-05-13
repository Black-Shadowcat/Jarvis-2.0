# Changelog — jarvis-whisper

All notable changes are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), versioning follows [SemVer](https://semver.org/).

---

## [0.1.2] — 2026-05-13

### Added
- **Kiosk-Mode**: `launch-session.sh` now uses `--kiosk` instead of `--app --start-fullscreen` — true fullscreen without browser chrome
- **Automator App**: `~/Applications/Jarvis starten.app` — manual start by double-click or from Dock, custom icon (blue orb with J)
- **App Icon**: `docs/jarvis.icns` + `docs/jarvis-icon.png` — all sizes from 16px to 1024px@2x

### Fixed
- `welcome.html`: removed hardcoded `v0.0.5` and `v0.0.5 // INIT` — no more version display on the intro page

### Other
- Old JARVIS (Port 8340): LaunchAgents `com.jarvis.{server,session,wake}.plist` unloaded via `launchctl unload` — no longer starts on reboot (plists still present, re-loadable anytime)

---

## [0.1.1] — 2026-05-13

### Added
- Server broadcasts `{"type": "user_input", "text": "..."}` to browser when STT text arrives
- Frontend shows recognized text as "Du:" line in chat history — like v2.6.x
- Applies equally to wake word, auto-listen, and F19 PTT

---

## [0.1.0] — 2026-05-13

### Fixed
- **No HUD feedback during Whisper transcription**: `_ww_thread` now shows `listen_open` (bright blue ring) immediately after voice onset — before Whisper processing. No more "long delay without reaction".
- **"Just Jarvis" without follow-up command**: Instead of follow-up recording (which always transcribed silence → filtered → nothing), now immediately sends `"Jarvis activate"`. Server responds, auto-listen handles the follow-up.
- **"Jarvis" not recognized**: HUD returns to idle (`listen_close`), no stuck listening state.
- **`initial_prompt="Jarvis."`**: Whisper hint for WW snippets → better recognition of the name in German mode.
- **Inline command**: Removed 0.15s flash — direct `stop` → thinking, no more flickering.

---

## [0.0.9] — 2026-05-13

### Fixed
- **Echo/Feedback loop**: `_audio_cb` no longer writes chunks to `_detect_q` while `_jarvis_speaking=True` — Jarvis doesn't listen to itself
- After `speaking_end`: `_detect_q` is flushed — queued speaker chunks from end of TTS are discarded

---

## [0.0.8] — 2026-05-13

### Fixed
- **`_jarvis_speaking` stuck True**: If `speaking_end` doesn't arrive after a TTS (e.g. after connection drop), the flag blocks wake word indefinitely. Fix: 25s safety timeout in `_ww_thread` — after 25s the flag auto-resets (warning log).
- **WS Reconnect Reset**: On every (re-)connection of the WebSocket, `_jarvis_speaking` and `_in_conversation` are reset to `False` — no stuck state after restart/reconnect.
- **`global _jarvis_speaking`**: Missing `global` declaration in `_ww_thread` caused `UnboundLocalError` on first timeout reset.

### Added
- **`scripts/launch-session.sh`**: Waits for macOS readiness (Dock + Finder) + server readiness, opens Chrome in app mode on `http://localhost:8341` with own profile (`~/.jarvis-whisper-chrome-profile`).
- **`com.jarvis.whisper.session.plist`**: LaunchAgent for browser autostart on login — like old JARVIS `com.jarvis.session.plist` but for port 8341.

---

## [0.0.7] — 2026-05-13

### Added
- **Wake Word "Jarvis"**: VAD + Whisper-based activation — no "Hey" needed, no external model
  - `speech_input.py`: RMS-VAD detects voice onset, short snippet (max 5s) transcribed with Whisper
  - If "Jarvis" detected + command in same sentence → send directly
  - If only "Jarvis" said → waits for follow-up with auto-stop after 1.5s silence
  - F19 remains active as PTT
- **ElevenLabs error display**:
  - `server.py`: `_speak()` sends `{type: tts_error}` when TTS fails
  - `frontend/index.html`: new orb state `error` (magenta), toast notification "TTS nicht verfügbar", auto-reset after 4s

---

## [0.0.6] — 2026-05-13

### Added
- LaunchAgent `com.jarvis.whisper.server.plist` — server.py starts automatically on login, KeepAlive, logs to `~/Library/Logs/jarvis-whisper/server.log`
- LaunchAgent `com.jarvis.whisper.speech.plist` — speech_input.py starts automatically on login, KeepAlive, logs to `~/Library/Logs/jarvis-whisper/speech.log`
- `scripts/start-dev.sh` + `scripts/stop-dev.sh` — start/stop via `launchctl` instead of manually
- Structured logging: `logging` module instead of `print()` in `server.py` and `speech_input.py`
  - Format: `HH:MM:SS  LEVEL  [jarvis] message`
  - Log levels: INFO/DEBUG/WARNING/ERROR by context
- `wake-monitor.py` pointing to port 8341

---

## [0.0.5] — 2026-05-12

### Added
- Visual F19 recording indicator: orb lights up red and pulses during recording
  - `speech_input.py` → `POST /api/ptt/start` & `/api/ptt/stop` on F19 press/release
  - `server.py` → broadcast `ptt_start`/`ptt_stop` to all browser connections
  - Orb flow: **recording** (red) → **thinking** (orange) → **speaking** (green) → **idle**
- TTS pronunciation: `J.A.R.V.I.S.` normalized to `Jarvis` before ElevenLabs (UI unchanged)
- Intro page on first start only: server-side flag file `data/intro_shown.flag`; `/welcome` always accessible from Config page
- 12s fallback timeout after `ptt_stop` → orb falls back to idle if no response

### Fixed
- **Critical**: `speech_input.py` and browser shared `/ws` → `_speak()` sent audio to STT client → WS conflicts, transcription lost, orb stuck on thinking. Fix: dedicated `/ws/stt` endpoint for `speech_input.py` (no audio broadcast)
- Activate debounce 30s → 5s: reload within 30s blocked completely (orb stuck on thinking)
- Removed mail fetch on every `Jarvis activate` (was active even on simple reconnect): saved 1–3s
- `asyncio.sleep` on reconnect greeting 0.8s → 0.2s
- 30s cache for `/api/get_mails_unread` and `/api/get_tasks`: dashboard load was blocking `initWS()` with live fetches from Mail.app / Reminders
- Update badge was pointing to old repo `jarvis-voice-assistant` → now points to `jarvis-whisper`
- `welcome.html`: corrected hardcoded version `v2.4.2` and port `8340`

---

## [0.0.4] — 2026-05-12

### Fixed
- GitHub update check was pointing to old repo `jarvis-voice-assistant` → now points to `jarvis-whisper`
- `welcome.html`: hardcoded version `v2.4.2` → `v0.0.3`, port `8340` → `8341`
- `version.json`: bumped to `0.0.3`

---

## [0.0.3] — 2026-05-12

### Removed
- Web Speech API completely removed from `frontend/index.html` (`initSpeechRecognition`, `startListening`, `recognition`, `isListening`)
- HUD mute toggle removed (was bound to Web Speech API)

### Changed
- Only input path now: F19 → Whisper → `speech_input.py` → server

---

## [0.0.2] — 2026-05-12

### Fixed
- `NEWS_INFO` missing from `global` declaration in `startup_and_refresh()` — news was not written to global state on server start, only locally.

---

## [0.0.1] — 2026-05-12

### Added
- `speech_input.py` — F19 push-to-talk + mlx-whisper large-v3 STT
- `server.py` — FastAPI on port 8341, `_speak()` broadcast to all WebSocket connections
- Standalone Python environment in `~/jarvis-v3/venv/`
- Git repository initialized (`main` branch)

### Changed
- STT: Chrome Web Speech API → mlx-whisper large-v3 (local, significantly better recognition quality)
- TTS routing: single WS connection → broadcast to all active connections

### Basis
- Forked from jarvis-voice-assistant v2.6.2 (server.py, systems/, frontend/, locales/)

---

---

## Legacy — jarvis-voice-assistant v2.x

> jarvis-whisper was forked from jarvis-voice-assistant v2.6.2. The following entries document the history of that base.

---

## [2.6.2] — 2026-05-12

### Fixed
- **News sorting** — `_ensure_news()` and startup load took `archive[:10]` (oldest first) instead of newest first.
- **System prompt date filter** — `build_system_prompt()` filtered on `saved_at` (doesn't exist in archive) → `recent` was always empty.

### Added
- **"✓ Zur Kenntnis" button** in news popup — marks article as read without opening the browser.

---

## [2.6.1] — 2026-05-12

### Fixed
- **Night greetings silent** — `wake_notification()` now returns silently before 6am.
- **Display sleep/wake detection** — `wake-monitor.py` now detects display-only sleep wakes via HIDIdleTime polling.
- **Stale news in morning brief** — Articles now filtered for `not a.get("read")` and marked read after use.

---

## [2.5.0] — 2026-05-08

### Added
- **Welcome page** — `/welcome` with triple-rotating HUD ring, feature descriptions, auto-TTS.

---

## [2.4.0] — 2026-05-08

### Added
- Language system (`de`/`en`), TTS locale files, UI i18n (28 keys), in-app update badge.

---

## [2.3.0] — 2026-05-07

### Added
- News System (RSS), Wake Brief, Daily Brief overhaul, Maintenance modal, RSS Feeds modal.

---

## [2.2.0] — 2026-05

### Added
- Daily Brief Memory System, wake smart unlock, WebSocket reconnect polish.

---

## [2.0.0] — 2026-04

### Changed
- Production migration — port 8340, Chrome app mode, launchd autostart, Config UI, Pydantic ActionModel.

---

## [1.0.0] — 2026-03

### Added
- Initial release — FastAPI backend, ElevenLabs TTS, Web Speech API, Playwright, Home Assistant, Apple Mail, Reminders, Kachelmann weather.
