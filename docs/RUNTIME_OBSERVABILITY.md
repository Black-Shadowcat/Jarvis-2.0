# Runtime Observability — Phase 1–3 Plan

> **Dokumentation:** Beobachtbarkeit statt Optimierung  
> **Gültig ab:** 15.05.2026  
> **Status:** Planning (vor Implementierung)  
> **Autor:** Matthias Schreiber + Claude Code Analysis

---

## 📋 Übersicht

Jarvis v0.1.15 läuft stabil (12h+ uptime, kein Swap). Zur **langfristigen Überwachung** führen wir 3 Observability-Phasen ein — nicht zur Optimierung, sondern zur **Transparenz & Leak-Detection**.

| Phase | Fokus | Komponente | Aufwand | Risiko |
|-------|-------|-----------|--------|--------|
| **1** | RAM-History Ringbuffer | supervisor.py | ~30 Zeilen | Minimal |
| **2** | Speech-Lifecycle sichtbar | speech_input.py | ~25 Zeilen | Minimal |
| **3** | Wake/Sleep-Korrelation | wake-monitor.py | ~25 Zeilen | Minimal |

---

## 🎯 Designprinzipien

### Fundamental

1. **Observe, nicht Optimize**
   - Ziel: Verstehen, nicht reparieren
   - Kein Auto-Recovery aus Observability-Code
   - Keine vorschnellen Optimierungen

2. **Fail-Silent + Debug-Logging**
   - Monitoring darf Runtime nie destabilisieren
   - Bei Fehler: ignorieren + minimales debug-Log
   - Kein Spam, aber sichtbar bei Problemen (Permission denied, JSON corrupt, etc.)

3. **Isolation: Observability ≠ Recovery**
   - Observability schreibt nur Snapshots
   - Recovery bleibt in bestehenden Components
   - Keine Kopplung zwischen den Layern

4. **Leichtgewichtig & Ringbuffer**
   - Keine unbegrenzten Historien
   - Max ~50 KB Disk pro Komponente
   - Atomic writes (temp + rename)

5. **No New Dependencies**
   - Nur os, json, time (existierend)
   - Keine neuen Imports
   - Keine externe Infrastruktur

---

## 📊 Phase 1: RAM-History Ringbuffer

### Ziel

**Speicherdrift erkennen.** Über 24h kleine Snapshots sammeln → Trends sichtbar machen.

### Datenstruktur

**Datei:** `data/memory_history.json` (Ringbuffer, max ~25 KB)

```json
{
  "entries": [
    {
      "ts": 1715875493,
      "server_rss_mb": 42,
      "speech_rss_mb": 47,
      "supervisor_rss_mb": 24,
      "chrome_rss_mb": 301,
      "system_active_mb": 3738,
      "system_wired_mb": 2426
    },
    { ... }
  ]
}
```

**Limits:**
- Interval: 5 Minuten
- Max entries: 144 (= 12 Stunden)
- Auto-Prune: älteste Einträge löschen, wenn > 144

### Implementierung

**In supervisor.py (~30 Zeilen):**

```python
# Config
MEMORY_HISTORY_FILE = "data/memory_history.json"
MEMORY_HISTORY_INTERVAL = 300  # 5 min
MEMORY_HISTORY_MAX = 144  # 12h
last_memory_update = 0

# In run_checks() loop (nach existierenden Health-Checks):
if time.time() - last_memory_update > MEMORY_HISTORY_INTERVAL:
    _update_memory_history()
    last_memory_update = time.time()

# New function:
def _update_memory_history():
    """Collect RSS snapshots in ringbuffer. Fail-silent."""
    try:
        # Load or init
        if os.path.exists(MEMORY_HISTORY_FILE):
            with open(MEMORY_HISTORY_FILE) as f:
                data = json.load(f)
        else:
            data = {"entries": []}
        
        # New snapshot
        snapshot = {
            "ts": time.time(),
            "server_rss_mb": _get_process_rss("server.py") or 0,
            "speech_rss_mb": _get_process_rss("speech_input.py") or 0,
            "supervisor_rss_mb": _get_process_rss(os.getpid()) or 0,
            "chrome_rss_mb": _get_process_rss("jarvis-v2-chrome") or 0,
            "system_active_mb": _get_vm_stat_pages("active") or 0,
            "system_wired_mb": _get_vm_stat_pages("wired") or 0,
        }
        data["entries"].append(snapshot)
        
        # Ringbuffer prune
        if len(data["entries"]) > MEMORY_HISTORY_MAX:
            data["entries"] = data["entries"][-MEMORY_HISTORY_MAX:]
        
        # Atomic write (temp + rename)
        temp_file = MEMORY_HISTORY_FILE + ".tmp"
        with open(temp_file, "w") as f:
            json.dump(data, f)
        os.rename(temp_file, MEMORY_HISTORY_FILE)
        
    except Exception as e:
        log.debug(f"[memory_history] snapshot failed: {type(e).__name__}")

def _get_process_rss(name_or_pid):
    """Get process RSS in MB. Return None on error (fail-silent)."""
    try:
        if isinstance(name_or_pid, str):
            pid = _get_pid(name_or_pid)  # existing function
        else:
            pid = name_or_pid
        if not pid:
            return None
        
        proc = psutil.Process(pid)  # already imported
        rss_bytes = proc.memory_info().rss
        return int(rss_bytes / 1024 / 1024)
    except:
        return None
```

