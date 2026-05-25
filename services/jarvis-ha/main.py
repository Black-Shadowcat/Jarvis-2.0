"""
jarvis-ha Service — Home Assistant, Dashboard Data, Weather, Mail Integration
FastAPI service on port 8342 for all dashboard aggregation and HA integration
"""

import asyncio
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import Optional
from logging.handlers import RotatingFileHandler

import httpx
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel

# Configure logging with rotation (prevent unbounded disk growth)
_log_dir = os.path.expanduser("~/Library/Logs/jarvis-v2")
os.makedirs(_log_dir, exist_ok=True)
_log_file = os.path.join(_log_dir, "ha.log")

log = logging.getLogger("jarvis-ha")
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

CACHE_TTL = 60.0  # Increased from 30s (tasks don't change frequently)
CACHE_RETRY_DELAY = 10.0  # M13: Retry failed calls every 10s instead of waiting 60s
_mail_cache = {"data": None, "ts": 0.0, "last_good": None, "etag": None}
_tasks_cache = {"data": None, "ts": 0.0, "last_good": None, "etag": None}
_tasks_raw_list: list = []  # raw string list from Reminders.app for ETag comparison
_weather_cache = {"data": None, "ts": 0.0, "last_good": None}

# ── Dashboard Data Functions ──────────────────────────────────────────────

def _calculate_etag(data: list) -> str:
    """M14: Calculate ETag (hash) to detect data changes."""
    if not data:
        return "empty"
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:8]


def _cache_with_fallback(cache_dict, source_fn, timeout=8):
    """M13: Graceful Degradation — try source, fallback to stale data on failure."""
    now = time.time()
    # Return cached data if fresh
    if cache_dict["data"] is not None and now - cache_dict["ts"] < CACHE_TTL:
        return cache_dict["data"]

    # Try to fetch fresh data with timeout
    try:
        result = source_fn()
        if result:  # Only cache if non-empty
            cache_dict["data"] = result
            cache_dict["last_good"] = result
            cache_dict["ts"] = now
            return result
    except Exception as e:
        log.warning(f"Source failed: {e}, falling back to last-known-good")

    # Fallback: return stale data instead of error
    if cache_dict["last_good"] is not None:
        log.info("Using stale data (last-known-good)")
        return cache_dict["last_good"]

    # Last resort: empty list/dict
    return []


def get_mail_sync():
    """M14: Fetch unread mails with ETag-based change detection."""
    try:
        # Only read INBOX of each account — avoids showing archived/sent/junk as "new"
        script = """
tell application "Mail"
    set mailList to ""
    repeat with acc in accounts
        try
            set mb to mailbox "INBOX" of acc
            if (unread count of mb) > 0 then
                repeat with msg in messages of mb
                    try
                        if read status of msg is false then
                            set subj to subject of msg
                            set fromAddr to ""
                            try
                                set msgSource to source of msg
                                set fromStart to offset of "From: " in msgSource
                                if fromStart > 0 then
                                    set restOfSource to text (fromStart + 6) thru -1 of msgSource
                                    set fromEnd to offset of linefeed in restOfSource
                                    if fromEnd > 0 then
                                        set fromAddr to text 1 thru (fromEnd - 1) of restOfSource
                                    else
                                        set fromAddr to restOfSource
                                    end if
                                end if
                            end try
                            if mailList is "" then
                                set mailList to fromAddr & "|||" & subj
                            else
                                set mailList to mailList & linefeed & fromAddr & "|||" & subj
                            end if
                        end if
                    end try
                end repeat
            end if
        end try
    end repeat
    return mailList
end tell
"""
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            mails = []
            if output:
                # Parse newline-delimited "sender|||subject" pairs
                lines = [s.strip() for s in output.split("\n") if s.strip()]
                for i, line in enumerate(lines[:20]):  # Limit to 20 to avoid UI overflow
                    parts = line.split("|||", 1)
                    sender = parts[0] if len(parts) > 0 else ""
                    subject = parts[1] if len(parts) > 1 else parts[0]
                    mails.append({
                        "id": f"mail_{i}",
                        "sender": sender,
                        "subject": subject,
                        "unread": True
                    })

            # M14: ETag detection — skip cache update if data unchanged
            new_etag = _calculate_etag(mails)
            if new_etag == _mail_cache.get("etag"):
                log.info(f"[mail] ETag match ({new_etag}) — no change, skipping cache update")
                return _mail_cache["data"]  # Return cached (don't update ts)

            # Data changed — update cache
            log.info(f"[mail] ETag changed ({_mail_cache.get('etag')} → {new_etag}) — {len(mails)} unread")
            result_dict = {"mails": mails, "total": len(mails)}
            _mail_cache["data"] = result_dict
            _mail_cache["etag"] = new_etag
            _mail_cache["last_good"] = result_dict
            _mail_cache["ts"] = time.time()
            return result_dict
        else:
            log.warning(f"get_mail_sync: Mail.app error code {result.returncode}")
            if result.stderr:
                log.debug(f"  stderr: {result.stderr.strip()[:200]}")
            return []
    except subprocess.TimeoutExpired:
        log.warning(f"get_mail_sync: Mail.app timeout (15s)")
        return []
    except Exception as e:
        log.warning(f"get_mail_sync error: {type(e).__name__}: {e}")
        return []


