# Phase 2: Detailed Service Specifications

> Exact API contracts and behavioral specifications for each microservice
> **Purpose:** Enable clean isolation with zero behavioral regression
> **Status:** Spike Phase (2026-05-16)

---

## Overview: Service Topology

```
┌─────────────────┐
│ jarvis-core     │  Port 8340
│ (FastAPI)       │  LLM, actions, routing, config
└────────┬────────┘
         │
    ┌────┴────┐
    │          │
┌───▼────┐  ┌─▼────────┐
│ jarvis-│  │ jarvis-ha│  Port 8342
│ audio  │  │(HA, Mail,│  Home Assistant, weather,
│        │  │ Weather) │  mail, tasks, calendar
│(TTS)   │  └──────────┘
│ 8341   │
└────────┘

External:
┌──────────────┐
│ speech_input │  /ws/stt (localhost:8340)
│ (Whisper STT)│  Sends text only
└──────────────┘

┌──────────────┐
│ index.html   │  /ws (localhost:8340)
│ (Browser)    │  Sends text, receives audio
└──────────────┘
```

---

## Service 1: jarvis-core (Port 8340)

### Purpose
Central orchestration: LLM processing, action dispatching, WebSocket routing, config management.

### Startup Sequence
1. Load `config.json` (required keys: anthropic_api_key, elevenlabs_api_key)
2. Load `voice.json` and locale files
3. Initialize DailyBrief system
4. Create FastAPI app
5. Register endpoints
6. Bind to `127.0.0.1:8340` (localhost only)

### Configuration File
**Path:** `./config.json`  
**Required Keys:**
- `anthropic_api_key` (string)
- `elevenlabs_api_key` (string)
- `elevenlabs_voice_id` (string)
- `user_name` (string, used in greetings)
- `user_address` (string, form of address "Sir", "Herr", etc.)
- `language` (string, "de" or "en")
- `city` (string, for weather context)
- `lat`, `lon` (floats, location)

**Optional Keys:**
- `kachelmann_api_key` (string, for weather)
- `ha_enabled` (bool, default true)
- `ha_url`, `ha_token` (strings, Home Assistant)
- `obsidian_inbox_path`, `obsidian_archive_path` (strings)
- `wake_greeting_enabled` (bool, default true)

### Incoming WebSocket Endpoints

#### `/ws` — Browser Dashboard
**Clients:** index.html (may be multiple tabs/windows)

**Message In:**
```json
{
  "text": "User message here"
}
```

**Messages Out (all JSON):**

**Response Message:**
```json
{
  "type": "response",
  "text": "Spoken response text",
  "audio": "base64-encoded-mp3-audio"
}
```

**User Input (broadcast to all browsers):**
```json
{
  "type": "user_input",
  "text": "Text recognized from speech_input.py"
}
```

**PTT Status:**
```json
{
  "type": "ptt_start"
}
```
```json
{
  "type": "ptt_stop"
}
```

**HUD State:**
```json
{
  "type": "listen_open"
}
```
```json
{
  "type": "listen_close"
}
```

**Error Message:**
```json
{
  "type": "tts_error",
  "message": "Error description"
}
```

---

#### `/ws/stt` — Speech-to-Text Input
**Clients:** speech_input.py (single connection)

**Message In:**
```json
{
  "text": "Jarvis activate"
}
```

**Messages Out:**
- None (one-way input only)
- Exception: Broadcasts user_input to `/ws` browsers

---

### Internal State Management

**Global Variables (synchronized with locks):**
```python
conversations: dict[str, list[dict]]
# Key: session_id
# Value: [{"role": "user|assistant", "content": str}, ...]
# Lifetime: Session duration

active_connections: set[WebSocket]
# All connected browser WebSocket instances
# Used for: Broadcasting responses

stt_connections: set[WebSocket]
# All connected speech_input.py instances
# Expected: 1 connection

_mail_lock = asyncio.Lock()
# Guards concurrent updates to MAIL_INFO

MAIL_INFO: list[str]
TASKS_INFO: list[str]
CALENDAR_INFO: list[str]
NEWS_INFO: list[dict]
WEATHER_INFO: dict
OBSIDIAN_INFO: list[str]
```