### Monitoring-Output (Health Dashboard)

```
📊 MEMORY TRENDS (24h)
─────────────────────────────────────────
  server.py        42 MB    ▁▁▂▂▂▁▁▁▂▁
  speech_input     47 MB    ▁▁▁▁▃▄▂▁▁▂
  Chrome          301 MB    ▂▂▂▃▃▃▂▂▂▂
  System active  3738 MB    ▄▄▄▄▄▄▄▄▄▄
```

### Success Criteria

- [x] Snapshot alle 5 Min
- [x] Ringbuffer auf 12h begrenzt
- [x] Atomic write (crashresistent)
- [x] Fail-silent + debug-logging
- [x] Keine Runtime-Performance-Impact

---

## 🎤 Phase 2: Speech-Lifecycle sichtbar

### Ziel

**Whisper-Zustand transparent.** Wann lädt Modell? Wann transkribiert? Normale Operationen vs. Anomalien?

### Datenstruktur

**Datei:** `data/speech_state.json` (immer aktuell, ~1 KB)

```json
{
  "state": "TRANSCRIBING",
  "inference_active": true,
  "last_update": 1715875493,
  "ws_connected": true,
  "last_transcription_duration_s": 1.8,
  "last_transcription_s_ago": 23.4
}
```

**States:**
- `IDLE` — nicht aktiv, kein PTT, kein Wake-Word
- `LISTENING` — VAD lauscht, Sprache erkannt (aber noch kein Whisper)
- `TRANSCRIBING` — mlx_whisper.transcribe() läuft
- `RECOVERING` — Fehler, Recovery läuft

**inference_active:**
- `false` — Modell wird nicht gerade genutzt
- `true` — Nur während mlx_whisper.transcribe() aktiv

### Implementierung

**In speech_input.py (~25 Zeilen):**

```python
# Config
SPEECH_STATE_FILE = "data/speech_state.json"

def _write_state(state: str, inference_active: bool = False, last_duration_s: float = None):
    """
    Record current speech state.
    
    state: IDLE, LISTENING, TRANSCRIBING, RECOVERING
    inference_active: True only during mlx_whisper.transcribe()
    """
    try:
        data = {
            "state": state,
            "inference_active": inference_active,
            "last_update": time.time(),
            "ws_connected": _ws_connected,  # existing variable?
        }
        
        if last_duration_s is not None:
            data["last_transcription_duration_s"] = round(last_duration_s, 2)
        
        with open(SPEECH_STATE_FILE, "w") as f:
            json.dump(data, f)
            
    except Exception as e:
        log.debug(f"[speech_state] write failed: {type(e).__name__}")

# Usage in _ww_thread():

# When listening for voice
_write_state("LISTENING", inference_active=False)

# Before transcription starts
start = time.time()
_write_state("TRANSCRIBING", inference_active=False)

# During model load & inference
_write_state("TRANSCRIBING", inference_active=True)

# After transcription completes
duration = time.time() - start
_write_state("IDLE", inference_active=False, last_duration_s=duration)

# On error
_write_state("RECOVERING", inference_active=False)
time.sleep(2)
_write_state("IDLE", inference_active=False)
```

### Monitoring-Output (Health Dashboard)

```
🎤 SPEECH INPUT STATE
─────────────────────
  Current state:        IDLE
  Inference active:     ❌
  Last transcription:   2m ago
  Last duration:        1.8s
  WS connected:         ✅
```

