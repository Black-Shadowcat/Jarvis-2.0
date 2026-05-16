# JARVIS Setup (macOS) — Jarvis 2.0 v1.0.0

Dein persönlicher KI-Sprachassistent mit Sprachsteuerung — optimiert für macOS Apple Silicon.

**v1.0.0 — Production Ready:** Vollständiger Neubau mit 3 unabhängigen Microservices für höchste Zuverlässigkeit und Skalierbarkeit.

---

## Empfohlene Vorgehensweise

**VS Code + Claude Code** ist der schnellste Weg:

1. Repo klonen: `git clone https://github.com/Black-Shadowcat/Jarvis-2.0.git Jarvis-2.0`
2. Ordner in VS Code öffnen
3. Claude Code starten (`Cmd+Shift+C` oder Terminal → `claude`)
4. Tippe: **„Richte Jarvis ein"**

Claude Code liest diese Datei und führt dich interaktiv durch den kompletten Setup.

---

## Bevor du anfängst — API Keys besorgen

| Service | Wo | Pflicht | Kosten |
|---|---|---|---|
| **Anthropic** (Claude Haiku) | console.anthropic.com | ✅ | ~$0.25 / 1M Tokens |
| **ElevenLabs** (Stimme) | elevenlabs.io → My Voices | ✅ | ab ~5 $/Monat (Starter nötig) |
| **Kachelmann** (Wetter) | kachelmannwetter.com/api | ⚡ | kostenpflichtig |
| **Home Assistant** Token | HA → Profil → Long-Lived Access Tokens | ⚡ | Nur wenn HA vorhanden |

> **Kein STT-Key nötig** — Whisper läuft lokal auf Apple Silicon. Keine Cloud-Kosten für Spracherkennung.

---

---

# Für Claude Code — Interaktiver Setup-Ablauf

> Du bist Claude Code und der Nutzer hat „Richte Jarvis ein" oder ähnliches gesagt.
> Führe die folgenden Schritte der Reihe nach aus. Stelle Fragen einzeln, warte auf Antwort, dann weiter.
> Gib nach jedem Schritt kurzes Feedback was du getan hast.

---

## Schritt 1: Voraussetzungen prüfen

```bash
# Python 3.11
/opt/homebrew/bin/python3.11 --version

# Google Chrome
ls "/Applications/Google Chrome.app" 2>/dev/null && echo "OK" || echo "FEHLT"
```

Falls Python 3.11 fehlt:
```bash
brew install python@3.11
```

Falls Chrome fehlt → den Nutzer bitten Chrome zu installieren (google.com/chrome).

---

## Schritt 2: Nutzer-Profil erfragen

Stelle diese Fragen **einzeln nacheinander**:

1. **„Wie heißt du?"** → `user_name`
2. **„Wie soll Jarvis dich ansprechen?"** → `user_address`
   - Männlich: „Sir", „Chef", „Boss", „Kapitän"
   - Weiblich: „Ms. Schmidt", „Mrs. Müller", „Miss Brown", „Madam"
3. **„In welcher Stadt wohnst du?"** → `city`
4. **„Was sind deine GPS-Koordinaten?"** → `lat` / `lon`
   - Tipp: maps.google.com → rechtsklick auf Standort → Koordinaten kopieren
5. **„Hast du Obsidian? Falls ja, was ist der Pfad zu deiner Inbox?"** → `obsidian_inbox_path`
   - Typisch: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/<VaultName>/01 Inbox`
   - Optional — kann leer bleiben

---

## Schritt 3: API Keys erfragen

1. **Anthropic API Key** (Pflicht)
   - Format: beginnt mit `sk-ant-`
   - Hole ihn: console.anthropic.com → API Keys

2. **ElevenLabs API Key** (Pflicht)
   - Format: beginnt mit `sk_`
   - Hole ihn: elevenlabs.io → Profile → API Keys

3. **ElevenLabs Voice ID** (Pflicht)
   - elevenlabs.io → My Voices → Voice auswählen → ID kopieren
   - Alternativ: nach dem Start in der Config UI auswählen

4. **Kachelmann Wetter API Key** (Optional)

5. **Home Assistant** (Optional)
   - **URL**: z.B. `http://10.0.0.190:8123`
   - **Token**: HA → Profil → Long-Lived Access Tokens erstellen