**DailyBrief State:**
```python
daily_brief = DailyBrief()
# Manages: last_morning_brief timestamp, activity tracking
# Persisted in: data/daily_brief_memory.json
# Auto-reset: at midnight (local time)
```

---

### REST API Endpoints Remaining in jarvis-core

#### **`GET /` — Dashboard**
- Returns `index.html`

#### **`GET /config` — Config UI**
- Returns `config.html`

#### **`GET /handbuch` — User Manual**
- Returns `handbuch.html`

#### **`POST /api/config` — Update Configuration**
- Saves updated config.json
- Payload: `{key: value, ...}`
- Response: `{status: "ok", changed_keys: [...]}`

#### **`GET /api/language` — Current Language**
- Returns: `{"language": "de|en", "speech_lang": "de-DE|en-US"}`

#### **`GET /api/update_check` — Version Check**
- Returns: `{current: "0.3.0", latest: "0.3.2", update_available: bool, url: "..."}`
- Cache: 24 hours

#### **`POST /api/restart` — Restart Server**
- Effect: Exits process → launchd auto-restarts
- Response: `{status: "restarting"}`

#### **`GET /static/*` — Static Files**
- Serves: index.html, config.html, locales, etc.

---

### Endpoints Delegated to jarvis-ha (via HTTP proxy)

These endpoints stay in jarvis-core but call jarvis-ha internally:

```
GET /api/get_mails_unread
GET /api/get_tasks
GET /api/get_obsidian_notes
POST /api/complete_task
POST /api/complete_note
GET /api/daily_brief
POST /api/daily_brief/manual
GET /api/daily_brief/memory
GET /api/news
GET /api/news/search
POST /api/news/read
GET /api/rss_feeds
POST /api/rss_feeds/*
DELETE /api/rss_feeds/*
POST /api/open_app
```

**Implementation Pattern:**
```python
async def get_mails_unread():
    async with httpx.AsyncClient() as client:
        return await client.get("http://localhost:8342/api/get_mails_unread")
```

---

### Endpoints Delegated to jarvis-audio (via HTTP proxy)

```
POST /api/synthesize  (internal only — called by process_message)
```

---

### Action Dispatching (process_message)

**Flow:**
1. Receive `user_text` from `/ws` or `/ws/stt`
2. Store in conversation history
3. Call LLM: `claude-haiku-4-5-20251001`
4. Parse structured action or legacy string action
5. Dispatch:
   - **SEARCH, BROWSE, NEWS_SEARCH** → jarvis-ha
   - **LICHT, HA_ACTION** → jarvis-ha
   - **TTS** → jarvis-audio
   - **SCREEN** → internal (Playwright)
6. Broadcast response

---

### LLM Integration

**Model:** `claude-haiku-4-5-20251001`

**Request Parameters:**
- `max_tokens: 300`
- `system`: Dynamic prompt (see `get_system_prompt()`)
- `messages`: Last 16 conversation turns

**System Prompt Composition:**
```
1. User identity: name, address
2. Location: city, lat/lon
3. Current time/date
4. Available actions and syntax
5. Home Assistant integration (if enabled)
6. Language instruction
7. Daily brief context (if triggered)
8. Recent brief history
```

**Response Parsing:**
1. Try JSON structured action: `parse_structured_action(reply)`
   - Expects: `{"action": "...", "payload": "...", "response": "..."}`
2. Fallback: regex-based legacy parsing: `extract_action(reply)`

---

### Error Handling

**Startup Errors (fatal):**
- Missing config.json → logs + SystemExit(1)
- Invalid anthropic_api_key → logs + SystemExit(1)
- Invalid elevenlabs_api_key → logs + SystemExit(1)
- Failed Anthropic connection → logs + SystemExit(1)

