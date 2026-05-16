#!/bin/bash
# ── Jarvis 2.0 — Stop ────────────────────────────────────────────────────
echo "════════════════════════════════════════"
echo "  Stoppe Jarvis 2.0"
echo "════════════════════════════════════════"

_stop_agent() {
    local name=$1
    local plist=$2
    local uid=$(id -u)
    # Use modern launchctl bootout (macOS Ventura+), fallback to unload
    launchctl bootout gui/$uid "$plist" 2>/dev/null || launchctl unload "$plist" 2>/dev/null
    [ $? -eq 0 ] && echo "  ✓ $name gestoppt" || echo "  (war nicht geladen)"
}

# PHASE 1: Supervisor ZUERST stoppen (verhindert KeepAlive-Restart-Loops)
echo "→ Phase 1: Entlade Supervisor LaunchAgent (ZUERST!)..."
_stop_agent "Supervisor" ~/Library/LaunchAgents/com.jarvis.v2.supervisor.plist
sleep 1

# PHASE 2: Core Services stoppen
echo "→ Phase 2: Entlade Core Services..."
_stop_agent "Server" ~/Library/LaunchAgents/com.jarvis.v2.server.plist
_stop_agent "Speech-Input" ~/Library/LaunchAgents/com.jarvis.v2.speech.plist
_stop_agent "Wake-Monitor" ~/Library/LaunchAgents/com.jarvis.v2.wake.plist

# PHASE 3: Microservices stoppen
echo "→ Phase 3: Entlade Microservices..."
_stop_agent "jarvis-audio (8341)" ~/Library/LaunchAgents/com.jarvis.v2.audio.plist
_stop_agent "jarvis-ha (8342)" ~/Library/LaunchAgents/com.jarvis.v2.ha.plist

# PHASE 4: Backup-Kill falls Prozesse noch aktiv sind
echo "→ Phase 4: Force-Kill aller Prozesse (Sicherheit)..."
pkill -f "supervisor.py" 2>/dev/null && echo "  ✓ supervisor.py gekilled" || true
pkill -f "server.py 8340" 2>/dev/null && echo "  ✓ server.py gekilled" || true
pkill -f "speech_input.py" 2>/dev/null && echo "  ✓ speech_input.py gekilled" || true
pkill -f "wake-monitor.py" 2>/dev/null && echo "  ✓ wake-monitor.py gekilled" || true
pkill -f "jarvis-audio" 2>/dev/null && echo "  ✓ jarvis-audio gekilled" || true
pkill -f "jarvis-ha" 2>/dev/null && echo "  ✓ jarvis-ha gekilled" || true

echo ""
echo "✓ Jarvis 2.0 vollständig gestoppt"
echo "  Für Autostart beim nächsten Login bleiben die Plists registriert."
echo "  start-dev.sh lädt sie bei Bedarf erneut."
echo "════════════════════════════════════════"
