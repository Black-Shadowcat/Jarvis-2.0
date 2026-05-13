#!/usr/bin/env python3
"""
Jarvis V3 — Spracheingabe via Whisper + F19 Push-to-Talk + Wake-Word
Verbindet sich mit dem Jarvis-Server via WebSocket und sendet transkribierten Text.

Aktivierung:
  • F19 halten    → Push-to-Talk (sofort)
  • "Jarvis, ..." → Wake-Word via VAD + Whisper (kein "Hey" nötig)
"""

import asyncio
import collections
import logging
import queue
import re
import threading
import time
import json
import urllib.request
import numpy as np
import sounddevice as sd
import mlx_whisper
from pynput import keyboard
import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("stt")

SAMPLE_RATE    = 16000
CHUNK_SIZE     = 1600   # 100 ms pro Callback-Chunk
PTT_KEY        = keyboard.Key.f19
SERVER_URL     = "ws://localhost:8341/ws/stt"
PTT_API        = "http://localhost:8341/api/ptt"
WHISPER_MODEL  = "mlx-community/whisper-large-v3-mlx"
MIN_DURATION   = 0.6    # Sekunden — kürzere Aufnahmen werden verworfen

# Wake-Word-Konfiguration
WW_VOICE_RMS    = 0.018  # RMS-Schwellwert: Sprache erkannt (oberhalb = Stimme)
WW_SILENCE_RMS  = 0.015  # RMS-Schwellwert: Stille (unterhalb = Pause)
WW_MAX_SECS     = 5.0    # Maximale Länge des Erkennung-Snippets
WW_SILENCE_SECS = 0.8    # Stille nach letztem Wort → Snippet fertig
WW_CMD_SILENCE  = 1.5    # Stille nach Befehl → Aufnahme beenden

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

# Queue: audio-chunks vom Callback → Wake-Word-Thread
_detect_q: queue.Queue = queue.Queue(maxsize=500)


# ── PTT-State an Browser melden ───────────────────────────────────────────

def _notify_ptt(state: str):
    try:
        req = urllib.request.Request(f"{PTT_API}/{state}", method="POST")
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass


# ── Gemeinsamer Start/Stop (F19 und Wake-Word) ────────────────────────────

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
    if chunks:
        audio = np.concatenate(chunks).flatten()
        duration = len(audio) / SAMPLE_RATE
        if duration < MIN_DURATION:
            log.debug(f"(zu kurz: {duration:.2f}s — verworfen) [{source}]")
        else:
            threading.Thread(target=_transcribe, args=(audio,), daemon=True).start()
    else:
        log.debug(f"(keine Aufnahme) [{source}]")


# ── Audio-Callback ────────────────────────────────────────────────────────

def _audio_cb(indata, frames, time_info, status):
    if _recording:
        with _buffer_lock:
            _audio_buffer.append(indata.copy())
    else:
        # Wake-Word-Thread mit Daten versorgen (non-blocking, drop wenn voll)
        try:
            _detect_q.put_nowait(indata.copy())
        except queue.Full:
            pass


# ── Tastatur ──────────────────────────────────────────────────────────────

def _on_press(key):
    if key == PTT_KEY:
        _start_recording("F19")


def _on_release(key):
    if key == PTT_KEY:
        _stop_recording_and_transcribe("F19")


# ── Whisper ───────────────────────────────────────────────────────────────

def _transcribe(audio: np.ndarray):
    log.info("■ Transkribiere…")
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


# ── Wake-Word-Detektor (VAD + Whisper) ────────────────────────────────────

def _detect_q_flush():
    """Alte Chunks aus der Queue verwerfen (nach Whisper-Inference)."""
    while not _detect_q.empty():
        try:
            _detect_q.get_nowait()
        except queue.Empty:
            break