**Runtime Errors (non-fatal):**
- WebSocket disconnect → logs, session purged after 30s
- LLM request fails → error message sent to user
- jarvis-ha unavailable → graceful degradation (no mail, tasks, etc.)
- jarvis-audio unavailable → error message (no audio response)

---

## Service 2: jarvis-audio (Port 8341)

### Purpose
Synthesis and broadcasting of TTS audio responses. Isolated from core LLM logic.

### Startup Sequence
1. Load `config.json` (need: elevenlabs_api_key, elevenlabs_voice_id)
2. Initialize httpx client
3. Bind to `127.0.0.1:8341` (localhost only)

### Configuration Requirements
**From config.json:**
- `elevenlabs_api_key` (required)
- `elevenlabs_voice_id` (required)

---

### REST API Endpoints

#### **`POST /api/synthesize` — Text-to-Speech**

**Request:**
```json
{
  "text": "Guten Morgen, Herr Schreiber.",
  "voice_id": "optional-override"
}
```

**Response (Success):**
```json
{
  "audio": "base64-encoded-mp3-audio",
  "bytes": 12345,
  "chunks": 1
}
```

**Response (Error):**
```json
{
  "error": "ElevenLabs API error",
  "status_code": 429
}
```

---

#### **`GET /health` — Health Check**
**Response:**
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "elevenlabs_connected": true
}
```

---

### Internal Logic

**Chunking Algorithm:**
```
Input: Long text
├─ If > 250 chars:
│  └─ Split at sentence boundaries (regex: (?<=[.!?])\s+)
├─ Create chunks (max 250 chars each)
└─ Synthesize in parallel (asyncio.gather)

Retry Logic:
├─ Each chunk: 2 attempts (0s, then +1s delay)
└─ If all chunks fail: return empty audio
```

**ElevenLabs Request Pattern:**
```python
POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
{
  "text": "...",
  "model_id": "eleven_turbo_v2_5",
  "voice_settings": {
    "stability": 0.65,
    "similarity_boost": 0.85
  }
}
Headers: xi-api-key, Content-Type: application/json, Accept: audio/mpeg
```

---

### Error Handling

**Startup Errors:**
- Missing elevenlabs_api_key → SystemExit(1)
- Invalid API key → logs warning (confirmed on first use)

**Runtime Errors:**
- Status code ≠ 200 → logs, retry once after 1s
- Timeout (30s) → logs, retry once
- All retries fail → return empty bytes (signal to caller)

---

## Service 3: jarvis-ha (Port 8342)

### Purpose
Dashboard data aggregation (mail, tasks, calendar, weather, news) and Home Assistant integration.

### Startup Sequence
1. Load `config.json` (check: ha_enabled, ha_url, ha_token)
2. Load locale files for formatting
3. Initialize AppleScript/system call handlers
4. Bind to `127.0.0.1:8342` (localhost only)

### Configuration Requirements
**From config.json:**
- `ha_enabled` (optional, default true)
- `ha_url` (if ha_enabled: required)
- `ha_token` (if ha_enabled: required)
- `kachelmann_api_key` (optional, for weather)
- `obsidian_inbox_path` (optional)
- `obsidian_archive_path` (optional)
- `user_address` (required, for greetings)
- `language` (required, for locale)

---

### REST API Endpoints

#### **`GET /api/get_mails_unread` — Unread Emails**

**Implementation:**
```python
def get_mail_sync():
    # AppleScript call to Mail.app
    # Returns: [
    #   "alice@example.com || Meeting Notes",
    #   "bob@company.com || Project Update",
    # ]
```

**Response:**
```json
{
  "mails": [
    {
      "id": "alice@example.com_Meeting Notes",
      "sender": "alice@example.com",
      "subject": "Meeting Notes",
      "unread": true
    }
  ],
  "total": 3
}
```

**Cache:** 30 seconds (managed by caller)

---

#### **`GET /api/get_tasks` — Reminders + Calendar**

**Implementation:**
```python
def get_tasks_sync():
    # AppleScript: reminders from Reminders.app
    # Returns list of reminder titles

