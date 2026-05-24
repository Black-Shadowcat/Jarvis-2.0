# JARVIS Setup (macOS) — Jarvis 2.0 v2.0.4

Dein persönlicher KI-Sprachassistent mit Sprachsteuerung — optimiert für macOS Apple Silicon.

**v2.0.0-beta — Tauri Native App:** Vollständiger Neubau mit 3 unabhängigen Microservices + nativer Tauri-App statt Chrome Kiosk (~66 MB statt 480 MB).

---

## 🚀 Schnelleinstieg (5 Minuten)

**VS Code + Claude Code** ist der schnellste Weg:

1. Repo klonen: `git clone https://github.com/Black-Shadowcat/Jarvis-2.0.git Jarvis-2.0`
2. Ordner in VS Code öffnen
3. Claude Code starten (`Cmd+Shift+C` oder Terminal → `claude`)
4. Tippe: **„Richte Jarvis ein"**

Claude Code liest diese Datei und führt dich interaktiv durch den kompletten Setup.

---

## Schritt 0: Voraussetzungen überprüfen

### System-Requirements
```bash
# macOS Version
sw_vers | grep "ProductVersion"

# Python 3.11 verfügbar?
which python3.11 || echo "FEHLT: Siehe unten"

# Rust/Cargo (für Tauri-Build)
which cargo || echo "FEHLT: brew install rustup && rustup-init"

# Google Chrome (optional — nur als Legacy-Fallback nötig)
ls "/Applications/Google Chrome.app" 2>/dev/null && echo "OK (optional)" || echo "Nicht installiert (optional)"
```

### Falls Python 3.11 fehlt:
```bash
brew install python@3.11

# Verifizieren
/opt/homebrew/bin/python3.11 --version  # sollte 3.11.x zeigen
```

### Falls Rust/Cargo fehlt:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
# Verifizieren
cargo --version  # sollte cargo 1.x.x zeigen
```

> **Hinweis:** Chrome ist nicht mehr Pflicht. Die Jarvis-App ist jetzt eine native Tauri-App.  
> Chrome kann als Fallback weiterhin verwendet werden: `USE_TAURI=0 bash scripts/launch-session.sh`

---

## Schritt 1: API Keys besorgen (10 Minuten)

Vor dem Setup brauchst du API-Keys. **Nur 2 sind Pflicht**, der Rest optional.

| Service | Link | Pflicht | Kosten | Hinweise |
|---------|------|---------|--------|----------|
| **Anthropic** (Claude) | https://console.anthropic.com | ✅ | ~$0.25 / 1M Tokens | "API Keys" → Copy Key (beginnt mit `sk-ant-`) |
| **ElevenLabs** (Stimme) | https://elevenlabs.io | ✅ | ab ~5 $/Monat | Profile → API Keys, + My Voices für Voice ID |
| **Kachelmann** (Wetter) | https://kachelmannwetter.com/api | ⚡ | kostenpflichtig | Optional |
| **Home Assistant** | (nur wenn vorhanden) | ⚡ | kostenlos lokal | Profil → Long-Lived Access Tokens |

> **Wichtig:** Kein STT-API nötig — Whisper läuft lokal auf deinem Mac. Kostenlos!

---

## Schritt 2: Repo klonen

```bash
git clone https://github.com/Black-Shadowcat/Jarvis-2.0.git Jarvis-2.0
cd Jarvis-2.0
```

Merke dir den Pfad (z.B. `~/Jarvis-2.0` oder `/Users/deinname/Jarvis-2.0`).

---

## Schritt 3: Konfiguration erstellen

```bash
# Kopiere die Example-Datei
cp config.example.json config.json
```

Öffne `config.json` und fülle aus:

```json
{
  "anthropic_api_key": "sk-ant-...",                              // Pflicht
  "elevenlabs_api_key": "sk_...",                                 // Pflicht
  "user_name": "Dein Name",                                       // Dein Name
  "user_address": "Sir",                                          // M: Sir/Chef | W: Ms./Mrs./Madam
  "city": "Hamburg",                                              // Deine Stadt
  "lat": 53.55,                                                   // GPS Breitengrad (maps.google.com → Rechtskl.)
  "lon": 10.00,                                                   // GPS Längengrad
  "kachelmann_api_key": "",                                       // Optional (Wetter)
  "ha_url": "http://192.168.1.10:8123",                           // Optional (Home Assistant)
  "ha_token": "eyJhbGciOiJIUzI1NiIs...",                          // Optional (HA Token)
  "ha_enabled": false,                                            // false wenn du keine HA hast
  "workspace_path": "/Users/DEINNAME/Jarvis-2.0",                // WICHTIG: Dein aktueller Pfad
  "obsidian_inbox_path": "/Users/DEINNAME/.../01 Inbox",         // Optional
  "wake_greeting_enabled": true,
  "language": "de"                                                // "de" oder "en"
}
```

> **Hinweis:** `workspace_path` ist wichtig! Das ist der Pfad zu deinem Jarvis-2.0 Verzeichnis.

---

## Schritt 4: Voice-Config erstellen

```bash
cp voice.example.json voice.json
```

Wähle deine Stimme aus: https://elevenlabs.io/app/speech-synthesis

```json
{
  "active_voice_id": "EXAVITQu4vr4xnSDxMaL",           // Beispiel Voice-ID
  "voices": [
    {
      "name": "Bella",
      "voice_id": "EXAVITQu4vr4xnSDxMaL"
    }
  ]
}
```

---

## Schritt 5: Python Dependencies installieren

```bash
/opt/homebrew/bin/python3.11 -m pip install --upgrade pip
/opt/homebrew/bin/python3.11 -m pip install -r requirements.txt
/opt/homebrew/bin/python3.11 -m playwright install chromium
```

Dauert 2-3 Minuten. ☕

---

## Schritt 6: Server testen (MANUELL, vor LaunchAgents)

```bash
cd ~/Jarvis-2.0  # oder dein Jarvis-Pfad

