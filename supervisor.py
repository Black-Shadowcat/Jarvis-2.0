#!/opt/homebrew/bin/python3.11
"""
Health supervisor for Jarvis-V3 services.

Monitors and auto-recovers: server.py, speech_input.py, wake-monitor.py, Chrome.
Uses launchctl kickstart for reliable process restart (not launchctl stop).
Includes failure_counts (3 consecutive failures before restart) to prevent flapping.
All checks have hard timeouts — supervisor never blocks.
"""

import os
import sys
import time
import json
import signal
import logging
import subprocess
import atexit
import asyncio
import urllib.request
import urllib.error
from typing import Optional

try:
    import websockets
except ImportError:
    print("[supervisor] ERROR: websockets not installed. Run: pip install websockets", flush=True)
    sys.exit(1)

# ============================================================================
# Configuration
# ============================================================================

SERVER_BASE = "http://localhost:8340"
WS_URL = "ws://localhost:8340/ws"
CHECK_INTERVAL = 30  # seconds between checks
RESTART_COOLDOWN = 120  # minimum seconds between restarts per service
STATUS_INTERVAL = 300  # seconds between "All healthy" logs (10 iterations)
FAILURE_THRESHOLD = 3  # consecutive failures before restart
HTTP_TIMEOUT = 5
WS_TIMEOUT = 5
SUBPROC_TIMEOUT = 3
PID_FILE = "/tmp/jarvis-supervisor.pid"

# ============================================================================
# Module State
# ============================================================================

_last_restart: dict[str, float] = {}
_failure_counts: dict[str, int] = {}
_check_iterations = 0
_uid = os.getuid()
_force_check_flag = False

# ============================================================================
# Logging
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
    force=True,
    stream=sys.stdout,
)
log = logging.getLogger("supervisor")

# Make stdout unbuffered
sys.stdout = open(sys.stdout.fileno(), 'w', buffering=1)


# ============================================================================
# Utilities
# ============================================================================


def _load_config() -> dict:
    """Load config.json, return dict with defaults."""
    config_path = os.path.expanduser("~/jarvis-v3/config.json")
    if not os.path.exists(config_path):
        log.warning(f"config.json not found at {config_path}, using empty config")
        return {}
    try:
        with open(config_path) as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Failed to load config: {e}")
        return {}


def _pid_lock() -> None:
    """
    PID lock pattern: prevent duplicate supervisor instances.
    Based on scripts/wake-monitor.py lines 13–23.
    """
    if os.path.exists(PID_FILE):
        try:
            old_pid = int(open(PID_FILE).read().strip())
            os.kill(old_pid, 0)  # Check if process exists
            log.error(
                f"[supervisor] Bereits aktiv (PID {old_pid}) — beende Duplikat."
            )
            sys.exit(0)
        except (OSError, ValueError):
            log.debug("[supervisor] stale pid lock detected, taking over")

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    atexit.register(
        lambda: os.path.exists(PID_FILE) and os.remove(PID_FILE)
    )


def _http_get(url: str, timeout: float = HTTP_TIMEOUT) -> bool:
    """
    GET request with timeout. Returns True if HTTP 2xx, False otherwise.
    """
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError:
        return False
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


async def _ws_check_async() -> bool:
    """
    WebSocket handshake check with timeout.
    Returns True if connection succeeds, False otherwise.
    """
    try:
        ws = await asyncio.wait_for(
            websockets.connect(WS_URL), timeout=WS_TIMEOUT
        )
        await ws.close()
        return True
    except asyncio.TimeoutError:
        return False
    except Exception:
        return False


def _ws_check() -> bool:
    """Wrapper for async WS check."""
    try:
        return asyncio.run(_ws_check_async())
    except Exception:
        return False


def _pgrep(pattern: str) -> bool:
    """
    Check if process matching pattern is running.
    Uses pgrep -f with timeout.
    """
    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            timeout=SUBPROC_TIMEOUT,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log.warning(f"pgrep timeout for pattern: {pattern}")
        return False
    except Exception as e:
        log.error(f"pgrep error for {pattern}: {e}")
        return False


