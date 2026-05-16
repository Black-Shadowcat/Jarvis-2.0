"""
jarvis-audio Service — Text-to-Speech Synthesis Microservice
FastAPI service on port 8341 for ElevenLabs TTS integration
"""

import asyncio
import base64
import json
import logging
import os
import re
import sys
from typing import Optional
from logging.handlers import RotatingFileHandler

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging with rotation (prevent unbounded disk growth)
_log_dir = os.path.expanduser("~/Library/Logs/jarvis-v2")
os.makedirs(_log_dir, exist_ok=True)
_log_file = os.path.join(_log_dir, "audio.log")

log = logging.getLogger("jarvis-audio")
log.setLevel(logging.INFO)

# File handler with rotation: 10 MB max size, keep 5 backups
_handler = RotatingFileHandler(_log_file, maxBytes=10*1024*1024, backupCount=5)
_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S"))
log.addHandler(_handler)

# Also log to stdout (visible in launchd logs)
_stdout_handler = logging.StreamHandler(sys.stdout)
_stdout_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S"))
log.addHandler(_stdout_handler)

# Load config from parent directory
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
try:
    with open(CONFIG_PATH) as f:
        config = json.load(f)
except FileNotFoundError:
    log.error(f"Config file not found: {CONFIG_PATH}")
    raise SystemExit(1)

ELEVENLABS_API_KEY = config.get("elevenlabs_api_key", "")
ELEVENLABS_VOICE_ID = config.get("elevenlabs_voice_id", "")
LANGUAGE = config.get("language", "de")

if not ELEVENLABS_API_KEY or not ELEVENLABS_VOICE_ID:
    log.error("Missing elevenlabs_api_key or elevenlabs_voice_id in config.json")
    raise SystemExit(1)

# Constants
_DE_MONTHS = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
              "Juli", "August", "September", "Oktober", "November", "Dezember"]

# HTTP client for ElevenLabs API
http = httpx.AsyncClient(timeout=30)

app = FastAPI(title="jarvis-audio", version="0.1.0")


def _tts_sanitize(text: str) -> str:
    """Convert symbols and number formats to speakable text before ElevenLabs TTS."""
    if LANGUAGE == "de":
        # °C mit Dezimalstelle: "12.5°C" → "12 Komma 5 Grad"
        text = re.sub(r'(-?\d+)\.(\d+)\s*°[CcKk]', lambda m: f"{m.group(1)} Komma {m.group(2)} Grad", text)
        # °C ganzzahlig: "12°C" → "12 Grad"
        text = re.sub(r'(-?\d+)\s*°[CcKk]', r'\1 Grad', text)
        text = text.replace('°', '')
        # % → " Prozent"
        text = re.sub(r'(\d+)\s*%', r'\1 Prozent', text)
        # Clean up numbers followed by letters
        text = re.sub(r'(\d)([a-zäöüß])', r'\1 \2', text)
        # € → Euro
        text = re.sub(r'€\s*(\d+)', r'\1 Euro', text)
        text = re.sub(r'(\d+)\s*€', r'\1 Euro', text)
        # HH:MM → "H Uhr" / "H Uhr M"
        def _fmt_time(m):
            h, mi = int(m.group(1)), int(m.group(2))
            return f"{h} Uhr {mi}" if mi else f"{h} Uhr"
        text = re.sub(r'\b([01]?\d|2[0-3]):([0-5]\d)\b(?!\s*Uhr)', _fmt_time, text)
        # Kurzdatum "07.05." → "7. Mai"
        def _fmt_short_date(m):
            d, mo = int(m.group(1)), int(m.group(2))
            if 1 <= mo <= 12 and 1 <= d <= 31:
                return f"{d}. {_DE_MONTHS[mo]}"
            return m.group(0)
        text = re.sub(r'\b(\d{1,2})\.(\d{1,2})\.\B', _fmt_short_date, text)
        # Dezimalpunkt: "12.5" → "12 Komma 5"
        text = re.sub(r'\b(\d+)\.(\d{1,2})\b(?!\.\d)', r'\1 Komma \2', text)
        # km/h → Kilometer pro Stunde
        text = re.sub(r'(\d+)\s*km/h\b', r'\1 Kilometer pro Stunde', text)
    else:
        # °C → degrees
        text = re.sub(r'(-?\d+(?:\.\d+)?)\s*°[CcKk]', r'\1 degrees', text)
        text = text.replace('°', '')
        # % → percent
        text = re.sub(r'(\d+)\s*%', r'\1 percent', text)
        # € → Euro
        text = re.sub(r'€\s*(\d+)', r'\1 Euro', text)
        text = re.sub(r'(\d+)\s*€', r'\1 Euro', text)
        # km/h → kilometers per hour
        text = re.sub(r'(\d+)\s*km/h\b', r'\1 kilometers per hour', text)
    return text


async def synthesize_speech(text: str, voice_id: Optional[str] = None) -> bytes:
    """Synthesize text to speech using ElevenLabs API."""
    if not text.strip():
        return b""

    text = text.replace("J.A.R.V.I.S.", "Jarvis")
    text = _tts_sanitize(text)

    # Split long text into chunks at sentence boundaries
    chunks = []
    if len(text) > 250:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        current = ""
        for s in sentences:
            if len(current) + len(s) > 250 and current:
                chunks.append(current.strip())
                current = s
            else:
                current = (current + " " + s).strip()
        if current:
            chunks.append(current.strip())
    else:
        chunks = [text]

    async def _tts_chunk(chunk: str) -> bytes:
        vid = voice_id or ELEVENLABS_VOICE_ID
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
        payload = {
            "text": chunk,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {"stability": 0.65, "similarity_boost": 0.85},
        }
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        for attempt in range(2):
            try:
                resp = await http.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    log.debug(f"TTS OK: {len(resp.content)} bytes")
                    return resp.content
                log.warning(f"TTS error ({attempt+1}/2): {resp.status_code} {resp.text[:100]}")
            except Exception as e:
                log.error(f"TTS EXCEPTION ({attempt+1}/2): {e}")
            if attempt == 0:
                await asyncio.sleep(1)
        return b""

    parts = await asyncio.gather(*[_tts_chunk(c) for c in chunks])
    total = b"".join(parts)
    log.debug(f"TTS final: {len(total)} bytes total from {len(chunks)} chunks")
    return total


# Request/Response Models
class SynthesizeRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None


class SynthesizeResponse(BaseModel):
    audio: str
    bytes: int
    chunks: int


# Endpoints
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "jarvis-audio",
        "version": "0.1.0",
        "language": LANGUAGE,
    }


@app.post("/api/synthesize", response_model=SynthesizeResponse)
async def synthesize(request: SynthesizeRequest):
    """Synthesize text to speech."""
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    try:
        audio_bytes = await synthesize_speech(text, request.voice_id)
        if not audio_bytes:
            raise HTTPException(status_code=500, detail="TTS synthesis failed")

        audio_b64 = base64.b64encode(audio_bytes).decode()
        return SynthesizeResponse(
            audio=audio_b64,
            bytes=len(audio_bytes),
            chunks=len(audio_bytes) // 5000,  # rough estimate
        )
    except Exception as e:
        log.error(f"Synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "jarvis-audio",
        "version": "0.1.0",
        "endpoints": ["/health", "/api/synthesize"],
    }


if __name__ == "__main__":
    import uvicorn
    log.info("Starting jarvis-audio service on 127.0.0.1:8341")
    uvicorn.run(app, host="127.0.0.1", port=8341, log_level="info")
