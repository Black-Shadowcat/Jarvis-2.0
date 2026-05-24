#!/bin/bash
# ── Jarvis 2.0 — Start (v0.4.0 mit Microservices) ──────────────────────────
# Sequential startup: Core (8340) → warte → Audio+HA parallel → warte → Speech

echo "════════════════════════════════════════"
echo "  Starte Jarvis 2.0 v0.4.0"
echo "  3 Microservices + 2 Begleiter"
echo "════════════════════════════════════════"

START_TIME=$(date +%s)

# Define LaunchAgents
SERVER_PLIST=~/Library/LaunchAgents/com.jarvis.v2.server.plist
AUDIO_PLIST=~/Library/LaunchAgents/com.jarvis.v2.audio.plist
HA_PLIST=~/Library/LaunchAgents/com.jarvis.v2.ha.plist
SPEECH_PLIST=~/Library/LaunchAgents/com.jarvis.v2.speech.plist

_start_agent() {
    local name=$1
    local plist=$2
    local port=$3
    local uid=$(id -u)
    echo "→ Starte $name (Port $port)..."
    # enable + load -w: loescht Disabled=true Flag (gesetzt durch Autostart-Deaktivierung)
    launchctl enable gui/$uid/$name 2>/dev/null
    launchctl load -w "$plist" 2>/dev/null
    if launchctl list "$name" &>/dev/null; then
        launchctl start "$name" 2>/dev/null
    else
        launchctl bootstrap gui/$uid "$plist" 2>/dev/null
    fi
}

_wait_health() {
    local port=$1
    local name=$2
    local max_wait=15
    echo "  Warte auf $name Health (/health auf :$port)..."
    for i in $(seq 1 $max_wait); do
        if curl -s "http://localhost:$port/health" &>/dev/null; then
            echo "  $name ✓"
            return 0
        fi
        sleep 1
    done
    echo "  ⚠ $name antwortet nicht nach ${max_wait}s"
    return 1
}

# Phase 1: jarvis-core starten (sequenziell)
_start_agent "com.jarvis.v2.server" "$SERVER_PLIST" "8340"
_wait_health 8340 "jarvis-core"

# Phase 2: jarvis-audio + jarvis-ha parallel starten
echo "→ Starte jarvis-audio + jarvis-ha (parallel)..."
_start_agent "com.jarvis.v2.audio" "$AUDIO_PLIST" "8341" &
_start_agent "com.jarvis.v2.ha" "$HA_PLIST" "8342" &
wait

_wait_health 8341 "jarvis-audio" &
_wait_health 8342 "jarvis-ha" &
wait

# Phase 3: Spracheingabe + sonstige
echo "→ Starte Spracheingabe..."
_start_agent "com.jarvis.v2.speech" "$SPEECH_PLIST" "STT"
sleep 2

# Phase 4: Supervisor (zuletzt — bewacht alle anderen Services)
echo "→ Starte Supervisor..."
SUPERVISOR_PLIST=~/Library/LaunchAgents/com.jarvis.v2.supervisor.plist
_start_agent "com.jarvis.v2.supervisor" "$SUPERVISOR_PLIST" "SVC"
sleep 1

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

# Tauri App öffnen
echo "→ Öffne Jarvis.app..."
if [[ -d "/Applications/Jarvis.app" ]]; then
    open "/Applications/Jarvis.app"
else
    open "http://localhost:8340"
fi

echo ""
echo "✓ Jarvis 2.0 läuft auf http://localhost:8340 (${ELAPSED}s Startup)"
echo "  F19 halten zum Sprechen | Cmd+Shift+J = Neu starten"
echo "  Logs: ~/Library/Logs/Jarvis\ 2.0/"
echo "════════════════════════════════════════"
