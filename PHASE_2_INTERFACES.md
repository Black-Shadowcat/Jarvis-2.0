# Phase 2: Interface Documentation — Complete Communication Map

> Comprehensive audit of all interfaces, data flows, and communication patterns in Jarvis 2.0
> **Purpose:** Understand exact touch-points for service isolation
> **Status:** Spike Phase — in-progress analysis (2026-05-16)

---

## 📋 Document Index

1. **WebSocket Endpoints** — Real-time communication
2. **REST API Endpoints** — Request-response communication
3. **Global State & Locks** — Shared data structures
4. **Inter-Service Communication** — speech_input.py ↔ server.py
5. **External Service Integration** — Claude API, ElevenLabs, Home Assistant
6. **Browser Control** — Playwright integration
7. **File System I/O** — Config, data, logs
8. **Communication Patterns** — Message flow diagrams

---

## 1. WebSocket Endpoints

### `/ws/stt` — Speech-to-Text Input (speech_input.py)

**Purpose:** Receive text transcriptions from mlx-whisper + VAD pipeline  
**Clients:** `speech_input.py` (dedicated connection)  
**Frequency:** ~1 per user utterance (every few seconds during active conversation)

#### Message Format (Input from speech_input.py):
```json
{
  "text": "Jarvis, sag mir die aktuelle Temperatur"
}
```

#### Connection Lifecycle:
1. `speech_input.py` connects on startup via WebSocket handshake
2. Remains open for lifetime of speech_input process
3. On disconnect: logs disconnection, retries (exponential backoff on client side)
4. **Critical:** Separate from `/ws` (browser) to avoid audio loop issues

#### Downstream Flow:
- Message received in `stt_endpoint()` (line 1887)
- Text extracted: `user_text = data.get("text", "")`
- Broadcast to all browser connections: `{"type": "user_input", "text": user_text}`
- Process message: `await process_message(session_id, user_text, ws)`

#### Global State Updated:
- None directly (state updated in process_message → conversations)

---

### `/ws` — Browser Dashboard (index.html)

**Purpose:** Bidirectional communication between browser UI and server  
**Clients:** `index.html` (may have multiple tabs/windows)  
**Frequency:** Real-time (response messages, status updates, audio streaming)

#### Message Format (Input from browser):
```json
{
  "text": "Was ist Morgen das Wetter?"
}
```

#### Message Formats (Output from server):
```json
{
  "type": "user_input",
  "text": "Jarvis activate"
}
```

```json
{
  "type": "response",
  "text": "Morgen wird es sonnig mit 18 Grad.",
  "audio": "base64-encoded-mp3-data"
}
```

```json
{
  "type": "ptt_start",
  "timestamp": "2026-05-16T10:30:45Z"
}
```

```json
{
  "type": "ptt_stop",
  "timestamp": "2026-05-16T10:30:47Z"
}
```

```json
{
  "type": "tts_error",
  "message": "ElevenLabs API error"
}
```

```json
{
  "type": "listen_open",
  "ring_state": "listen_open"
}
```

```json
{
  "type": "listen_close",
  "ring_state": "listen_close"
}
```

#### Connection Lifecycle:
1. Browser connects on page load
2. Client-side reconnect logic: exponential backoff (3s → 60s)
3. On reconnect: "Jarvis activate" is debounced (5s window) to prevent double-greeting
4. Remains open for conversation duration
5. On disconnect: session stored 30s, then purged

#### Connection Management (global state):
- `active_connections: set[WebSocket]` — all active browser connections
- `conversations: dict[str, list]` — message history per session

#### Critical Pattern:
- Browser connections receive **ALL** output (audio, status)
- Speech_input connections receive **ONLY** text (no audio feedback loop)

---

## 2. REST API Endpoints

### Dashboard Data Endpoints

#### `GET /api/get_mails_unread` — Unread Emails
**Cache:** 30 seconds  
**Source:** macOS Mail.app (via `get_mail_sync()`)

**Response:**
```json
{
  "mails": [
    {
      "id": "sender_subject",
      "sender": "alice@example.com",
      "subject": "Meeting Notes",
      "timestamp": "",
      "unread": true
    }
  ],
  "total": 3
}
```

**Global State Updated:** `MAIL_INFO` (used in briefing logic)

---

#### `GET /api/get_tasks` — Reminders + Calendar
**Cache:** 30 seconds  
**Sources:** macOS Reminders + Home Assistant Calendar

