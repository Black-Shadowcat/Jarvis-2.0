#!/bin/bash
# ── Jarvis Whisper — Start ──────────────────────────────────────────────
echo "════════════════════════════════════════"
echo "  Starte jarvis-whisper (Port 8340)"
echo "════════════════════════════════════════"

SERVER_PLIST=~/Library/LaunchAgents/com.jarvis.whisper.server.plist
SPEECH_PLIST=~/Library/LaunchAgents/com.jarvis.whisper.speech.plist

# Server starten (laden falls nötig, sonst starten)
echo "→ Server LaunchAgent..."
if launchctl list com.jarvis.whisper.server &>/dev/null; then
    launchctl start com.jarvis.whisper.server
    echo "  gestartet"
else
    launchctl load "$SERVER_PLIST"
    echo "  geladen + gestartet"
fi

# Warten bis Port offen
echo "→ Warte auf Server..."
for i in $(seq 1 15); do
    lsof -i :8340 -sTCP:LISTEN &>/dev/null && break
    sleep 1
done
lsof -i :8340 -sTCP:LISTEN &>/dev/null && echo "  Port 8340 offen ✓" || echo "  Warnung: Server antwortet nicht"

# Spracheingabe starten
echo "→ Spracheingabe LaunchAgent..."
if launchctl list com.jarvis.whisper.speech &>/dev/null; then
    launchctl start com.jarvis.whisper.speech
    echo "  gestartet"
else
    launchctl load "$SPEECH_PLIST"
    echo "  geladen + gestartet"
fi

sleep 1

# Browser öffnen
echo "→ Öffne Dashboard..."
open "http://localhost:8340"

echo ""
echo "✓ jarvis-whisper läuft auf http://localhost:8340"
echo "  F19 halten zum Sprechen"
echo "  Logs: ~/Library/Logs/jarvis-whisper/"
echo "════════════════════════════════════════"
