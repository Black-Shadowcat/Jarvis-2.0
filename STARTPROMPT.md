# JARVIS 2.0 — Startprompt für neue Sessions

> Diesen Text am Anfang jedes neuen Chats einfügen.
> Zuletzt aktualisiert: 2026-05-24 | Version: v2.0.3

---

## Deine Rolle

Du bist Claude Code und hilfst mir dabei, **Jarvis 2.0** — meinen persönlichen KI-Assistenten auf macOS — zu verbessern und Fehler zu beheben. Das Projekt läuft produktiv auf meinem Mac und wird täglich benutzt. Jede Änderung betrifft den laufenden Betrieb.

---

## Pflicht vor dem ersten Task: Obsidian lesen

**Bevor du mit irgendeiner Aufgabe beginnst**, lies folgende Dokumente in dieser Reihenfolge:

```
Vault (NUR dieser Ordner erlaubt):
/Users/matthiasschreiber/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidan/02 JARVIS 2.0/

1. 03 Projektdokumentation/01_CORE/CURRENT_STATE.md      ← Projektstatus, Version, aktuelle Bugs
2. 03 Projektdokumentation/01_CORE/BUG_TRACKER.md        ← Offene + gerade behobene Bugs
3. 03 Projektdokumentation/01_CORE/ANTI_PATTERNS.md      ← Was NIE tun (teuer bezahlt!)
4. 03 Projektdokumentation/05_SESSIONS/SESSION_18_HANDOVER.md  ← Letzte Session-Details
5. 02 JARVIS 2.0/01 Inbox/                               ← Aktuelle offene ToDos
```

---

## Projekt-Übersicht

**Jarvis 2.0** ist ein persönlicher KI-Assistent mit:
- Sprachsteuerung (Wake-Word "Jarvis" + F19 Push-to-Talk)
- Morgen- und Abend-Briefing (Mails, Kalender, Wetter, Aufgaben, News)
- Home-Assistant-Integration (Licht, Sensoren, Wetter)
- Native Tauri-App auf macOS (WKWebView, kein Chrome)

**Verzeichnis:** `/Users/matthiasschreiber/Jarvis-2.0`
**Branch:** `main`
**Version:** `v2.0.3`
**Letzter Commit:** `12d3c9a` (docs: README v2.0.3)

---

## Architektur

| Service | Port | Datei | Zweck |
|---------|------|-------|-------|
| jarvis-core | 8340 | `server.py` | FastAPI, LLM, WebSocket, Orchestrierung |
| jarvis-audio | 8341 | `services/jarvis-audio/` | ElevenLabs TTS, Chunking |
| jarvis-ha | 8342 | `services/jarvis-ha/main.py` | Mail, Tasks, Wetter, HA-Integration |
| speech_input | — | `speech_input.py` | Whisper STT, Wake-Word, F19 PTT |
| wake-monitor | — | `scripts/wake-monitor.py` | Sleep/Wake-Erkennung → /api/wake |
| supervisor | — | `supervisor.py` | Health-Check, Auto-Restart |

**Autostart:** macOS launchd — `~/Library/LaunchAgents/com.jarvis.v2.{server,speech,session,supervisor,wake}.plist`
**Logs:** `~/Library/Logs/jarvis-v2/`
**KI-Modell:** `claude-haiku-4-5-20251001`
**TTS:** ElevenLabs `eleven_turbo_v2_5`
**Tauri-App:** `~/Applications/Jarvis.app`

---

## Wichtige Invarianten (NICHT brechen)

- `index.html` ist die Haupt-UI — alles JS/CSS inline, kein externer Build-Step
- Immer `config.get("key", "")` statt `config["key"]`
- `speech_input.py` **NIE manuell starten** — nur via `launchctl` (KeepAlive → Duplikat)
- Vor jedem Neustart: `lsof -i :8340 -i :8341 -i :8342` + Browser-Tabs prüfen (Hall-Effekt!)
- `active_connections` = nur `/ws` Verbindungen (Tauri); `/ws/stt` liegt in `stt_connections`
- `record_morning_brief()` erst NACH erfolgreichem `_speak()` aufrufen
- `conversations.setdefault(session_id, [])` statt direktem Zugriff (Race Condition)