**Response:**
```json
{
  "tasks": [
    {
      "id": "task_0",
      "title": "Buy groceries",
      "source": "reminders",
      "completed": false
    },
    {
      "id": "cal_0",
      "title": "Team Meeting",
      "label": "14:00 – 15:00",
      "source": "calendar",
      "completed": null
    }
  ],
  "total": 5
}
```

**Global State Updated:** `TASKS_INFO` (used in briefing logic)

---

#### `GET /api/get_obsidian_notes` — Inbox Notes
**Cache:** None (real-time)  
**Source:** Obsidian inbox folder (file system)

**Response:**
```json
{
  "notes": [
    {
      "id": "call_alice.md",
      "title": "call alice",
      "preview": "Schedule call about project X…",
      "content": "Full note content here",
      "completed": false
    }
  ],
  "total": 2
}
```

**Global State Updated:** None (read-only)

---

#### `GET /api/daily_brief` — Morning/Evening Brief Trigger
**Cache:** None (state-dependent)  
**Logic:** Detects time-based triggers (morning 6-10am, evening 18-22:00)

**Response:**
```json
{
  "triggered": true,
  "trigger_type": "morning",
  "text": "Guten Morgen Herr Schreiber. Es ist Donnerstag der 16. Mai 2026…"
}
```

**Global State Updated:** `daily_brief._data` (last_morning_brief timestamp, activity tracking)

---

#### `POST /api/daily_brief/manual` — Manual Brief Trigger
**Payload:**
```json
{
  "trigger": "morning" | "evening" | "absence" | "reset"
}
```

**Global State Updated:** `daily_brief._data` (forced trigger, state reset)

---

#### `GET /api/daily_brief/memory` — Debug State
**Returns:** Full internal state of DailyBrief system for debugging

---

#### `GET /api/news` — All News Articles
**Source:** RSS feeds (NewsSystem)  
**Returns:** All articles with read/unread status

---

#### `GET /api/news/search?q=...` — Search News
**Returns:** Articles matching query

---

#### `POST /api/news/read` — Mark Article Read
**Payload:**
```json
{
  "id": "article_uuid",
  "read": true
}
```

---

#### `GET /api/rss_feeds` — List RSS Feeds
**Returns:** All configured RSS feeds with active/inactive status

---

#### `POST /api/rss_feeds` — Bulk Save Feeds
**POST /api/rss_feeds/add` — Add New Feed  
**PUT /api/rss_feeds/{feed_id}` — Edit Feed  
**DELETE /api/rss_feeds/{feed_id}` — Remove Feed

---

### System Control Endpoints

#### `POST /api/complete_task` — Mark Task Complete
**Payload:**
```json
{
  "task_id": "task_0"
}
```

**Action:** Calls `complete_task_sync()` → macOS Reminders.app

---

#### `POST /api/complete_note` — Mark Note Complete
**Payload:**
```json
{
  "note_id": "call_alice.md"
}
```

**Action:** Appends `#done` tag to Obsidian file

---

#### `POST /api/open_app` — Launch Application
**Payload:**
```json
{
  "app_name": "Finder"
}
```

**Action:** `subprocess.run(["open", "-a", app_name])`

---

#### `POST /api/restart` — Restart Server
**Action:** Kills own process → launchd auto-restarts

---

#### `POST /api/supervisor/force-check` — Health Check
**Returns:** Current status of all supervised services (speech_input, wake-monitor, etc.)

---

#### `POST /api/supervisor/restart` — Restart Service
**Payload:**
```json
{
  "service": "speech_input" | "wake-monitor" | "browser"
}
```

---

### Config & Info Endpoints

#### `GET /api/language` — Current Language Setting
**Returns:**
```json
{
  "language": "de",
  "speech_lang": "de-DE"
}
```

---

#### `GET /api/update_check` — Check for Updates
**Cache:** 24 hours  
**Logic:** Compares `version.json` against GitHub API latest release

**Returns:**
```json
{
  "current": "0.3.0",
  "latest": "0.3.1",
  "update_available": true,
  "url": "https://github.com/..."
}
```

---

#### `GET /config` — Config UI Page

#### `POST /api/config` — Save Configuration
**Payload:** User-editable config keys (name, city, API keys, etc.)

---

## 3. Global State & Locks

