#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  Alex Voice — Linux Quick Start
# ═══════════════════════════════════════════════════════════════
#  Usage: chmod +x run.sh && ./run.sh
#  Opens the main menu at http://localhost:5000
# ═══════════════════════════════════════════════════════════════

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo ""
echo "============================================="
echo "    ⚡ Alex Voice — Quick Start"
echo "============================================="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "  ${GREEN}✓${NC} Virtual environment activated"
else
    echo "  ⚠ No virtual environment found, using system Python"
    echo "  Run ./setup.sh first for best results."
fi

echo ""
echo "  Opening menu: http://localhost:5000"
echo "  Press Ctrl+C to stop all servers."
echo ""

# Start menu server
python3 menu_server.py &

# Give it a moment to start
sleep 2

# Open browser
if command -v xdg-open &>/dev/null; then
    xdg-open http://localhost:5000
elif command -v gnome-open &>/dev/null; then
    gnome-open http://localhost:5000
else
    echo "  Open http://localhost:5000 in your browser."
fi

# Wait and cleanup on exit
trap 'kill $(jobs -p) 2>/dev/null' EXIT

# Keep running
wait
