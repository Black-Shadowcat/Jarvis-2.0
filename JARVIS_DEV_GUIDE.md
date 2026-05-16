# J.A.R.V.I.S. 2.0 — Developer Guide

**Version:** 1.2.0  
**Für:** Developers, Contributors, Maintainers  
**Letztes Update:** Mai 2026

---

## 🏗️ Architecture Overview

Jarvis ist ein **Microservices-System** mit 3 unabhängigen Python-Services:

```
┌─────────────────────────────────────────────────────┐
│  Browser Frontend (index.html)                      │
│  ├─ WebSocket Connection (localhost:8340/ws)       │
│  ├─ Dashboard UI (Mail, Tasks, Weather)             │
│  └─ Settings & Health Monitor                       │
└──────────────┬──────────────────────────────────────┘
               │ WebSocket
       ┌───────┴────────────┬──────────────┬──────────┐
       ▼                    ▼              ▼          ▼
   jarvis-core         jarvis-audio   jarvis-ha   supervisor
   :8340               :8341          :8342       (health)
   ├─ FastAPI          ├─ Speech      ├─ Mail     ├─ Monitor
   ├─ Claude AI        │  Recognition │ Tasks     │  Services
   ├─ Browser Control  ├─ TTS         │ Weather   ├─ Restart
   ├─ Actions          └─ VAD         │ Calendar  │  Policy
   └─ WebSocket          (M10)        └─ HA       └─ Logs
       Handler                           Caching
```

### Services

| Service | Port | Verantwortung |
|---------|------|---------------|
| **jarvis-core** | 8340 | FastAPI Backend, Claude AI, Actions, WebSocket |
| **jarvis-audio** | 8341 | Speech Recognition (mlx-whisper), TTS (ElevenLabs) |
| **jarvis-ha** | 8342 | Mail (AppleScript), Tasks, Weather, Home Assistant |
| **supervisor** | — | LaunchAgent, Health Monitor, Auto-Restart |

---

## 🛠️ Setup & Local Development

### Prerequisites
```bash
# Python 3.11
python3.11 --version

# Homebrew packages
brew install python@3.11 pipx
```

### Clone & Install
```bash
git clone https://github.com/Black-Shadowcat/Jarvis-2.0
cd Jarvis-2.0
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### Configuration
```bash
cp config.example.json config.json
# Edit config.json with your API keys
# Required: anthropic_api_key, elevenlabs_api_key
```

### Run Locally
```bash
# Terminal 1: Main server
python3.11 server.py

# Terminal 2: Check status
curl http://localhost:8340/health
```

### Debug Mode
```bash
# With logging
PYTHONUNBUFFERED=1 python3.11 server.py 2>&1 | tee debug.log

# With profiling
python3.11 -m cProfile -s cumulative server.py
```

---

## 📂 Code Structure

### Root Files
```
Jarvis-2.0/
├─ server.py              ← Main FastAPI server (2000+ lines)
├─ browser_tools.py       ← Playwright browser control
├─ screen_capture.py      ← Vision integration (Claude)
├─ config.json            ← User configuration (gitignored)
└─ requirements.txt       ← Python dependencies
```

### Frontend
```
frontend/
├─ index.html             ← Main dashboard (8000+ lines, all inline JS/CSS)
├─ config.html            ← Settings page
├─ handbuch.html          ← User manual
└─ i18n/
   ├─ de.json             ← German UI labels
   └─ en.json             ← English UI labels
```

### Services
```
services/
├─ jarvis-ha/main.py     ← Mail, Tasks, Weather, HA integration
├─ audio/                ← (Future) Speech processing
└─ (future services)
```

### System Modules
```
systems/
├─ daily_brief.py        ← Daily Brief intelligence (M15)
├─ news_system.py        ← News briefing
└─ (future modules)
```

### Data & Scripts
```
data/
├─ daily_brief_memory.json        ← Session state
└─ daily_brief_archive/           ← Historical data

scripts/
├─ launch-session.sh              ← Auto-launch setup
├─ setup-plists.sh                ← LaunchAgent installation
└─ calibrate-vad.py               ← Voice VAD tuning
```

---

## 🔄 Data Flow

### User gives voice command:
```
1. Browser captures audio (Web Audio API)
   ↓
2. Sends to /ws WebSocket endpoint
   ↓
3. server.py processes (Claude thinking)
   ↓
4. Action execution (lights, browser, etc)
   ↓
5. Response TTS → Browser plays audio
```

### Daily Brief triggers:
```
1. detect_morning_trigger() / detect_pause_return()
   ↓
2. (M15) Check calendar availability
   ↓
3. Fetch mail, tasks, weather (M16: parallel!)
   ↓
4. Generate brief text (generate_morning_brief)
   ↓
5. TTS + speak
```

### Email/Tasks polling:
```
1. GET /api/get_mails_unread
   ↓
2. (M14) Check ETag cache
   ↓
3. If unchanged: return cached
   ↓
4. If changed: call AppleScript, update cache
   ↓
5. Return to frontend
```

---

## 💡 Key Concepts & Patterns

### M13: Graceful Degradation
```python
def get_data_with_fallback(service_name):
    try:
        fresh = fetch_from_service()
        if fresh:
            cache['data'] = fresh
            cache['last_good'] = fresh
            return fresh
    except:
        pass
    # Fallback to stale data instead of error
    return cache.get('last_good', [])
```
**Use:** Mail, Tasks, Weather endpoints fail gracefully

### M14: ETag Caching
```python
new_etag = calculate_etag(data)  # SHA256 hash
if new_etag == cache.get('etag'):
    return cache['data']  # Skip expensive fetch