### Conversation Storage
```python
conversations: dict[str, list[dict]] = {}
# Key: session_id (str(id(ws)))
# Value: [{role: "user|assistant", content: str}, ...]
# Lifetime: Session duration, purged on disconnect or 30s timeout
# Access: process_message() → append/read history
```

### Active Connections
```python
active_connections: set[WebSocket] = set()
# All browser WebSocket connections
# Used for: Broadcasting user_input, responses, status messages
# Thread-safe: asyncio operations on main event loop

stt_connections: set[WebSocket] = set()
# All speech_input.py WebSocket connections
# Used for: Receive transcribed text only
# Expected: Usually 1 connection (speech_input.py instance)
```

### Cached Data
```python
_mail_cache: dict = {"data": None, "ts": 0.0}
_tasks_cache: dict = {"data": None, "ts": 0.0}
_DASHBOARD_CACHE_TTL = 30.0  # seconds

# Global data synchronized from background tasks
MAIL_INFO: list[str] = []        # Cache of unread email lines
TASKS_INFO: list[str] = []       # Cache of reminders
CALENDAR_INFO: list[str] = []    # Cache of calendar events
NEWS_INFO: list[dict] = []       # Cache of RSS articles
WEATHER_INFO: dict = {}          # Current weather
OBSIDIAN_INFO: list[str] = []    # Obsidian inbox notes
```

### Thread Synchronization Locks
```python
_mail_lock = asyncio.Lock()
_licht_room_lock = asyncio.Lock()
# Guard concurrent updates to shared state
# Pattern: async with lock: SHARED_STATE = new_value
```

### Singleton Instances
```python
ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
http = httpx.AsyncClient(timeout=30)
browser_tools = BrowserTools()
screen_capture = ScreenCapture()
news = NewsSystem()
daily_brief = DailyBrief()
```

---

## 4. Inter-Service Communication

### speech_input.py ↔ server.py

**Connection:** WebSocket `/ws/stt`

**Data Flow:**
```
[Microphone Audio]
        ↓
[speech_input.py: RMS-VAD]
        ↓
[Wake-word "Jarvis" detected?]
        ├─ No → keep listening
        └─ Yes → Whisper transcription
                ↓
        [Text: "Jarvis, play music"]
                ↓
        [WebSocket POST /ws/stt]
                ↓
        [server.py: stt_endpoint()]
                ↓
        [Broadcast to browsers: {"type": "user_input", ...}]
                ↓
        [process_message() → LLM → Actions → Response]
                ↓
        [Response sent via /ws (browsers)]
```

**Message Protocol:**
- Speech_input → Server: `{"text": "..."}` (JSON)
- Server → Browsers: `{"type": "user_input", "text": "..."}` (JSON)
- Server → Speech_input: No direct messages (one-way)

**State Sharing Between Services:**
- `speech_input.py`: Maintains `_jarvis_speaking`, `_in_conversation` flags (local state)
- `server.py`: Broadcasts `speaking_start` / `speaking_end` messages to browsers
- Speech_input monitors `speaking_end` to reset audio buffer

**Failure Scenarios:**
1. speech_input.py disconnects → server continues serving browser
2. speech_input.py reconnects → conversation continues (no state loss)
3. Server restarts → speech_input loses connection, reconnects with backoff

---

### server.py ↔ index.html (Browser)

**Connection:** WebSocket `/ws`

**Data Flow:**
```
[Browser sends text via WS]
        ↓
[server.py: websocket_endpoint()]
        ↓
[process_message(session_id, user_text, ws)]
        ├─ LLM processing
        ├─ Action execution (SEARCH, BROWSE, OPEN, etc.)
        └─ TTS synthesis
                ↓
[Response broadcast to all /ws connections]
                ↓
[index.html receives and plays audio]
```

**Message Handling (Browser → Server):**
```json
{
  "text": "Wie spät ist es?"
}
```

**Message Handling (Server → Browser):**
```json
{
  "type": "response",
  "text": "Es ist 14:30 Uhr.",
  "audio": "base64-encoded-mp3"
}
```

**Status Messages:**
- `type: "listen_open"` — HUD shows blue listening ring
- `type: "listen_close"` — HUD returns to idle
- `type: "ptt_start"` — F19 PTT started (red ring)
- `type: "ptt_stop"` — F19 PTT ended
- `type: "tts_error"` — ElevenLabs failure (magenta ring, auto-reset 4s)