---

## Schritt 4: config.json erstellen

```bash
cp config.example.json config.json
```

```json
{
  "anthropic_api_key": "<Anthropic Key>",
  "elevenlabs_api_key": "<ElevenLabs Key>",
  "user_name": "<Name>",
  "user_address": "<Anrede>",
  "city": "<Stadt>",
  "lat": <Breitengrad>,
  "lon": <Längengrad>,
  "kachelmann_api_key": "<Key oder leer>",
  "ha_url": "<HA URL oder leer>",
  "ha_token": "<HA Token oder leer>",
  "ha_enabled": true,
  "obsidian_inbox_path": "<Pfad oder leer>",
  "workspace_path": "<absoluter Pfad zum Projektordner>",
  "wake_greeting_enabled": true
}
```

> `workspace_path` = absoluter Pfad zum geklonten Ordner, z.B. `/Users/matthias/Jarvis-2.0`

---

## Schritt 5: voice.json erstellen

```bash
cp voice.example.json voice.json
```

```json
{
  "active_voice_id": "<Voice ID>",
  "voices": [
    {"name": "<Name der Stimme>", "voice_id": "<Voice ID>"}
  ]
}
```

---

## Schritt 6: Dependencies installieren

```bash
/opt/homebrew/bin/python3.11 -m pip install -r requirements.txt
/opt/homebrew/bin/python3.11 -m playwright install chromium
```

---

## Schritt 7: Server testen

```bash
/opt/homebrew/bin/python3.11 server.py
```

Prüfe ob der Server läuft:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8340/
# → 200 = OK
```

API Keys testen (empfohlen):
```bash
open http://localhost:8340/config
# → Testen-Buttons bei Anthropic und ElevenLabs klicken
```

---

## Schritt 8: LaunchAgents laden (v0.4.0+: 3 Microservices)

Ab v0.4.0 laufen **drei Microservices parallel**. Alle werden als LaunchAgents mit KeepAlive konfiguriert.

```bash
# Status vor dem Setup prüfen
launchctl list | grep "jarvis.v2"

# Alle Services laden (werden bei Absturz automatisch neu gestartet)
launchctl load ~/Library/LaunchAgents/com.jarvis.v2.server.plist      # jarvis-core (8340)
launchctl load ~/Library/LaunchAgents/com.jarvis.v2.audio.plist       # jarvis-audio (8341)
launchctl load ~/Library/LaunchAgents/com.jarvis.v2.ha.plist          # jarvis-ha (8342)
launchctl load ~/Library/LaunchAgents/com.jarvis.v2.speech.plist      # Speech Input
launchctl load ~/Library/LaunchAgents/com.jarvis.v2.session.plist     # Browser Session
launchctl load ~/Library/LaunchAgents/com.jarvis.v2.wake.plist        # Wake Monitor
launchctl load ~/Library/LaunchAgents/com.jarvis.v2.supervisor.plist  # Health Monitor

# Status prüfen (alle sollten laufen)
sleep 2 && launchctl list | grep "jarvis.v2"

