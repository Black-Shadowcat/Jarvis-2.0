#!/bin/zsh
# Jarvis 2.0 — Launch Session (macOS)
# Wartet auf macOS-Bereitschaft + Server, dann öffnet Frontend.
#
# Umgebungsvariablen:
#   USE_TAURI=0  → Chrome Kiosk-Mode (Standard, Production)
#   USE_TAURI=1  → Native Tauri-App (Phase 3 Migration)

USE_TAURI="${USE_TAURI:-0}"
JARVIS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TAURI_BINARY="$JARVIS_DIR/target/debug/jarvis-tauri"

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

SERVER_URL="http://localhost:8340"

echo "[session] Warte auf Server $SERVER_URL..."
for i in {1..30}; do
    curl -s -o /dev/null -w "%{http_code}" "$SERVER_URL" 2>/dev/null | grep -q "200" && break
    sleep 2
    if [[ $i -eq 30 ]]; then
        echo "[session] Server nicht erreichbar nach 60s — trotzdem Frontend öffnen"
    fi
done

# ─── Tauri oder Chrome? ───────────────────────────────────────────────────────
if [[ "$USE_TAURI" == "1" ]]; then
    echo "[session] Tauri-Modus aktiv..."

    if [[ ! -f "$TAURI_BINARY" ]]; then
        echo "[session] Tauri-Binary nicht gefunden — baue jetzt (einmalig ~2 Min)..."
        source "$HOME/.cargo/env"
        cd "$JARVIS_DIR" && cargo build 2>&1 | tail -5
        if [[ ! -f "$TAURI_BINARY" ]]; then
            echo "[session] Build fehlgeschlagen — Fallback auf Chrome"
            USE_TAURI=0
        fi
    fi

    if [[ "$USE_TAURI" == "1" ]]; then
        pkill -f "jarvis-tauri" 2>/dev/null
        sleep 1
        echo "[session] Tauri starten..."
        "$TAURI_BINARY" &
        sleep 3
        if pgrep -f "jarvis-tauri" > /dev/null 2>&1; then
            echo "[session] Tauri läuft ✓"
        else
            echo "[session] Tauri nicht gestartet — Fallback auf Chrome"
            USE_TAURI=0
        fi
    fi
fi

# ─── Chrome Kiosk (Standard oder Fallback) ───────────────────────────────────
if [[ "$USE_TAURI" == "0" ]]; then
    JARVIS_PROFILE="$HOME/.jarvis-v2-chrome-profile"
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

    pkill -f "jarvis-v2-chrome-profile" 2>/dev/null
    sleep 1

    echo "[session] Chrome öffnen (Kiosk-Mode)..."
    open -na "Google Chrome" --args \
        --kiosk http://localhost:8340 \
        --autoplay-policy=no-user-gesture-required \
        --user-data-dir="$JARVIS_PROFILE" \
        --no-first-run \
        --disable-restore-session-state \
        --no-default-browser-check \
        --disable-gpu \
        --in-process-gpu

    sleep 3
    if ! pgrep -f "jarvis-v2-chrome-profile" > /dev/null 2>&1; then
        echo "[session] Chrome nicht gestartet — retry..."
        sleep 3
        open -na "Google Chrome" --args \
            --kiosk http://localhost:8340 \
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
fi
