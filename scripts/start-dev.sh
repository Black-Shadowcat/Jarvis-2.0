#!/bin/bash
# ── Jarvis 2.0 — Start ───────────────────────────────────────────────────
echo "════════════════════════════════════════"
echo "  Starte Jarvis 2.0 (Port 8340)"
echo "════════════════════════════════════════"

SERVER_PLIST=~/Library/LaunchAgents/com.jarvis.v2.server.plist
SPEECH_PLIST=~/Library/LaunchAgents/com.jarvis.v2.speech.plist

# Server starten (laden falls nötig, sonst starten)
echo "→ Server LaunchAgent..."
if launchctl list com.jarvis.v2.server &>/dev/null; then
    launchctl start com.jarvis.v2.server
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
if launchctl list com.jarvis.v2.speech &>/dev/null; then
    launchctl start com.jarvis.v2.speech
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
echo "✓ Jarvis 2.0 läuft auf http://localhost:8340"
echo "  F19 halten zum Sprechen"
echo "  Logs: ~/Library/Logs/jarvis-v2/"
echo "════════════════════════════════════════"
