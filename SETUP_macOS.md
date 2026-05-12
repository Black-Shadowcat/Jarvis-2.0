# JARVIS Setup (macOS)

Dein persönlicher KI-Sprachassistent — optimiert für macOS.

---

## Empfohlene Vorgehensweise

**VS Code + Claude Code** ist der schnellste Weg:

1. Repo klonen: `git clone https://github.com/Black-Shadowcat/jarvis-voice-assistant`
2. Ordner in VS Code öffnen
3. Claude Code starten (`Cmd+Shift+C` oder Terminal → `claude`)
4. Tippe: **„Richte Jarvis ein"**

Claude Code liest diese Datei und führt dich interaktiv durch den kompletten Setup.

---

## Bevor du anfängst — API Keys besorgen

Claude Code wird dich nach diesen Keys fragen. Besorge sie vorab:

| Service | Wo | Pflicht | Kosten |
|---|---|---|---|
| **Anthropic** (Claude Haiku) | console.anthropic.com | ✅ | ~$0.25 / 1M Tokens |
| **ElevenLabs** (Stimme) | elevenlabs.io → My Voices | ✅ | ab ~5 $/Monat (Starter nötig) |
| **Kachelmann** (Wetter) | kachelmannwetter.com/api | ⚡ | kostenpflichtig |
| **Home Assistant** Token | HA → Profil → Long-Lived Access Tokens | ⚡ | Nur wenn HA vorhanden |

> **ElevenLabs Voice ID:** Nach dem Login unter *My Voices* oder *Voice Library* — die ID steht in der URL oder unter Voice Settings.

---

---

# Für Claude Code — Interaktiver Setup-Ablauf

> Du bist Claude Code und der Nutzer hat „Richte Jarvis ein" oder ähnliches gesagt.
> Führe die folgenden Schritte der Reihe nach aus. Stelle Fragen einzeln, warte auf Antwort, dann weiter.
> Gib nach jedem Schritt kurzes Feedback was du getan hast.

---

## Schritt 1: Voraussetzungen prüfen

Prüfe und installiere falls nötig:

```bash
# Python 3.11
/opt/homebrew/bin/python3.11 --version

# Google Chrome
ls "/Applications/Google Chrome.app" 2>/dev/null && echo "OK" || echo "FEHLT"
```

Falls Python 3.11 fehlt → installieren:
```bash
brew install python@3.11
```

Falls Chrome fehlt → den Nutzer bitten Chrome zu installieren (google.com/chrome).

---

## Schritt 2: Nutzer-Profil erfragen

Stelle diese Fragen **einzeln nacheinander**:

1. **„Wie heißt du?"** → `user_name` (z.B. „Matthias")
2. **„Wie soll Jarvis dich ansprechen?"** → `user_address`
   - Männlich: „Sir", „Chef", „Boss", „Kapitän"
   - Weiblich: „Ms. Schmidt", „Mrs. Müller", „Miss Brown", „Madam"
3. **„In welcher Stadt wohnst du?"** → `city` (z.B. „Hamburg")
4. **„Was sind deine GPS-Koordinaten?"** → `lat` / `lon`
   - Tipp: maps.google.com → rechtsklick auf Standort → Koordinaten kopieren
   - Oder: „Ich schau das für [Stadt] nach" → du kannst typische Koordinaten vorschlagen