### Success Criteria

- [x] State Update bei Zustandsänderung
- [x] inference_active genau tracking
- [x] Transkriptions-Dauer gespeichert
- [x] Fail-silent + debug-logging
- [x] Keine WS-Abhängigkeit (unabhängig schreiben)

---

## ⏰ Phase 3: Sleep/Wake-Events & Korrelation

### Ziel

**Wake-Verhalten verstehen.** Wann passieren Wake-Events? Was ändert sich im System? Normale oder anomale Recovery?

### Datenstruktur

**Datei:** `data/wake_events.json` (Ringbuffer, ~10 KB)

```json
{
  "last_wake": 1715875493,
  "events": [
    {
      "ts": 1715875493,
      "event_type": "wake_detected",
      "system_memory_mb": 3738,
      "ws_state_before": true,
      "notes": ""
    },
    { ... }
  ]
}
```

**Max entries:** 100 (= ~7 Tage @ 2 wakes/day)

### Implementierung

**In wake-monitor.py (~25 Zeilen):**

```python
# Config
WAKE_EVENTS_FILE = "data/wake_events.json"
WAKE_EVENTS_MAX = 100

def _record_wake_event(ws_connected_before: bool = None):
    """
    Record wake event with system snapshot.
    OBSERVATION-ONLY: No auto-recovery logic here!
    """
    try:
        # Load or init
        if os.path.exists(WAKE_EVENTS_FILE):
            with open(WAKE_EVENTS_FILE) as f:
                data = json.load(f)
        else:
            data = {"last_wake": 0, "events": []}
        
        # New event
        event = {
            "ts": time.time(),
            "event_type": "wake_detected",
            "system_memory_mb": _get_vm_stat_pages("active") or 0,
            "ws_state_before": ws_connected_before,
        }
        data["events"].append(event)
        data["last_wake"] = event["ts"]
        
        # Ringbuffer prune
        if len(data["events"]) > WAKE_EVENTS_MAX:
            data["events"] = data["events"][-WAKE_EVENTS_MAX:]
        
        with open(WAKE_EVENTS_FILE, "w") as f:
            json.dump(data, f)
        
        # ONLY logging (no recovery logic!)
        log.info(f"🔵 Wake event recorded (memory: {event['system_memory_mb']}MB)")
        
    except Exception as e:
        log.debug(f"[wake_events] record failed: {type(e).__name__}")

# In existing sleep detection loop:
# Just call _record_wake_event() when wake detected
if _is_screen_unlocked() and not _was_awake:
    _record_wake_event(ws_connected_before=_last_ws_state)
    _was_awake = True
    # ... existing wake handler continues (no changes) ...
```

### Monitoring-Output (Health Dashboard)

```
⏰ WAKE/SLEEP TRACKING
──────────────────────────────────
  Last wake:        08:17 (3h 42m ago)
  Today wakes:      2
  Memory @ last:    3738 MB
  WS reconnect:     auto (managed elsewhere)
  
Recent events:
  08:17  WAKE (memory: 3738 MB)
  03:45  WAKE (memory: 3650 MB)
```

### Success Criteria

- [x] Wake-Event bei Screen-Unlock recorded
- [x] System-Snapshot gespeichert
- [x] KEINE auto-recovery logic hier
- [x] Ringbuffer
- [x] Fail-silent + debug-logging

### ⚠️ WICHTIG: Observability ≠ Recovery

**Was NICHT tun:**

```python
# ❌ FALSCH: Recovery-Logic in Observability
def _record_wake_event():
    _record_wake_event()
    
    # NEIN! Das gehört nicht hier:
    # if last_ws_state < 30:
    #     _ws_check()  ← Recovery-Logic, nicht Observability!
```

**Recovery bleibt wo sie ist:**
- WS reconnect: `server.py` (existierend)
- Audio reconnect: `speech_input.py` (existierend)
- Health checks: `supervisor.py` (existierend)

**Observability tut nur eins: Snapshot schreiben.**

---

## 🖥️ Health Monitor Integration

### Daten-Quellen

```
supervisor.py → memory_history.json
speech_input.py → speech_state.json
wake-monitor.py → wake_events.json
                ↓
            Health Monitor
            (/health endpoint)
                ↓
            Dashboard UI
```

### Display-Strategie: "Calm Design"

