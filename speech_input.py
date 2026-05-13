#!/usr/bin/env python3
"""
Jarvis V3 — Spracheingabe via Whisper + F19 Push-to-Talk
Verbindet sich mit dem Jarvis-Server via WebSocket und sendet transkribierten Text.
"""

import asyncio
import logging
import threading
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

SAMPLE_RATE   = 16000
PTT_KEY       = keyboard.Key.f19
SERVER_URL    = "ws://localhost:8341/ws/stt"
PTT_API       = "http://localhost:8341/api/ptt"
WHISPER_MODEL = "mlx-community/whisper-large-v3-mlx"
MIN_DURATION  = 0.6  # Sekunden — kürzere Aufnahmen werden verworfen

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


# ── PTT-State an Browser melden ───────────────────────────────────────────

def _notify_ptt(state: str):
    try:
        req = urllib.request.Request(f"{PTT_API}/{state}", method="POST")
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass


# ── Audio ─────────────────────────────────────────────────────────────────

def _audio_cb(indata, frames, time, status):
    if _recording:
        with _buffer_lock:
            _audio_buffer.append(indata.copy())


# ── Tastatur ──────────────────────────────────────────────────────────────

def _on_press(key):
    global _recording
    if key == PTT_KEY and not _recording:
        _recording = True
        with _buffer_lock:
            _audio_buffer.clear()
        log.info("● Aufnahme läuft...")
        threading.Thread(target=_notify_ptt, args=("start",), daemon=True).start()


def _on_release(key):
    global _recording
    if key == PTT_KEY and _recording:
        _recording = False
        threading.Thread(target=_notify_ptt, args=("stop",), daemon=True).start()
        with _buffer_lock:
            chunks = list(_audio_buffer)
        if chunks:
            audio = np.concatenate(chunks).flatten()
            duration = len(audio) / SAMPLE_RATE
            if duration < MIN_DURATION:
                log.debug(f"(zu kurz: {duration:.2f}s — verworfen)")
            else:
                threading.Thread(target=_transcribe, args=(audio,), daemon=True).start()
        else:
            log.debug("(keine Aufnahme)")


# ── Whisper ───────────────────────────────────────────────────────────────

def _transcribe(audio: np.ndarray):
    log.info("■ Transkribiere...")
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
                               dtype="float32", callback=_audio_cb)
    listener = keyboard.Listener(on_press=_on_press, on_release=_on_release)

    stream.start()
    listener.start()

    log.info("─" * 42)
    log.info("  Jarvis V3 — Spracheingabe")
    log.info("─" * 42)
    log.info(f"  F19 halten → sprechen → loslassen")
    log.info(f"  Server: {SERVER_URL}")
    log.info("─" * 42)

    try:
        async for ws in websockets.connect(SERVER_URL, ping_interval=20):
            log.info("  Server verbunden ✓\n")
            try:
                await asyncio.gather(_sender(ws), _receiver(ws))
            except websockets.ConnectionClosed:
                log.warning("Verbindung getrennt — versuche erneut...")
                continue
    finally:
        stream.stop()
        listener.stop()


if __name__ == "__main__":
    asyncio.run(_run())
