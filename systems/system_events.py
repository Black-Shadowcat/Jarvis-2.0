"""System Events Logger — Phase 4 Observability"""
import json
import os
import time
from datetime import datetime

class SystemEvents:
    """Collect and manage system events (service status, health checks, etc.)."""

    MAX_EVENTS = 100  # Keep last 100 events (~24h)
    FILE_PATH = "data/system_events.json"

    _EMPTY_STATE = {
        "events": []
    }

    @classmethod
    def log_event(cls, level, message, event_type="system"):
        """Log a system event atomically."""
        try:
            state = cls._load_state()
            event = {
                "ts": time.time(),
                "level": level,
                "message": message,
                "type": event_type
            }
            state["events"].append(event)
            state["events"] = state["events"][-cls.MAX_EVENTS:]
            cls._save_state(state)
        except Exception as e:
            # Fail-silent + debug-log
            import logging
            logging.debug(f"[system-events] log_event failed: {e}")

    @classmethod
    def get_events(cls, limit=10):
        """Get last N events."""
        try:
            state = cls._load_state()
            events = state.get("events", [])
            return events[-limit:]
        except Exception as e:
            import logging
            logging.debug(f"[system-events] get_events failed: {e}")
            return []

    @classmethod
    def _load_state(cls):
        """Load current state from file."""
        if not os.path.exists(cls.FILE_PATH):
            return cls._EMPTY_STATE.copy()
        try:
            with open(cls.FILE_PATH, "r") as f:
                return json.load(f)
        except:
            return cls._EMPTY_STATE.copy()

    @classmethod
    def _save_state(cls, state):
        """Save state atomically (temp + rename)."""
        os.makedirs("data", exist_ok=True)
        temp_path = cls.FILE_PATH + ".tmp"
        try:
            with open(temp_path, "w") as f:
                json.dump(state, f)
            os.replace(temp_path, cls.FILE_PATH)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
