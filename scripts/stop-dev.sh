#!/bin/bash
# ── Jarvis 2.0 — Stop ────────────────────────────────────────────────────
echo "════════════════════════════════════════"
echo "  Stoppe Jarvis 2.0"
echo "════════════════════════════════════════"

# PHASE 1: Supervisor ZUERST stoppen (verhindert KeepAlive-Restart-Loops)
echo "→ Phase 1: Entlade Supervisor LaunchAgent (ZUERST!)..."
launchctl unload ~/Library/LaunchAgents/com.jarvis.v2.supervisor.plist 2>/dev/null && echo "  ✓ Supervisor gestoppt" || echo "  (war nicht geladen)"
sleep 1

# PHASE 2: Core Services stoppen
echo "→ Phase 2: Entlade Core Services..."
launchctl unload ~/Library/LaunchAgents/com.jarvis.v2.server.plist 2>/dev/null && echo "  ✓ Server gestoppt" || echo "  (war nicht geladen)"
launchctl unload ~/Library/LaunchAgents/com.jarvis.v2.speech.plist 2>/dev/null && echo "  ✓ Speech-Input gestoppt" || echo "  (war nicht geladen)"
launchctl unload ~/Library/LaunchAgents/com.jarvis.v2.wake.plist 2>/dev/null && echo "  ✓ Wake-Monitor gestoppt" || echo "  (war nicht geladen)"

# PHASE 3: Microservices stoppen
echo "→ Phase 3: Entlade Microservices..."
launchctl unload ~/Library/LaunchAgents/com.jarvis.v2.audio.plist 2>/dev/null && echo "  ✓ jarvis-audio (8341) gestoppt" || echo "  (war nicht geladen)"
launchctl unload ~/Library/LaunchAgents/com.jarvis.v2.ha.plist 2>/dev/null && echo "  ✓ jarvis-ha (8342) gestoppt" || echo "  (war nicht geladen)"

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