5. **„Hast du Obsidian? Falls ja, was ist der Pfad zu deiner Inbox?"** → `obsidian_inbox_path`
   - Typisch: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/<VaultName>/01 Inbox`
   - Optional — kann leer bleiben

---

## Schritt 3: API Keys erfragen

Stelle diese Fragen **einzeln**, erkläre kurz wozu der Key dient:

1. **Anthropic API Key** (Pflicht — Jarvis' Gehirn)
   - Format: beginnt mit `sk-ant-`
   - Hole ihn: console.anthropic.com → API Keys

2. **ElevenLabs API Key** (Pflicht — Jarvis' Stimme)
   - Format: beginnt mit `sk_`
   - Hole ihn: elevenlabs.io → Profile → API Keys

3. **ElevenLabs Voice ID** (Pflicht — welche Stimme)
   - elevenlabs.io → My Voices → Voice auswählen → ID kopieren
   - Alternativ: nach dem Start in der Config UI auswählen (dann `YOUR_VOICE_ID` lassen und später setzen)
   - Frage nach dem **Namen** der Stimme (z.B. „Felix Serenitas") — für voice.json

4. **Kachelmann Wetter API Key** (Optional — für präzises lokales Wetter)
   - kachelmannwetter.com/api → Account erstellen (kostenpflichtig)
   - Ohne Key: kein Wetter in der Begrüßung

5. **Home Assistant** (Optional — für Lichtsteuerung, Kalender, Wetterdaten)
   - **URL**: z.B. `http://10.0.0.190:8123`
   - **Token**: HA → Profil → ganz unten → Long-Lived Access Tokens → Token erstellen

---

## Schritt 4: config.json erstellen

```bash
cp config.example.json config.json
```

Trage alle gesammelten Werte ein:

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

> `workspace_path` = absoluter Pfad zum geklonten Ordner, z.B. `/Users/matthias/jarvis-voice-assistant V_2.1`

---

## Schritt 5: voice.json erstellen

```bash
cp voice.example.json voice.json
```

Trage die Voice ID und den Namen ein:

```json
{
  "active_voice_id": "<Voice ID>",
  "voices": [
    {"name": "<Name der Stimme>", "voice_id": "<Voice ID>"}
  ]
}
```

> Falls der Nutzer noch keine Voice ID hat: `YOUR_VOICE_ID` stehen lassen — nach dem Start in der Config UI unter **⚙ Verwalten** ergänzen.

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

## Schritt 8: LaunchAgents prüfen und laden

Die Plist-Dateien müssen auf den korrekten Projektpfad zeigen:

```bash
# Vorhandene LaunchAgents prüfen
ls ~/Library/LaunchAgents/com.jarvis.*.plist 2>/dev/null || echo "Keine vorhanden"
```

Falls vorhanden — Pfade prüfen und ggf. anpassen. Falls nicht vorhanden — mit dem Nutzer klären ob Auto-Start gewünscht ist.

```bash
# Laden
launchctl load ~/Library/LaunchAgents/com.jarvis.server.plist
launchctl load ~/Library/LaunchAgents/com.jarvis.session.plist
launchctl load ~/Library/LaunchAgents/com.jarvis.wake.plist

# Status prüfen
launchctl list | grep jarvis
```

---

## Schritt 9: macOS Berechtigungen

Erinnere den Nutzer an folgende Berechtigungen in **Systemeinstellungen → Datenschutz & Sicherheit**:

| Berechtigung | Wofür | Pflicht |
|---|---|---|
| **Mikrofon** | Spracherkennung im Browser | ✅ |
| **Bildschirmaufnahme** | „Was siehst du?" Feature | ⚡ |
| **Bedienungshilfen** | Hotkey `Cmd+Shift+J` | ⚡ |

Chrome und Terminal jeweils hinzufügen.

---

## Abschluss

Setup fertig! Sage dem Nutzer:

- **`Cmd+Shift+J`** → startet Jarvis komplett (Server + Chrome + Apps)
- **`http://localhost:8340`** → Jarvis HUD direkt im Browser
- **`http://localhost:8340/config`** → Config UI (Einstellungen, Voices, Apps)
- **Server-Log:** `tail -f /tmp/jarvis-server.log`
- **Jarvis starten:** sag „Jarvis activate"

---

---

# Referenz

## Was Jarvis kann

- `Cmd+Shift+J` → komplettes Arbeits-Setup startet automatisch
- Sprachsteuerung auf Deutsch
- Begrüßung mit Wetter, Aufgaben und Kalender
- Browser steuern (suchen, Seiten öffnen, Seite vorlesen)
- Bildschirm analysieren via Claude Vision
- Lichter steuern via Home Assistant
- Apple Reminders verwalten (lesen, hinzufügen, abhaken)
- Notizen direkt in Obsidian Inbox schreiben/lesen/löschen
- iCloud Mails lesen
- Kalendertermine via Home Assistant CalDAV
- Mic-Mute-Button in der macOS Menüleiste

