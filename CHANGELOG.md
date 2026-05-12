# Changelog

All notable changes to Jarvis are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), versioning follows [SemVer](https://semver.org/).

---

## [2.6.2] — 2026-05-12

### Fixed
- **News-Sortierung** — `_ensure_news()` und Startup-Load nahmen `archive[:10]` (älteste zuerst) statt neueste zuerst. Fix: sortiert nach `archived_at` descending, ungelesene bevorzugt. Damit kommen im Morgen-Brief immer aktuelle Artikel, nicht die vom ersten Archiv-Tag.
- **System-Prompt Datumsfilter** — `build_system_prompt()` filterte auf `saved_at` (existiert im Archiv nicht) → `recent` war immer leer → LLM-Kontext zeigte immer die 3 ältesten Artikel. Fix: auf `archived_at` umgestellt.

### Added
- **"✓ Zur Kenntnis"-Button** im News-Popup — markiert Artikel als gelesen und entfernt ihn aus dem Panel, ohne den Browser zu öffnen. `popup_ack`-i18n-Key in `de.json`/`en.json` ergänzt.

---

## [2.6.1] — 2026-05-12

### Fixed
- **Nacht-Greetings stumm schalten** — `wake_notification()` gibt vor 6 Uhr jetzt lautlos zurück. Bisheriger Fehler: Non-Morning-Wake-Pfad (detect_morning_trigger = False, d.h. Stunde < 6) sprach "Willkommen zurück" wenn Debounce abgelaufen war — mitten in der Nacht. Fix: `if datetime.now().hour < 6: update_activity(); return` am Anfang des Non-Morning-Pfads.
- **Display-Sleep-Wake-Erkennung** — `wake-monitor.py` erkennt jetzt auch reine Display-Schlafs-Wakes (kein System-Sleep), die keinen kernel "Wake reason"-Log-Event erzeugen. Lösung: Daemon-Thread mit HIDIdleTime-Polling alle 10s via `ioreg -c IOHIDSystem`; Transition `idle > 600s → idle < 30s` löst `_try_trigger()` aus. Beide Quellen (log stream + HIDIdleTime) teilen `threading.Lock` + Cooldown-Variable.
- **Veraltete News im Morgen-Brief** — Dieselben RSS-Artikel wurden täglich im Morgen-Snippet vorgelesen, weil sie nie als gelesen markiert wurden. Fix: Selektion filtert jetzt `not a.get("read")`; nach Verwendung werden Artikel sofort in-memory auf `read=True` gesetzt und via `news.mark_as_read()` ins Archiv geschrieben.

### Technical
- `_wake_lock = threading.Lock()` + `_try_trigger(label)` in wake-monitor als thread-safe Cooldown-Helper für beide Wake-Quellen
- `get_user_idle_seconds()` liest `HIDIdleTime`-Nanosekunden aus `ioreg -c IOHIDSystem`

---

## [2.5.0] — 2026-05-08

### Added
- **Willkommensseite** — `/welcome` zeigt beim ersten Besuch eine futuristische Onboarding-Seite mit dreifach-rotierendem HUD-Ring, Status-Bar, Eck-Brackets und aufklappbaren Feature-Beschreibungen.
- **Auto-TTS auf /welcome** — Jarvis begrüßt neue User beim Laden per Stimme (`user_address` wird aus Config geladen). Jedes Feature spricht beim Aufklappen seinen Steckbrief.
- **`/api/tts` Endpoint** — `POST { "text": "..." }` → `{ "audio": "<base64 MP3>" }`. Reusable TTS-Endpoint für beliebige Seiten ohne WebSocket.
- **Welcome-Guard in index.html** — Erster Besuch leitet automatisch auf `/welcome` um (`localStorage: jarvis_welcome_shown`). Nach Dismiss: Weiterleitung zu `/`, Jarvis sagt „Zu Ihren Diensten."
- **Intro-Link in Config-UI** — `◎ Intro` neben Handbuch-Link; setzt localStorage zurück und öffnet `/welcome` erneut.

---

## [2.4.2] — 2026-05-08

### Added
- **Kalender im Aufgaben-Panel** — `/api/get_tasks` liefert jetzt auch Termine für heute und morgen aus Home Assistant CalDAV. Kalender-Einträge erscheinen ohne Checkbox (nicht abhakbar), mit dem Zeit-Label als Quelle (blau).

### Fixed
- **Aussprache in Kalender-/Aktions-Antworten** — Summary-Prompts behalten numerische Form ("17 Uhr", "12. Mai"). ElevenLabs German TTS liest diese korrekt aus (z.B. "siebzehn Uhr") ohne dass der Chat-Text Lautschrift zeigt.

---

## [2.4.1] — 2026-05-08

### Fixed
- `UnboundLocalError: 'OBSIDIAN_INBOX'` in `save_config_api` — `OBSIDIAN_INBOX` und `OBSIDIAN_ARCHIVE` wurden in der Funktion zugewiesen ohne `global`-Deklaration. Python behandelte sie dadurch als lokale Variablen, was beim Speichern der Config (insbesondere nach Sprach-Wechsel) zu einem 500-Fehler führte.
- `NEWS_BRIEF` meldete "Keine neuen Artikel" obwohl ungelesene Artikel im Archiv lagen — Action berichtet jetzt alle `read: False` Einträge aus dem Archiv, nicht nur frisch geholte. `NewsSystem.get_unread_articles()` hinzugefügt.

---

## [2.4.0] — 2026-05-08

### Added
- **Language System** — `language: "de"/"en"` config key switches system prompt language, Web Speech API locale (`de-DE`/`en-US`), and TTS phrasing. Live-reload without restart. `/api/language` endpoint.
- **TTS Locale Files** — `locales/de.json` + `locales/en.json` extract all hardcoded TTS strings (greetings, Daily Brief templates, reconnect phrases, news snippets, light responses). `DailyBrief` reads locale via `set_locale()`.
- **UI i18n** — `frontend/i18n/de.json` + `en.json` (28 keys each). `data-i18n` / `data-i18n-placeholder` attributes on all panel titles, status text, placeholders, popup buttons, and dynamic JS strings. Language loaded from `/api/language` on DOMContentLoaded.
- **In-App Update Badge** — Dashboard checks GitHub Releases API (`/repos/.../releases/latest`) on startup. Badge appears if a newer version exists (blue for patch/minor, gold for major). 24h server-side cache. Dismissable per session via sessionStorage.

### Fixed
- `UnboundLocalError: 'os'` in `NOTIZ_ERLEDIGT` action — two misplaced `import os` statements inside `execute_action()` made Python treat `os` as a local variable for the entire function scope. Removed; module-level import is sufficient.

---

## [2.3.1] — 2026-05-08

### Added
- Gender-neutral address system — `user_address` config field replaces all hardcoded "Sir" references. Supports Sir, Chef, Boss, Ms./Mrs./Miss/Madam + surname.
- Configurable Obsidian archive path (`obsidian_archive_path`) — completed notes move to the correct folder instead of a hardcoded fallback.
- Config UI: all panels are now collapsible accordions (▼/▶). Default open: API Keys, Profile, Home Assistant, Behavior. Default closed: Obsidian, Services & Paths, Programs.

### Fixed
- TTS date pronunciation — "7. Mai" → "siebten Mai", "2026" → "zweitausendsechsundzwanzig"
- `_speak()` now separates TTS audio text from frontend display text — date shown correctly in chat.
- `DailyBrief.load()` now updates `self._data` in place — date change at midnight works correctly.
- Morning news snippet phrasing — more natural sentences instead of robotic list format. Once-per-day guard prevents repeat on reconnect.
- `NOTIZ_ERLEDIGT` action now moves notes to archive folder instead of permanently deleting them.
- Config UI: browser cache issue with `toggleObsidian()` — fixed via cache-busting version parameter on `config.js`.

### Removed
- Danger Zone panel — functionality consolidated into the Maintenance modal with per-item confirmation checkbox.
- Duplicate "delete brain" modal — replaced by inline checkbox flow in Maintenance.

---

## [2.3.0] — 2026-05-07

### Added
- **News System** — RSS feed fetching, archiving, deduplication, category support. Feeds manageable via Config UI modal.
- **Wake Brief** — on wake-from-sleep, Jarvis checks how long it was inactive and delivers a contextual morning/absence brief via `_speak()`.
- Daily Brief overhaul — morning brief, evening brief, absence detection, threshold configuration, maintenance API endpoints.
- Maintenance modal in Config UI — clear news archive, reset daily brief, set absence threshold.
- RSS Feeds modal in Config UI — add, edit, delete, enable/disable feeds.

### Fixed
- Wake endpoint sets `_last_activate_spoken` — prevents triple greeting on reconnect.
- `OPEN` action writes history entry — prevents action loop repetition.
- Date pronunciation — ISO format converted to readable German.
- `NEWS_SEARCH` returns URL as silent history entry — enables follow-up questions.

---

## [2.2.0] — 2026-05

### Added
- Daily Brief Memory System — `data/daily_brief_memory.json` tracks morning brief, absence, last activity. Auto-archives at midnight.
- Wake smart unlock — `wake-monitor.py` waits for actual screen unlock before triggering brief.
- WebSocket reconnect polish — exponential backoff (3→60s), activate debounce prevents double greeting.

---

## [2.1.3] — 2026-05

### Changed
- Stabilization Phase 7 — CSS variable consolidation, race condition fixes, technical debt cleanup. `dashboard.html` removed, `/dashboard` redirects to `/`.

---

## [2.1.2] — 2026-05

### Fixed
- Stabilization Phases 1–5: state management fixes, TTS retry logic, dashboard consolidation.
- Config hardening — missing keys no longer crash server, `ha_enabled: false` guard consistent.
- Completed Obsidian notes (all checkboxes checked) excluded from task list.
- Stale mail count in greeting — refreshes live on "Jarvis activate".

---

## [2.1.1] — 2026-04

### Added
- Voice library — multiple ElevenLabs voices manageable via Config UI, activate per-click.
- `OPEN_APP` action — open macOS applications by voice.
- Live data refresh in Config UI.

---

## [2.1.0] — 2026-04

### Added
- User manual — `/handbuch` route, HTML + PDF versions.
- Window layout configurator in Config UI.
- HUD mute button.

### Fixed
- AppleScript stability improvements for Reminders and Mail.
- Autostart via launchd keepalive.

---

## [2.0.0] — 2026-04

### Changed
- Production migration — port changed to **8340**, Chrome app mode, launchd autostart.
- Config UI introduced (`/config`).
- Structured JSON output layer (Pydantic ActionModel) alongside legacy string parser.

---

## [1.0.0] — 2026-03

### Added
- Initial release — FastAPI backend, ElevenLabs TTS, Web Speech API, Playwright browser control.
- Home Assistant light control, Apple Mail, macOS Reminders integration.
- Kachelmann weather API, voice-controlled browser navigation.