def _ww_thread():
    """
    Lauscht auf Sprache, transkribiert kurze Snippets via Whisper.
    Wenn 'Jarvis' erkannt → Befehl extrahieren oder auf Folgebefehl warten.
    """
    log.info("Wake-Word aktiv — VAD+Whisper, Aktivierungswort: 'Jarvis'")
    chunk_secs = CHUNK_SIZE / SAMPLE_RATE  # 0.1 s

    while True:
        # 1. Warte auf Sprachbeginn (RMS-VAD)
        chunk = _detect_q.get()
        rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
        if _recording:
            continue
        if rms < WW_VOICE_RMS:
            continue

        # 2. Sprache erkannt → sammle Snippet bis Stille
        snippet: list = [chunk.astype(np.float32)]
        silence_secs = 0.0
        total_secs   = chunk_secs

        while total_secs < WW_MAX_SECS and not _recording:
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

        if _recording:
            _detect_q_flush()
            continue

        # 3. Transkribiere Snippet
        audio_snip = np.concatenate(snippet).flatten()
        if len(audio_snip) / SAMPLE_RATE < 0.3:
            continue

        result = mlx_whisper.transcribe(
            audio_snip,
            path_or_hf_repo=WHISPER_MODEL,
            language="de",
        )
        text = result["text"].strip()
        _detect_q_flush()  # stale Chunks nach Inference verwerfen

        if not text or text.lower() in _HALLUCINATIONS:
            continue
        log.info(f"WW-Snippet: '{text}'")
        if "jarvis" not in text.lower():
            continue

        log.info(f'Wake-Word erkannt: "{text}"')

        # 4. Befehl aus dem gleichen Utterance extrahieren
        command = re.sub(
            r'^[\s,!.]*jarvis[\s,!.]*', '', text, flags=re.IGNORECASE
        ).strip()

        if command and command.lower() not in _HALLUCINATIONS and len(command) > 3:
            # Befehl war im gleichen Satz → direkt senden, Orb kurz anzeigen
            log.info(f"Befehl inline: » {command}")
            threading.Thread(target=_notify_ptt, args=("start",), daemon=True).start()
            time.sleep(0.15)
            threading.Thread(target=_notify_ptt, args=("stop",), daemon=True).start()
            asyncio.run_coroutine_threadsafe(_queue.put(command), _loop)
        else:
            # Nur "Jarvis" gesagt → auf Folgebefehl warten
            log.info("Warte auf Befehl…")
            _start_recording("wake-word")

            # Auto-Stop: Audio kommt jetzt in _audio_buffer (nicht in _detect_q)
            # → letzten Chunk per Buffer-Check auf Stille überwachen
            silence_c = 0.0
            max_secs  = 10.0
            start_t   = time.time()
            while _recording and (time.time() - start_t) < max_secs:
                time.sleep(0.1)
                with _buffer_lock:
                    if not _audio_buffer:
                        continue
                    recent = _audio_buffer[-1]
                rms_cmd = float(np.sqrt(np.mean(recent.astype(np.float32) ** 2)))
                if rms_cmd < WW_SILENCE_RMS:
                    silence_c += 0.1
                    if silence_c >= WW_CMD_SILENCE:
                        break
                else:
                    silence_c = 0.0

            _stop_recording_and_transcribe("wake-word")
            _detect_q_flush()


# ── WebSocket Client ──────────────────────────────────────────────────────

async def _sender(ws):
    while True:
        text = await _queue.get()
        await ws.send(json.dumps({"text": text}))


async def _receiver(ws):
    async for _ in ws:
        pass  # TTS-Audio wird vom Browser abgespielt


async def _run():
    global _loop, _queue
    _loop  = asyncio.get_running_loop()
    _queue = asyncio.Queue()

    stream   = sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                               dtype="float32", blocksize=CHUNK_SIZE,
                               callback=_audio_cb)
    listener = keyboard.Listener(on_press=_on_press, on_release=_on_release)

    stream.start()
    listener.start()

    threading.Thread(target=_ww_thread, daemon=True).start()

    log.info("─" * 44)
    log.info("  Jarvis V3 — Spracheingabe")
    log.info("─" * 44)
    log.info("  F19 halten       → Push-to-Talk")
    log.info("  'Jarvis, ...'    → Wake-Word")
    log.info(f"  Server: {SERVER_URL}")
    log.info("─" * 44)

    try:
        async for ws in websockets.connect(SERVER_URL, ping_interval=20):
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
    asyncio.run(_run())
