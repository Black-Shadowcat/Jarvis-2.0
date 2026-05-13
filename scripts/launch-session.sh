#!/bin/zsh
# jarvis-whisper — Launch Session (macOS)
# Wartet auf macOS-Bereitschaft + Server, dann öffnet Chrome auf Port 8341.

echo "[boot] Warte auf macOS (Dock + Finder)..."
until pgrep -x "Dock" > /dev/null 2>&1 && pgrep -x "Finder" > /dev/null 2>&1; do
    sleep 3
done

BOOT_TIME=$(sysctl -n kern.boottime | awk '{print $4}' | tr -d ',')
UPTIME_SECS=$(( $(date +%s) - BOOT_TIME ))
if [[ $UPTIME_SECS -lt 120 ]]; then
    echo "[boot] Frischer Boot (${UPTIME_SECS}s) — 20s warten..."
    sleep 20
else
    echo "[boot] System läuft (${UPTIME_SECS}s) — 2s warten"
    sleep 2
fi

SERVER_URL="http://localhost:8341"
JARVIS_PROFILE="$HOME/.jarvis-whisper-chrome-profile"

echo "[session] Warte auf Server $SERVER_URL..."
for i in {1..30}; do
    curl -s -o /dev/null -w "%{http_code}" "$SERVER_URL" 2>/dev/null | grep -q "200" && break
    sleep 2
    if [[ $i -eq 30 ]]; then
        echo "[session] Server nicht erreichbar nach 60s — trotzdem Chrome öffnen"
    fi
done

JARVIS_DEFAULT="$JARVIS_PROFILE/Default"
JARVIS_PREF="$JARVIS_DEFAULT/Preferences"

rm -rf "$JARVIS_DEFAULT/Cache" \
       "$JARVIS_DEFAULT/Code Cache" \
       "$JARVIS_DEFAULT/GPUCache" \
       "$JARVIS_DEFAULT/blob_storage" 2>/dev/null

if [[ -f "$JARVIS_PREF" ]]; then
    /opt/homebrew/bin/python3.11 - <<PYEOF 2>/dev/null
import json
with open("$JARVIS_PREF", "r") as f:
    p = json.load(f)
p.setdefault("profile", {})["exit_type"] = "Normal"
p.setdefault("profile", {})["exited_cleanly"] = True
with open("$JARVIS_PREF", "w") as f:
    json.dump(p, f)
PYEOF
fi

pkill -f "jarvis-whisper-chrome-profile" 2>/dev/null
sleep 1

echo "[session] Chrome öffnen (Kiosk-Mode)..."
open -na "Google Chrome" --args \
    --kiosk http://localhost:8341 \
    --autoplay-policy=no-user-gesture-required \
    --user-data-dir="$JARVIS_PROFILE" \
    --no-first-run \
    --disable-restore-session-state \
    --no-default-browser-check \
    --disable-gpu \
    --in-process-gpu

sleep 3
if ! pgrep -f "jarvis-whisper-chrome-profile" > /dev/null 2>&1; then
    echo "[session] Chrome nicht gestartet — retry..."
    sleep 3
    open -na "Google Chrome" --args \
        --kiosk http://localhost:8341 \
        --autoplay-policy=no-user-gesture-required \
        --user-data-dir="$JARVIS_PROFILE" \
        --no-first-run \
        --disable-restore-session-state \
        --no-default-browser-check \
        --disable-gpu \
        --in-process-gpu
    echo "[session] Chrome retry gestartet"
else
    echo "[session] Chrome läuft ✓"
fi