def _kickstart(label: str) -> bool:
    """
    Restart service via launchctl kickstart -k.
    More reliable than stop (guarantees Kill + respawn by launchd).
    Returns True if successful, False otherwise.
    """
    try:
        cmd = ["launchctl", "kickstart", "-k", f"gui/{_uid}/{label}"]
        result = subprocess.run(cmd, capture_output=True, timeout=5)
        success = result.returncode == 0
        if success:
            log.info(f"✓ kickstart {label}")
        else:
            log.error(f"✗ kickstart {label} failed: {result.stderr.decode()}")
        return success
    except Exception as e:
        log.error(f"kickstart exception for {label}: {e}")
        return False


def _can_restart(name: str) -> bool:
    """Check if enough time has passed since last restart."""
    last = _last_restart.get(name, 0)
    elapsed = time.time() - last
    can = elapsed > RESTART_COOLDOWN
    if not can:
        remaining = RESTART_COOLDOWN - elapsed
        log.debug(f"  restart suppressed for {name} (cooldown {remaining:.0f}s remaining)")
    return can


def _mark_restarted(name: str) -> None:
    """Record restart time and reset failure count."""
    _last_restart[name] = time.time()
    _failure_counts[name] = 0


def _record_failure(name: str) -> int:
    """Record failure and return current count."""
    _failure_counts[name] = _failure_counts.get(name, 0) + 1
    return _failure_counts[name]


def _record_success(name: str) -> None:
    """Reset failure count on success."""
    _failure_counts[name] = 0


# ============================================================================
# Health Checks
# ============================================================================


def check_server_http() -> bool:
    """Check if server.py HTTP endpoint (/api/version) is reachable."""
    url = f"{SERVER_BASE}/api/version"
    ok = _http_get(url, timeout=HTTP_TIMEOUT)
    if not ok:
        log.warning(f"✗ server HTTP unreachable: {url}")
    return ok


def check_server_ws() -> bool:
    """
    Check if server.py WebSocket is responding.
    Separate from HTTP: catches Event-Loop deadlocks.
    """
    ok = _ws_check()
    if not ok:
        log.warning(f"✗ server WebSocket unreachable: {WS_URL}")
    return ok


def check_speech_input() -> bool:
    """Check if speech_input.py process is running."""
    ok = _pgrep("speech_input.py")
    if not ok:
        log.warning("✗ speech_input.py not running")
    return ok


def check_wake_monitor() -> bool:
    """Check if wake-monitor.py process is running."""
    ok = _pgrep("wake-monitor.py")
    if not ok:
        log.warning("✗ wake-monitor.py not running")
    return ok


def check_chrome() -> bool:
    """
    Check if Chrome Kiosk is running.
    Only logs result — restart logic is in launch-session.sh, not here.
    """
    ok = _pgrep("jarvis-v2-chrome-profile")
    if not ok:
        log.info("ℹ Chrome not running (expected during sleep or manual close)")
    return ok