# Terminal 1: Starte den Server
/opt/homebrew/bin/python3.11 server.py

# Terminal 2: Teste ob er läuft (warte 5 Sekunden)
sleep 5
curl http://localhost:8340/ | head -5
```

Sollte HTML zurückgeben. Wenn OK, weitermachen!

```bash
# Server stoppen (Ctrl+C in Terminal 1)
```

---

## Schritt 7: LaunchAgents installieren (AUTOMATISCH)

Dieses Script kopiert die LaunchAgent Plists mit **korrekten Pfaden** in `~/Library/LaunchAgents/` und ladet sie in launchd.

```bash
bash scripts/setup-plists.sh

# Output sollte zeigen:
# ✓ Processing com.jarvis.v2.server.plist...
# ✓ Processing com.jarvis.v2.audio.plist...
# ... etc
```

> Das Script **ersetzt automatisch** Pfade in den Plists, damit sie auf deinem System funktionieren.

---

## Schritt 8: macOS Berechtigungen setzen

Damit Jarvis Mikrofon + F19 + Screenshots benutzen kann, brauchst du Berechtigungen.

Öffne **Systemeinstellungen → Datenschutz & Sicherheit**:

| Bereich | Berechtigung | Was hinzufügen | Pflicht |
|---------|--------------|----------------|---------|
| **Bedienungshilfen** | Accessibility | `Terminal` (und `Python` falls sichtbar) | ✅ |
| **Mikrofon** | Microphone | `Terminal` | ✅ |
| **Bildschirmaufnahme** | Screen Recording | `Terminal` | ⚡ (für "Was siehst du?") |

> **Wichtig:** Ohne Bedienungshilfen kann F19 nicht erkannt werden!

---

## Schritt 9: Test — Ist alles läuft?

```bash
# Status prüfen
launchctl list | grep "jarvis.v2"
# Sollte 7 Zeilen zeigen

# Ports prüfen
lsof -i :8340 -i :8341 -i :8342 | grep LISTEN
# Sollte 3 Zeilen zeigen (8340, 8341, 8342)

# Schnell-Tests
curl http://localhost:8340/ | head -1      # server OK?
curl http://localhost:8341/health | jq .   # audio OK?
curl http://localhost:8342/health | jq .   # ha OK?
```

Alle drei sollten antworten. ✓

---

## Schritt 10: Jarvis-App öffnen

Die Tauri-App startet automatisch via LaunchAgent. Falls nicht:

```bash
bash ~/Jarvis-2.0/scripts/launch-session.sh
```

Beim ersten Start wird die Tauri-App gebaut (~2 Min einmalig). Danach öffnet sie sofort.  
Du solltest das **Jarvis HUD** (blauer Ring mit Chat) sehen!

> **Fallback auf Chrome:** `USE_TAURI=0 bash ~/Jarvis-2.0/scripts/launch-session.sh`  
> **Browser direkt:** `open http://localhost:8340`

---

## Schritt 11: skhd Hotkey (Cmd+Shift+J) - Optional

Um Jarvis mit **Cmd+Shift+J** zu starten:

```bash
# skhd installieren (falls nicht vorhanden)
brew install skhd

# skhd Auto-Start aktivieren
skhd --start-service
```

Dann ergänze `~/.skhdrc` mit dieser Zeile:

```bash
cmd + shift + j: ~/Jarvis-2.0/scripts/launch-session.sh &
```

