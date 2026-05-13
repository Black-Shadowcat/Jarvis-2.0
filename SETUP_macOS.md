# JARVIS Setup (macOS) — jarvis-whisper

Dein persönlicher KI-Sprachassistent — optimiert für macOS Apple Silicon.

---

## Empfohlene Vorgehensweise

**VS Code + Claude Code** ist der schnellste Weg:

1. Repo klonen: `git clone https://github.com/Black-Shadowcat/jarvis-whisper.git jarvis-v3`
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

> `workspace_path` = absoluter Pfad zum geklonten Ordner, z.B. `/Users/matthias/jarvis-v3`

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

## Schritt 8: LaunchAgents laden

Die Plist-Dateien liegen im Repo unter `launchagents/` und müssen nach `~/Library/LaunchAgents/` kopiert und auf den korrekten Projektpfad angepasst werden.

```bash
# Ins LaunchAgents-Verzeichnis kopieren
cp launchagents/com.jarvis.whisper.server.plist ~/Library/LaunchAgents/
cp launchagents/com.jarvis.whisper.speech.plist ~/Library/LaunchAgents/
cp launchagents/com.jarvis.whisper.session.plist ~/Library/LaunchAgents/

# Pfade in den Plists anpassen (falls nötig)
# Lade anschließend
launchctl load ~/Library/LaunchAgents/com.jarvis.whisper.server.plist
launchctl load ~/Library/LaunchAgents/com.jarvis.whisper.speech.plist
launchctl load ~/Library/LaunchAgents/com.jarvis.whisper.session.plist

# Status prüfen
launchctl list | grep jarvis.whisper
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

- **`~/Applications/Jarvis starten.app`** → manueller Start per Doppelklick
- **`http://localhost:8340`** → Jarvis HUD im Browser
- **`http://localhost:8340/config`** → Config UI (Einstellungen, Voices, Apps)
- **Server-Log:** `tail -f ~/Library/Logs/jarvis-whisper/server.log`
- **Spracheingabe-Log:** `tail -f ~/Library/Logs/jarvis-whisper/speech.log`
- **Jarvis aktivieren:** Sag „Jarvis" + Befehl oder drücke F19

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

## Projektstruktur

```
jarvis-whisper/
├── server.py              # FastAPI Backend — Hauptlogik (Port 8340)
├── speech_input.py        # mlx-whisper STT + Wake Word + F19 PTT
├── browser_tools.py       # Playwright Browser-Steuerung
├── screen_capture.py      # Screenshot + Claude Vision
├── requirements.txt       # Python Dependencies
├── config.json            # Deine Config (gitignored)
├── config.example.json    # Template
├── voice.json             # Deine Voice-Bibliothek (gitignored)
├── voice.example.json     # Voice Template
├── version.json           # Versionsnummer (Single Source of Truth)
├── CLAUDE.md              # Anweisungen für Claude Code
├── SETUP_macOS.md         # Diese Datei
├── launchagents/
│   ├── com.jarvis.whisper.server.plist
│   ├── com.jarvis.whisper.speech.plist
│   └── com.jarvis.whisper.session.plist
├── frontend/
│   ├── index.html         # JARVIS HUD (Kiosk, Port 8340)
│   ├── config.html        # Config UI
│   ├── config.js          # Config UI Logik
│   ├── handbuch.html      # Benutzerhandbuch
│   └── i18n/
│       ├── de.json
│       └── en.json
└── scripts/
    ├── launch-session.sh  # Chrome im Kiosk-Modus starten
    └── wake-monitor.py    # Wake-from-Sleep → /api/wake
```

---

## LaunchAgents

| Plist | Funktion |
|---|---|
| `com.jarvis.whisper.server.plist` | Server KeepAlive (startet bei Absturz neu) |
| `com.jarvis.whisper.speech.plist` | speech_input.py KeepAlive (Wake Word + F19 PTT) |
| `com.jarvis.whisper.session.plist` | Chrome Kiosk beim Login |

```bash
# Status
launchctl list | grep jarvis.whisper

# Neu laden
launchctl unload ~/Library/LaunchAgents/com.jarvis.whisper.server.plist
launchctl load   ~/Library/LaunchAgents/com.jarvis.whisper.server.plist

# Logs
tail -f ~/Library/Logs/jarvis-whisper/server.log
tail -f ~/Library/Logs/jarvis-whisper/speech.log
```

---

## Troubleshooting

**Server startet nicht / Port belegt**
```bash
lsof -i :8340
kill <PID>
/opt/homebrew/bin/python3.11 server.py
```

**Wake Word / F19 funktioniert nicht**
```bash
tail -f ~/Library/Logs/jarvis-whisper/speech.log
# → Bedienungshilfen-Berechtigung prüfen
```

**Jarvis spricht nicht (TTS Fehler)**
→ ElevenLabs Key in Config UI testen. Voice ID in `voice.json` prüfen.

**Chrome öffnet sich nicht**
```bash
bash ~/jarvis-v3/scripts/launch-session.sh
```

**Kein Wetter**
→ Kachelmann API Key fehlt oder ungültig. Ohne Key: kein Wetter.

**Home Assistant antwortet nicht**
→ `ha_url` und `ha_token` in Config UI prüfen.

**Obsidian Notiz wird nicht erstellt**
→ `obsidian_inbox_path` muss absoluter Pfad sein und der Ordner muss existieren.

**Screen Capture funktioniert nicht**
→ Systemeinstellungen → Datenschutz → Bildschirmaufnahme → Terminal hinzufügen.

---

## Nützliche Befehle

```bash
# Server neu starten (launchd startet automatisch neu)
pkill -f "server.py"

# speech_input neu starten
pkill -f "speech_input.py"

# Jarvis komplett neu starten (Browser + alles)
bash ~/jarvis-v3/scripts/launch-session.sh

# Config UI
open http://localhost:8340/config

# Logs live
tail -f ~/Library/Logs/jarvis-whisper/server.log
tail -f ~/Library/Logs/jarvis-whisper/speech.log
```
