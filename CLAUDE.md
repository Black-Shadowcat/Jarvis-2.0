# CLAUDE.md

Dieses Workspace ist **Jarvis** — ein persoenlicher KI-Assistent mit Sprachsteuerung, Browser-Kontrolle und Cmd+Shift+J Hotkey (macOS). Version: siehe `version.json`.

---

## Setup-Modus

Wenn der Nutzer nach dem Setup fragt oder "Richte Jarvis ein" sagt, folge `SETUP_macOS.md`.  
Frage nach Name, Taetigkeit und bevorzugter Anrede — diese Infos gehoeren in den Systemprompt in `server.py`.

**Voraussetzungen pruefen:**
1. `Python 3.11`: `/opt/homebrew/bin/python3.11 --version`
2. `pip install -r requirements.txt`
3. `playwright install chromium`

---

## Projektstruktur

```
.
├── CLAUDE.md                    # Diese Datei
├── SETUP_macOS.md               # Setup-Anleitung
├── README.md / README_de.md     # Projektdoku (EN/DE)
├── version.json                 # Aktuelle Version (z.B. 2.4.0)
├── config.json                  # Persoenliche Config (gitignored)
├── config.example.json          # Template (alle Keys mit Defaults)
├── voice.json                   # ElevenLabs Voice-Config (gitignored)
├── voice.example.json           # Voice-Config Template
├── requirements.txt             # Python Dependencies
├── server.py                    # FastAPI Backend — Hauptdatei
├── browser_tools.py             # Playwright Browser-Steuerung
├── screen_capture.py            # Screenshot + Claude Vision (SCREEN-Action)
├── locales/
│   ├── de.json                  # Deutsche TTS-Strings (Begrüßungen, Briefs, Reconnect, News, Licht)
│   └── en.json                  # Englische Entsprechungen
├── systems/
│   ├── __init__.py              # Leer
│   └── daily_brief.py           # Daily Brief Memory System (DailyBrief-Klasse)
├── data/
│   ├── daily_brief_memory.json  # Tagesgedaechtnis (gitignored, auto-reset um Mitternacht)
│   └── daily_brief_archive/     # Archiv vergangener Tage (gitignored)
├── frontend/
│   ├── index.html               # Jarvis Dashboard — Haupt-UI (/) — alles JS/CSS inline
│   ├── config.html              # Config UI (/config)
│   ├── config.js                # Config UI Logik
│   ├── handbuch.html            # Benutzerhandbuch (/handbuch)
│   └── i18n/
│       ├── de.json              # Deutsche UI-Labels (28 Keys, via /static/i18n/de.json)
│       └── en.json              # Englische UI-Labels
├── docs/
│   ├── JARVIS_Handbuch.pdf      # PDF-Handbuch
│   └── Jarvis-Start.mp4         # Demo-Video
├── scripts/
│   ├── launch-session.sh        # Startet Server + Chrome App Mode
│   ├── mic-mute-menubar.py      # Mic-Mute in macOS Menuleiste
│   └── wake-monitor.py          # Wake-from-Sleep → /api/wake (wartet auf Screen-Unlock)
└── JARVIS_Handbuch.html         # HTML-Handbuch (Quelle fuer PDF)
```

---

## Architektur

| Komponente | Detail |
|---|---|
| Backend | FastAPI, Python 3.11, Port **8340** |
| KI-Modell | `claude-haiku-4-5-20251001` (Anthropic) |
| TTS | ElevenLabs `eleven_turbo_v2_5`, chunked parallel |
| Spracherkennung | Web Speech API (Chrome, `de-DE` / `en-US` — via `language` Config-Key) |
| Browser | Playwright Chromium (headless) |
| Autostart | macOS launchd (keepalive) |