Neustarten:
```bash
skhd --restart
```

Jetzt: **Cmd+Shift+J** → öffnet Jarvis als native Tauri-App automatisch! 🚀

---

## ✅ Fertig!

**Browser URLs:**
- `http://localhost:8340` — Jarvis HUD + Chat
- `http://localhost:8340/config` — Config UI (API Keys testen)
- `http://localhost:8340/handbuch` — Benutzerhandbuch (DE/EN)
- `http://localhost:8340/health` — Health Monitor (System Status)

**Jarvis aktivieren:**
- Sag: **„Jarvis, …"** (Wake Word)
- Oder: **F19** (Push-to-Talk)
- Oder: **Cmd+Shift+J** (falls skhd aktiv)

**Logs anschauen:**
```bash
tail -f ~/Library/Logs/jarvis-v2/server.log
tail -f ~/Library/Logs/jarvis-v2/audio.log
tail -f ~/Library/Logs/jarvis-v2/ha.log
tail -f ~/Library/Logs/jarvis-v2/speech.log
```

---

---

# 📖 Referenz

## Was Jarvis kann

- 🎤 Wake Word "Jarvis" + F19 Push-to-Talk
- 🧠 Claude Haiku (Anthropic)
- 🎙️ ElevenLabs TTS
- 📧 Apple Mail lesen
- ✅ Apple Reminders verwalten
- 📔 Obsidian Inbox Notes
- 🏠 Home Assistant Lights steuern
- 🌍 Wetter (Kachelmann)
- 📅 Kalender (Home Assistant)
- 🔍 Browser-Automation (suchen, URLs öffnen)
- 👁️ Screenshot + Claude Vision ("Was siehst du?")
- 📰 RSS News
- 🖥️ Native Tauri-App (WKWebView, ~66 MB — kein Chrome nötig)

---

## Alle Voice-Commands

| Beispiel | Was passiert |
|----------|-------------|
| „Jarvis, suche nach KI" | DuckDuckGo-Suche + Seite vorlesen |
| „Jarvis, öffne github.com" | Browser öffnet URL |
| „Jarvis, öffne Mail" | macOS Mail-App startet |
| „Jarvis, was siehst du?" | Screenshot + Vision-Analyse |
| „Jarvis, aktuelle Nachrichten" | News laden + vorlesen |
| „Jarvis, erinnere mich an..." | Reminder hinzufügen |
| „Jarvis, was steht heute an?" | Reminders + Kalender |
| „Jarvis, meine Mails" | Ungelesene Mails vorlesen |
| „Jarvis, Wohnzimmerlicht 50%" | Home Assistant Light steuern |
| „Jarvis, notiere..." | Text in Obsidian Inbox |

---

## Projektstruktur (v1.0.0)

```
Jarvis-2.0/
├── server.py                   # jarvis-core (8340) — LLM Brain
├── speech_input.py             # STT + Wake Word + F19
├── requirements.txt            # Python Dependencies
├── config.json / config.example.json
├── voice.json / voice.example.json
├── version.json                # Version (1.0.0)
│
├── services/
│   ├── jarvis-audio/main.py    # TTS Microservice (8341)
│   └── jarvis-ha/main.py       # Dashboard + HA (8342)
│
├── frontend/
│   ├── index.html              # HUD + Chat
│   ├── config.html             # Config UI
│   ├── handbuch.html           # Benutzerhandbuch
│   └── i18n/{de,en}.json       # UI-Übersetzungen
│
├── scripts/
│   ├── setup-plists.sh         # LaunchAgent Installer
│   ├── launch-session.sh       # Start all Services + Browser
│   ├── start-dev.sh            # Lokales Development
│   └── stop-dev.sh             # Stop all Services
│
├── launchagents/               # Service Plists (templates)
│   ├── com.jarvis.v2.server.plist
│   ├── com.jarvis.v2.audio.plist
│   ├── com.jarvis.v2.ha.plist
│   └── ... (7 total)
│
└── data/
    └── daily_brief_memory.json # Tagesgedächtnis (auto-reset)
```

---

## LaunchAgents — 7 Microservices

| Plist | Port | Aufgabe |
|-------|------|---------|
| `com.jarvis.v2.server` | 8340 | LLM Brain + Orchestration |
| `com.jarvis.v2.audio` | 8341 | TTS Synthese (ElevenLabs) |
| `com.jarvis.v2.ha` | 8342 | Dashboard + Home Assistant |
| `com.jarvis.v2.speech` | — | STT + Wake Word Detection |
| `com.jarvis.v2.session` | — | Tauri Native App (Chrome Fallback: `USE_TAURI=0`) |
| `com.jarvis.v2.wake` | — | Wake-from-Sleep Handler |
| `com.jarvis.v2.supervisor` | — | Health Monitor (30s checks) |

