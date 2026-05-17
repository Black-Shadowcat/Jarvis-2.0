#!/usr/bin/env python3
"""
Jarvis V3 — Spracheingabe via Whisper + F19 Push-to-Talk + Wake-Word
Verbindet sich mit dem Jarvis-Server via WebSocket und sendet transkribierten Text.

Aktivierung:
  • F19 halten    → Push-to-Talk (sofort)
  • "Jarvis, ..." → Wake-Word via VAD + Whisper

Gesprächsmodus:
  Nach einer Wake-Word-Antwort bleibt das Mikrofon kurz offen (blau im HUD).
  Wenn der Nutzer spricht, wird der Befehl verarbeitet und das Gespräch
  fortgeführt. Bei Stille geht Jarvis nach wenigen Sekunden in den Ruhezustand.
"""

import asyncio
import difflib
import gc
import logging
import os
import psutil
import queue
import re
import signal
import subprocess
import sys
import threading
import time
import tracemalloc
import urllib.request
import json
import numpy as np
import sounddevice as sd
import mlx_whisper
from pynput import keyboard
import websockets
from logging.handlers import RotatingFileHandler

# Configure logging with rotation (prevent unbounded disk growth)
_log_dir = os.path.expanduser("~/Library/Logs/jarvis-v2")
os.makedirs(_log_dir, exist_ok=True)
_log_file = os.path.join(_log_dir, "speech.log")

log = logging.getLogger("stt")
log.setLevel(logging.INFO)

# File handler with rotation: 10 MB max size, keep 5 backups
_handler = RotatingFileHandler(_log_file, maxBytes=10*1024*1024, backupCount=5)
_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S"))
log.addHandler(_handler)

# Also log to stdout (visible in launchd logs)
_stdout_handler = logging.StreamHandler(sys.stdout)
_stdout_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S"))
log.addHandler(_stdout_handler)

SAMPLE_RATE    = 16000
CHUNK_SIZE     = 1600   # 100 ms pro Callback-Chunk
PTT_KEY        = keyboard.Key.f19
SERVER_URL     = "ws://localhost:8340/ws/stt"
PTT_API        = "http://localhost:8340/api/ptt"
WHISPER_MODEL  = "mlx-community/whisper-large-v3-mlx"
MIN_DURATION   = 0.6    # Sekunden — kürzere Aufnahmen werden verworfen

# Phase 2 observability
SPEECH_STATE_FILE = "data/speech_state.json"

# Wake-Word VAD-Schwellwerte
WW_VOICE_RMS    = 0.002   # Sprache erkannt (oberhalb) — optimiert für Sennheiser Profile USB
WW_SILENCE_RMS  = 0.001   # Stille (unterhalb)
WW_MAX_SECS     = 5.0    # Maximale Länge des Erkennung-Snippets
WW_SILENCE_SECS = 0.8    # Stille nach letztem Wort → Snippet fertig
WW_CMD_SILENCE  = 1.5    # Stille nach Befehl → Aufnahme beenden

# Memory limits (prevent unbounded growth)
MAX_AUDIO_BUFFER_SECS = 30  # Max 30s of audio in _audio_buffer before forced stop
MAX_SNIPPET_SECS = 10       # Max 10s per snippet accumulation

# VAD Kalibrierungs-Pfad
VAD_CALIB_PATH = os.path.join(os.path.dirname(__file__), "data", "vad_calibration.json")

def _load_vad_calibration():
    global WW_VOICE_RMS, WW_SILENCE_RMS, WW_MAX_SECS, WW_SILENCE_SECS, WW_CMD_SILENCE
    if os.path.exists(VAD_CALIB_PATH):
        try:
            with open(VAD_CALIB_PATH) as f:
                data = json.load(f)
            old_voice, old_silence = WW_VOICE_RMS, WW_SILENCE_RMS
            WW_VOICE_RMS   = data.get("voice_rms",    WW_VOICE_RMS)
            WW_SILENCE_RMS = data.get("silence_rms",  WW_SILENCE_RMS)
            WW_MAX_SECS    = data.get("max_secs",     WW_MAX_SECS)
            WW_SILENCE_SECS = data.get("silence_secs", WW_SILENCE_SECS)
            WW_CMD_SILENCE = data.get("cmd_silence",  WW_CMD_SILENCE)
            if old_voice != WW_VOICE_RMS or old_silence != WW_SILENCE_RMS:
                print(f"[VAD] Calibration loaded: voice={WW_VOICE_RMS:.4f} silence={WW_SILENCE_RMS:.4f}")
        except Exception as e:
            print(f"[VAD] Calibration load error (using defaults): {e}")