def get_tasks_sync():
    """M14: Fetch reminders with ETag-based change detection."""
    global _tasks_raw_list
    script = '''tell application "Reminders"
    set cutoff to current date
    set hours of cutoff to 23
    set minutes of cutoff to 59
    set seconds of cutoff to 59
    set cutoff to cutoff + (1 * days)
    get name of (every reminder whose completed is false and due date ≤ cutoff)
end tell'''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10
        )

        tasks_raw = []
        if result.returncode == 0 and result.stdout.strip():
            tasks_raw = [i.strip() for i in result.stdout.strip().split(",") if i.strip()]
        elif result.returncode != 0:
            log.warning(f"get_tasks_sync: Reminders.app returned error code {result.returncode}")

        # M14: ETag detection — skip cache update if data unchanged
        new_etag = _calculate_etag(tasks_raw)
        if new_etag == _tasks_cache.get("etag"):
            log.info(f"[tasks] ETag match ({new_etag}) — no change, skipping cache update")
            # Return raw strings (not _tasks_cache["data"] which contains processed dicts)
            return {"tasks": _tasks_raw_list, "total": len(_tasks_raw_list)}

        # Data changed — update raw list and etag
        log.info(f"[tasks] ETag changed ({_tasks_cache.get('etag')} → {new_etag}) — {len(tasks_raw)} tasks")
        _tasks_raw_list = tasks_raw
        _tasks_cache["etag"] = new_etag
        _tasks_cache["ts"] = time.time()
        return {"tasks": tasks_raw, "total": len(tasks_raw)}

    except subprocess.TimeoutExpired:
        log.error(f"get_tasks_sync: Reminders.app timeout (10s)")
        return []
    except Exception as e:
        log.error(f"get_tasks_sync error: {e}")
        return []


def get_calendar_sync(days: int = 3) -> list[str]:
    """Fetch calendar events from Home Assistant CalDAV integration."""
    if not HA_URL or not HA_TOKEN:
        return []

    calendars = [
        "calendar.kalender",
        "calendar.dienstliches",
        "calendar.a_dienst",
        "calendar.stammtisch",
        "calendar.arzttermine",
        "calendar.family",
    ]
    headers = {"Authorization": f"Bearer {HA_TOKEN}"}

    start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = start_dt + timedelta(days=days)
    start_str = start_dt.strftime('%Y-%m-%dT%H:%M:%S')
    end_str = end_dt.strftime('%Y-%m-%dT%H:%M:%S')

    seen_occ: set = set()
    results: list = []

    import urllib.request as _urlreq
    for entity_id in calendars:
        try:
            url = f"{HA_URL}/api/calendars/{entity_id}?start={start_str}&end={end_str}"
            req = _urlreq.Request(url, headers=headers)
            with _urlreq.urlopen(req, timeout=5) as resp:
                events = json.loads(resp.read())
            for e in events:
                title = e.get('summary', '').strip()
                if not title:
                    continue
                s = e['start'].get('dateTime') or e['start'].get('date')
                if 'T' in s:
                    dt = datetime.fromisoformat(s).replace(tzinfo=None)
                else:
                    dt = datetime.fromisoformat(s)
                key = f"{title}|{dt.strftime('%Y-%m-%d %H:%M')}"
                if key not in seen_occ:
                    seen_occ.add(key)
                    results.append((dt, title))
        except Exception as exc:
            log.debug(f"get_calendar_sync: {entity_id} fehler: {exc}")
            continue

    results.sort(key=lambda x: x[0])
    seen_titles: set = set()
    lines = []
    for dt, title in results:
        if title in seen_titles:
            continue
        seen_titles.add(title)
        # Label: Uhrzeit oder "Ganztags" + Datum wenn nicht heute
        today = datetime.now().date()
        if dt.date() == today:
            label = dt.strftime('%H:%M') if dt.hour or dt.minute else "Ganztags"
        else:
            label = dt.strftime('%d.%m. %H:%M') if dt.hour or dt.minute else dt.strftime('%d.%m. Ganztags')
        lines.append(f"{title} -- {label}")
    return lines


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
            timeout=3
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        log.warning(f"get_weather_sync: curl returned error code {result.returncode}")
        return {}
    except subprocess.TimeoutExpired:
        log.error(f"get_weather_sync: Kachelmann API timeout (3s)")
        return {}
    except json.JSONDecodeError as e:
        log.error(f"get_weather_sync: invalid JSON from Kachelmann: {e}")
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
    """M13+M14: Get unread emails with graceful degradation (fallback to stale data)."""
    now = time.time()
    # Check if cached data is still fresh (TTL)
    if _mail_cache["data"] is not None and now - _mail_cache["ts"] < CACHE_TTL:
        log.debug(f"[mail] Cache hit (fresh for {int(now - _mail_cache['ts'])}s)")
        return _mail_cache["data"]

    # Cache expired — fetch with M14 ETag detection
    try:
        result = get_mail_sync()
        if isinstance(result, dict) and "mails" in result:
            return result
        # Fallback if sync returned unexpected format
        if result and isinstance(result, list):
            return {"mails": result, "total": len(result)}
        # Empty result
        return _mail_cache.get("last_good", {"mails": [], "total": 0})
    except Exception as e:
        log.warning(f"get_mails_unread failed: {e}, falling back to stale data")
        # M13: Return last-known-good data instead of error
        if _mail_cache.get("last_good"):
            return _mail_cache["last_good"]
        return {"mails": [], "total": 0}


