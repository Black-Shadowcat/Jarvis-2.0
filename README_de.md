# J.A.R.V.I.S. — Persönlicher KI-Sprachassistent (macOS v2.4)

> **Dieses Projekt basiert auf der ursprünglichen Idee und Windows-Implementierung von [Julian Ivanov](https://github.com/Julian-Ivanov/jarvis-voice-assistant).**
> Was als macOS-Port begann, ist zu einer erheblich erweiterten Version gewachsen — mit Home Assistant Integration, Apple Erinnerungen, Obsidian, einer Config-Oberfläche, einem Dashboard und einem neuen Action-System. Grundkonzept, Persönlichkeit und Architektur stammen von Julian. Kein Support. Dieses Projekt wird ausschließlich für den persönlichen Gebrauch gepflegt.

---

## macOS-Anpassungen

Entwickelt für macOS (Apple Silicon M4) mit [Claude Code](https://claude.ai/code). Wesentliche Unterschiede zum ursprünglichen Windows-Projekt:

| Original (Windows) | Dieser Fork (macOS V2.1) |
|--------------------|--------------------------|
| Doppelklatschen-Trigger | Cmd+Shift+J via launchd |
| PowerShell-Skripte | zsh Shell-Skripte |
| Windows-Dienst | launchd KeepAlive (startet bei Absturz automatisch neu) |
| Manuelle Aufgabenverwaltung | Apple Erinnerungen via AppleScript (`whose`-Klausel) |
| Kein Smart Home | Home Assistant Integration (30+ Licht-Synonyme) |
| Kein Kalender | iCal via HA CalDAV (heute + morgen) |
| Keine Notizen | Obsidian Inbox (schreiben/lesen/löschen) |
| Keine Config-Oberfläche | Config UI unter `/config` (kein Texteditor nötig) |
| Kein Dashboard | Dashboard unter `/` (Mails, Aufgaben, News, App-Starter) |
| Fenster-Snapping | Chrome App Mode Vollbild (`--start-fullscreen`) |

---

> Cmd+Shift+J drücken. Jarvis wacht auf, begrüßt dich mit Wetter und Aufgaben, beantwortet deine Fragen, steuert deinen Browser und sieht deinen Bildschirm.

---

## 📖 Handbuch

**[→ JARVIS_Handbuch.pdf herunterladen](docs/JARVIS_Handbuch.pdf)** — vollständige Bedienungsanleitung für Nicht-Programmierer, direkt auf GitHub vorschaubar und druckfertig.

---

## Features

- **Sprachgespräch** — Spreche frei auf Deutsch oder Englisch. Jarvis hört zu, denkt nach, antwortet per Stimme. Echo-Schutz verhindert Rückkopplungsschleifen.
- **Sprachumschaltung** — `language: "de"/"en"` in der Config schaltet System-Prompt, Spracherkennung, TTS-Phrasen und alle UI-Labels um. Kein Neustart erforderlich.
- **HUD-Klick-Stummschaltung** — Klick auf den animierten SVG-Ring schaltet das Mikrofon stumm/aktiv. Ring wird rot bei Stummschaltung.
- **Texteingabe-Toggle** — Stift-Icon im Panel-Header blendet ein Texteingabefeld für getippte Befehle ein.
- **Britischer Butler** — Trockene, witzige Persönlichkeit. Spricht dich mit deiner konfigurierten Anrede an (Sir, Ms. Schmidt, Chef, …).
- **Wetter & Aufgaben** — Beim Start: aktuelles Wetter (Kachelmann API + HA-Wetterstation) und heutige offene Erinnerungen.
- **Apple Erinnerungen** — Erinnerungen lesen, hinzufügen und abhaken via AppleScript. Optimistische UI-Updates — kein 25-Sekunden-Freeze.
- **Apple Mail** — Ungelesene Mails auf Anfrage vorlesen.
- **Kalender** — Termine für heute und morgen via Home Assistant CalDAV.
- **Home Assistant Lichter** — Lichter per Raumname mit 30+ Synonymen steuern. Helligkeit, Farbe, An/Aus.
- **Obsidian Inbox** — Notizen schreiben, lesen, erledigen — alles per Stimme.
- **Browser-Automatisierung** — Playwright steuert einen echten Browser: suchen, URLs öffnen, Seiteninhalte lesen.
- **Bildschirm-Vision** — Screenshot + Claude Vision: "Was ist auf meinem Bildschirm?"
- **RSS-Neuigkeiten** — RSS-Artikel nach Kategorie abrufen und vorlesen. Feeds über Config-UI-Modal verwalten.
- **Daily Brief Memory System** — Ereignisgesteuerte Intelligenz: Morgen-Briefing (Wetter, Mails, Aufgaben), Pause-Brief nach >30 min Abwesenheit, Abwesenheits-Brief nach >90 min, Abend-Briefing ab 17:00. Tagesgedächtnis speichert Mail-IDs — Jarvis schweigt wenn sich nichts geändert hat.
- **Wake-from-Sleep** — Wartet auf den Screen-Unlock, spricht dann automatisch den passenden Brief.
- **Update-Badge** — Dashboard zeigt ein Badge wenn eine neue GitHub-Version verfügbar ist.
- **Mikrofon-Stummschaltung in der Menüleiste** — macOS-Menüleisten-Button zum systemweiten Stummschalten.
- **Config UI** — Alle Einstellungen (API-Keys, Stimme, Sprache, Stadt etc.) im Browser unter `/config`. Kein Texteditor.
- **Dashboard** — Unter `/`: Mails, Aufgaben, Obsidian-Notizen, RSS-News, App-Starter.
- **launchd KeepAlive** — Server startet bei Absturz automatisch neu. Session startet beim Login.

---

## Architektur

```
Du (sprechen) → Chrome Browser (Web Speech API de-DE) → FastAPI Server (localhost:8340)
                                                                  ↓
                                                         Claude Haiku (denkt nach)
                                                                  ↓
                                             parse_structured_action() [JSON-first]
                                                                  ↓
                                ┌─────────────────────┬──────────┴───────────────┐
                                ↓                     ↓                          ↓
                         ElevenLabs TTS        Playwright Browser         AppleScript
                         (spricht zurück)       (suchen/öffnen)       (Erinnerungen/Mail)
                                ↓
                         Audio → Chrome → Du (hören)
```

| Komponente | Technologie | Zweck |
|------------|-------------|-------|
| Spracheingabe | Web Speech API (Chrome, de-DE / en-US) | Stimme zu Text |
| Server | FastAPI (Python 3.11) | Lokale Orchestrierung |
| Gehirn | Claude Haiku (Anthropic) | Denken, entscheiden, antworten |
| Stimme | ElevenLabs TTS (eleven_turbo_v2_5) | Natürliche deutsche Sprachausgabe |
| Browser-Steuerung | Playwright | Echte Browser-Automatisierung |
| Bildschirm-Vision | Claude Vision + Pillow | Screenshot-Analyse |
| Smart Home | Home Assistant REST API | Lichtsteuerung |
| Erinnerungen/Mail | AppleScript (`whose`-Klausel) | macOS-nativer Datenzugriff |
| Autostart | launchd (KeepAlive + Session) | Server + Session beim Login |
| Wake-Handling | wake-monitor.py → /api/wake | Reaktivierung nach Schlaf |

---

## Voraussetzungen

- **macOS 14+** (Apple Silicon, getestet auf M4)
- **Python 3.11** via Homebrew (`/opt/homebrew/bin/python3.11`)
- **Google Chrome** (für Web Speech API)
- **Home Assistant** (optional, für Lichter und CalDAV-Kalender)

### Benötigte API-Keys

| Dienst | Wofür | Link |
|--------|-------|------|
| Anthropic | Claude Haiku (das Gehirn) | [console.anthropic.com](https://console.anthropic.com) |
| ElevenLabs | Stimme (TTS, Pro Plan empfohlen) | [elevenlabs.io](https://elevenlabs.io) |

---

## Schnellstart

1. **Klonen und installieren:**
   ```bash
   git clone https://github.com/Black-Shadowcat/jarvis-voice-assistant.git
   cd jarvis-voice-assistant
   /opt/homebrew/bin/pip3.11 install -r requirements.txt
   playwright install chromium
   ```

2. **Config erstellen:**
   ```bash
   cp config.example.json config.json
   ```

3. **`config.json` bearbeiten** — mindestens erforderliche Felder:
   ```json
   {
     "anthropic_api_key": "sk-ant-...",
     "elevenlabs_api_key": "sk_...",
     "elevenlabs_voice_id": "DEINE_VOICE_ID",
     "user_name": "Dein Name",
     "user_address": "Sir",          // Männlich: Sir, Boss | Weiblich: Ms. Schmidt, Mrs. Müller, Miss Brown, Madam
     "city": "Deine Stadt"
   }
   ```

4. **Jarvis starten:**
   ```bash
   bash scripts/launch-session.sh
   ```

5. `http://localhost:8340` im Chrome öffnen, falls er sich nicht automatisch öffnet.

---

## Was du sagen kannst

| Befehl | Was passiert |
|--------|-------------|
| *"Guten Morgen, Jarvis"* | Wetter + heutige Aufgaben |
| *"Was steht heute an?"* | Erinnerungen + Kalender für heute/morgen |
| *"Schalte das Wohnzimmerlicht ein"* | Lichtsteuerung per Stimme |
| *"Dimme das Licht auf 30%"* | Helligkeit via Home Assistant |
| *"Suche nach KI-Neuigkeiten"* | Browser öffnet, sucht, fasst zusammen |
| *"Was ist auf meinem Bildschirm?"* | Screenshot + Claude Vision |
| *"Schreib eine Notiz: ..."* | Obsidian Inbox Eintrag |
| *"Meine Erinnerungen"* | Apple Erinnerungen vorlesen |
| *Beliebige Frage* | Jarvis antwortet im Butler-Stil |

---

## Projektstruktur

```
jarvis-voice-assistant/
├── server.py              # FastAPI Backend — Gehirn + Action-System
├── browser_tools.py       # Playwright Browser-Automatisierung
├── screen_capture.py      # Screenshot + Claude Vision
├── version.json           # Zentrale Versionsnummer
├── config.json            # Persönliche Config (gitignored)
├── config.example.json    # Vorlage für neue Nutzer
├── requirements.txt       # Python-Abhängigkeiten
├── locales/
│   ├── de.json            # Deutsche TTS-Strings (Begrüßungen, Briefs etc.)
│   └── en.json            # Englische Entsprechungen
├── systems/
│   └── daily_brief.py     # Daily Brief Memory System (DailyBrief-Klasse)
├── data/
│   ├── daily_brief_memory.json   # Tagesgedächtnis (gitignored)
│   └── daily_brief_archive/      # Archiv vergangener Tage (gitignored)
├── frontend/
│   ├── index.html         # Jarvis Dashboard + HUD (Chrome App Mode, Port 8340)
│   ├── config.html        # Config UI (/config)
│   ├── config.js          # Config UI Logik
│   ├── handbuch.html      # Benutzerhandbuch (/handbuch)
│   └── i18n/
│       ├── de.json        # Deutsche UI-Labels
│       └── en.json        # Englische UI-Labels
└── scripts/
    ├── launch-session.sh  # Startet Server + Chrome + Mic-Mute Button
    ├── mic-mute-menubar.py # macOS Menüleisten-Stummschaltung
    └── wake-monitor.py    # Wake-from-Sleep → /api/wake (wartet auf Screen-Unlock)
```

---

## Wichtige macOS-Hinweise

- **Chrome muss via `open -na` gestartet werden**, nicht direkt als Binary — von launchd gestartete Prozesse erben nicht den GUI-Bootstrap-Kontext, den Chrome benötigt.
- **AppleScript-Loops (`repeat with r in every reminder`) sind unzuverlässig** für den Eigenschaftszugriff — immer `whose`-Klausel-Filter verwenden.
- **`result` ist ein reserviertes Wort in AppleScript** — stattdessen `taskList` o.ä. verwenden.
- **REMINDER_DONE nutzt optimistische Updates**: entfernt den Eintrag sofort aus dem In-Memory-Cache, AppleScript läuft im Hintergrund-Thread. Verhindert 25-Sekunden-UI-Freeze.

---

## launchd Agents

Drei Agents unter `~/Library/LaunchAgents/`:

| Agent | Zweck |
|-------|-------|
| `com.jarvis.server.plist` | FastAPI Server mit KeepAlive (startet bei Absturz neu) |
| `com.jarvis.session.plist` | Session-Start beim Login (Chrome + Mic-Mute Button) |
| `com.jarvis.wake.plist` | Wake-from-Sleep Monitor |

---

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| Server antwortet nicht | `pkill -f "server.py"` — launchd startet ihn automatisch neu |
| Chrome öffnet sich nicht | `bash scripts/launch-session.sh` manuell starten |
| Mikrofon funktioniert nicht | Systemeinstellungen → Datenschutz → Mikrofon → Chrome erlauben |
| Erinnerungen werden nicht angezeigt | Server-Log prüfen: `tail -f /tmp/jarvis-server.log` |
| Browser-Automatisierung schlägt fehl | `playwright install chromium` erneut ausführen |

---

## Technologie-Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** — Python Web-Framework
- **[Claude Haiku](https://anthropic.com)** — KI-Modell (Gehirn)
- **[ElevenLabs](https://elevenlabs.io)** — Natürliche Sprachsynthese
- **[Playwright](https://playwright.dev)** — Browser-Automatisierung
- **[Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)** — Browser-native Spracherkennung
- **[Home Assistant](https://www.home-assistant.io/)** — Smart Home Integration
- **AppleScript** — macOS Erinnerungen & Mail Zugriff

---

## Danksagung

Ursprüngliche Idee und Windows-Implementierung von [Julian Ivanov](https://github.com/Julian-Ivanov) — entwickelt mit [Claude Code](https://claude.ai/code).
macOS v2.4 — erheblich erweitert von Matthias Schreiber, ebenfalls mit [Claude Code](https://claude.ai/code).

Inspiriert von Iron Mans J.A.R.V.I.S. — *"Zu Ihren Diensten, Sir."*

---

## Lizenz

MIT — nutze es, verändere es, baue darauf auf.