_load_vad_calibration()

# Bekannte Whisper-Fehltranskriptionen von "Jarvis"
_JARVIS_ALIASES = {"jarvis", "javis", "jarwis", "jarves", "garvis", "jarvis.", "javis."}

def _is_jarvis(text: str) -> bool:
    """True wenn Text 'Jarvis' enthält — exakt, als Alias oder per Fuzzy-Match."""
    for word in re.split(r'\W+', text.lower()):
        if not word:
            continue
        if word in _JARVIS_ALIASES:
            return True
        if len(word) >= 4 and difflib.SequenceMatcher(None, word, "jarvis").ratio() >= 0.80:
            return True
    return False


# Bekannte Whisper-Halluzinationen bei Stille
_HALLUCINATIONS = {
    "vielen dank.", "vielen dank", "danke.", "danke", "danke schön.",
    "danke schön", "bitte.", "bitte", "tschüss.", "tschüss",
    "thank you.", "thank you", "thanks.", "thanks", "bye.", "bye",
    "you", "you.", ".", "..", "...",
}

_audio_buffer: list  = []
_recording:    bool  = False
_buffer_lock         = threading.Lock()
_loop:  asyncio.AbstractEventLoop = None
_queue: asyncio.Queue             = None

_detect_q: queue.Queue = queue.Queue(maxsize=500)

_in_conversation:    bool  = False   # True nach Wake-Word → Auto-Listen aktiv
_ww_muted:           bool  = False   # Wake-Word via HUD-Click deaktiviert
_jarvis_speaking:    bool  = False   # True während Jarvis TTS abspielt → WW stumm
_speaking_started_at: float = 0.0    # Zeitstempel des letzten speaking_start

# ── RMS-Watchdog für Audio-Device-Recovery nach Sleep/Wake ────────────────
_last_nonzero_rms_time: float = 0.0  # Letzter Zeitpunkt mit Non-Zero-Audio
_stream_ref: sd.InputStream = None   # Referenz zum Audio-Stream für Restart


# ── PTT-State an Browser melden ───────────────────────────────────────────

def _notify_ptt(state: str):
    """Sendet PTT/Listen-State an Server → Browser-Broadcast."""
    try:
        req = urllib.request.Request(f"{PTT_API}/{state}", method="POST")
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass


# ── Memory Profiling (detect leaks) ──────────────────────────────────────

def _log_memory_snapshot(label: str):
    """Log current memory usage for C3 leak detection."""
    try:
        gc.collect()  # Force garbage collection before snapshot
        snap = tracemalloc.take_snapshot()
        top_stats = snap.statistics('lineno')[:3]
        total_mb = sum(stat.size for stat in snap.statistics('lineno')) / 1024 / 1024
        log.debug(f"[memory] {label}: {total_mb:.1f} MB total")
        for stat in top_stats:
            log.debug(f"  {stat}")
    except Exception as e:
        log.debug(f"[memory] snapshot failed: {e}")


# ── Phase 2 Observability: Speech State Tracking ────────────────────────

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
            "ws_connected": _ws_connected if '_ws_connected' in globals() else False,
        }

        if last_duration_s is not None:
            data["last_transcription_duration_s"] = round(last_duration_s, 2)

        with open(SPEECH_STATE_FILE, "w") as f:
            json.dump(data, f)

    except Exception as e:
        log.debug(f"[speech_state] write failed: {type(e).__name__}")


# ── Gemeinsamer Start/Stop ────────────────────────────────────────────────

def _start_recording(source: str = "ptt"):
    global _recording
    if _recording:
        return
    _recording = True
    with _buffer_lock:
        _audio_buffer.clear()
    log.info(f"● Aufnahme läuft… [{source}]")
    threading.Thread(target=_notify_ptt, args=("start",), daemon=True).start()


