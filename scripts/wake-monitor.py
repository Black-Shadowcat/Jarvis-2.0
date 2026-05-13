#!/opt/homebrew/bin/python3.11
"""Monitors macOS wake-from-sleep events and notifies the Jarvis server."""
import subprocess
import urllib.request
import time
import sys
import os
import atexit
import threading

JARVIS_WAKE_URL = "http://localhost:8341/api/wake"
_LOCK = "/tmp/jarvis-wake-monitor.pid"

if os.path.exists(_LOCK):
    try:
        old = int(open(_LOCK).read())
        os.kill(old, 0)
        print(f"[wake-monitor] Bereits aktiv (PID {old}) — beende Duplikat.", flush=True)
        sys.exit(0)
    except (OSError, ValueError):
        print("[wake-monitor] stale pid lock detected, taking over", flush=True)
open(_LOCK, "w").write(str(os.getpid()))
atexit.register(lambda: os.path.exists(_LOCK) and os.remove(_LOCK))


def is_screen_locked() -> bool:
    """Returns True if the screen is currently locked."""
    try:
        r = subprocess.run(
            ["ioreg", "-n", "Root", "-d1"],
            capture_output=True, text=True, timeout=5,
        )
        return '"IOConsoleLocked" = Yes' in r.stdout
    except Exception:
        return False


def wait_for_unlock(timeout: int = 120) -> bool:
    """Blocks until screen is unlocked. Returns False if timeout exceeded."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not is_screen_locked():
            return True
        time.sleep(2)
    return False


def notify_jarvis():
    unlocked = wait_for_unlock()
    if not unlocked:
        print("[wake-monitor] Timeout — Screen blieb gesperrt, kein Brief", flush=True)
        return

    # Buffer after unlock: Chrome needs ~10s to reconnect WebSocket after sleep
    time.sleep(10)

    for attempt in range(6):
        try:
            req = urllib.request.Request(JARVIS_WAKE_URL, method="POST")
            req.add_header("Content-Type", "application/json")
            urllib.request.urlopen(req, data=b"{}", timeout=5)
            print(f"[wake-monitor] Jarvis benachrichtigt", flush=True)
            return
        except Exception as e:
            print(f"[wake-monitor] Versuch {attempt + 1}: {e}", flush=True)
            time.sleep(5)


def get_user_idle_seconds() -> float | None:
    """Returns seconds since last user input event via HIDIdleTime, or None on error."""
    try:
        r = subprocess.run(
            ["ioreg", "-c", "IOHIDSystem"],
            capture_output=True, text=True, timeout=5,
        )
        for line in r.stdout.splitlines():
            if "HIDIdleTime" in line:
                # Format: "HIDIdleTime" = 12345678901
                ns = int(line.split("=")[-1].strip())
                return ns / 1_000_000_000
        return None
    except Exception:
        return None


COOLDOWN = 120  # seconds — shared between log-stream thread and display-wake thread
_wake_lock = threading.Lock()
_last_wake = 0.0


def _try_trigger(label: str) -> None:
    """Thread-safe cooldown check + notify. Fires if cooldown has passed."""
    global _last_wake
    now = time.time()
    with _wake_lock:
        if now - _last_wake < COOLDOWN:
            return
        _last_wake = now
    print(f"[wake-monitor] Wake erkannt ({label})", flush=True)
    notify_jarvis()
    with _wake_lock:
        _last_wake = time.time()  # restart cooldown after blocking call returns


# Threshold: if idle was above this and drops below 30s, the display was woken by user
_DISPLAY_SLEEP_THRESHOLD = 600  # 10 min — avoids false triggers from brief pauses


def display_wake_watcher() -> None:
    """
    Polls HIDIdleTime every 10s. Detects display-only wakes (no kernel log event):
    when idle time transitions from > threshold to < 30s, the user woke the display.
    """
    was_idle = False
    print("[wake-monitor] Display-Wake-Watcher gestartet (HIDIdleTime-Polling)", flush=True)
    while True:
        idle = get_user_idle_seconds()
        if idle is not None:
            if was_idle and idle < 30:
                _try_trigger("HIDIdleTime display-wake")
                was_idle = False
            elif idle > _DISPLAY_SLEEP_THRESHOLD:
                was_idle = True
            elif idle > 30:
                # Still idle but below threshold — don't set was_idle, don't clear it either
                pass
            else:
                # Active — reset flag
                was_idle = False
        time.sleep(10)


# Start display-wake thread as daemon so it exits with the main process
_t = threading.Thread(target=display_wake_watcher, daemon=True)
_t.start()

proc = subprocess.Popen(
    ["log", "stream", "--predicate", 'eventMessage contains "Wake reason"', "--style", "compact"],
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
)

print("[wake-monitor] Überwache System-Wake-Events...", flush=True)

for line in proc.stdout:
    if ("Wake reason" in line
            and "Filtering the log data using" not in line
            and "wifibt" not in line
            and "E_RX_IP_PACKET" not in line
            and "updateWoWReason" not in line):
        _try_trigger(f"log stream: {line.strip()}")