# Ports prüfen (alle 3 Services sollten binden)
lsof -i :8340 -i :8341 -i :8342 | grep LISTEN
```

**Logs für die 3 Services:**
```bash
tail -f ~/Library/Logs/jarvis-v2/server.log    # jarvis-core
tail -f ~/Library/Logs/jarvis-v2/audio.log     # jarvis-audio
tail -f ~/Library/Logs/jarvis-v2/ha.log        # jarvis-ha
```

---

## Schritt 9: macOS Berechtigungen

| Berechtigung | Wofür | Pflicht |
|---|---|---|
| **Bedienungshilfen** | speech_input.py (Wake Word + F19 PTT) | ✅ |
| **Mikrofon** | speech_input.py (Audioaufnahme) | ✅ |
| **Bildschirmaufnahme** | „Was siehst du?" Feature | ⚡ |

In **Systemeinstellungen → Datenschutz & Sicherheit** eintragen:
- **Bedienungshilfen**: Terminal (und ggf. Python) hinzufügen
- **Mikrofon**: Terminal hinzufügen
- **Bildschirmaufnahme**: Terminal hinzufügen (optional)

> **Wichtig:** Ohne Bedienungshilfen-Berechtigung kann `speech_input.py` weder F19 erkennen noch das Aktivierungswort abhören.

---

## Abschluss

Setup fertig! Sag dem Nutzer:

**Browser URLs:**
- **`http://localhost:8340`** → Jarvis HUD + Chat
- **`http://localhost:8340/config`** → Config UI (API Keys, Voices, Apps)
- **`http://localhost:8340/handbuch`** → Benutzerhandbuch (Deutsch/English)
- **`http://localhost:8340/health`** → Health Monitor (System Status)

**Service Status prüfen:**
- **`curl http://localhost:8340/`** → jarvis-core (should return HTML)
- **`curl http://localhost:8341/health`** → jarvis-audio (should return JSON)
- **`curl http://localhost:8342/health`** → jarvis-ha (should return JSON)

**Logs:**
- **Core:** `tail -f ~/Library/Logs/jarvis-v2/server.log`
- **Audio:** `tail -f ~/Library/Logs/jarvis-v2/audio.log`
- **Dashboard:** `tail -f ~/Library/Logs/jarvis-v2/ha.log`
- **Speech Input:** `tail -f ~/Library/Logs/jarvis-v2/speech.log`

**Jarvis aktivieren:**
- Sag **„Jarvis, …"** + Befehl (Wake Word, offline)
- Oder drücke **F19** (Push-to-Talk)
- Oder verwende **Cmd+Shift+J** → startet alle Services und öffnet Browser

---

---

# Referenz

## Was Jarvis kann

- Aktivierungswort „Jarvis" → hands-free Steuerung
- F19 Push-to-Talk
- Lokale Spracherkennung (mlx-whisper, kein Cloud-STT)
- Begrüßung mit Wetter, Aufgaben und Kalender
- Browser steuern (suchen, Seiten öffnen, Seite vorlesen)
- Bildschirm analysieren via Claude Vision
- Lichter steuern via Home Assistant
- Apple Reminders verwalten (lesen, hinzufügen, abhaken)
- Notizen direkt in Obsidian Inbox schreiben/lesen/löschen
- iCloud Mails lesen
- Kalendertermine via Home Assistant CalDAV

---

## Aktivierungswort — Wie es funktioniert

```
Du sprichst → RMS-VAD erkennt Stimme → blauer Ring leuchtet
→ Whisper transkribiert Snippet (lokal)
→ „jarvis" im Text?
  Ja + Befehl im gleichen Satz → Befehl direkt senden
  Ja, nur „Jarvis" → Jarvis activate → Auto-Listen wartet auf Folgebefehl
  Nein → Ring zurück zu idle
```

**Kein „Hey" nötig.** Kurze Pause nach „Jarvis" ist OK — Jarvis wartet auf den Folgebefehl (6s Auto-Listen mit Stille-Erkennung).

---

## Alle Sprach-Actions

| Spracheingabe (Beispiele) | Was passiert |
|---|---|
| „Jarvis, suche nach...", „Jarvis, was ist..." | DuckDuckGo + erste Seite lesen |
| „Jarvis, öffne google.com" | URL im Browser öffnen |
| „Jarvis, öffne Mail / VS Code / Obsidian" | macOS App starten |
| „Jarvis, was siehst du?" | Screenshot + Claude Vision |
| „Jarvis, aktuelle Nachrichten" | Weltnachrichten laden |
| „Jarvis, erinnere mich an..." | Apple Reminders Inbox |
| „Jarvis, was steht an?" | Reminders live laden |
| „Jarvis, meine Mails" | Ungelesene Mails vorlesen |
| „Jarvis, Termine heute" | Kalender via Home Assistant |
| „Jarvis, Licht an", „Wohnzimmer 50%" | Home Assistant Lichter |
| „Jarvis, notiere..." | Markdown in Obsidian Inbox |

