# J.A.R.V.I.S. — jarvis-whisper (macOS v0.1.2)

> **jarvis-whisper** ersetzt die browserbasierte Web Speech API des ursprünglichen JARVIS durch lokales Whisper-STT auf Apple MLX.
>
> Basiert auf der ursprünglichen Idee von [Julian Ivanov](https://github.com/Julian-Ivanov/jarvis-voice-assistant) und jarvis-voice-assistant v2.6.2 von Matthias Schreiber. Entwickelt mit [Claude Code](https://claude.ai/code). Kein Support. Nur für den persönlichen Gebrauch.

---

## Was sich gegenüber v2.x geändert hat

| Alter JARVIS (v2.x) | jarvis-whisper (v0.1.x) |
|---|---|
| Web Speech API (Chrome) | mlx-whisper large-v3 (lokal, Apple Silicon) |
| Chrome-Mikrofonberechtigung | pynput + sounddevice (Systemebene) |
| Kein Aktivierungswort | Aktivierungswort **„Jarvis"** (sag „Jarvis, …") |
| Nur F19 PTT | F19 PTT **+** Aktivierungswort |
| Port 8340 | Port **8340** |
| `--app --start-fullscreen` | `--kiosk` (echter Kiosk-Modus) |
| Cmd+Shift+J Start | Automator-App + LaunchAgent |

---

> Sag **„Jarvis, …"** — Jarvis erkennt deinen Befehl lokal mit Whisper, denkt mit Claude Haiku nach und antwortet mit ElevenLabs TTS. Kein Cloud-STT, keine Browser-Mikrofonberechtigung nötig.

---

## Features

- **Aktivierungswort „Jarvis"** — Sag „Jarvis, …" zum Aktivieren. Kein „Hey" nötig. VAD + Whisper, kein externes Modell.
- **F19 Push-to-Talk** — Physische PTT-Taste funktioniert weiterhin neben dem Aktivierungswort.
- **Lokales STT** — mlx-whisper large-v3 auf Apple MLX. Vollständig offline, kein API-Key nötig.
- **Echo-Schutz** — Mikrofon stumm während Jarvis spricht. Keine Rückkopplungsschleifen.
- **Erkannter Text im Chat** — Jeder erkannte Befehl erscheint als „Du:" im Chatverlauf.
- **Sprachgespräch** — Sprich frei auf Deutsch. Jarvis hört zu, denkt nach, antwortet per Stimme.
- **Wetter & Aufgaben** — Bei der Begrüßung: aktuelles Wetter + heutige offene Erinnerungen.
- **Apple Erinnerungen** — Erinnerungen lesen, hinzufügen und abhaken via AppleScript.
- **Apple Mail** — Ungelesene Mails auf Anfrage vorlesen.
- **Kalender** — Termine für heute und morgen via Home Assistant CalDAV.
- **Home Assistant Lichter** — Lichter per Raumname mit 30+ Synonymen steuern.
- **Obsidian Inbox** — Notizen schreiben, lesen, erledigen — alles per Stimme.
- **Browser-Automatisierung** — Playwright steuert einen echten Browser: suchen, URLs öffnen, Seiten lesen.
- **Bildschirm-Vision** — Screenshot + Claude Vision: „Was ist auf meinem Bildschirm?"
- **RSS-Neuigkeiten** — RSS-Artikel abrufen und vorlesen. Feeds über Config UI verwalten.
- **Daily Brief Memory System** — Morgen-/Pause-/Abwesenheits-/Abend-Briefings mit Zustandsverfolgung.
- **Wake-from-Sleep** — Erkennt den Bildschirm-Unlock, spricht dann automatisch den passenden Brief.
- **Update-Badge** — Alle Seiten zeigen ein Badge wenn eine neue GitHub-Version verfügbar ist.
- **Kiosk-Modus** — Chrome öffnet sich im echten Kiosk-Modus (keine Browser-Leiste, Vollbild).
- **Automator-App** — `~/Applications/Jarvis starten.app` zum manuellen Start mit eigenem Icon.
- **launchd Autostart** — Server, Spracheingabe und Session starten automatisch beim Login.

---

## Architektur

```
Du (sagst „Jarvis, …")
        ↓
speech_input.py
  RMS-VAD erkennt Spracheinsatz
  → HUD: listen_open (blauer Ring sofort)
  → mlx-whisper large-v3 (lokal)
  → „jarvis" im Text? → Befehl an Server senden
        ↓
FastAPI Server (localhost:8340)
  → Claude Haiku (Gehirn)
  → parse_structured_action()
        ↓
    ┌──────────┬──────────────┬────────────────┐
    ↓          ↓              ↓                ↓
ElevenLabs  Playwright    AppleScript    Home Assistant
  TTS        Browser    Erinnerungen/Mail  Lichtsteuerung
    ↓
Audio-Chunks → Chrome (Kiosk) → Du
```