**Session Management:**
- Browser A sends → only Browser A's session_id is used
- Multiple browsers → each has separate conversation history
- Debounce: "Jarvis activate" within 5s of last one is suppressed

---

## 5. External Service Integration

### Claude API (Anthropic)

**Endpoint:** `https://api.anthropic.com/v1/messages`

**Request Pattern:**
```python
response = await ai.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=300,
    system=get_system_prompt(),
    messages=history[-16:],  # Last 16 messages for context
)
```

**System Prompt Contents:**
- User name, address (form of address)
- Location (city, lat/lon for weather)
- Home Assistant integration info
- Available actions and syntax
- Language setting
- Current date/time
- Recent context from briefing system

**Response Handling:**
- Raw text extraction: `reply = response.content[0].text`
- Structured action parsing: JSON extraction for ActionModel
- Legacy fallback: regex-based action parsing

**Frequency:** 1 request per user message (not per utterance — debounced/buffered)

**Errors:**
- API key invalid → SystemExit(1) at startup
- API limit → 429 response → no retry, message to user
- Timeout (30s) → caught, logged, error message sent

---

### ElevenLabs TTS (Text-to-Speech)

**Endpoint:** `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`

**Request Pattern:**
```python
async def _tts_chunk(chunk: str) -> bytes:
    payload = {
        "text": chunk,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {"stability": 0.65, "similarity_boost": 0.85},
    }
    resp = await http.post(url, headers=headers, json=payload)
    return resp.content  # MP3 audio bytes
```

**Chunking Strategy:**
- Text split at sentence boundaries (regex: `(?<=[.!?])\s+`)
- Max 250 chars per chunk → avoids API cutoff
- Chunks synthesized in parallel via `asyncio.gather()`
- Retry once after 1s if fails (2 attempts total)

**Integration with Response:**
```python
audio_bytes = await synthesize_speech(spoken_text)
# Send to all browsers
await ws.send_json({
    "type": "response",
    "text": spoken_text,
    "audio": base64.b64encode(audio_bytes).decode()
})
```

**Errors:**
- API key invalid → SystemExit(1) at startup
- Status code ≠ 200 → logs warning, returns empty bytes
- Timeout → logs error, retry after 1s
- All chunks failed → silent (no audio sent to browser)

---

### Home Assistant Integration

**Endpoint:** Configured in `config.json` (e.g., `http://192.168.1.100:8123/api/`)

**Enabled Flag:** `ha_enabled: true` in config

**Services Called:**

#### Light Control (LICHT action)
```python
POST /api/services/light/turn_on
{
  "entity_id": "light.wohnzimmer",
  "brightness": 200  # Optional: 0-255
}
```

#### Calendar Events
```python
GET /api/states/calendar.home
```
Returns iCal event list for next N days

#### Temperature Sensor
```python
GET /api/states/sensor.indoor_temperature
# Returns: {"state": "21.5", "attributes": {...}}
```

**Guard Pattern:**
```python
if HA_URL and HA_TOKEN:
    # Make HA call
else:
    # Graceful degradation
```

**Errors:**
- Connection timeout → logs warning, continues
- Invalid token → 401 response → logs error
- Entity not found → returns empty/default value

---

### Weather API (Kachelmann)

**Endpoint:** Kachelmann REST API (paid subscription)

**Request Pattern:**
```python
GET https://api.kachelmannwetter.com/v4/...?lat=53.55&lon=10.00&access_token=...
```

**Data Points:**
- Current temperature
- Forecast for next 5 days
- Precipitation, wind, humidity

**Fallback:** If API fails, defaults to generic weather statements

---

### Apple Mail.app (AppleScript)

**Interface:** macOS AppleScript (subprocess)

**Data Extraction:**
```bash
osascript -e 'tell app "Mail"...'
```

Returns unread email list in format: `sender || subject`

---

### macOS Reminders (AppleScript)

**Interface:** macOS AppleScript (subprocess)

**Operations:**
- Get reminders: `GET /api/get_tasks`
- Mark complete: `POST /api/complete_task` (appends ✓)

---

## 6. Browser Control (Playwright)

### browser_tools.py Interface

**Singleton:** `browser_tools = BrowserTools()`

**Methods Called:**

#### `async search_and_read(query: str) -> dict`
- Searches Google
- Reads page content using claude-vision
- Returns: `{url, title, content}`