# Conditional on HA:
def get_calendar_sync(days=2):
    # If ha_enabled and ha_url/token valid:
    #   GET /api/states/calendar.home (Home Assistant)
    #   Parse iCal data
    # Returns formatted event list:
    #   ["Meeting -- 14:00-15:00", "Doctor -- tomorrow 10:00"]
```

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
      "source": "calendar"
    }
  ],
  "total": 5
}
```

**Cache:** 30 seconds

---

#### **`GET /api/get_obsidian_notes` — Inbox**

**Implementation:**
```python
def get_obsidian_info_sync():
    # Reads files from obsidian_inbox_path
    # Filters: only .md files, skips #done marked
    # Returns: [
    #   "Talk to Alice",
    #   "Review document",
    # ]
```

**Response:**
```json
{
  "notes": [
    {
      "id": "call_alice.md",
      "title": "call alice",
      "preview": "Schedule call about...",
      "content": "Full note content",
      "completed": false
    }
  ],
  "total": 2
}
```

---

#### **`POST /api/complete_task` — Mark Reminder Complete**

**Request:**
```json
{
  "task_id": "task_0"
}
```

**Implementation:**
```python
# AppleScript: append "✓" to reminder in Reminders.app
```

**Response:**
```json
{
  "status": "ok",
  "task_id": "task_0"
}
```

---

#### **`POST /api/complete_note` — Mark Note Complete**

**Request:**
```json
{
  "note_id": "call_alice.md"
}
```

**Implementation:**
```python
# File I/O: append " #done" tag to obsidian_inbox_path/note_id
```

**Response:**
```json
{
  "status": "ok",
  "note_id": "call_alice.md"
}
```

---

#### **`GET /api/daily_brief` — Morning/Evening Trigger**

**Request Params:**
- `trigger_type` (optional): force trigger ("morning" | "evening" | "absence" | "reset")

**Logic:**
1. Check if morning (6-10am) or evening (18-22:00)
2. Load daily_brief_memory.json
3. Detect if first brief of day, pause, or absence
4. Fetch fresh mail, tasks, weather, news
5. Return: `{triggered: bool, text: "..."}`

**Response:**
```json
{
  "triggered": true,
  "trigger_type": "morning",
  "text": "Guten Morgen Herr Schreiber..."
}
```

---

#### **`GET /api/weather` — Current Weather**

**Implementation (if weather API available):**
```python
def get_weather_sync():
    if KACHELMANN_KEY:
        # Call Kachelmann API
    else:
        # Return generic message
```

**Response:**
```json
{
  "temp": 21.5,
  "condition": "Partly cloudy",
  "forecast": "..."
}
```

---

#### **`GET /api/news` — All News Articles**

**Response:**
```json
{
  "articles": [
    {
      "id": "uuid",
      "source": "Der Spiegel",
      "title": "Article title",
      "published": "2026-05-16T10:00:00Z",
      "read": false
    }
  ],
  "total": 42
}
```

---

#### **`GET /api/rss_feeds` — List Feeds**

**Response:**
```json
{
  "feeds": [
    {
      "id": "feed_1",
      "name": "Der Spiegel",
      "url": "https://...",
      "active": true,
      "article_count": 15
    }
  ],
  "total": 5
}
```

---

### Home Assistant Service Calls

**Pattern (if ha_enabled and HA credentials available):**

```python
async def ha_call(service: str, entity_id: str, data: dict):
    POST {HA_URL}/api/services/{service}
    {
      "entity_id": entity_id,
      **data
    }
    Headers: Authorization: Bearer {HA_TOKEN}
```

**Services Called:**