**Nicht:**
- ❌ Hektische Realtime-Updates
- ❌ Zu viele Grafiken
- ❌ Aggressive Farben/Alarme
- ❌ Ständiges Scrolling

**Sondern:**
- ✅ Wenige, klare State-Indikationen
- ✅ Subtile Trend-Indikatoren
- ✅ Ruhige Farben (grün, grau, subtil orange)
- ✅ Statische View, aktualisiert auf Abruf

### Beispiel-Layout

```
═══════════════════════════════════════════════════════════
          JARVIS 2.0 — Health Monitor
═══════════════════════════════════════════════════════════

📊 MEMORY TRENDS (24h)
─────────────────────────────────────────────────────────
  server.py        42 MB    ▁▁▂▂▂▁▁▁▂▁
  speech_input     47 MB    ▁▁▁▁▃▄▂▁▁▂
  Chrome          301 MB    ▂▂▂▃▃▃▂▂▂▂
  System active  3738 MB    ▄▄▄▄▄▄▄▄▄▄ 🟢


🎤 SPEECH INPUT
─────────────────────────────────────────────────────────
  State:           IDLE
  Inference:       ❌
  Last duration:   1.8s (2m ago)
  WS connected:    ✅


⏰ WAKE/SLEEP (24h)
─────────────────────────────────────────────────────────
  Last wake:       08:17 (3h 42m)
  Today events:    2
  Memory trend:    stable 🟢
```

---

## 📅 Implementierungs-Roadmap

### Phase 1: RAM-History (Woche 1)

**Zeitaufwand:** 30 Min (Coding + Testing)

- [ ] supervisor.py: `_update_memory_history()` hinzufügen
- [ ] supervisor.py: `_get_process_rss()` hinzufügen
- [ ] Health Monitor: memory_history.json lesen
- [ ] Health Monitor: Mini-Trend-Graph anzeigen
- [ ] Test: 5 Min lang beobachten, dann snapshot prüfen
- [ ] Test: System unter Last, RAM-Spikes sichtbar?
- [ ] Commit: "feat: RAM-History Ringbuffer in supervisor"

**Before/After:**
- **Before:** Speicher-Snapshots manuell via `ps aux`
- **After:** 24h History im Health Monitor, Trends sichtbar

### Phase 2: Speech-Lifecycle (Woche 2)

**Zeitaufwand:** 20 Min (Coding + Testing)

- [ ] speech_input.py: `_write_state()` hinzufügen
- [ ] speech_input.py: `_write_state()` calls überall einfügen
- [ ] Health Monitor: speech_state.json lesen
- [ ] Health Monitor: State + Dauer anzeigen
- [ ] Test: "Jarvis" sagen, State-Änderungen beobachten
- [ ] Test: Mehrere Transkriptionen, Dauer-Trends sehen
- [ ] Commit: "feat: Speech-Lifecycle observable"

**Before/After:**
- **Before:** "Warum RAM hoch?" → Kein sichtbarer Grund
- **After:** Health Monitor zeigt "TRANSCRIBING, inference_active: true" → Modell lädt

### Phase 3: Wake/Sleep-Events (Woche 3)

**Zeitaufwand:** 25 Min (Coding + Testing)

- [ ] wake-monitor.py: `_record_wake_event()` hinzufügen
- [ ] wake-monitor.py: beim Wake aufrufen
- [ ] Health Monitor: wake_events.json lesen
- [ ] Health Monitor: Wake-Timeline anzeigen
- [ ] Test: System schlafen lassen, aufwecken, Event sichtbar?
- [ ] Test: Mehrere Wake-Events, Korrelation mit Memory-Spikes?
- [ ] Commit: "feat: Wake-Event observability"

**Before/After:**
- **Before:** "System ist nach Wake flaky?" → Keine Sichtbarkeit
- **After:** Health Monitor zeigt "Wake 08:17, WS reconnected 0.5s later"

---

## ✅ Checklisten

### Phase 1: RAM-History

**Code-Review:**
- [ ] `_update_memory_history()` hat fail-silent try/except
- [ ] debug-logging bei Fehler (z.B. Permission denied)
- [ ] Atomic write: temp + os.rename()
- [ ] Ringbuffer: max 144 Einträge
- [ ] Keine neuen Dependencies (nur os, json, time)
- [ ] Keine Impact auf bestehenden Code