---

## Projektstruktur (v1.0.0: 3 Microservices)

```
Jarvis-2.0/
├── server.py                   # jarvis-core (Port 8340) — LLM Orchestration
├── speech_input.py             # mlx-whisper STT + Wake Word + F19 PTT
├── browser_tools.py            # Playwright Browser-Steuerung
├── screen_capture.py           # Screenshot + Claude Vision
├── requirements.txt            # Python Dependencies (Core)
├── config.json                 # Deine Config (gitignored)
├── config.example.json         # Config Template
├── voice.json                  # Voice-Bibliothek (gitignored)
├── voice.example.json          # Voice Template
├── version.json                # Versionsnummer (1.0.0)
├── CLAUDE.md                   # Anweisungen für Claude Code
├── SETUP_macOS.md              # Diese Datei
├── README.md                   # Dokumentation mit Architektur-Diagramm
├── CHANGELOG.md                # Version History
│
├── services/                   # 🆕 v0.4.0: Microservices
│   ├── jarvis-audio/           # Port 8341 — TTS Synthese
│   │   ├── main.py             # ElevenLabs TTS Microservice
│   │   └── requirements.txt    # Audio-Dependencies (FastAPI, httpx)
│   │
│   └── jarvis-ha/              # Port 8342 — Dashboard & Home Assistant
│       ├── main.py             # HA Integration Microservice
│       └── requirements.txt    # HA-Dependencies (FastAPI, httpx)
│
├── frontend/
│   ├── index.html              # JARVIS HUD + Chat (Kiosk)
│   ├── config.html             # Config UI
│   ├── handbuch.html           # Benutzerhandbuch
│   └── i18n/
│       ├── de.json             # Deutsche UI-Labels
│       └── en.json             # English UI-Labels
│
├── scripts/
│   ├── launch-session.sh       # Chrome im Kiosk-Modus starten
│   ├── start-dev.sh            # Starte alle Services lokal
│   ├── stop-dev.sh             # Stoppe alle Services
│   └── wake-monitor.py         # Wake-from-Sleep → /api/wake
│
├── systems/
│   └── daily_brief.py          # Daily Brief Memory System
│
└── data/                       # (gitignored)
    └── daily_brief_memory.json # Tagesgedächtnis
```

---

## LaunchAgents (v1.0.0)

| Plist | Port | Funktion |
|---|---|---|
| `com.jarvis.v2.server.plist` | 8340 | **jarvis-core** — LLM & Orchestration |
| `com.jarvis.v2.audio.plist` | 8341 | **jarvis-audio** — TTS Synthese |
| `com.jarvis.v2.ha.plist` | 8342 | **jarvis-ha** — Dashboard & Home Assistant |
| `com.jarvis.v2.speech.plist` | — | **speech_input.py** — Wake Word + F19 PTT |
| `com.jarvis.v2.session.plist` | — | **Chrome Browser** — Kiosk beim Login |
| `com.jarvis.v2.wake.plist` | — | **wake-monitor.py** — Wake-from-Sleep Detection |
| `com.jarvis.v2.supervisor.plist` | — | **supervisor.py** — Health Monitor UI |

**Service-Architektur:**
```
User: "Jarvis, ..."
         ↓
   speech_input.py (Wake Word detection)
         ↓
   jarvis-core (8340) — LLM Brain
      ↙         ↘
   jarvis-audio   jarvis-ha
   (8341)         (8342)
   TTS           Dashboard/HA
```

**Befehle:**
```bash
# Status aller Services
launchctl list | grep "jarvis.v2"

# Einzelnen Service neu laden
launchctl unload ~/Library/LaunchAgents/com.jarvis.v2.server.plist
launchctl load   ~/Library/LaunchAgents/com.jarvis.v2.server.plist

# Alle Logs live
tail -f ~/Library/Logs/jarvis-v2/*.log

# Ports prüfen
lsof -i :8340 -i :8341 -i :8342
```

