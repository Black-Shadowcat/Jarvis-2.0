# Jarvis-V3 Architektur & Roadmap

> **Dokumentiert:** 2026-05-14  
> **Status:** v0.1.13 (Aktueller Stand)  
> **Reviewiert:** ChatGPT Architektur-Analyse + interne Betriebserfahrung

---

## 📋 Inhaltsverzeichnis

1. [Aktuelle Architektur](#aktuelle-architektur)
2. [Bekannte Fragilities](#bekannte-fragilities)
3. [Design-Entscheidungen & Gründe](#design-entscheidungen--gründe)
4. [Recovery & Stabilität](#recovery--stabilität)
5. [Langfristige Roadmap](#langfristige-roadmap)

---

## Aktuelle Architektur

### High-Level Übersicht

```
┌─────────────────────────────────────────────────────────────┐
│                    macOS System                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ launchd (KeepAlive Supervision)                      │   │
│  │  ├─ com.jarvis.whisper.server (Port 8340)           │   │
│  │  ├─ com.jarvis.whisper.speech (speech_input.py)     │   │
│  │  ├─ com.jarvis.whisper.wake (wake-monitor.py)       │   │
│  │  └─ com.jarvis.whisper.session (Chrome Kiosk)       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ server.py (FastAPI, Port 8340) — MONOLITHIC         │   │
│  │  ├─ Claude LLM Integration                          │   │
│  │  ├─ ElevenLabs TTS                                  │   │
│  │  ├─ HomeAssistant Bridge                            │   │
│  │  ├─ WebSocket Handler (Browser + speech_input)      │   │
│  │  ├─ Daily Brief System                              │   │
│  │  ├─ News Aggregation                                │   │
│  │  ├─ Calendar/Task/Mail Sync                         │   │
│  │  ├─ Light/Automation Control                        │   │
│  │  └─ Browser Automation (Playwright)                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ speech_input.py (Whisper STT)                        │   │
│  │  ├─ VAD (Voice Activity Detection)                  │   │
│  │  ├─ Wake-Word Detection                             │   │
│  │  ├─ Push-to-Talk (F19)                              │   │
│  │  ├─ Audio Input Stream                              │   │
│  │  └─ WebSocket Client to server.py                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Chrome Kiosk (index.html)                            │   │
│  │  ├─ Dashboard (HUD, Chat, Tasks, Mail)              │   │
│  │  ├─ WebSocket to server.py                          │   │
│  │  ├─ Text-to-Speech Playback                         │   │
│  │  └─ Microphone/Input Control                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ wake-monitor.py (Sleep/Wake Handler)                │   │
│  │  └─ Listens for IOConsoleLocked → triggers briefing │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Datenfluss

```
Benutzer spricht
    ↓
speech_input.py (Whisper VAD + STT)
    ↓ (WebSocket: {"text": "..."})
server.py (FastAPI)
    ↓ (Process via Claude)
ElevenLabs TTS
    ↓ (Audio Stream)
Chrome (index.html) — Audio Playback
    ↓
Benutzer hört Antwort
```

### Kommunikationsprotokolle

| Sender | Empfänger | Protokoll | Zweck |
|--------|-----------|-----------|-------|
| speech_input.py | server.py | WebSocket `/ws/stt` | STT Input, receive messages |
| Chrome | server.py | WebSocket `/ws` | Chat, UI Updates |
| speech_input.py | server.py | HTTP `/api/ptt/*` | PTT State (listen_open/close) |
| server.py | ElevenLabs | HTTPS REST | TTS Synthesis |
| server.py | HomeAssistant | HTTP REST | Entity State, Automation |
| Chrome | Browser Automation | Playwright | Web Search, News Fetch |

---

## Bekannte Fragilities

### 🔴 **Kritisch: server.py Monolith**

**Problem:**
- Bündelt 10+ unabhängige Funktionen in einem Prozess
- Ein Bug in Feature X kann gesamten Server lahmlegen
- Memory-Leaks schwer zu lokalisieren
- Recovery ist immer "alles neustarten"

**Beispiele aus Betrieb:**
- HomeAssistant HTTP-Timeout blockiert Chat-Response
- Weather-Forecast-Laden mit 10s Timeout → Chat hängt
- Playwright Browser-Automation blockiert STT-WebSocket
- News-Fetch kann kompletten Server hang verursachen

**Impact:** Höchstes Risiko für Instabilität

**Severity:** 🔴 Kritisch (mittelfristig lösen)

---

### 🟠 **Hoch: Audio nicht isoliert**

**Problem:**
- Wakeword (speech_input.py)
- TTS Playback (Chrome)
- STT Input Stream
- Browser Audio

sind alle im **Betriebssystem-Audio-Kern** gekoppelt.

**macOS Audio ist instabil:**
- CoreAudio-Deadlocks
- Zombie-Streams bei Crash
- Device-Handle-Leaks
- Exclusive-Lock-Konflikte

**Szenario aus Vergangenheit:**
- Browser Audio exclusive-locked Device
- speech_input.py konnte nicht starten
- Volle Reboot notwendig

**Impact:** Audio-Recovery unmöglich ohne Audio-Prozess-Neustart

**Severity:** 🟠 Hoch (Phase 2 Priorität)

---

### 🟠 **Hoch: Chrome Kiosk Abhängigkeit**

**Problem:**
- Entire UI läuft in Chrome Kiosk
- Flags wie `--disable-gpu` sind defensive Hacks
- Kein Fallback bei Chrome-Crash

**Risiken:**
- macOS Update kann Chrome Kiosk-Kompatibilität brechen (ist schon passiert)
- GPU-Probleme auf ARM64 Macs
- Audio-API Inkompatibilität
- Keine kontrollierte Runtime

**Impact:** Unerwartete macOS-Updates können UI lahmlegen

**Severity:** 🟠 Hoch (mittelfristig evaluieren)

---

### 🟡 **Mittel: Kein Health-Supervisor**

**Aktuell vorhanden:**
- launchd KeepAlive (Process-Level)
- wake-monitor.py (Sleep/Wake)
- Retry-Loops im Code

**Was fehlt:**
Zentrale Überwachung der Service-Health.

Beispiel aus Betrieb:
```
server.py läuft ✓
aber WebSocket ist stuck → Chrome zeigt "Disconnected"
launchd startet server.py aber WebSocket-State bleibt kaputt
→ Benutzer muss manuell refreshen
```

**Bessere Lösung:**
```
supervisor.py:
  every 10s:
    ✓ Check WebSocket alive?
    ✓ Check Audio alive?
    ✓ Check Claude reachable?
    ✓ Check HomeAssistant?
    → Restart specific service wenn Problem
    → Log incident
```

**Impact:** Längere Fehler-Recovery (minutes statt seconds)

**Severity:** 🟡 Mittel (schnelle Gewinne möglich)

---

### 🟡 **Mittel: Config-System unsicher**

**Problem:**
```python
# Überall im Code:
config.get("key", "")
# Keine Validierung
# Keine Typsicherheit
# Defaults versteckt
```

**Risiken:**
- Falsche Config wird zur Laufzeit erkannt
- Schwer nachvollziehbare Defaults
- Keine Schema-Validierung
- Config-Fehler sind Runtime-Fehler

**Impact:** Config-Fehler schwer zu debuggen

**Severity:** 🟡 Mittel (Tech Debt, aber nicht kritisch)

---

## Design-Entscheidungen & Gründe

### ✅ Warum launchd statt Login-Items?

**Entscheidung:** launchd mit KeepAlive für Process-Supervision

**Gründe:**
- KeepAlive startet Prozess automatisch neu falls er crashed
- RunAtLoad — startet beim macOS Boot
- StandardOutPath / StandardErrorPath für Logging
- Keine Shell-Loop nötig (simpler, stabiler)
- Native macOS Integration

**Alternative (abgelehnt):** Login-Items
- Zu fragil (User kann deaktivieren)
- Nicht persistent über Reboot
- Keine automatische Restart

---

### ✅ Warum dediziertes Chrome-Profil?

**Entscheidung:** `--user-data-dir="/Users/.../jarvis-profile"`

**Gründe:**
- Verhindert Session-Kollisionen mit normalem Chrome
- Audio/Mic-Permissions isoliert
- Cache/Cookies separiert
- Keine Chrome-Update-Conflicts

**Impact aus Betrieb:**
Ohne das: Chrome-Updates haben Audio-Permissions zurückgesetzt → TTS funktioniert nicht mehr

---

### ✅ Warum Whisper lokal statt cloud STT?

**Entscheidung:** mlx-whisper (lokal) statt Google/Azure Cloud STT

**Gründe:**
- Keine API-Abhängigkeit
- Keine Latenz (200ms vs. 1-2s cloud)
- Datenschutz (Audio bleibt lokal)
- Kostenlos (lokal)

**Trade-off:** mlx-whisper langsamer als cloud STT, aber Latenz unkritisch für Wake-Word

---

### ✅ Warum VAD (Voice Activity Detection)?

**Entscheidung:** RMS-basierte VAD vor Whisper

**Gründe:**
- Whisper ist teuer (CPU-intensive)
- VAD filtert Stille/Rauschen → reduziert Whisper-Calls
- Schnelle Wake-Word-Detection (keine 2-3s Latenz)

**Trade-off:** VAD-Tuning ist schwierig (siehe v0.1.10/0.1.12 Bugs)

---

### ✅ Warum HomeAssistant als Broker?

**Entscheidung:** HomeAssistant als API-Bridge statt direkt mit Devices sprechen

**Gründe:**
- HomeAssistant ist bereits lokal vorhanden
- Abstrahiert Hardware-Details (Philips Hue, Somfy, etc.)
- Standard REST API (einfach zu integrieren)
- Recovery bei Device-Ausfall ist HA-Problem, nicht Jarvis-Problem

**Beispiel:**
```
Jarvis → HA REST API → Hue Bridge → Licht an
         (HA handles retries, device errors)
```

---

## Recovery & Stabilität

### Sleep/Wake Recovery

```
Benutzer schaltet Mac in Ruhezustand
    ↓
IOConsoleLocked Signal
    ↓
wake-monitor.py erkennt Aufwachen
    ↓
HTTP POST /api/wake
    ↓
server.py triggert Daily Brief
    ↓
Chrome kriegt Audio-fokus zurück
    ↓
Brief wird abgespielt
```

**Bekannte Probleme:**
- Audio-Playback startet erst wenn Chrome aktiv (B006)
- Browser-State kann stuck sein → reconnect nötig
- HomeAssistant kann offline sein nach lange Sleep

---

### Fehler-Szenarien & Handling

| Fehler | Auslöser | Recovery | Status |
|--------|----------|----------|--------|
| **Chrome crashed** | Graphics/Extension/Memory | launchd restarts | ✅ Funktioniert |
| **server.py hung** | HTTP Timeout, WebSocket stuck | launchd restarts (30s) | ✅ Funktioniert |
| **speech_input.py crashed** | Audio device error, exception | launchd restarts | ✅ Funktioniert |
| **HomeAssistant offline** | Network/HA crash | Graceful fallback (cached data) | ✅ Funktioniert |
| **WebSocket stuck** | Event loop blocked | Browser muss reconnect manuell | ❌ Kein Auto-Recovery |
| **Audio device exclusive-locked** | Another app took mic | Full system restart needed | ❌ Unlösbar |
| **TTS rate-limited** | ElevenLabs quota | Queue + Retry | ✅ Funktioniert |

---

## Langfristige Roadmap

### Phase 1: Health & Observability (2-3 Wochen)

**Ziel:** Bessere Fehler-Erkennung und Auto-Recovery

```
supervisor.py (neuer Service):
  ✓ Health-Check Loop (10s interval)
  ✓ WebSocket alive?
  ✓ Audio system alive?
  ✓ Claude reachable?
  ✓ HomeAssistant reachable?
  
  → Restart stuck components
  → Log incidents to dashboard
  → Alert wenn Fehler persistent
```

**Implementierung:** ~200 Lines Python

**Gewinn:** Fehler-Recovery von minutes → seconds

---

### Phase 2: Service Isolation (4-6 Wochen)

**Ziel:** Prozess-Trennung für Stabilität

```
Neue Architektur:

jarvis-core (FastAPI Gateway)
  ├─ HTTP Port 8340 (Browser)
  ├─ WebSocket /ws (Browser Events)
  └─ routes nur noch Dispatching

jarvis-audio (Separate Service)
  ├─ speech_input.py in neuen Prozess
  ├─ Audio Device Management
  ├─ STT Pipeline
  ├─ TTS queueing
  └─ HTTP API :8341 für jarvis-core

jarvis-ha (HomeAssistant Bridge)
  ├─ Lights/Automation Logic
  ├─ Entity Caching
  ├─ Retry-Logic
  └─ HTTP API :8342

jarvis-llm (Claude Integration)
  ├─ Prompt Management
  ├─ Conversation History
  ├─ Tool Dispatch
  └─ HTTP API :8343

jarvis-memory (Daily Brief, News)
  ├─ News Archive
  ├─ Daily Brief DB
  ├─ Calendar/Task Sync
  └─ HTTP API :8344
```

**IPC (Inter-Process Communication):**
```
HTTP REST (einfach, aber langsam)
  vs.
Unix Sockets (schneller, für lokal)
  vs.
Message Queue (RabbitMQ, wenn Queue-basiert nötig)
```

**Vorteil:**
- ✅ Audio-Crash isoliert (kein Chrome-Crash)
- ✅ HA-Timeout isoliert (kein Chat-Block)
- ✅ Einzelne Services restart → anderen läuft weiter
- ✅ Memory-Leaks lokalisierbar

**Aufwand:** ~2 Wochen Refactoring

---

### Phase 3: Kontrollierte Runtime (8-12 Wochen)

**Ziel:** Chrome Kiosk → echte App Runtime

**Option A: Tauri** (Empfohlen)
```
Vorteile:
- Web-basiert (index.html bleibt)
- Rust-basiert (sicherer als Electron)
- Kleinere Binary
- Native macOS Integration

Nachteile:
- Neues Dependency
- Setup-Zeit
```

**Option B: Electron**
```
Vorteile:
- Known Quantities
- Large Ecosystem

Nachteile:
- Größere Binary
- Mehr CPU/Memory
```

**Option C: Weiterhin Chrome Kiosk**
```
Nur wenn Tauri/Electron zu viel Aufwand.
Aber: Fragil gegen macOS-Updates.
```

**Entscheidung:** Erst Phase 1+2, dann evaluieren.

---

### Phase 4: Distributed Observability (Optional, Q4)

**Ziel:** Zentrale Health-Dashboard + Alerting

```
Möglichkeiten:
- Grafana + Prometheus (open-source)
- DataDog (commercial, aber easy)
- Custom Django Dashboard (simple, aber viel Code)

Zeigen:
- Service Health (up/down)
- CPU/Memory pro Service
- WebSocket Status
- Error Rate
- Audio Quality Metrics
```

---

## Technische Schulden & Vermeidung

### Was Schmerzen verursacht hat (und wie man es vermeidet)

| Problem | Verursacher | Vermeidung |
|---------|-------------|-----------|
| VAD-Thresholds instabil | Hard-coded Konstanten | Config-basiert + Telemetrie |
| Weather Forecast bricht | Wrong HA Entity | Schema Validation + Tests |
| Audio Exclusive-Lock | Cross-Process Resource | Separate Audio Service |
| WebSocket hung | Event Loop blocked | Health checks |
| Config Defaults versteckt | runtime `config.get()` | Typed Config Class |

---

## Fazit & Nächste Schritte

**Jarvis-V3 ist stabiler als v2.x, aber noch nicht produktionsreif für 24/7 ohne Supervision.**

### Unmittelbare Prioritäten:

1. ✅ **v0.1.13** — VAD/Weather/TTS Fixes (DONE)
2. **v0.2.0** — Health Supervisor (Phase 1, 2-3 Wochen)
3. **v0.3.0** — Service Isolation (Phase 2, 4-6 Wochen)
4. **v1.0.0** — Runtime Evaluation + Distributed Observability

### Erfolgskriterien:

- [ ] 99% Uptime ohne Manual Restarts
- [ ] Auto-Recovery < 10 seconds für transient errors
- [ ] Audio/Chrome/Server crash isoliert (andere Services laufen weiter)
- [ ] Config Validation bei Startup
- [ ] Health Dashboard (kann User sehen dass alles OK ist)

---

**Dokumentiert von:** Claude Code (mit ChatGPT Architektur-Review)  
**Nächstes Review:** Nach Phase 1 Implementation