**Service-Flow:**
```
User: "Jarvis, Licht an"
  ↓
speech_input.py (STT)
  ↓
jarvis-core (8340) — denkt
  ↙              ↘
jarvis-audio    jarvis-ha
(8341)          (8342)
TTS             Light Command
```

---

## Troubleshooting

### Services starten nicht

```bash
# Alle Jarvis-Prozesse killen
pkill -9 -f "jarvis"
sleep 2

# Setup erneut ausführen
bash scripts/setup-plists.sh

# Status prüfen
launchctl list | grep "jarvis.v2"
```

### Ports sind belegt

```bash
lsof -i :8340 -i :8341 -i :8342

# Falls ja: Prozesse killen
pkill -f "server.py"
pkill -f "jarvis-audio"
pkill -f "jarvis-ha"

# Services neu starten
launchctl load ~/Library/LaunchAgents/com.jarvis.v2.*.plist
```

### Server startet nicht (Port 8340)

```bash
tail -f ~/Library/Logs/jarvis-v2/server.log

# Manuell testen:
/opt/homebrew/bin/python3.11 ~/Jarvis-2.0/server.py

# Häufige Fehler:
# - config.json Syntax-Fehler
# - API-Key ungültig
# - Port 8340 bereits belegt
```

### Wake Word / F19 funktioniert nicht

```bash
tail -f ~/Library/Logs/jarvis-v2/speech.log

# Meist: Bedienungshilfen-Berechtigung fehlt!
# Systemeinstellungen → Datenschutz → Bedienungshilfen → Terminal hinzufügen
```

### TTS funktioniert nicht (kein Sound)

```bash
curl http://localhost:8341/health | jq .

# Falls unhealthy:
# - ElevenLabs API-Key ungültig?
# - Voice ID existent?
# - Logs: tail -f ~/Library/Logs/jarvis-v2/audio.log
```

### Dashboard leer (Mail/Tasks/Wetter fehlt)

```bash
curl http://localhost:8342/health | jq .

# Mail.app muss offen sein (AppleScript-Zugriff)
# Reminders.app muss offen sein
# Kachelmann-API Key gesetzt? (für Wetter)
```

### Tauri-App öffnet nicht

```bash
# Tauri-App manuell starten
bash ~/Jarvis-2.0/scripts/launch-session.sh

# Oder direkt (nach erstem Build):
~/Jarvis-2.0/target/debug/jarvis-tauri

# Fallback auf Chrome (Legacy):
USE_TAURI=0 bash ~/Jarvis-2.0/scripts/launch-session.sh
```

### Cmd+Shift+J funktioniert nicht

```bash
# skhd läuft?
ps aux | grep skhd

# Falls nein:
skhd --start-service

# skhd.log prüfen:
cat ~/.skhd/skhd.log | tail -20

# ~/.skhdrc Syntax?
cat ~/.skhdrc | grep "jarvis"
```

---

## Nützliche Commands

```bash
# ===== STATUS =====
launchctl list | grep "jarvis.v2"           # Service Status
lsof -i :8340 -i :8341 -i :8342             # Ports prüfen
curl http://localhost:8340/ | head -1       # Server OK?

# ===== RESTART =====
pkill -f "server.py"                        # jarvis-core neu starten
pkill -f "services/jarvis-audio"            # jarvis-audio neu starten
pkill -f "services/jarvis-ha"               # jarvis-ha neu starten
pkill -f "speech_input.py"                  # Speech Input neu starten

# ===== LOGS =====
tail -f ~/Library/Logs/jarvis-v2/server.log    # Core logs
tail -f ~/Library/Logs/jarvis-v2/audio.log     # Audio logs
tail -f ~/Library/Logs/jarvis-v2/ha.log        # Dashboard logs
tail -f ~/Library/Logs/jarvis-v2/speech.log    # Speech logs
tail -f ~/Library/Logs/jarvis-v2/*.log         # Alle logs

# ===== BROWSER =====
open http://localhost:8340                  # HUD
open http://localhost:8340/config           # Config UI
open http://localhost:8340/health           # Health Monitor

# ===== ENTWICKLUNG =====
bash scripts/start-dev.sh                   # Alle Services lokal starten
bash scripts/stop-dev.sh                    # Alle Services stoppen
bash scripts/launch-session.sh              # Tauri + Services starten (Default)
USE_TAURI=0 bash scripts/launch-session.sh  # Chrome Kiosk (Legacy-Fallback)
```

---

**Fragen? Schau dir die Logs an oder öffne ein Issue auf GitHub!**

Viel Spaß mit Jarvis 2.0! 🎉
