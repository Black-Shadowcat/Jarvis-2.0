"""
jarvis-ha Service — Home Assistant, Dashboard Data, Weather, Mail Integration
FastAPI service on port 8342 for all dashboard aggregation and HA integration
"""

import json
import logging
import os
import subprocess
import time
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("jarvis-ha")

# Load config from parent directory
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
try:
    with open(CONFIG_PATH) as f:
        config = json.load(f)
except FileNotFoundError:
    log.error(f"Config file not found: {CONFIG_PATH}")
    raise SystemExit(1)

# Configuration
USER_NAME = config.get("user_name", "")
USER_ADDRESS = config.get("user_address", "Sir")
CITY = config.get("city", "Hamburg")
LAT = config.get("lat", 53.55)
LON = config.get("lon", 10.00)
KACHELMANN_KEY = config.get("kachelmann_api_key", "")
OBSIDIAN_INBOX = config.get("obsidian_inbox_path", "")
OBSIDIAN_ARCHIVE = config.get("obsidian_archive_path", "")
HA_URL = config.get("ha_url", "").rstrip("/") if config.get("ha_enabled", True) else ""
HA_TOKEN = config.get("ha_token", "")
LANGUAGE = config.get("language", "de")

# HTTP client
http = httpx.AsyncClient(timeout=30)

app = FastAPI(title="jarvis-ha", version="0.1.0")

# Light control mapping
LIGHT_MAP = {
    "alle": "light.alle_lichter", "alles": "light.alle_lichter", "ueberall": "light.alle_lichter",
    "überall": "light.alle_lichter", "gesamt": "light.alle_lichter",
    "wohnzimmer": "light.wohnzimmer", "wohnraum": "light.wohnzimmer", "living": "light.wohnzimmer",
    "küche": "light.kuche", "kuche": "light.kuche", "kueche": "light.kuche", "kitchen": "light.kuche",
    "büro": "light.buro", "buro": "light.buro", "buero": "light.buro", "arbeitszimmer": "light.buro",
    "arbeitsraum": "light.buro", "office": "light.buro", "studio": "light.buro",
    "flur": "light.flur", "gang": "light.flur", "eingang": "light.flur", "diele": "light.flur", "hallway": "light.flur",
    "schlafzimmer": "light.schlafzimmer", "schlafraum": "light.schlafzimmer", "bedroom": "light.schlafzimmer",
    "balkon": "light.balkon_led", "terrasse": "light.balkon_led",
    "iris": "light.hue_iris", "hue go": "light.hue_go_1", "go": "light.hue_go_1",
    "sideboard": ["light.sideboard_links", "light.sideboard_rechts"],
    "nachtschrank": ["light.nachtschrank_links", "light.nachtschrank_rechts"],
}

_LIGHT_STOP = {"das", "die", "den", "dem", "der", "ein", "eine", "licht", "lampe",
               "im", "in", "am", "an", "bitte", "mal", "doch", "kannst", "du",
               "mach", "mache", "schalte", "schalten", "stell", "stelle"}
_CMD_ON = {"an", "ein", "einschalten", "einschalte", "anschalten", "anschalte", "anmachen", "anmache", "einmachen", "einmache"}
_CMD_OFF = {"aus", "ausschalten", "ausschalte", "ausmachen", "ausmache"}

CACHE_TTL = 30.0
_mail_cache = {"data": None, "ts": 0.0}
_tasks_cache = {"data": None, "ts": 0.0}
_weather_cache = {"data": None, "ts": 0.0}

# ── Dashboard Data Functions ──────────────────────────────────────────────

def get_mail_sync():
    """Fetch unread mails from macOS Mail.app via AppleScript."""
    try:
        script = """
        tell application "Mail"
            set result to {}
            repeat with acc in accounts
                repeat with mb in mailboxes of acc
                    if (unread count of mb) > 0 then
                        repeat with msg in messages of mb
                            if read status of msg is false then
                                set sender to sender of msg
                                set subj to subject of msg
                                set end of result to (sender & " || " & subj)
                            end if
                        end repeat
                    end if
                end repeat
            end repeat
            return result
        end tell
        """
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            return [l.strip() for l in lines if l.strip()]
        return []
    except Exception as e:
        log.error(f"get_mail_sync error: {e}")
        return []