def check_homeassistant(config: dict) -> Optional[bool]:
    """
    Check if HomeAssistant API is reachable.
    Only logs result — external service, no restart.
    Returns None if HA is disabled.
    """
    if not config.get("ha_enabled", False):
        return None

    ha_url = config.get("ha_url", "")
    ha_token = config.get("ha_token", "")

    if not ha_url or not ha_token:
        log.debug("HA not configured (no URL or token)")
        return None

    try:
        req = urllib.request.Request(
            f"{ha_url}/api/",
            headers={"Authorization": f"Bearer {ha_token}"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            ok = 200 <= resp.status < 300
            if not ok:
                log.warning(f"HA returned {resp.status}")
            return ok
    except Exception as e:
        log.warning(f"HA unreachable: {e}")
        return False


# ============================================================================
# Main Check Loop
# ============================================================================


def run_checks(config: dict) -> None:
    """Execute one round of health checks with recovery logic."""
    global _check_iterations
    _check_iterations += 1
    log.debug(f"[run_checks] Starting check iteration {_check_iterations}")

    all_ok = True

    # ========================================================================
    # Server HTTP Check
    # ========================================================================
    http_ok = check_server_http()
    if http_ok:
        log.info("✓ server HTTP OK")
    if not http_ok:
        n = _record_failure("server_http")
        all_ok = False
        if n >= FAILURE_THRESHOLD and _can_restart("server"):
            log.warning(
                f"server_http: {n}/{FAILURE_THRESHOLD} failures → kickstart server"
            )
            _kickstart("com.jarvis.v2.server")
            _mark_restarted("server")
        else:
            log.warning(f"server_http FAIL ({n}/{FAILURE_THRESHOLD})")
    else:
        _record_success("server_http")

        # ====================================================================
        # Server WebSocket Check (only if HTTP OK)
        # ====================================================================
        ws_ok = check_server_ws()
        if not ws_ok:
            n = _record_failure("server_ws")
            all_ok = False
            if n >= FAILURE_THRESHOLD and _can_restart("server"):
                log.warning(
                    f"server_ws: {n}/{FAILURE_THRESHOLD} failures → kickstart server (WS stuck)"
                )
                _kickstart("com.jarvis.v2.server")
                _mark_restarted("server")
            else:
                log.warning(f"server_ws FAIL ({n}/{FAILURE_THRESHOLD})")
        else:
            _record_success("server_ws")

    # ========================================================================
    # speech_input.py Check
    # ========================================================================
    if check_speech_input():
        log.info("✓ speech_input running")
    if not check_speech_input():
        n = _record_failure("speech")
        all_ok = False
        if n >= FAILURE_THRESHOLD and _can_restart("speech"):
            log.warning(f"speech: {n}/{FAILURE_THRESHOLD} failures → kickstart")
            _kickstart("com.jarvis.v2.speech")
            _mark_restarted("speech")
        else:
            log.warning(f"speech FAIL ({n}/{FAILURE_THRESHOLD})")
    else:
        _record_success("speech")

    # ========================================================================
    # wake-monitor.py Check
    # ========================================================================
    if check_wake_monitor():
        log.info("✓ wake-monitor running")
    if not check_wake_monitor():
        n = _record_failure("wake")
        all_ok = False
        if n >= FAILURE_THRESHOLD and _can_restart("wake"):
            log.warning(f"wake: {n}/{FAILURE_THRESHOLD} failures → kickstart")
            _kickstart("com.jarvis.v2.wake")
            _mark_restarted("wake")
        else:
            log.warning(f"wake FAIL ({n}/{FAILURE_THRESHOLD})")
    else:
        _record_success("wake")

    # ========================================================================
    # Chrome Check (log only, no restart)
    # ========================================================================
    if check_chrome():
        log.info("ℹ Chrome running")

    # ========================================================================
    # HomeAssistant Check (log only, no restart)
    # ========================================================================
    ha_status = check_homeassistant(config)
    if ha_status is None:
        log.debug("ℹ HomeAssistant disabled")
    elif ha_status:
        log.info("✓ HomeAssistant OK")

    # ========================================================================
    # Periodic "All Healthy" Log
    # ========================================================================
    if all_ok and (_check_iterations % (STATUS_INTERVAL // CHECK_INTERVAL) == 0):
        log.info("✓ All services healthy")


def main_loop() -> None:
    """Main supervisor loop."""
    global _force_check_flag

    def _handle_sigusr1(signum, frame):
        global _force_check_flag
        _force_check_flag = True

    signal.signal(signal.SIGUSR1, _handle_sigusr1)

    config = _load_config()
    log.info("supervisor started, check_interval=%ds", CHECK_INTERVAL)
    log.handlers[0].flush() if log.handlers else None

    try:
        # Run first check immediately (for smoke testing / debugging)
        run_checks(config)

        while True:
            if _force_check_flag:
                _force_check_flag = False
                log.info("🔔 Force-check triggered by SIGUSR1")
                run_checks(config)
            else:
                time.sleep(CHECK_INTERVAL)
                run_checks(config)
    except KeyboardInterrupt:
        log.info("supervisor stopped (KeyboardInterrupt)")
    except Exception as e:
        log.error(f"Unexpected error in main_loop: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    _pid_lock()
    main_loop()