---

## Meine Arbeitsregeln (von mir eingefordert)

1. **Erklären vor Umsetzen** — Lösung beschreiben und meine Zustimmung einholen, bevor Code geändert wird. Keine eigenmächtigen Änderungen.
2. **System vollständig stoppen vor Tests** — Ports + Prozesse + Browser prüfen, nicht nur LaunchAgents.
3. **Keine manuellen Brief-Trigger** ohne explizite Aufforderung.
4. **Root Cause, nicht Symptom** — Keine Workarounds die Probleme verstecken (AP-005).
5. **Fix verifizieren** — Nach einem Fix messen/testen, nicht nur "Done" markieren (AP-004).
6. **Datum/Uhrzeit bewusst** — Nicht "gestern" sagen wenn "heute" gemeint ist. Kein Datums-Raten.

---

## Dokumentationspflicht nach JEDER Session (non-negotiable)

Am Ende **jeder** Session — egal wie klein die Änderung:

```
Obsidian-Pflichtdateien (in dieser Reihenfolge):

□ 05_SESSIONS/SESSION_XX_HANDOVER.md    ← neue Session-Datei anlegen
    - Bootstrap-Block (Pfade, Branch, Version, nächster Task)
    - Was wurde gemacht (Commits, Root Causes, Tests)
    
□ 01_CORE/BUG_TRACKER.md               ← neue/behobene Bugs eintragen
    - Format: ID | Prio | Bereich | Problem | Ursache | Lösung | Commit
    
□ 01_CORE/CURRENT_STATE.md             ← Header aktualisieren
    - Version, Latest Commit, Datum, aktive Features
    
□ 04_BUGS/BXXX_NAME.md                 ← für jeden neuen Bug eine eigene Datei
    - Problem, Ursache, Fix, Commit, betroffene Dateien
    
□ 07_RELEASES/vX.Y.Z-FINALIZATION.md   ← bei neuem Release-Tag

□ Git: alle Änderungen committed, Tag gesetzt falls Release
□ GitHub: Push + GitHub Release anlegen
□ README.md: Versionsnummer aktualisieren
```

**Obsidian-Pfad:**
```
/Users/matthiasschreiber/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidan/02 JARVIS 2.0/03 Projektdokumentation/
```

---

## Aktueller Stand (v2.0.3, 2026-05-24)

### Zuletzt behoben
| Bug | Details |
|-----|---------|
| B031 | Morgen-Brief Zombie-WS: `record_morning_brief()` vor `_speak()`, kein Audio geliefert → record-after-deliver, `hello`-Protokoll, proaktiver Trigger |
| B030 | Tasks-Titel Doppel-Escaping nach Cache-Expiry → `_tasks_raw_list` |
| B029 | Keine Begrüßung nach Reawake → Zwei unabhängige Cooldowns (Kernel/HIDIdle) |

### Neu in v2.0.3
- `_speak()` returns `bool` (delivered)
- `hello`-Protokoll: Client identifiziert frische Seite → Server bereinigt Zombies
- Proaktiver Brief-Trigger beim WS-Connect (kein `_wsIsFirst` nötig)
- `_tts_to_display()`: "20 Komma 1" → "20,1" im UI
- Temperatursensor: `sensor.thermometer_temperatur` (eigene Wetterstation)
- Mail INBOX-Filter: nur Posteingang, kein Archiv/Sent/Junk
- News-Checkbox: direktes Abhaken im Panel
- Morgen-Brief Startzeit: 04:00 Uhr

