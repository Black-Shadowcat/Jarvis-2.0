#!/bin/bash
# ── Jarvis 2.0 — Stop ────────────────────────────────────────────────────
echo "════════════════════════════════════════"
echo "  Stoppe Jarvis 2.0"
echo "════════════════════════════════════════"

# LaunchAgents entladen (stoppt + verhindert KeepAlive-Neustart)
echo "→ Entlade Server LaunchAgent..."
launchctl unload ~/Library/LaunchAgents/com.jarvis.v2.server.plist 2>/dev/null && echo "  gestoppt" || echo "  (war nicht geladen)"

echo "→ Entlade Spracheingabe LaunchAgent..."
launchctl unload ~/Library/LaunchAgents/com.jarvis.v2.speech.plist 2>/dev/null && echo "  gestoppt" || echo "  (war nicht geladen)"

# Sicherheitshalber Prozesse beenden falls noch aktiv
pkill -f "server.py 8340" 2>/dev/null
pkill -f "speech_input.py" 2>/dev/null

echo ""
echo "✓ Jarvis 2.0 gestoppt"
echo "  Für Autostart beim nächsten Login bleiben die Plists registriert."
echo "  start-dev.sh lädt sie bei Bedarf erneut."
echo "════════════════════════════════════════"