@app.get("/api/get_tasks")
async def get_tasks():
    """M13+M14: Get reminders and calendar events with graceful degradation."""
    now = time.time()
    # Check if cached data is still fresh (TTL)
    if _tasks_cache["data"] is not None and now - _tasks_cache["ts"] < CACHE_TTL:
        log.debug(f"[tasks] Cache hit (fresh for {int(now - _tasks_cache['ts'])}s)")
        return _tasks_cache["data"]

    # Cache expired — fetch with M14 ETag detection
    try:
        tasks_result = get_tasks_sync()

        # Parse reminders
        tasks = []
        if isinstance(tasks_result, dict) and "tasks" in tasks_result:
            fresh_tasks = tasks_result["tasks"]
        else:
            fresh_tasks = tasks_result if isinstance(tasks_result, list) else []

        for i, task_name in enumerate(fresh_tasks):
            tasks.append({
                "id": f"task_{i}",
                "title": task_name.strip() if isinstance(task_name, str) else str(task_name),
                "source": "reminders",
                "completed": False
            })

        # Add calendar events
        cal_lines = get_calendar_sync(days=2)
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
        # Update cache if not already done by get_tasks_sync() (fallback only)
        if not _tasks_cache["data"] or now - _tasks_cache["ts"] >= CACHE_TTL:
            _tasks_cache["data"] = result
            _tasks_cache["last_good"] = result
            _tasks_cache["ts"] = now
        return result
    except Exception as e:
        log.warning(f"get_tasks failed: {e}, falling back to stale data")
        # M13: Return last-known-good data instead of error
        if _tasks_cache.get("last_good"):
            return _tasks_cache["last_good"]
        return {"tasks": [], "total": 0}


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
    """M13: Get weather data with graceful degradation."""
    now = time.time()
    if _weather_cache["data"] is not None and now - _weather_cache["ts"] < 3600:  # 1 hour cache
        return _weather_cache["data"]

    try:
        data = get_weather_sync()
        if data:
            _weather_cache["data"] = data
            _weather_cache["last_good"] = data  # M13: Remember successful result
            _weather_cache["ts"] = now
            return _weather_cache["data"]
    except Exception as e:
        log.warning(f"get_weather failed: {e}, falling back to stale data")

    # M13: Return last-known-good data instead of error
    if _weather_cache["last_good"]:
        log.info("Using stale weather data (last-known-good)")
        return _weather_cache["last_good"]
    return {"error": "Weather unavailable"}


def complete_task_sync(task_name: str) -> bool:
    """
    Mark reminder as complete in Reminders.app.
    Uses AppleScript to find reminder by name (contains search) and set completed=true.
    """
    # Escape quotes in task name for AppleScript
    safe_name = task_name.replace('"', '\\"')

    script = f'''tell application "Reminders"
    set found to (every reminder whose completed is false and name contains "{safe_name}")
    repeat with r in found
        set completed of r to true
    end repeat
end tell'''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            log.info(f"✓ Task marked complete: {task_name}")
            return True
        else:
            log.warning(f"complete_task_sync: AppleScript error code {result.returncode}")
            return False
    except subprocess.TimeoutExpired:
        log.error(f"complete_task_sync: Reminders.app timeout (10s) for '{task_name}'")
        return False
    except Exception as e:
        log.error(f"complete_task_sync error for '{task_name}': {e}")
        return False


@app.post("/api/complete_task")
async def complete_task(request: Request):
    """Mark task as complete in Reminders.app."""
    body = await request.json()
    task_id = body.get("task_id", "")

    if not task_id:
        raise HTTPException(status_code=400, detail="task_id is required")

    # Run completion in background (don't block)
    success = await asyncio.get_event_loop().run_in_executor(
        None,
        complete_task_sync,
        task_id
    )

    return {
        "status": "ok" if success else "error",
        "task_id": task_id,
        "completed": success
    }


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