---

## Troubleshooting (v1.0.0)

**Services starten nicht / Ports belegt**
```bash
# Alle Jarvis-Prozesse killen
pkill -9 -f "jarvis"
sleep 2

# Ports prüfen
lsof -i :8340 -i :8341 -i :8342

# Services neu laden
launchctl load ~/Library/LaunchAgents/com.jarvis.v2.server.plist
launchctl load ~/Library/LaunchAgents/com.jarvis.v2.audio.plist
launchctl load ~/Library/LaunchAgents/com.jarvis.v2.ha.plist
sleep 2

# Ports sollten jetzt binden
lsof -i :8340 -i :8341 -i :8342 | grep LISTEN
```

**jarvis-audio antwortet nicht (Port 8341)**
```bash
curl http://localhost:8341/health
# Sollte: {"status":"healthy","service":"jarvis-audio",...}
# Logs: tail -f ~/Library/Logs/jarvis-v2/audio.log
```

**jarvis-ha antwortet nicht (Port 8342)**
```bash
curl http://localhost:8342/health
# Sollte: {"status":"healthy","service":"jarvis-ha",...}
# Logs: tail -f ~/Library/Logs/jarvis-v2/ha.log
# Prüfe: Home Assistant URL, Token, Obsidian Pfad in config.json
```

**Wake Word / F19 funktioniert nicht**
```bash
tail -f ~/Library/Logs/jarvis-v2/speech.log
# → Bedienungshilfen-Berechtigung prüfen
# Systemeinstellungen → Datenschutz → Bedienungshilfen → Terminal hinzufügen
```

**Jarvis spricht nicht (TTS Fehler)**
```bash
curl http://localhost:8341/health
# Prüfe ElevenLabs Key + Voice ID in config.json und voice.json
# Teste TTS in Config UI: http://localhost:8340/config
```

**Chrome öffnet sich nicht**
```bash
bash ~/Jarvis-2.0/scripts/launch-session.sh
```

**Dashboard lädt nicht (Mail/Tasks/Wetter leer)**
- Prüfe `curl http://localhost:8342/api/get_mails_unread`
- Mail.app muss offen sein (AppleScript-Zugriff)
- Prüfe Reminders.app Zugriff
- Kachelmann Key für Wetter? (optional)

**Screen Capture funktioniert nicht**
→ Systemeinstellungen → Datenschutz → Bildschirmaufnahme → Terminal hinzufügen.

---

## Nützliche Befehle (v1.0.0)

```bash
# ========== STOPP / START ==========
# Alle Services stoppen
pkill -9 -f "jarvis"

# Einzelnen Service neu starten (launchd restarts automatisch)
pkill -f "server.py"          # jarvis-core neu starten
pkill -f "services/jarvis-audio"  # jarvis-audio neu starten
pkill -f "services/jarvis-ha"     # jarvis-ha neu starten
pkill -f "speech_input.py"    # Speech Input neu starten

# ========== STATUS ==========
# Alle Ports prüfen
lsof -i :8340 -i :8341 -i :8342

# Service Health prüfen
curl http://localhost:8340/ | head -1
curl http://localhost:8341/health | jq .
curl http://localhost:8342/health | jq .

# ========== LOGS ==========
# Live-Logs aller Services
tail -f ~/Library/Logs/jarvis-v2/*.log

# Nur einen Service loggen
tail -f ~/Library/Logs/jarvis-v2/server.log
tail -f ~/Library/Logs/jarvis-v2/audio.log
tail -f ~/Library/Logs/jarvis-v2/ha.log

# ========== BROWSER ==========
# HUD öffnen
open http://localhost:8340

# Config UI
open http://localhost:8340/config

# Health Monitor
open http://localhost:8340/health

# ========== HOTKEY ==========
# Cmd+Shift+J: Startet launch-session.sh (alle Services + Browser)
# Wird durch skhd-Config in ~/.skhdrc definiert
# Manuell ausführen:
bash ~/Jarvis-2.0/scripts/launch-session.sh
```