def _stop_recording_and_transcribe(source: str = "ptt"):
    global _recording
    if not _recording:
        return
    _recording = False
    threading.Thread(target=_notify_ptt, args=("stop",), daemon=True).start()
    with _buffer_lock:
        chunks = list(_audio_buffer)
        _audio_buffer.clear()  # B020 FIX: Clear buffer after copy to prevent accumulation
    if chunks:
        audio = np.concatenate(chunks).flatten()
        duration = len(audio) / SAMPLE_RATE
        log.info(f"◇ Aufnahme beendet: {duration:.2f}s [{source}]")
        if duration < MIN_DURATION:
            log.info(f"  ✗ zu kurz — verworfen (min: {MIN_DURATION}s) [{source}]")
        else:
            log.info(f"  ✓ Transkription gestartet [{source}]")
            threading.Thread(target=_transcribe, args=(audio,), daemon=True).start()
    else:
        log.info(f"✗ keine Aufnahme [{source}]")


# ── Audio-Callback ────────────────────────────────────────────────────────

def _audio_cb(indata, frames, time_info, status):
    global _last_nonzero_rms_time

    # RMS-Tracking für Watchdog (detect audio-device death after sleep)
    rms = np.sqrt(np.mean(indata**2))
    if rms > 0.0001:  # Non-silence threshold (avoid floating-point noise)
        _last_nonzero_rms_time = time.time()

    if _recording:
        with _buffer_lock:
            _audio_buffer.append(indata.copy())
    elif not _jarvis_speaking or _in_conversation:
        try:
            _detect_q.put_nowait(indata.copy())
        except queue.Full:
            pass


# ── Tastatur ──────────────────────────────────────────────────────────────

def _on_press(key):
    if key == PTT_KEY:
        global _in_conversation
        _in_conversation = False  # F19 beendet aktiven Gesprächsmodus
        _start_recording("F19")


def _on_release(key):
    if key == PTT_KEY:
        _stop_recording_and_transcribe("F19")


# ── Whisper ───────────────────────────────────────────────────────────────

def _transcribe(audio: np.ndarray):
    log.info("■ Transkribiere…")
    try:
        _log_memory_snapshot("[transcribe] before")
        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=WHISPER_MODEL,
            language="de",
        )
        text = result["text"].strip()
        if not text or text.lower() in _HALLUCINATIONS:
            log.debug(f"(verworfen: '{text}')")
            return
        log.info(f"» {text}")
        asyncio.run_coroutine_threadsafe(_queue.put(text), _loop)
    finally:
        # Explicitly free the audio buffer and force GC
        del audio
        gc.collect()
        _log_memory_snapshot("[transcribe] after")


# ── RMS-Watchdog: Audio-Device-Recovery nach Sleep/Wake ────────────────────

def _rms_watchdog():
    """
    Monitor audio stream for death after system sleep.
    If >60s of silence (RMS ≈ 0), restart the stream.

    Problem: After macOS sleep, PortAudio CoreAudio handle becomes invalid.
    The stream appears to run but delivers only zeros. This watchdog detects
    that silent state and restarts the stream without a full process restart.
    """
    global _last_nonzero_rms_time, _stream_ref

    log.info("[watchdog] RMS-Watchdog gestartet (60s Timeout für Audio-Device-Recovery)")

    while True:
        time.sleep(10)  # Check every 10 seconds

        if _stream_ref is None:
            continue

        # Check if stream has been silent for >60s
        elapsed = time.time() - _last_nonzero_rms_time

        if elapsed > 60 and _last_nonzero_rms_time > 0:
            # Audio device is dead — recover without full restart
            log.warning(f"[watchdog] Audio-Device silent für {elapsed:.0f}s — restart stream")
            _write_state("RECOVERING")

            try:
                _stream_ref.stop()
                time.sleep(0.5)
                _stream_ref.start()
                log.info("[watchdog] ✓ Audio-Stream neugestartet")
                _write_state("IDLE")
            except Exception as e:
                log.error(f"[watchdog] ✗ Stream-Restart fehlgeschlagen: {e}")
                _write_state("IDLE")


# ── Auto-Listen (Gesprächsmodus nach Wake-Word-Antwort) ───────────────────