#### `async visit(url: str) -> dict`
- Opens URL in headless browser
- Extracts page text
- Returns: `{title, content}`

#### `async open_url(url: str) -> None`
- Opens URL in default browser (macOS `open` command)

#### `async fetch_news() -> str`
- Aggregates news from multiple sources
- Returns formatted news snippet

**Integration Point in process_message():**
```python
if action["type"] == "SEARCH":
    result = await browser_tools.search_and_read(payload)
    _last_result_url = result.get('url')
    return f"Seite: {result...}\nURL: {_last_result_url}..."
```

---

## 7. File System I/O

### Configuration Files

#### `config.json` (Required)
- Loaded at startup: `CONFIG_PATH = os.path.join(..., "config.json")`
- Keys: anthropic_api_key, elevenlabs_api_key, user_name, city, lat, lon, etc.
- On missing → SystemExit(1)
- On invalid JSON → SystemExit(1)
- Not reloaded during runtime

#### `voice.json` (Optional)
- Loaded at startup: `_voice_db = _load_voice_db()`
- Contains voice profiles for ElevenLabs
- Fallback: uses `config.json` elevenlabs_voice_id

#### `version.json`
- Format: `{"version": "0.3.0", "release_date": "2026-05-16"}`
- Used in: update check (SemVer comparison)

#### `locales/{de|en}.json`
- TTS response strings (greetings, briefs, etc.)
- Loaded once at startup based on `LANGUAGE` config
- Format: key → value pairs (sometimes lists for random selection)

### Data Files

#### `data/intro_shown.flag`
- Marker file indicating welcome page was shown
- Controls whether `/welcome` is shown on first start

#### `data/daily_brief_memory.json`
- **Purpose:** Track daily activity state for morning/evening briefs
- **Structure:** 
  ```json
  {
    "last_morning_brief": {
      "timestamp": "2026-05-16T07:30:00Z",
      "news_snippet_spoken": false,
      "mails_mentioned": 2,
      ...
    },
    "pause_threshold_minutes": 30,
    "long_absence_threshold_minutes": 90,
    "activity_log": [...]
  }
  ```
- **Lifecycle:** Auto-reset at midnight (detected by DailyBrief class)
- **Access:** Mutex protection via DailyBrief.load/save()

#### `data/daily_brief_archive/`
- Directory containing old daily_brief_memory.json files
- One file per day: `brief_2026-05-15.json`
- Read by DailyBrief for historical context

#### `data/news_archive/`
- RSS article cache
- Prevents duplicate articles and tracks read status

---

### Log Files

#### `~/Library/Logs/jarvis-v2/server.log`
- LaunchAgent logs from `com.jarvis.v2.server.plist`
- Format: `HH:MM:SS LEVEL [jarvis] message`

#### `~/Library/Logs/jarvis-v2/speech.log`
- LaunchAgent logs from `com.jarvis.v2.speech.plist`
- Contains RMS values, wake-word detection, transcription

---

### Obsidian Integration

**Paths configured in config.json:**
```json
{
  "obsidian_inbox_path": "/Users/.../Obsidian Vault/Inbox/",
  "obsidian_archive_path": "/Users/.../Obsidian Vault/Archive/"
}
```

**Operations:**
- Read: `GET /api/get_obsidian_notes` → lists files in inbox
- Mark done: `POST /api/complete_note` → appends `#done` tag
- Optional: Send to archive folder

---

## 8. Communication Patterns

### Pattern 1: Request-Response with Broadcast

**Trigger:** Browser sends message via `/ws`

```
Browser A sends → server.process_message()
    ├─ LLM processes
    ├─ TTS synthesizes
    └─ Broadcasts response to ALL /ws connections
        ├─ Browser A (sender)
        ├─ Browser B (other tabs)
        └─ Browser C (if open)
```

**Effect:** Multiple browsers see same conversation

---

### Pattern 2: Speech Input Queue

**Trigger:** speech_input.py sends text via `/ws/stt`

```
speech_input.py sends text
    ↓
stt_endpoint() receives
    ↓
Broadcast to all /ws connections: {"type": "user_input", ...}
    ↓
process_message() (using stt_endpoint's WebSocket or first browser)
    ↓
Response back to /ws connections
```

**Critical:** speech_input receives no audio feedback (prevents loop)

---

### Pattern 3: Background Task with Global State Update