---

## Alle Sprach-Actions

| Spracheingabe (Beispiele) | Was passiert |
|---|---|
| „Suche nach...", „Was ist..." | DuckDuckGo + erste Seite lesen |
| „Öffne google.com" | URL im Browser öffnen |
| „Öffne Mail / VS Code / Obsidian" | macOS App starten |
| „Was siehst du?", „Schau auf den Bildschirm" | Screenshot + Claude Vision |
| „Aktuelle Nachrichten" | Weltnachrichten laden |
| „Erinnere mich an...", „Füge hinzu..." | Apple Reminders Inbox |
| „Erledigt: Stichwort" | Reminder abhaken |
| „Was steht an?", „Aufgaben?" | Reminders live laden |
| „Meine Mails", „Mail von..." | Ungelesene Mails / Inhalt |
| „Termine heute / diese Woche" | Kalender via Home Assistant |
| „Licht an", „Wohnzimmer 50%", „Alles aus" | Home Assistant Lichter |
| „Notiere...", „Merke dir..." | Markdown in Obsidian Inbox |
| „Welche Notizen hast du?" | Alle Inbox-Notizen vorlesen |
| „Erledigt: Notiz-Stichwort" | Obsidian Notiz löschen |

---

## Projektstruktur

```
jarvis-voice-assistant/
├── server.py              # FastAPI Backend — Hauptlogik
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
├── frontend/
│   ├── index.html         # JARVIS HUD (Hauptansicht)
│   ├── config.html        # Config UI
│   ├── config.js          # Config UI Logik
│   ├── main.js            # Speech Recognition (nicht anfassen!)
│   └── style.css          # Dark/Light Theme
└── scripts/
    ├── launch-session.sh  # Vollständiger Start
    ├── mic-mute-menubar.py
    └── wake-monitor.py    # Wake-from-Sleep → /api/wake
```

---

## LaunchAgents

| Plist | Funktion |
|---|---|
| `com.jarvis.server.plist` | Server KeepAlive (startet bei Absturz neu) |
| `com.jarvis.session.plist` | Chrome + Apps beim Login (wartet auf Dock+Finder) |
| `com.jarvis.wake.plist` | Wake-from-Sleep Monitor |

```bash
# Status
launchctl list | grep jarvis

# Neu laden
launchctl unload ~/Library/LaunchAgents/com.jarvis.server.plist
launchctl load   ~/Library/LaunchAgents/com.jarvis.server.plist
```

---

## Troubleshooting

**Server startet nicht / Port belegt**
```bash
lsof -i :8340
kill <PID>
/opt/homebrew/bin/python3.11 server.py
```

**Jarvis spricht nicht (TTS Fehler)**
→ ElevenLabs Key in Config UI testen. Voice ID in `voice.json` prüfen.

**Chrome öffnet sich nicht**
```bash
./scripts/launch-session.sh
cat /tmp/jarvis-chrome.log
```

**Kein Wetter**
→ Kachelmann API Key fehlt oder ungültig. Ohne Key: kein Wetter.

**Home Assistant antwortet nicht**
→ `ha_url` und `ha_token` in Config UI prüfen. Token muss Long-Lived Access Token sein.

**Obsidian Notiz wird nicht erstellt**
→ `obsidian_inbox_path` muss absoluter Pfad sein und der Ordner muss existieren.

**Screen Capture funktioniert nicht**
→ Systemeinstellungen → Datenschutz → Bildschirmaufnahme → Terminal hinzufügen.

**`rumps` nicht gefunden (Mic-Mute Button)**
```bash
/opt/homebrew/bin/python3.11 -m pip install rumps
```

**Logs**
```bash
tail -f /tmp/jarvis-server.log
```

---

## Nützliche Befehle

```bash
# Server neu starten (launchd startet automatisch neu)
pkill -f "server.py"

# Jarvis komplett neu starten
pkill -f "jarvis-chrome-profile"
bash "scripts/launch-session.sh"

# Config UI
open http://localhost:8340/config

# Server-Log
tail -f /tmp/jarvis-server.log
```