def _auto_listen(timeout: float):
    """
    Öffnet Mikrofon für timeout Sekunden nach einer Wake-Word-Antwort.
    Phase 1: Warte auf Stimme (blau im HUD, detect_q).
    Phase 2: Sprache erkannt → aufnehmen bis Stille (_audio_buffer).
    """
    global _in_conversation

    if _recording or _ww_muted:
        log.debug(f"auto_listen skip: recording={_recording}, muted={_ww_muted}")
        return

    log.info(f"▶ Auto-Listen: Mikrofon offen für {timeout}s")
    _detect_q_flush()
    threading.Thread(target=_notify_ptt, args=("listen_open",), daemon=True).start()

    start_t = time.time()

    # Phase 1: Warte auf Stimmeinsatz
    while (time.time() - start_t) < timeout and not _recording and not _ww_muted:
        try:
            chunk = _detect_q.get(timeout=0.3)
        except queue.Empty:
            continue
        rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
        if rms < WW_VOICE_RMS:
            continue

        # Phase 2: Stimme erkannt → Aufnahme starten
        log.info(f"  ▶ Stimme erkannt (RMS={rms:.4f}) → Phase 2 starten")
        _start_recording("auto-listen")

        silence_c = 0.0
        max_secs  = 12.0
        rec_start = time.time()
        while _recording and (time.time() - rec_start) < max_secs:
            time.sleep(0.1)

            # Check buffer size to prevent unbounded growth
            with _buffer_lock:
                buffer_secs = sum(len(chunk) for chunk in _audio_buffer) / SAMPLE_RATE
                if buffer_secs > MAX_AUDIO_BUFFER_SECS:
                    log.warning(f"auto_listen: buffer exceeded {MAX_AUDIO_BUFFER_SECS}s — stopping")
                    break
                if not _audio_buffer:
                    continue
                recent = _audio_buffer[-1]

            rms_c = float(np.sqrt(np.mean(recent.astype(np.float32) ** 2)))
            if rms_c < WW_SILENCE_RMS:
                silence_c += 0.1
                if silence_c >= WW_CMD_SILENCE:
                    break
            else:
                silence_c = 0.0

        _stop_recording_and_transcribe("auto-listen")
        threading.Thread(target=_notify_ptt, args=("listen_close",), daemon=True).start()
        return

    # Timeout ohne Sprache → Gesprächsmodus beenden
    log.info("  ⏱ Auto-Listen: Timeout ohne Spracheinsatz — Gesprächsmodus beendet")
    _in_conversation = False
    threading.Thread(target=_notify_ptt, args=("listen_close",), daemon=True).start()


# ── Queue-Hilfsfunktion ───────────────────────────────────────────────────

def _detect_q_flush():
    while not _detect_q.empty():
        try:
            _detect_q.get_nowait()
        except queue.Empty:
            break


# ── Wake-Word-Detektor (VAD + Whisper) ────────────────────────────────────

