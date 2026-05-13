#!/bin/bash
# ── Jarvis Whisper — Stop ───────────────────────────────────────────────
echo "════════════════════════════════════════"
echo "  Stoppe jarvis-whisper"
echo "════════════════════════════════════════"

# LaunchAgents entladen (stoppt + verhindert KeepAlive-Neustart)
echo "→ Entlade Server LaunchAgent..."
launchctl unload ~/Library/LaunchAgents/com.jarvis.whisper.server.plist 2>/dev/null && echo "  gestoppt" || echo "  (war nicht geladen)"

echo "→ Entlade Spracheingabe LaunchAgent..."
launchctl unload ~/Library/LaunchAgents/com.jarvis.whisper.speech.plist 2>/dev/null && echo "  gestoppt" || echo "  (war nicht geladen)"

# Sicherheitshalber Prozesse beenden falls noch aktiv
pkill -f "server.py 8341" 2>/dev/null
pkill -f "speech_input.py" 2>/dev/null

echo ""
echo "✓ jarvis-whisper gestoppt"
echo "  Für Autostart beim nächsten Login bleiben die Plists registriert."
echo "  start-dev.sh lädt sie bei Bedarf erneut."
echo "════════════════════════════════════════"