### Bekannte offene Punkte
| Punkt | Priorität |
|-------|-----------|
| Morgen-Brief Startzeit in `config.json` auslagern (aktuell hardcoded `hour < 4`) | Niedrig |
| `start-dev.sh` startet `wake` und `supervisor` LaunchAgents nicht automatisch | Niedrig |
| Langzeit-Test: Brief nach echtem nächtlichem Ruhezustand (v2.0.3 noch ungetestet über Nacht) | Mittel |

---

## Anti-Patterns (niemals wiederholen)

- **AP-001:** `tracemalloc.start()` in Production → 3.5 GB Memory-Explosion
- **AP-002:** User-Space-Locks für Race Conditions → nur `fcntl.flock()`
- **AP-003:** System-Prompt ohne Datum → LLM rät falsch
- **AP-004:** "Done" ohne Verifikation → C3-Desaster
- **AP-005:** Symptome statt Root Cause beheben
- **AP-006:** Dateien im Root des Doku-Ordners → Subordner benutzen
- **AP-007:** Whisper-Memory als Leak deuten → 3.5 GB nach erstem Transcribe ist NORMAL

Vollständig in: `01_CORE/ANTI_PATTERNS.md`

---

## Typische Befehle

```bash
# Server neu starten
launchctl kickstart -k gui/$(id -u)/com.jarvis.v2.server

# Alle Services stoppen
cd ~/Jarvis-2.0 && bash scripts/stop-dev.sh

# Ports prüfen (vor Neustart!)
lsof -i :8340 -i :8341 -i :8342

# Log beobachten
tail -f ~/Library/Logs/jarvis-v2/server.log

# Syntax-Check
/opt/homebrew/bin/python3.11 -m py_compile server.py

# Morning-Brief Memory zurücksetzen (Test)
python3 -c "import json; d=json.load(open('data/daily_brief_memory.json')); d['last_morning_brief']=None; json.dump(d,open('data/daily_brief_memory.json','w'),indent=2)"

# HA-Sensor testen
curl -s -H "Authorization: Bearer $(python3 -c \"import json; print(json.load(open('config.json'))['ha_token'])\")" \
  "$(python3 -c \"import json; print(json.load(open('config.json'))['ha_url'])\")/api/states/sensor.thermometer_temperatur"
```

---

## Meine Erinnerungen an dich (Claude)

Diese Hinweise kamen aus früheren Sessions — bitte beachten:

- **Hall-Effekt:** Safari oder andere Browser mit `localhost:8340` offen → zweite WS-Verbindung → doppeltes Audio. Immer Browser-Tabs prüfen.
- **speech_input.py** läuft als LaunchAgent mit KeepAlive — manueller Start erzeugt Duplikat. Nur `launchctl bootout/kickstart` benutzen.
- **Doppel-Logging:** Alle Server-Log-Zeilen erscheinen doppelt in der Logdatei (stdout + stderr → selbe Datei). Das ist kein Bug, nur ein Formatting-Artefakt.
- **WS active=2 → active=1** Muster: Wenn eine neue WS-Verbindung sofort wieder stirbt, gibt es eine Zombie-Verbindung bei `active=1`. Seit v2.0.3 durch `hello`-Protokoll behoben — aber bei Regression wieder prüfen.
- **Morgen-Brief Timing:** `detect_morning_trigger()` gibt True zurück wenn `hour >= 4` UND `last_morning_brief is None`. Wenn der Brief nicht gehört wird: prüfen ob er in `data/daily_brief_memory.json` trotzdem als erledigt eingetragen ist.
- **launchctl stop** funktioniert nicht für KeepAlive-Services → stattdessen `bootout` oder `stop-dev.sh`.
- **Änderungen erklären:** Der Nutzer möchte die Lösung ERST beschrieben bekommen und zustimmen, bevor etwas geändert wird.
- **"Gestern ist nicht heute":** Datum immer bewusst halten. Aktuelles Datum via `date` prüfen bevor Log-Zeitstempel interpretiert werden.
