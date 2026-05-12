#!/usr/bin/env python3
"""
Jarvis V3 — Spracheingabe via Whisper + F19 Push-to-Talk
Verbindet sich mit dem Jarvis-Server via WebSocket und sendet transkribierten Text.
"""

import asyncio
import threading
import json
import numpy as np
import sounddevice as sd
import mlx_whisper
from pynput import keyboard
import websockets

SAMPLE_RATE   = 16000
PTT_KEY       = keyboard.Key.f19
SERVER_URL    = "ws://localhost:8341/ws"
WHISPER_MODEL = "mlx-community/whisper-large-v3-mlx"

_audio_buffer: list  = []
_recording:    bool  = False
_buffer_lock         = threading.Lock()
_loop:  asyncio.AbstractEventLoop = None
_queue: asyncio.Queue             = None


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
        print("● Aufnahme läuft...", flush=True)


def _on_release(key):
    global _recording
    if key == PTT_KEY and _recording:
        _recording = False
        with _buffer_lock:
            chunks = list(_audio_buffer)
        if chunks:
            audio = np.concatenate(chunks).flatten()
            threading.Thread(target=_transcribe, args=(audio,), daemon=True).start()
        else:
            print("(keine Aufnahme)", flush=True)


# ── Whisper ───────────────────────────────────────────────────────────────

def _transcribe(audio: np.ndarray):
    print("■ Transkribiere...", flush=True)
    result = mlx_whisper.transcribe(
        audio,
        path_or_hf_repo=WHISPER_MODEL,
        language="de",
    )
    text = result["text"].strip()
    if text:
        print(f"» {text}", flush=True)
        asyncio.run_coroutine_threadsafe(_queue.put(text), _loop)
    else:
        print("(nichts erkannt)", flush=True)


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

    print("─" * 42, flush=True)
    print("  Jarvis V3 — Spracheingabe", flush=True)
    print("─" * 42, flush=True)
    print(f"  F19 halten → sprechen → loslassen", flush=True)
    print(f"  Server: {SERVER_URL}", flush=True)
    print("─" * 42, flush=True)

    try:
        async for ws in websockets.connect(SERVER_URL, ping_interval=20):
            print("  Server verbunden ✓\n", flush=True)
            try:
                await asyncio.gather(_sender(ws), _receiver(ws))
            except websockets.ConnectionClosed:
                print("Verbindung getrennt — versuche erneut...", flush=True)
                continue
    finally:
        stream.stop()
        listener.stop()


if __name__ == "__main__":
    asyncio.run(_run())
