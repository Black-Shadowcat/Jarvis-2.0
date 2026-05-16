#!/bin/bash

# setup-plists.sh — Installiert LaunchAgent Plists mit korrekten Pfaden
#
# Verwendung:
#   bash scripts/setup-plists.sh
#
# Diese Script:
# 1. Kopiert alle .plist Dateien aus launchagents/ nach ~/Library/LaunchAgents/
# 2. Ersetzt hardcodierte Pfade durch $HOME und aktuelle Repo-Pfade
# 3. Ladet die Plists in launchd

set -e

# Farben für Output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Repo-Pfad ermitteln (sollte das Verzeichnis sein, in dem dieses Script liegt)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_PATH="$(dirname "$SCRIPT_DIR")"
PYTHON_BIN="${PYTHON_BIN:-/opt/homebrew/bin/python3.11}"

echo -e "${BLUE}🔧 Jarvis 2.0 LaunchAgent Setup${NC}"
echo "Repo-Pfad: $REPO_PATH"
echo "Python: $PYTHON_BIN"
echo "Home: $HOME"
echo ""

# Zielverzeichnis erstellen
mkdir -p ~/Library/LaunchAgents

# Alle .plist Dateien aus launchagents/ verarbeiten
for plist_src in "$REPO_PATH/launchagents"/*.plist; do
    if [ ! -f "$plist_src" ]; then
        continue
    fi

    plist_name=$(basename "$plist_src")
    plist_dest="$HOME/Library/LaunchAgents/$plist_name"

    echo -ne "Processing $plist_name... "

    # Plist kopieren und Pfade ersetzen:
    # 1. /Users/matthiasschreiber → $HOME
    # 2. jarvis-voice-assistant → aktueller Repo-Name
    cat "$plist_src" | \
        sed "s|/Users/matthiasschreiber|$HOME|g" | \
        sed "s|jarvis-voice-assistant|Jarvis-2.0|g" | \
        sed "s|/opt/homebrew/bin/python3.11|$PYTHON_BIN|g" \
        > "$plist_dest"

    if [ -f "$plist_dest" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        exit 1
    fi
done

echo ""
echo -e "${BLUE}📋 Installierte LaunchAgents:${NC}"
ls -la ~/Library/LaunchAgents/com.jarvis.v2.*.plist | wc -l | xargs echo "   Plists:"

echo ""
echo -e "${BLUE}🚀 Starten der Services...${NC}"

# Alte Instanzen unloaden (falls vorhanden)
for plist in ~/Library/LaunchAgents/com.jarvis.v2.*.plist; do
    launchctl unload "$plist" 2>/dev/null || true
done

sleep 1

# Services laden
for plist in ~/Library/LaunchAgents/com.jarvis.v2.*.plist; do
    plist_name=$(basename "$plist")
    launchctl load "$plist"
    echo -e "  ${GREEN}✓${NC} $plist_name"
done

echo ""
sleep 2

# Status prüfen
echo -e "${BLUE}📊 Service Status:${NC}"
launchctl list | grep "jarvis.v2" | wc -l | xargs echo "   Running:"

# Ports prüfen
echo ""
echo -e "${BLUE}🔌 Port-Status:${NC}"
for port in 8340 8341 8342; do
    if lsof -i :$port &>/dev/null; then
        echo -e "  Port $port: ${GREEN}✓ Listening${NC}"
    else
        echo -e "  Port $port: ${RED}✗ Not listening (yet)${NC}"
    fi
done

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "Nächste Schritte:"
echo "1. Berechtigungen in Systemeinstellungen setzen (siehe SETUP_macOS.md Schritt 9)"
echo "2. Testen: open http://localhost:8340"
echo "3. Logs: tail -f ~/Library/Logs/jarvis-v2/server.log"
echo ""