| Komponente | Technologie | Zweck |
|---|---|---|
| Aktivierungswort + PTT | mlx-whisper large-v3 + pynput | Sprache-zu-Text, lokal |
| Server | FastAPI (Python 3.11), Port 8340 | Lokale Orchestrierung |
| Gehirn | Claude Haiku (Anthropic) | Denken, entscheiden, antworten |
| Stimme | ElevenLabs TTS (eleven_turbo_v2_5) | Natürliche deutsche Sprachausgabe |
| Browser-Steuerung | Playwright | Echte Browser-Automatisierung |
| Bildschirm-Vision | Claude Vision + Pillow | Screenshot-Analyse |
| Smart Home | Home Assistant REST API | Lichtsteuerung |
| Erinnerungen/Mail | AppleScript | macOS-nativer Datenzugriff |
| Autostart | launchd (3 KeepAlive-Agents) | Server + Speech + Session beim Login |
| Wake-Handling | wake-monitor.py → /api/wake | Reaktivierung nach Schlaf |

---

## Voraussetzungen

- **macOS 14+** (Apple Silicon, getestet auf M4)
- **Python 3.11** via Homebrew (`/opt/homebrew/bin/python3.11`)
- **Google Chrome**
- **Bedienungshilfen-Berechtigung** für speech_input.py (Systemeinstellungen → Datenschutz → Bedienungshilfen)
- **Home Assistant** (optional, für Lichter und CalDAV-Kalender)

### Benötigte API-Keys