cache['etag'] = new_etag
cache['data'] = data
```
**Use:** Reduces AppleScript calls by 90%

### M15: Adaptive Thresholds
```python
stats = analyze_pause_patterns()  # From archive
thresholds = calculate_adaptive_thresholds(stats)
# Tomorrow uses learned thresholds from today!
```
**Use:** Daily Brief learns from user history

### M16: Parallel Fetches
```python
results = await asyncio.gather(
    executor(get_mail),
    executor(get_tasks),
    executor(get_weather),
    return_exceptions=True
)
```
**Use:** 36% faster API responses

---

## 🎯 Adding Features

### Template: New Action Command

```python
# In server.py, add to execute_action():
elif action.type == "MY_NEW_ACTION":
    result = await _do_my_action(action.param)
    await _speak(ws, session_id, f"Done! {result}")

async def _do_my_action(param: str) -> str:
    """Execute my new feature."""
    log.info(f"Executing my_action with {param}")
    # Implementation here
    return "success"
```

### Template: New API Endpoint

```python
# In services/jarvis-ha/main.py or server.py:
@app.get("/api/my_feature")
async def my_feature():
    """Get data for my feature."""
    try:
        data = fetch_my_data()
        return {"status": "ok", "data": data}
    except Exception as e:
        log.error(f"my_feature error: {e}")
        return {"status": "error", "reason": str(e)}
```

### Testing Locally
```bash
# Test new endpoint
curl http://localhost:8340/api/my_feature

# Test in WebSocket (browser console):
ws.send(JSON.stringify({action: "MY_NEW_ACTION", param: "test"}))
```

---

## 📊 Performance Profiling (M16)

### Measure Startup Time
```bash
time python3.11 server.py
# Should be <10 seconds
```

### Profile Code
```python
import cProfile
cProfile.run('main()', 'profile_stats')

# Then analyze:
python3.11 -m pstats profile_stats
```

### Memory Profiling
```bash
# Using psutil (already imported)
import psutil
proc = psutil.Process()
print(f"Memory: {proc.memory_info().rss / 1024 / 1024:.1f} MB")
```

### Response Time Testing
```bash
# Measure endpoint latency
time curl -w "@curl_format.txt" http://localhost:8340/api/get_mails_unread
```

---

## 🧪 Testing Strategy

### Unit Tests
```bash
# Run existing tests
python3.11 -m pytest tests/

# Add new test
# tests/test_my_feature.py:
def test_my_feature():
    result = my_function("input")
    assert result == "expected"
```

### Integration Tests
```bash
# Test API endpoints
curl http://localhost:8340/api/health | jq .

# Test WebSocket
# (Manual in browser console)
ws.send(JSON.stringify({type: "test_action"}))
```

### Performance Tests
```bash
# Run 100 requests concurrently
ab -n 100 -c 10 http://localhost:8340/api/get_mails_unread

# Monitor memory growth over time
watch -n 1 'ps aux | grep python3.11 | grep server'
```

---

## 🔄 Release Process

### Versioning (Semantic)
```
MAJOR.MINOR.PATCH
1.    2.     0

- MAJOR: Breaking changes (new architecture, API incompatible)
- MINOR: New features (M14, M15, M16)
- PATCH: Bug fixes, performance tweaks
```

### Steps to Release
```bash
# 1. Update version.json
echo '{"version": "1.2.0"}' > version.json

# 2. Update changelog
# Edit CHANGELOG.md with new features

# 3. Commit
git add -A
git commit -m "chore: Release v1.2.0"

# 4. Tag
git tag -a v1.2.0 -m "Version 1.2.0 - M14/M15/M16"

# 5. Push
git push origin main
git push origin v1.2.0

# 6. Create GitHub Release
gh release create v1.2.0 -t "v1.2.0" -n "Release notes here"
```

---

## 📋 Commit Message Format

```
<type>: <subject>

<body>

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Types
- `feat:` New feature (M14, M15, etc)
- `fix:` Bug fix
- `perf:` Performance improvement
- `refactor:` Code restructuring
- `docs:` Documentation
- `chore:` Build, release, deps

### Example
```
feat: M14 — Email/Tasks Polling Optimization

Implement ETag-based change detection to reduce AppleScript
calls by 90%. Only fetches when data actually changes.

- Add _calculate_etag() helper function
- Modify get_mail_sync() with ETag comparison
- Expected impact: -36% response time

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 🐛 Common Issues for Developers

| Issue | Solution |
|-------|----------|
| Import errors | `pip install -r requirements.txt` |
| Module not found | Check `sys.path` in server.py |
| Async errors | Use `asyncio.gather()` for parallel tasks |
| WebSocket drops | Exponential backoff in index.html (done) |
| Memory leaks | Profile with `tracemalloc` |
| Slow startup | Check M16 profiling tips |

---

## 📚 Resources

- **Main README:** `/Jarvis-2.0/README.md`
- **User Guide:** `JARVIS_USER_GUIDE.md`
- **Troubleshooting:** `JARVIS_TROUBLESHOOTING.md`
- **Architecture Docs:** `CLAUDE.md`
- **Git Repo:** https://github.com/Black-Shadowcat/Jarvis-2.0

---

## 🎓 Learning Path

1. **Read this guide** (you're here!)
2. **Run locally** and poke around
3. **Read server.py** (understand main flow)
4. **Read one feature** (M14, M15, M16)
5. **Add a small feature** (follow template above)
6. **Open PR** → Review → Merge!

---

**Version 1.2.0 — Happy Coding! 🚀**

Questions? Open an issue or submit a PR!