**Wichtige Routen:**
- `/` → Dashboard (`index.html`) — HUD, Chat, Mail, Tasks, Programme
- `/config` → Konfiguration (`config.html`)
- `/handbuch` → Benutzerhandbuch (`handbuch.html`)
- `/dashboard` → **301 Redirect** auf `/` (veraltet, `dashboard.html` geloescht)
- `/ws` → WebSocket (Sprachsteuerung + TTS)
- `/api/*` → REST-Endpoints
- `GET /api/daily_brief` → Trigger-Detection + Briefing-Text (kein WS noetig)
- `POST /api/daily_brief/manual` → Manueller Trigger: `{ "trigger": "morning|evening|absence|reset" }`
- `GET /api/daily_brief/memory` → Debug: kompletter Tagesgedaechtnisstand
- `POST /api/wake` → Von wake-monitor.py — prueft Brief-Trigger, spricht direkt via _speak()
- `GET /api/language` → `{ "language": "de"|"en", "speech_lang": "de-DE"|"en-US" }`
- `GET /api/update_check` → GitHub-Release-Vergleich, 24h-Cache
- `/static/*` → StaticFiles aus `frontend/` — inkl. `/static/i18n/{de|en}.json`

---

## Config-System

`config.json` wird beim Start geladen. Fehlt die Datei oder ein Pflicht-Key → `SystemExit(1)` mit klarer Fehlermeldung.

**Pflicht-Keys:** `anthropic_api_key`, `elevenlabs_api_key`  
**Alle Keys:** siehe `config.example.json`

`ha_enabled: false` → `HA_URL` wird auf `""` gesetzt, alle HA-Guards greifen automatisch.  
`voice.json` steuert ElevenLabs Voice-ID (getrennt von `config.json`).

---

## Wichtige Invarianten

- **`index.html` ist die aktive Hauptdatei** — alles JS/CSS inline, keine externen .js/.css fuer die Haupt-UI
- **`main.js` und `style.css` existieren nicht mehr** — waren verwaist, in Phase 7 geloescht
- **`dashboard.html` existiert nicht mehr** — `/dashboard` redirectet auf `/`
- **Kein `config["key"]`** — immer `config.get("key", "")` verwenden
- **TTS-Chunks** werden parallel gefeuert (`asyncio.gather`) mit einem Retry nach 1s bei Fehler
- **WebSocket-Reconnect** laeuft mit exponentiellem Backoff (3 → 60s) in `index.html`
- **Activate-Debounce**: "Jarvis activate" wird innerhalb von 10s nach der letzten Ausfuehrung still ignoriert (verhindert Doppel-Begruessung bei WS-Reconnect)
- **Daily Brief Routing**: "Jarvis activate" geht NICHT mehr an den LLM fuer Morgen-Briefings — direkt durch `DailyBrief.generate_morning_brief()` → `_speak()`
- **Action-System**: Structured Output (ActionModel via Pydantic) → `_structured_to_legacy_action()` → `execute_action()`. Nicht ohne Phase-7-Plan anfassen.
- **Daily Brief Memory**: `data/daily_brief_memory.json` — gitignored, wird bei Datumswechsel automatisch archiviert und neu erstellt. Schwellenwerte (30/90 min) stehen in der JSON selbst.
- **Language-System**: `LANGUAGE = config.get("language", "de")` → laedt `locales/{lang}.json` via `_load_locale()` → wird in `DailyBrief.set_locale()` injiziert. UI-Labels kommen aus `frontend/i18n/{lang}.json` via `/static/i18n/`. Live-Reload bei Config-Save.
- **Update-Badge**: `_check_for_update()` per `httpx` gegen GitHub API, SemVer-Vergleich als int-Listen, 24h-Cache in `_update_cache`. Kein Auto-Update.

---

## Starten

```bash
cd "/Users/matthiasschreiber/jarvis-voice-assistant V_2.1"
/opt/homebrew/bin/python3.11 server.py
# oder via Autostart: Cmd+Shift+J
```

Server laeuft auf `http://localhost:8340` — Dashboard oeffnet sich automatisch via `launch-session.sh`.
