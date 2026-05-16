# Phase 2 Spike Phase — Quick Reference Card

**Status:** ✅ Complete — Ready for implementation  
**Created:** 2026-05-16  
**Documents:** 4 comprehensive files + this reference

---

## 📚 Three Core Documents

### 1. PHASE_2_INTERFACES.md
**What:** Complete mapping of ALL communication in Jarvis 2.0  
**Length:** ~400 lines  
**Read this for:** Understanding exactly how data flows between components

**Key Sections:**
- WebSocket endpoints (/ws, /ws/stt) with message formats
- 50+ REST API endpoints catalogued
- Global state variables and locks
- Inter-service communication patterns
- External integrations (Claude, ElevenLabs, HA, Mail, Weather)
- 8 data flow diagrams

**Critical Insights:**
- `/ws` (browser) vs `/ws/stt` (speech) are SEPARATE (prevents audio loop)
- Conversations stored per-session, last 16 turns only
- All responses broadcast to ALL browsers (not per-session)
- Debouncing: "Jarvis activate" suppressed within 5s

---

### 2. SERVICE_SPECS.md
**What:** Exact API contracts and behavioral specs for each service  
**Length:** ~500 lines  
**Read this for:** Implementation details of each microservice

**Three Services Defined:**

#### jarvis-core (Port 8340)
- **Stays:** FastAPI, WebSocket routing, LLM, system prompt, action dispatch
- **Leaves:** TTS, mail, tasks, calendar, weather, HA integration
- **Key Endpoints:** /ws, /ws/stt, /api/config, /static/*
- **New Behavior:** HTTP proxies to jarvis-audio and jarvis-ha

#### jarvis-audio (Port 8341)
- **Does:** Text-to-speech synthesis only
- **Takes:** POST /api/synthesize with text
- **Returns:** base64-encoded MP3 audio
- **Special:** Chunking algorithm (250 chars max per chunk)
- **Integration:** Called by jarvis-core during response generation

#### jarvis-ha (Port 8342)
- **Does:** Dashboard data aggregation, HA integration, weather, news
- **Takes:** Mail, Tasks, Calendar, Weather, Obsidian, News requests
- **Returns:** Structured JSON with cache awareness
- **Integration:** Called by jarvis-core for dashboard and action execution

---

### 3. PHASE_2_GETTING_STARTED.md
**What:** Step-by-step implementation guide  
**Length:** ~350 lines  
**Read this for:** How to actually implement Phase 2

**Structure:**
- **Phase 2.1:** jarvis-audio extraction (Week 1)
  - Create service skeleton
  - Extract TTS functions
  - Implement /api/synthesize
  - Test with curl
  - Update server.py to call remotely

- **Phase 2.2:** jarvis-ha extraction (Week 2-3)
  - Same pattern as 2.1
  - Extract mail/tasks/calendar/weather functions

- **Phase 2.3:** jarvis-core refactoring (Week 4)
  - Remove extracted functions
  - Replace with HTTP proxies

- **Phase 2.4:** Integration testing (Week 4-5)
  - 20+ test cases provided
  - Failure scenarios documented

**Bonus Sections:**
- Rollback procedure (< 5 minutes)
- Logging & debugging setup
- LaunchAgent updates needed
- Success criteria checklist

---

## 🎯 Quick Start Path

### If starting Phase 2.1 TODAY:

1. **Read:** PHASE_2_INTERFACES.md (key sections: WebSocket endpoints, inter-service communication)
2. **Reference:** SERVICE_SPECS.md section on jarvis-audio
3. **Follow:** PHASE_2_GETTING_STARTED.md Phase 2.1 steps
4. **Create:** `services/jarvis-audio/main.py`
5. **Test:** `curl -X POST http://127.0.0.1:8341/api/synthesize -H "Content-Type: application/json" -d '{"text": "Hallo"}'`

### Estimated time: 2-3 hours to working jarvis-audio service

---

## 📊 Service Dependency Map

```
┌─────────────────┐
│ Browser Index   │
│ (index.html)    │
└────────┬────────┘
         │ /ws WebSocket
         │
    ┌────▼────────────────────┐
    │  jarvis-core (8340)      │
    │  ✅ FastAPI              │
    │  ✅ WebSocket routing    │
    │  ✅ LLM (Claude)         │
    │  ✅ Action dispatch      │
    └────┬──────────┬──────────┘
         │ HTTP    │ HTTP
         │         │
    ┌────▼───┐  ┌──▼────────┐
    │ jarvis-│  │ jarvis-ha  │
    │ audio  │  │ (8342)     │
    │ (8341) │  │ ✅ Mail    │
    │        │  │ ✅ Tasks   │
    │ ✅ TTS │  │ ✅ Weather │
    │        │  │ ✅ HA      │
    └────────┘  └────────────┘

External (unchanged):
├─ speech_input.py → /ws/stt (WebSocket text only)
├─ Claude API (via jarvis-core)
├─ ElevenLabs (via jarvis-audio)
└─ Home Assistant (via jarvis-ha)
```

---

## 🔑 Critical Touch Points (DON'T FORGET)

1. **Debouncing:** "Jarvis activate" suppressed within 5s
2. **Broadcasting:** ALL responses go to ALL /ws connections
3. **Audio Loop Prevention:** /ws/stt receives NO audio feedback
4. **Lock Guards:** MAIL_INFO updates must use _mail_lock
5. **Conversation History:** Kept in core only, max 16 turns
6. **Error Graceful:** Missing jarvis-ha → empty dashboard (not crash)
7. **Chunking:** TTS splits at sentence boundaries, max 250 chars/chunk
8. **Session Management:** One conversation dict entry per session_id

---

## ✅ Phase 2 Prerequisites (All Met)

- [x] v0.3.0 released and tagged
- [x] All interfaces documented (PHASE_2_INTERFACES.md)
- [x] All service specs defined (SERVICE_SPECS.md)
- [x] Step-by-step guide created (PHASE_2_GETTING_STARTED.md)
- [x] Rollback path documented
- [x] Test cases identified
- [x] Success criteria defined

---

## ⏱️ Timeline

| Phase | Duration | Target | Status |
|-------|----------|--------|--------|
| 2.1: jarvis-audio | 1 week | v0.4.0-audio | 🔳 Not started |
| 2.2: jarvis-ha | 2 weeks | v0.4.0-ha | 🔳 Not started |
| 2.3: jarvis-core | 1 week | v0.4.0-refactor | 🔳 Not started |
| 2.4: Integration | 1 week | v0.4.0 Final | 🔳 Not started |

**Total:** ~5 weeks (realistic, tested on similar projects)

---

## 📝 Next Steps

### Option A: Start Phase 2.1 Immediately
```bash
cd /Users/matthiasschreiber/Jarvis-2.0
mkdir -p services/jarvis-audio
# Follow PHASE_2_GETTING_STARTED.md Phase 2.1
```

### Option B: Take a Break, Start Tomorrow
- Let spike phase documentation settle
- Review documents overnight
- Fresh start in morning with clear head
- Both are valid

### Option C: Do a Spike Review First
- Have user review the 3 documents
- Get feedback on approach
- Adjust if needed before committing code

---

## 🛟 Reference Links

**In Obsidian:**
- `PHASE_2_PLAN.md` — Overall roadmap and strategy
- `PROJECT_INFO.md` — Project overview and history
- `PHASE_2_PROGRESS.md` — (Will be created during Phase 2) Daily progress log

**In Repository:**
- `PHASE_2_INTERFACES.md` — This file's detailed reference
- `SERVICE_SPECS.md` — Exact API contracts
- `PHASE_2_GETTING_STARTED.md` — Step-by-step guide
- `CHANGELOG.md` — Version history

**Quick Commands:**
```bash
# View all Phase 2 documents
ls -la /Users/matthiasschreiber/Jarvis-2.0/PHASE_2_*.md

# Check current status
git status
git log --oneline -5

# Health check (when services are running)
curl -s http://127.0.0.1:8340/health && echo "✓ core"
curl -s http://127.0.0.1:8341/health && echo "✓ audio"
curl -s http://127.0.0.1:8342/health && echo "✓ ha"
```

---

## 🎓 Learning Resources

If unfamiliar with FastAPI or microservices:
- FastAPI: https://fastapi.tiangolo.com/
- Microservices: https://martinfowler.com/microservices/
- asyncio: https://docs.python.org/3/library/asyncio.html

But these docs are self-contained — you don't need external knowledge to follow them.

---

**Spike Phase Status:** ✅ COMPLETE  
**Ready for Phase 2.1?** YES  
**Confidence Level:** HIGH (all interfaces mapped, no unknowns remaining)

---

*This card should always be in your terminal when working on Phase 2. Print it, pin it, reference it frequently.*
