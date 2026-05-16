# Phase 2: Getting Started — Step-by-Step Implementation Guide

> From monolith to microservices: A practical, safe path to service isolation
> **Target:** v0.4.0 (estimated 2 weeks from spike completion)

---

## Before You Start

### Prerequisites
1. ✅ Read PHASE_2_INTERFACES.md (understand all communication patterns)
2. ✅ Read SERVICE_SPECS.md (understand service boundaries)
3. ✅ Have PHASE_2_PLAN.md open (reference implementation timeline)
4. ✅ Current working version: v0.3.0 (git tag exists, can rollback)

### Backup Strategy
```bash
# Current state is safe
git tag v0.3.0-backup
git branch develop  # Shadow main during implementation
# Switch to develop for all Phase 2 work
git checkout develop
```

---

## Phase 2.1: jarvis-audio Service (Week 1)

### Goal
Extract TTS (text-to-speech) synthesis into isolated service on port 8341.

### What Stays in server.py
- ❌ Remove: `synthesize_speech()`, `_tts_chunk()`, `_tts_sanitize()`
- ✅ Keep: LLM processing, action dispatching, WebSocket routing
- ✅ Add: HTTP client to call jarvis-audio for TTS

### Implementation Steps

#### Step 1: Create jarvis-audio skeleton
```bash
mkdir -p services/jarvis-audio
cd services/jarvis-audio
cat > main.py << 'EOF'
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import json
import os

app = FastAPI(title="jarvis-audio", version="0.1.0")

# Load config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
with open(CONFIG_PATH) as f:
    config = json.load(f)

ELEVENLABS_API_KEY = config.get("elevenlabs_api_key", "")
ELEVENLABS_VOICE_ID = config.get("elevenlabs_voice_id", "")

if not ELEVENLABS_API_KEY or not ELEVENLABS_VOICE_ID:
    raise SystemExit("Missing elevenlabs_api_key or elevenlabs_voice_id in config.json")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "jarvis-audio", "version": "0.1.0"}

@app.post("/api/synthesize")
async def synthesize(request: dict):
    # TODO: Implement TTS
    return {"error": "Not implemented"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8341)
EOF
```

#### Step 2: Extract TTS functions from server.py

**File:** Extract from server.py lines 925-1022
```python
def _tts_sanitize(text: str) -> str:
    # [copy from server.py]

async def synthesize_speech(text: str, voice_id: Optional[str] = None) -> bytes:
    # [copy from server.py]
```

**Add to:** `services/jarvis-audio/tts_engine.py`

#### Step 3: Implement /api/synthesize endpoint

```python
from tts_engine import synthesize_speech

@app.post("/api/synthesize")
async def synthesize(request: dict):
    """POST {"text": "...", "voice_id": "optional-override"}"""
    text = request.get("text", "").strip()
    if not text:
        return {"error": "Empty text"}
    
    voice_id = request.get("voice_id") or ELEVENLABS_VOICE_ID
    try:
        audio_bytes = await synthesize_speech(text, voice_id)
        if not audio_bytes:
            return {"error": "TTS failed"}
        
        import base64
        return {
            "audio": base64.b64encode(audio_bytes).decode(),
            "bytes": len(audio_bytes),
            "chunks": len(audio_bytes) // 1000  # rough estimate
        }
    except Exception as e:
        return {"error": str(e)}
```

#### Step 4: Update server.py to call jarvis-audio

**Find:** Line 1385 `async def _speak(ws: WebSocket, session_id: str, text: str, display: str = ""):`

**Replace synthesize_speech() call:**
```python
async def _speak(ws: WebSocket, session_id: str, text: str, display: str = ""):
    """Unchanged except TTS call is now remote"""
    # ... existing code ...
    
    # OLD:
    # hint_audio = await synthesize_speech("Einen Moment.")
    
    # NEW:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "http://127.0.0.1:8341/api/synthesize",
                json={"text": hint_text}
            )
            if resp.status_code == 200:
                audio_b64 = resp.json().get("audio", "")
            else:
                audio_b64 = ""
        except Exception as e:
            log.error(f"jarvis-audio call failed: {e}")
            audio_b64 = ""
    
    # Continue as before with audio_b64
```

#### Step 5: Test locally

**Terminal 1 — Start jarvis-audio:**
```bash
cd services/jarvis-audio
python3.11 main.py
# Should print: Uvicorn running on http://127.0.0.1:8341
```