| Dienst | Wofür | Link |
|---|---|---|
| Anthropic | Claude Haiku (das Gehirn) | [console.anthropic.com](https://console.anthropic.com) |
| ElevenLabs | Stimme (TTS, mindestens Starter-Plan) | [elevenlabs.io](https://elevenlabs.io) |

Kein STT-API-Key nötig — Whisper läuft lokal auf Apple Silicon.

---

## Schnellstart

1. **Klonen und installieren:**
   ```bash
   git clone https://github.com/Black-Shadowcat/jarvis-whisper.git jarvis-v3
   cd jarvis-v3
   /opt/homebrew/bin/python3.11 -m pip install -r requirements.txt
   /opt/homebrew/bin/python3.11 -m playwright install chromium
   ```

2. **Config erstellen:**
   ```bash
   cp config.example.json config.json
   ```

3. **`config.json` bearbeiten** — mindestens erforderlich:
   ```json
   {
     "anthropic_api_key": "sk-ant-...",
     "elevenlabs_api_key": "sk_...",
     "elevenlabs_voice_id": "DEINE_VOICE_ID",
     "user_name": "Dein Name",
     "user_address": "Sir",
     "city": "Deine Stadt"
   }
   ```

4. **LaunchAgents laden:**
   ```bash
   launchctl load ~/Library/LaunchAgents/com.jarvis.whisper.server.plist
   launchctl load ~/Library/LaunchAgents/com.jarvis.whisper.speech.plist
   launchctl load ~/Library/LaunchAgents/com.jarvis.whisper.session.plist
   ```

5. `http://localhost:8340` im Chrome öffnen, falls er sich nicht automatisch öffnet.

---

## Manueller Start

**Option A — Automator-App** (empfohlen):
```
Doppelklick: ~/Applications/Jarvis starten.app
```

**Option B — Terminal:**
```bash
bash ~/jarvis-v3/scripts/launch-session.sh
```

---

## Was du sagen kannst

| Befehl | Was passiert |
|---|---|
| *„Jarvis, guten Morgen"* | Wetter + heutige Aufgaben |
| *„Jarvis, was steht heute an?"* | Erinnerungen + Kalender |
| *„Jarvis, schalte das Wohnzimmerlicht ein"* | Lichtsteuerung per Stimme |
| *„Jarvis, suche nach KI-Neuigkeiten"* | Browser öffnet, sucht, fasst zusammen |
| *„Jarvis, was ist auf meinem Bildschirm?"* | Screenshot + Claude Vision |
| *„Jarvis, schreib eine Notiz: …"* | Obsidian Inbox Eintrag |
| *„Jarvis"* (allein) | Aktiviert, wartet auf Folgebefehl |

---

## Projektstruktur

```
jarvis-whisper/
├── server.py              # FastAPI Backend — Gehirn + Action-System (Port 8340)
├── speech_input.py        # mlx-whisper STT + Aktivierungswort + F19 PTT
├── browser_tools.py       # Playwright Browser-Automatisierung
├── screen_capture.py      # Screenshot + Claude Vision
├── version.json           # Zentrale Versionsnummer
├── config.json            # Persönliche Config (gitignored)
├── config.example.json    # Vorlage für neue Nutzer
├── requirements.txt       # Python-Abhängigkeiten
├── locales/
│   ├── de.json            # Deutsche TTS-Strings
│   └── en.json            # Englische Entsprechungen
├── systems/
│   └── daily_brief.py     # Daily Brief Memory System
├── data/
│   └── daily_brief_memory.json   # Tagesgedächtnis (gitignored)
├── frontend/
│   ├── index.html         # Jarvis Dashboard + HUD (Kiosk, Port 8340)
│   ├── config.html        # Config UI (/config)
│   ├── config.js          # Config UI Logik
│   ├── handbuch.html      # Benutzerhandbuch (/handbuch)
│   └── i18n/
│       ├── de.json        # Deutsche UI-Labels
│       └── en.json        # Englische UI-Labels
├── docs/
│   ├── jarvis.icns        # App-Icon (alle Größen)
│   └── jarvis-icon.png    # App-Icon (PNG)
├── launchagents/
│   ├── com.jarvis.whisper.server.plist   # Server Autostart
│   ├── com.jarvis.whisper.speech.plist   # Spracheingabe Autostart
│   └── com.jarvis.whisper.session.plist  # Browser-Session Autostart
└── scripts/
    ├── launch-session.sh  # Startet Chrome im Kiosk-Modus
    └── wake-monitor.py    # Wake-from-Sleep → /api/wake
```

---

## launchd Agents

Drei Agents unter `~/Library/LaunchAgents/`:

| Agent | Zweck |
|---|---|
| `com.jarvis.whisper.server.plist` | FastAPI Server, KeepAlive (startet bei Absturz neu) |
| `com.jarvis.whisper.speech.plist` | speech_input.py (Aktivierungswort + F19 PTT), KeepAlive |
| `com.jarvis.whisper.session.plist` | Browser-Session beim Login (Chrome Kiosk-Modus) |

```bash
# Neu laden
launchctl unload ~/Library/LaunchAgents/com.jarvis.whisper.server.plist
launchctl load   ~/Library/LaunchAgents/com.jarvis.whisper.server.plist

# Logs
tail -f ~/Library/Logs/jarvis-whisper/server.log
tail -f ~/Library/Logs/jarvis-whisper/speech.log
```

---

## Fehlerbehebung

| Problem | Lösung |
|---|---|
| Server antwortet nicht | `pkill -f "server.py"` — launchd startet automatisch neu |
| Aktivierungswort funktioniert nicht | `~/Library/Logs/jarvis-whisper/speech.log` prüfen |
| Chrome öffnet sich nicht | `bash ~/jarvis-v3/scripts/launch-session.sh` manuell starten |
| Mikrofonberechtigung | Systemeinstellungen → Datenschutz → Bedienungshilfen → Terminal erlauben |
| Erinnerungen werden nicht angezeigt | `~/Library/Logs/jarvis-whisper/server.log` prüfen |
| Browser-Automatisierung schlägt fehl | `playwright install chromium` erneut ausführen |

---

## Technologie-Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** — Python Web-Framework
- **[mlx-whisper](https://github.com/ml-explore/mlx-examples)** — Lokales STT auf Apple MLX
- **[Claude Haiku](https://anthropic.com)** — KI-Modell (Gehirn)
- **[ElevenLabs](https://elevenlabs.io)** — Natürliche Sprachsynthese
- **[Playwright](https://playwright.dev)** — Browser-Automatisierung
- **[pynput](https://pynput.readthedocs.io/)** — Globaler Tastatur-Listener (F19 PTT)
- **[sounddevice](https://python-sounddevice.readthedocs.io/)** — Audio-Aufnahme
- **[Home Assistant](https://www.home-assistant.io/)** — Smart Home Integration
- **AppleScript** — macOS Erinnerungen & Mail Zugriff

---

## Danksagung

Ursprüngliche Idee und Windows-Implementierung von [Julian Ivanov](https://github.com/Julian-Ivanov) — entwickelt mit [Claude Code](https://claude.ai/code).
jarvis-whisper — entwickelt von Matthias Schreiber mit [Claude Code](https://claude.ai/code).

Inspiriert von Iron Mans J.A.R.V.I.S. — *„Zu Ihren Diensten, Sir."*

---

## Lizenz

MIT — nutze es, verändere es, baue darauf auf.