**Example:** Daily brief morning trigger

```
Browser polls GET /api/daily_brief
    ↓
detect_morning_trigger() in DailyBrief
    ↓
Yes → fetch fresh data (mails, weather, calendar)
    ↓
Update MAIL_INFO, WEATHER_INFO, CALENDAR_INFO globals
    ↓
LLM generates rich greeting
    ↓
Spoken response
    ↓
Save state (news_snippet_spoken, timestamp)
```

**Thread Safety:** Locks guard updates to shared state

---

### Pattern 4: Action Execution with Result Feedback

**Example:** SEARCH action

```
process_message() extracts action: SEARCH
    ↓
execute_action({"type": "SEARCH", "payload": "weather forecast"})
    ↓
browser_tools.search_and_read() 
    ├─ Google search
    ├─ Headless browser visit
    └─ Claude vision analysis → content
    ↓
Result returned to process_message()
    ↓
LLM sees result, generates spoken response
    ↓
_speak() → TTS → broadcast response
```

---

## 9. Data Flow Diagrams

### Morning Brief Trigger Flow

```
6:00-10:00 AM
      ↓
Browser: GET /api/daily_brief
      ↓
daily_brief.detect_morning_trigger() → YES
      ↓
fetch_mail_sync() → MAIL_INFO
fetch_weather_sync() → WEATHER_INFO
fetch_calendar_sync() → CALENDAR_INFO
fetch_news() → NEWS_INFO
      ↓
daily_brief.record_morning_brief()
      ↓
get_system_prompt() → injects briefing context
      ↓
LLM: generate greeting + briefing
      ↓
_speak() → synthesize_speech() → ElevenLabs
      ↓
Broadcast to /ws: {"type": "response", "audio": "..."}
      ↓
Browser plays audio
      ↓
daily_brief.save() → mark last_morning_brief timestamp
```

---

### Command Execution Flow

```
User says: "Schreib mir eine Mail an Alice"
      ↓
speech_input.py → Whisper transcription
      ↓
/ws/stt: {"text": "Schreib mir eine Mail an Alice"}
      ↓
server.stt_endpoint() → process_message()
      ↓
LLM processes → structured action: MAIL_ACTION
      ↓
execute_action({"type": "MAIL_ACTION", "payload": "..."})
      ↓
browser_tools.compose_mail() or MAIL_SERVICE.send()
      ↓
Result: "Mail an Alice versendet"
      ↓
_speak() → broadcast
      ↓
browser plays response
```

---

## 10. Critical Touch Points for Service Isolation

### Must Stay in jarvis-core (Port 8340)

1. **FastAPI app instance** — all routing logic
2. **Conversations storage** — session management
3. **LLM integration** — Claude API calls
4. **System prompt generation** — context assembly
5. **Action dispatching** — determines what to execute
6. **Config loading** — startup initialization
7. **DailyBrief system** — state tracking
8. **NewsSystem** — RSS management

### Should Move to jarvis-audio (Port 8341)

1. **TTS synthesis** — ElevenLabs calls
2. **Speech response broadcasting** — WebSocket `/ws` audio streaming
3. **PTT state management** — ptt_start/ptt_stop
4. **Audio format conversion** — MP3 encoding

### Should Move to jarvis-ha (Port 8342)

1. **Home Assistant integration** — light control, calendar, temperature
2. **Weather API calls** — Kachelmann
3. **macOS service calls** — Mail.app, Reminders (AppleScript)
4. **Dashboard data fetching** — mail, tasks, calendar aggregation
5. **Obsidian operations** — file I/O

### Remains External

1. **speech_input.py** — separate microphone service (Port: none, uses `/ws/stt`)
2. **index.html** — browser UI (consumes `/ws` WebSocket)
3. **browser_tools.py** — Playwright (refactor to separate jarvis-browser service later)

---

## 11. Next Steps (Spike Phase Complete)

1. ✅ Document all interfaces (this file)
2. ⬜ Create `SERVICE_SPECS.md` — detailed specification for each microservice
3. ⬜ Create `PHASE_2_MIGRATION.md` — step-by-step migration guide per service
4. ⬜ Begin Phase 1 implementation: jarvis-audio service skeleton

---

**Last Updated:** 2026-05-16  
**Status:** Spike Phase — ready for implementation  
**Next Review:** Before Phase 1 implementation begins