**Terminal 2 — Test with curl:**
```bash
curl -X POST http://127.0.0.1:8341/api/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hallo Welt"}'

# Should return:
# {"audio": "//NExAAiZAOp/QACEQ...", "bytes": 12345, "chunks": 12}
```

**Terminal 3 — Start server.py (existing):**
```bash
cd /Users/matthiasschreiber/Jarvis-2.0
python3.11 server.py
# Should print: Uvicorn running on http://127.0.0.1:8340
```

**Browser test:**
1. Open http://localhost:8340/
2. Type "Hallo" in chat
3. Listen for audio response (calls jarvis-audio internally)

#### Step 6: Commit

```bash
git add .
git commit -m "feat: Extract TTS to jarvis-audio microservice (port 8341)"
# Update CHANGELOG.md and version.json for v0.4.0-dev
```

---

## Phase 2.2: jarvis-ha Service (Week 2-3)

### Goal
Extract dashboard data fetching (mail, tasks, calendar, weather) into service on port 8342.

### What to Extract
1. `get_mail_sync()` (AppleScript)
2. `get_tasks_sync()` (Reminders.app)
3. `get_calendar_sync()` (Home Assistant or file)
4. `get_weather_sync()` (Kachelmann API)
5. `get_obsidian_info_sync()` (file I/O)
6. Home Assistant integration code
7. NewsSystem and RSS management

### Implementation Steps

#### Same pattern as jarvis-audio:
1. Create `services/jarvis-ha/main.py`
2. Extract sync functions
3. Implement REST endpoints (/api/get_mails_unread, /api/get_tasks, etc.)
4. Update server.py to proxy calls via HTTP
5. Test each endpoint with curl
6. Test from browser (dashboard loads)

#### Key Difference from jarvis-audio:
- jarvis-ha is stateful (owns daily_brief memory, news archive)
- Must load/save data files atomically
- Must handle Home Assistant errors gracefully

---

## Phase 2.3: jarvis-core Refactoring (Week 4)

### Goal
Refactor server.py to delegate to services, keeping only orchestration logic.

### What Stays
- FastAPI app and WebSocket endpoints
- LLM processing (Claude API calls)
- Action dispatching logic
- System prompt generation
- Configuration management
- Static file serving (index.html, config.html)

### What Moves
- All *_sync() functions → jarvis-ha
- TTS synthesis → jarvis-audio
- Home Assistant calls → jarvis-ha
- Browser control (Playwright) → future jarvis-browser service (optional)

### HTTP Proxying Pattern

**Current (monolith):**
```python
async def get_mails_unread():
    loop = asyncio.get_event_loop()
    fresh = await loop.run_in_executor(None, get_mail_sync)
    return {"mails": mails, "total": len(mails)}
```

**After refactoring:**
```python
async def get_mails_unread():
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://127.0.0.1:8342/api/get_mails_unread")
        return resp.json()
```

---

## Phase 2.4: Integration Testing (Week 4-5)

### Test Checklist

#### Service Startup
- [ ] Start jarvis-audio → health check passes
- [ ] Start jarvis-ha → health check passes
- [ ] Start server.py → binds to 8340
- [ ] All services respond to /health endpoint

#### Core Workflows
- [ ] Browser sends "Hallo" → server.py processes → jarvis-audio TTs → browser plays audio
- [ ] Morning 7am → server.py detects trigger → jarvis-ha fetches mail/weather → LLM generates brief → audio plays
- [ ] "Schalte Licht an" → server.py extracts action → jarvis-ha controls HA → light turns on
- [ ] "Zeig mir Mails" → server.py dispatches → jarvis-ha fetches → dashboard shows emails

#### Failure Scenarios
- [ ] jarvis-audio down → server.py shows error, user hears voice message
- [ ] jarvis-ha down → mail/tasks/calendar empty, but server continues
- [ ] speech_input.py down → browser still works, manual text input works
- [ ] Network latency → 5s timeout configured, user sees "Einen Moment"

#### Edge Cases
- [ ] "Jarvis activate" within 5s → suppressed (debounce)
- [ ] Multiple browser tabs → all receive same response
- [ ] Long text (2000+ chars) → chunked correctly → plays without cutoff
- [ ] HA not configured → dashboard shows empty, no errors
- [ ] Obsidian path invalid → notes return empty, no crash

---

## Deployment Changes

### Current (v0.3.0 Monolith)
```bash
/opt/homebrew/bin/python3.11 /Users/matthiasschreiber/Jarvis-2.0/server.py
# LaunchAgent: com.jarvis.v2.server.plist
```