def _ww_thread():
    """
    Lauscht auf Sprache, transkribiert kurze Snippets via Whisper.
    Wenn 'Jarvis' erkannt → Befehl extrahieren oder auf Folgebefehl warten.
    """
    global _jarvis_speaking
    log.info("Wake-Word aktiv — VAD+Whisper, Aktivierungswort: 'Jarvis'")
    _write_state("IDLE", inference_active=False)  # Phase 2: Initial state
    chunk_secs = CHUNK_SIZE / SAMPLE_RATE  # 0.1 s
    chunk_count = 0
    last_rms_log = 0
    last_gc = time.time()

    while True:
        # Periodic garbage collection (every 30s) to prevent unbounded growth
        if time.time() - last_gc > 30:
            gc.collect()
            _log_memory_snapshot("[_ww_thread] periodic GC")
            last_gc = time.time()

        # 1. Warte auf Sprachbeginn (RMS-VAD)
        # Timeout nötig: wenn _jarvis_speaking=True füllt _audio_cb die Queue nicht —
        # ohne Timeout würde .get() ewig blockieren und der Auto-Reset nie greifen.
        try:
            chunk = _detect_q.get(timeout=1.0)
            chunk_count += 1
        except queue.Empty:
            if chunk_count > 0 and time.time() - last_rms_log > 10:
                log.debug(f"[chunk count: {chunk_count}] Audio wird empfangen aber unterhalb RMS-Schwelle")
                chunk_count = 0
            if _jarvis_speaking and time.time() - _speaking_started_at > 25:
                log.warning("speaking_start timeout (>25s) — _jarvis_speaking auto-reset")
                _jarvis_speaking = False
            continue
        rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
        last_rms_log = time.time()
        if _recording or _ww_muted:
            continue
        if _jarvis_speaking:
            if time.time() - _speaking_started_at > 25:
                log.warning("speaking_start timeout (>25s) — _jarvis_speaking auto-reset")
                _jarvis_speaking = False
            else:
                continue
        if rms < WW_VOICE_RMS:
            if time.time() - last_rms_log < 0.5:
                log.debug(f"  RMS={rms:.5f} < {WW_VOICE_RMS:.5f}")
            continue

        # 2. Sprache erkannt → sofort visuelles Feedback + Snippet sammeln
        _write_state("LISTENING", inference_active=False)  # Phase 2: Listening
        threading.Thread(target=_notify_ptt, args=("listen_open",), daemon=True).start()
        snippet: list = [chunk.astype(np.float32)]
        silence_secs = 0.0
        total_secs   = chunk_secs

        while total_secs < WW_MAX_SECS and not _recording and not _ww_muted and not _jarvis_speaking:
            # Safety limit: prevent snippet from growing unbounded
            if total_secs > MAX_SNIPPET_SECS:
                log.warning(f"_ww_thread: snippet exceeded {MAX_SNIPPET_SECS}s — truncating")
                break

            try:
                c = _detect_q.get(timeout=0.3)
            except queue.Empty:
                break
            snippet.append(c.astype(np.float32))
            total_secs += chunk_secs
            rms_c = float(np.sqrt(np.mean(c.astype(np.float32) ** 2)))
            if rms_c < WW_SILENCE_RMS:
                silence_secs += chunk_secs
                if silence_secs >= WW_SILENCE_SECS:
                    break
            else:
                silence_secs = 0.0

        if _recording or _ww_muted:
            threading.Thread(target=_notify_ptt, args=("listen_close",), daemon=True).start()
            _detect_q_flush()
            continue

        # 3. Transkribiere Snippet
        audio_snip = np.concatenate(snippet).flatten()
        del snippet  # Explicit cleanup

        if len(audio_snip) / SAMPLE_RATE < 0.3:
            threading.Thread(target=_notify_ptt, args=("listen_close",), daemon=True).start()
            _write_state("IDLE", inference_active=False)  # Phase 2: Back to idle
            del audio_snip
            gc.collect()
            continue

        _write_state("TRANSCRIBING", inference_active=False)  # Phase 2: Before model load
        start_time = time.time()
        try:
            _log_memory_snapshot("[ww_thread] before whisper")
            result = mlx_whisper.transcribe(
                audio_snip,
                path_or_hf_repo=WHISPER_MODEL,
                language="de",
                initial_prompt="Jarvis.",
            )
            transcription_duration = time.time() - start_time
            text = result["text"].strip()
            _log_memory_snapshot("[ww_thread] after whisper")
        finally:
            del audio_snip  # Explicit cleanup of audio buffer
            gc.collect()

        _detect_q_flush()
        _write_state("IDLE", inference_active=False, last_duration_s=transcription_duration)  # Phase 2: Done

        if not text or text.lower() in _HALLUCINATIONS:
            threading.Thread(target=_notify_ptt, args=("listen_close",), daemon=True).start()
            continue
        log.info(f"WW-Snippet: '{text}'")
        if not _is_jarvis(text):
            threading.Thread(target=_notify_ptt, args=("listen_close",), daemon=True).start()
            continue

        log.info(f'Wake-Word erkannt: "{text}"')
        global _in_conversation
        _in_conversation = True

        # 4. Befehl aus dem gleichen Utterance extrahieren
        command = re.sub(
            r'^[\s,!.]*jarvis[\s,!.]*', '', text, flags=re.IGNORECASE
        ).strip()

        if command and command.lower() not in _HALLUCINATIONS and len(command) > 3:
            # Befehl inline → direkt senden
            log.info(f"Befehl inline: » {command}")
            threading.Thread(target=_notify_ptt, args=("stop",), daemon=True).start()
            asyncio.run_coroutine_threadsafe(_queue.put(command), _loop)
        else:
            # Nur "Jarvis" → sofort aktivieren, Auto-Listen übernimmt Folgebefehl
            log.info("Jarvis aktiviert → sende activate")
            threading.Thread(target=_notify_ptt, args=("stop",), daemon=True).start()
            asyncio.run_coroutine_threadsafe(_queue.put("Jarvis activate"), _loop)


# ── WebSocket Client ──────────────────────────────────────────────────────

async def _sender(ws):
    while True:
        text = await _queue.get()
        await ws.send(json.dumps({"text": text}))