#### **Light Control (LICHT action)**
```
GET /api/states/light.{entity}
POST /api/services/light/turn_on
  {entity_id: light.{name}, brightness: 0-255}
POST /api/services/light/turn_off
  {entity_id: light.{name}}
```

#### **Temperature Sensor**
```
GET /api/states/sensor.indoor_temperature
  Returns: {state: "21.5", attributes: {...}}
```

#### **Calendar Events**
```
GET /api/states/calendar.home
  Returns: iCal events for next N days
```

---

### Error Handling

**Graceful Degradation:**
- HA unavailable → mail/tasks/calendar endpoints return empty
- Mail.app not running → empty mail list
- Obsidian path not configured → empty notes
- Weather API fail → generic message

**Startup Errors:**
- AppleScript environment broken → logs warning, continues
- HA URL unreachable → logs warning, continues

**Runtime Errors:**
- HA API call fails → logs, returns empty/default
- File I/O fails → logs, returns empty list

---

## Cross-Service Communication

### jarvis-core → jarvis-audio

**Pattern:**
```python
# In process_message():
text = "Guten Morgen"
async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8341/api/synthesize",
        json={"text": text}
    )
    audio_b64 = resp.json()["audio"]

# Broadcast to browsers
await ws.send_json({
    "type": "response",
    "text": text,
    "audio": audio_b64
})
```

---

### jarvis-core → jarvis-ha

**Pattern:**
```python
# In REST handlers:
async with httpx.AsyncClient() as client:
    resp = await client.get(
        "http://localhost:8342/api/get_mails_unread"
    )
    result = resp.json()

# Cache and return to browser
return result
```

---

### jarvis-core ← jarvis-ha (process_message receives action)

**Pattern:**
```python
# LLM returns action
action = {
    "type": "LICHT",
    "payload": "wohnzimmer an"
}

# jarvis-core dispatches to jarvis-ha
async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8342/api/execute_action",
        json=action
    )
    result = resp.json()["result"]

# Continue process_message with result
```

---

## Deployment Checklist

### jarvis-core
- [ ] Remove TTS synthesis code
- [ ] Replace with HTTP call to jarvis-audio:8341
- [ ] Remove Home Assistant code
- [ ] Replace with HTTP proxies to jarvis-ha:8342
- [ ] Keep: LLM, WebSocket routing, action dispatching
- [ ] Keep: index.html, config.html, system prompt generation
- [ ] Test: "Jarvis activate" still works
- [ ] Test: Browser receives audio from jarvis-audio

### jarvis-audio
- [ ] Extract synthesize_speech(), _tts_chunk(), _tts_sanitize()
- [ ] Create new FastAPI app on port 8341
- [ ] POST /api/synthesize endpoint
- [ ] Test: curl http://localhost:8341/api/synthesize with text
- [ ] Test: Audio bytes returned correctly

### jarvis-ha
- [ ] Extract all *_sync() functions for mail, tasks, calendar, weather
- [ ] Extract Home Assistant integration code
- [ ] Extract Obsidian file I/O
- [ ] Extract NewsSystem
- [ ] Create new FastAPI app on port 8342
- [ ] Implement all /api/* endpoints
- [ ] Test: curl http://localhost:8342/api/get_mails_unread returns JSON
- [ ] Test: Weather, calendar, notes all return correct data

---

## Testing Strategy

### Unit Tests
- TTS chunking algorithm (jarvis-audio)
- HA entity parsing (jarvis-ha)
- Action extraction regex (jarvis-core)

### Integration Tests
- speech_input.py → jarvis-core → jarvis-audio → browser
- Browser command → jarvis-core → jarvis-ha → HA light control
- Morning brief → jarvis-core → jarvis-ha → jarvis-audio

### Smoke Tests
- Start all 3 services
- Verify health endpoints respond
- Send test message via browser
- Verify response audio received
- Verify light control works (if HA available)

---

**Document Version:** 0.1  
**Last Updated:** 2026-05-16  
**Next Step:** Create PHASE_2_MIGRATION.md with step-by-step implementation guide