### After Phase 2 (v0.4.0 Microservices)
```bash
# Still need: server.py (core) on 8340
/opt/homebrew/bin/python3.11 /Users/matthiasschreiber/Jarvis-2.0/server.py

# NEW: audio service on 8341
/opt/homebrew/bin/python3.11 /Users/matthiasschreiber/Jarvis-2.0/services/jarvis-audio/main.py

# NEW: ha service on 8342
/opt/homebrew/bin/python3.11 /Users/matthiasschreiber/Jarvis-2.0/services/jarvis-ha/main.py
```

### LaunchAgent Updates Required
- Update `com.jarvis.v2.server.plist` to remain unchanged (still runs server.py)
- Create `com.jarvis.v2.audio.plist` (runs jarvis-audio/main.py)
- Create `com.jarvis.v2.ha.plist` (runs jarvis-ha/main.py)
- Update supervisor.py to monitor 3 services instead of 2

---

## Rollback Path (if needed)

### Scenario: jarvis-audio service broken in production

**Time to rollback:** < 5 minutes

```bash
# Stop problematic Phase 2 work
git stash

# Return to known-good state
git checkout v0.3.0

# Restart services
launchctl kickstart -k gui/501/com.jarvis.v2.server

# All traffic goes to monolith again
# Users see no disruption
```

### Scenario: Phase 2 partially working, want to stabilize before continuing

```bash
# Create v0.4.0-phase2-step1 tag for current state
git tag v0.4.0-phase2-step1

# If Phase 2.2 causes issues, revert to Phase 2.1 state:
git reset --hard v0.4.0-phase2-step1
```

---

## Logging & Debugging

### Each Service Logs to Separate File

**jarvis-core:**
```
~/Library/Logs/jarvis-v2/core.log
```

**jarvis-audio:**
```
~/Library/Logs/jarvis-v2/audio.log
```

**jarvis-ha:**
```
~/Library/Logs/jarvis-v2/ha.log
```

### Monitoring Script

```bash
# Terminal 1: Core logs
tail -f ~/Library/Logs/jarvis-v2/core.log | grep -v DEBUG

# Terminal 2: Audio logs
tail -f ~/Library/Logs/jarvis-v2/audio.log

# Terminal 3: HA logs
tail -f ~/Library/Logs/jarvis-v2/ha.log

# Terminal 4: Health check loop
while true; do
  echo "=== $(date) ==="
  curl -s http://127.0.0.1:8340/health | jq .
  curl -s http://127.0.0.1:8341/health | jq .
  curl -s http://127.0.0.1:8342/health | jq .
  sleep 5
done
```

---

## Documentation Updates During Phase 2

### What to Update When
1. **Each commit:** Update CHANGELOG.md with what moved/changed
2. **Weekly:** Update PHASE_2_PROGRESS.md with blockers and learnings
3. **After each service:** Update service README in services/jarvis-{audio,ha}/
4. **Final:** Update main README.md with new architecture diagram

### Obsidian Documents to Create
- `PHASE_2_PROGRESS.md` — Daily log of implementation progress
- `SERVICE_AUDITS.md` — Testing results for each service
- `INTEGRATION_TESTS.md` — Detailed test results
- `ROLLBACK_LOG.md` — Record of any rollbacks/fixes

---

## Success Criteria for Phase 2

### Code Quality
- [ ] No circular dependencies between services
- [ ] Each service has single responsibility
- [ ] All public APIs documented (docstrings)
- [ ] Error handling is graceful (no crashes)

### Performance
- [ ] Service startup time < 2 seconds each
- [ ] HTTP inter-service calls < 500ms average
- [ ] Total latency (browser→core→audio→browser) < 2s
- [ ] TTS chunking prevents ElevenLabs timeouts

### Reliability
- [ ] Service restarts don't lose conversation history
- [ ] Missing service gracefully degrades
- [ ] No audio feedback loops (speech_input.py sleeps during server TTS)
- [ ] Debouncing prevents double-activations

### Maintainability
- [ ] New dev can understand each service in < 30 minutes
- [ ] Services can be developed/tested independently
- [ ] Clear rollback path documented
- [ ] All interfaces versioned (can evolve without breaking)

---

## Next Session: Begin Phase 2.1

When ready to start:
1. Create `services/jarvis-audio/` directory
2. Copy config.json reference
3. Implement main.py skeleton
4. Extract TTS functions from server.py
5. Commit and test

---

**Document Version:** 0.1  
**Last Updated:** 2026-05-16  
**Status:** Ready for implementation