async def _receiver(ws):
    """Empfängt Nachrichten vom Server: speaking_start/end, listen_open, ww_mute."""
    global _in_conversation, _ww_muted, _jarvis_speaking, _speaking_started_at
    async for raw in ws:
        try:
            data = json.loads(raw)
        except Exception:
            continue
        msg_type = data.get("type")
        log.debug(f"← WS-Msg: {msg_type}")

        if msg_type == "speaking_start":
            _jarvis_speaking = True
            _speaking_started_at = time.time()
            log.info("[MUTE] Jarvis spricht — Mikrofon gestummt")

        elif msg_type == "speaking_end":
            _jarvis_speaking = False
            _detect_q_flush()
            log.info("[UNMUTE] Jarvis fertig — Mikrofon aktiv")

        elif msg_type == "listen_open":
            _jarvis_speaking = False
            if _in_conversation and not _ww_muted:
                timeout = data.get("timeout", 6)
                threading.Thread(target=_auto_listen, args=(timeout,), daemon=True).start()

        elif msg_type == "ww_mute":
            _ww_muted = data.get("muted", False)
            log.info(f"Wake-Word {'deaktiviert' if _ww_muted else 'aktiviert'}")


# ── B021: Prevent Duplicate speech_input.py Processes (File-Lock) ──────────
def _ensure_single_instance():
    """Ensure only one speech_input.py process runs using file-based lock."""
    lock_file = os.path.expanduser("~/.jarvis-speech-input.lock")
    current_pid = os.getpid()

    try:
        # Read existing lock file if it exists
        if os.path.exists(lock_file):
            with open(lock_file, 'r') as f:
                old_pid_str = f.read().strip()
            try:
                old_pid = int(old_pid_str)
                # Check if old process still exists
                if psutil.pid_exists(old_pid):
                    old_proc = psutil.Process(old_pid)
                    if 'speech_input.py' in ' '.join(old_proc.cmdline() or []):
                        log.warning(f"Killing existing speech_input.py process PID {old_pid}")
                        old_proc.kill()
                        time.sleep(0.2)
            except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Write current PID to lock file (atomic via temp file)
        with open(lock_file, 'w') as f:
            f.write(str(current_pid))
        log.info(f"[B021] Single-instance lock acquired (PID {current_pid})")

    except Exception as e:
        log.warning(f"[B021] Lock initialization failed: {e} (continuing anyway)")


async def _run():
    global _loop, _queue, _stream_ref, _last_nonzero_rms_time

    # Enable memory profiling for C3 leak detection
    tracemalloc.start()

    # B020 WORKAROUND: DISABLED — caused issues with process restart loop
    # Reverting to rely on _audio_buffer.clear() fix instead
    async def _memory_watchdog_disabled():
        pass  # Do nothing — fix should prevent leak

    _loop  = asyncio.get_running_loop()
    _loop.add_signal_handler(signal.SIGUSR2, _load_vad_calibration)  # M10: Live-reload VAD calibration
    _queue = asyncio.Queue()

    # B020: Memory watchdog disabled (was causing restart loop issues)
    # asyncio.create_task(_memory_watchdog_disabled())

    stream   = sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                               dtype="float32", blocksize=CHUNK_SIZE,
                               callback=_audio_cb)
    listener = keyboard.Listener(on_press=_on_press, on_release=_on_release)
    _stream_ref = stream  # Store reference for watchdog restart

    stream.start()
    listener.start()

    # Initialize RMS watchdog time
    _last_nonzero_rms_time = time.time()

    threading.Thread(target=_ww_thread, daemon=True).start()
    threading.Thread(target=_rms_watchdog, daemon=True).start()  # NEW: RMS watchdog

    log.info("─" * 44)
    log.info("  Jarvis V3 — Spracheingabe")
    log.info("─" * 44)
    log.info("  F19 halten       → Push-to-Talk")
    log.info("  'Jarvis, ...'    → Wake-Word")
    log.info("  HUD-Click        → Mikrofon stumm/aktiv")
    log.info(f"  Server: {SERVER_URL}")
    log.info("─" * 44)

    try:
        async for ws in websockets.connect(SERVER_URL, ping_interval=20):
            global _jarvis_speaking, _in_conversation
            _jarvis_speaking = False   # Reset bei (Re-)Verbindung
            _in_conversation = False
            log.info("  Server verbunden ✓")
            try:
                await asyncio.gather(_sender(ws), _receiver(ws))
            except websockets.ConnectionClosed:
                log.warning("Verbindung getrennt — versuche erneut…")
                continue
    finally:
        stream.stop()
        listener.stop()


if __name__ == "__main__":
    _ensure_single_instance()  # B021: Kill any duplicate processes before starting
    asyncio.run(_run())