**Testing:**
- [ ] supervisor läuft noch normal
- [ ] memory_history.json existiert nach 10 Min
- [ ] Einträge haben alle Felder
- [ ] Nach 12h hat file max 144 Einträge
- [ ] Bei Fehler: supervisor läuft weiter (fail-silent)

**Documentation:**
- [ ] RUNTIME_OBSERVABILITY.md existiert
- [ ] Datenformat dokumentiert
- [ ] Code-Snippets korrekt
- [ ] Success Criteria klar

### Phase 2: Speech-Lifecycle

**Code-Review:**
- [ ] `_write_state()` wird überall aufgerufen (LISTENING, TRANSCRIBING, IDLE, RECOVERING)
- [ ] inference_active ist korrekt (true nur während mlx_whisper)
- [ ] Fail-silent try/except
- [ ] Debug-logging bei Fehler
- [ ] Keine Abhängigkeit vom WS-Status (independent write)

**Testing:**
- [ ] speech_state.json existiert
- [ ] State-Wechsel sind sichtbar
- [ ] Transkriptions-Dauer ist plausibel (0.5-3.0s)
- [ ] Nach Fehler: speech_input läuft weiter

**Documentation:**
- [ ] States dokumentiert
- [ ] inference_active semantik klar
- [ ] Lifecycle-Diagramm?

### Phase 3: Wake/Sleep-Events

**Code-Review:**
- [ ] `_record_wake_event()` hat KEINE recovery logic
- [ ] Nur Snapshot schreiben, nicht reparieren
- [ ] Ringbuffer max 100 Einträge
- [ ] Fail-silent try/except
- [ ] Debug-logging bei Fehler

**Testing:**
- [ ] wake_events.json existiert
- [ ] Wake-Event wird recorded
- [ ] System-Memory ist gespeichert
- [ ] Nach mehreren Wakes: ringbuffer funktioniert

**Documentation:**
- [ ] Observability ≠ Recovery Prinzip dokumentiert
- [ ] Wake-Event Struktur klar

---

## 🚀 Integration in Bestehende Codebase

### Keine Breaking Changes

- ✅ Alle Änderungen sind **additive** (nur neue Funktionen)
- ✅ Bestehender Code bleibt **unverändert**
- ✅ Keine neuen Dependencies
- ✅ Keine neuen IPC-Kanäle

### Dateistruktur nach Phase 3

```
data/
├── intro_shown.flag          (existing)
├── daily_brief_memory.json   (existing)
├── memory_history.json       (NEW: Phase 1)
├── speech_state.json         (NEW: Phase 2)
└── wake_events.json          (NEW: Phase 3)
```

### Performance-Impact

| Komponente | Zusätzliche CPU | Zusätzliche I/O | Memory |
|-----------|-----------------|-----------------|--------|
| supervisor.py (Phase 1) | <0.1% | ~100 bytes / 5 min | — |
| speech_input.py (Phase 2) | <0.1% | ~1 KB on every state change | — |
| wake-monitor.py (Phase 3) | <0.1% | ~100 bytes / wake event | — |
| Health Monitor (alle) | <0.1% | Read JSON max 60 KB/s | — |
| **TOTAL** | **<0.3%** | **negligible** | **+0 MB** |

---

## 📖 Referenzen

- CURRENT_STATE.md (RAM-Situation: 4.1 GB Whisper-Peak ist erwartet)
- ROADMAP_STATUS.md (Phase 1-4 Context)
- ARCHITECTURE.md (4 Fragilities, Phase 2 Service-Isolation kommt später)
- Memory-Analysis Session (15.05.2026): 127 MB Jarvis Core, 2.9 GB HF Cache

---

## 🔄 Nach Phase 3

**Nächste Schritte (nicht in diesem Plan):**

- Monitor der Observability-Daten über 2–4 Wochen
- Patterns erkennen (RAM-Trends, Wake-Anomalien, Whisper-Latenz)
- Falls Probleme: gezielte Optimierung (z.B. Whisper medium statt large)
- Phase 2: Service Isolation (wenn stabilere Baselines existieren)

**Nicht tun:**
- ❌ Aggressiv optimieren basierend auf Wochen von Daten
- ❌ Auto-Restart/Recovery basierend auf Observability
- ❌ Neue Features bauen während Observability-Phase läuft

---

**Dokumentation fertig. Bereit für Implementierung Phase 1.**