def get_tasks_sync():
    """Fetch reminders from macOS Reminders.app."""
    try:
        script = """
        tell application "Reminders"
            set result to {}
            repeat with lst in lists
                repeat with rem in reminders of lst
                    if completed of rem is false then
                        set end of result to name of rem
                    end if
                end repeat
            end repeat
            return result
        end tell
        """
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            return [l.strip() for l in lines if l.strip()]
        return []
    except Exception as e:
        log.error(f"get_tasks_sync error: {e}")
        return []


def get_calendar_sync(days: int = 7) -> list[str]:
    """Fetch calendar events from Home Assistant."""
    if not HA_URL or not HA_TOKEN:
        return []

    try:
        result = subprocess.run(
            ["curl", "-s", "-H", f"Authorization: Bearer {HA_TOKEN}",
             f"{HA_URL}/api/states/calendar.home"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return []

        data = json.loads(result.stdout)
        if not data or "attributes" not in data:
            return []

        events = []
        for attr_key in ["start_time", "description"]:
            if attr_key in data["attributes"]:
                event_str = f"{data['attributes'].get('description', '?')} -- {data['attributes'].get('start_time', '?')}"
                events.append(event_str)
        return events
    except Exception as e:
        log.error(f"get_calendar_sync error: {e}")
        return []


def get_weather_sync() -> dict:
    """Fetch weather data from Kachelmann API."""
    if not KACHELMANN_KEY:
        return {}

    try:
        result = subprocess.run(
            ["curl", "-s",
             f"https://api.kachelmannwetter.com/v4/forecast?lat={LAT}&lon={LON}&access_token={KACHELMANN_KEY}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {}
    except Exception as e:
        log.error(f"get_weather_sync error: {e}")
        return {}


def _obsidian_note_done(content: str) -> bool:
    """Check if note is marked done with #done tag."""
    return "#done" in content.lower() or "✓" in content


def get_obsidian_info_sync() -> list[str]:
    """Fetch unfinished Obsidian notes from inbox."""
    if not OBSIDIAN_INBOX:
        return []

    try:
        notes = []
        for fname in sorted(os.listdir(OBSIDIAN_INBOX)):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(OBSIDIAN_INBOX, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if not _obsidian_note_done(content):
                    notes.append(fname.replace(".md", "").replace("_", " "))
            except Exception as e:
                log.warning(f"Error reading {fname}: {e}")
        return notes
    except Exception as e:
        log.error(f"get_obsidian_info_sync error: {e}")
        return []


# ── API Endpoints ──────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "jarvis-ha",
        "version": "0.1.0",
        "ha_enabled": bool(HA_URL),
        "language": LANGUAGE,
    }


@app.get("/api/get_mails_unread")
async def get_mails_unread():
    """Get unread emails with caching."""
    now = time.time()
    if _mail_cache["data"] is not None and now - _mail_cache["ts"] < CACHE_TTL:
        return _mail_cache["data"]

    try:
        fresh = get_mail_sync()
        mails = []
        for mail_str in fresh:
            parts = mail_str.split(" || ", 1)
            if len(parts) == 2:
                sender, subject = parts
                mails.append({
                    "id": f"{sender}_{subject}",
                    "sender": sender.strip(),
                    "subject": subject.strip(),
                    "unread": True
                })

        result = {"mails": mails, "total": len(mails)}
        _mail_cache["data"] = result
        _mail_cache["ts"] = now
        return result
    except Exception as e:
        log.error(f"get_mails_unread error: {e}")
        return {"mails": [], "total": 0, "error": str(e)}


@app.get("/api/get_tasks")
async def get_tasks():
    """Get reminders and calendar events with caching."""
    now = time.time()
    if _tasks_cache["data"] is not None and now - _tasks_cache["ts"] < CACHE_TTL:
        return _tasks_cache["data"]

    try:
        fresh_tasks = get_tasks_sync()
        cal_lines = get_calendar_sync(days=2)

        tasks = []
        for i, task_name in enumerate(fresh_tasks):
            tasks.append({
                "id": f"task_{i}",
                "title": task_name.strip(),
                "source": "reminders",
                "completed": False
            })

        for i, line in enumerate(cal_lines):
            if " -- " in line:
                title, label = line.split(" -- ", 1)
            else:
                title, label = line, ""
            title = title.strip()
            tasks.append({
                "id": f"cal_{i}",
                "title": title,
                "label": label.strip(),
                "source": "calendar",
                "completed": None
            })

        result = {"tasks": tasks, "total": len(tasks)}
        _tasks_cache["data"] = result
        _tasks_cache["ts"] = now
        return result
    except Exception as e:
        log.error(f"get_tasks error: {e}")
        return {"tasks": [], "total": 0, "error": str(e)}


@app.get("/api/get_obsidian_notes")
async def get_obsidian_notes():
    """Get Obsidian inbox notes."""
    try:
        note_names = get_obsidian_info_sync()
        notes = []
        for i, name in enumerate(note_names):
            notes.append({
                "id": f"{name}.md",
                "title": name,
                "preview": f"Note: {name}",
                "completed": False
            })
        return {"notes": notes, "total": len(notes)}
    except Exception as e:
        log.error(f"get_obsidian_notes error: {e}")
        return {"notes": [], "total": 0, "error": str(e)}


@app.get("/api/weather")
async def get_weather():
    """Get weather data with caching."""
    now = time.time()
    if _weather_cache["data"] is not None and now - _weather_cache["ts"] < 3600:  # 1 hour cache
        return _weather_cache["data"]

    try:
        data = get_weather_sync()
        _weather_cache["data"] = data or {"error": "No weather data"}
        _weather_cache["ts"] = now
        return _weather_cache["data"]
    except Exception as e:
        log.error(f"get_weather error: {e}")
        return {"error": str(e)}


@app.post("/api/complete_task")
async def complete_task(request: Request):
    """Mark task as complete."""
    body = await request.json()
    task_id = body.get("task_id", "")

    if task_id.startswith("task_"):
        # Reminders.app completion
        try:
            # Would append ✓ to reminder (simplified)
            return {"status": "ok", "task_id": task_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok", "task_id": task_id}


@app.post("/api/complete_note")
async def complete_note(request: Request):
    """Mark Obsidian note as done."""
    body = await request.json()
    note_id = body.get("note_id", "")

    try:
        if OBSIDIAN_INBOX:
            fpath = os.path.join(OBSIDIAN_INBOX, note_id)
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                if "#done" not in content:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(content + "\n\n#done")
                return {"status": "ok", "note_id": note_id}

        return {"status": "error", "note_id": note_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/licht")
async def control_light(request: Request):
    """Control lights via Home Assistant."""
    body = await request.json()
    raum = body.get("raum", "").lower()
    zustand = body.get("zustand", "an")
    helligkeit = body.get("helligkeit")

    if not HA_URL or not HA_TOKEN:
        return {"error": "Home Assistant not configured"}

    if raum not in LIGHT_MAP:
        return {"error": f"Room not found: {raum}"}

    entity_ids = LIGHT_MAP[raum]
    if isinstance(entity_ids, str):
        entity_ids = [entity_ids]

    try:
        service = "light/turn_on" if zustand == "an" else "light/turn_off"
        payload = {"entity_id": entity_ids}
        if zustand == "an" and helligkeit:
            payload["brightness"] = int(helligkeit * 255 / 100)

        # Call HA service
        await http.post(
            f"{HA_URL}/api/services/{service}",
            json=payload,
            headers={"Authorization": f"Bearer {HA_TOKEN}"}
        )
        return {"status": "ok", "raum": raum, "zustand": zustand}
    except Exception as e:
        log.error(f"Light control error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "jarvis-ha",
        "version": "0.1.0",
        "endpoints": [
            "/health",
            "/api/get_mails_unread",
            "/api/get_tasks",
            "/api/get_obsidian_notes",
            "/api/weather",
            "/api/licht",
            "/api/complete_task",
            "/api/complete_note",
        ],
    }


if __name__ == "__main__":
    import uvicorn
    log.info("Starting jarvis-ha service on 127.0.0.1:8342")
    uvicorn.run(app, host="127.0.0.1", port=8342, log_level="info")
