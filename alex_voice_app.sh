#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  Alex Voice — Unified Launcher (v3)
#  Model: prometheus-orchestrator (Qwen3.5 4B Instruct) via Ollama API
#  Opens menu at http://localhost:5000
#  Only ONE subproject at a time (Teacher, Conversation, Translator)
#  Proper cleanup on exit (kills processes + offloads model from VRAM via Ollama)
# ═══════════════════════════════════════════════════════════════

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${CYAN}${BOLD}════════════════════════════════════════${NC}"
echo -e "${CYAN}${BOLD}  🎙️  Alex Voice — Unified Launcher (v3)${NC}"
echo -e "${CYAN}${BOLD}════════════════════════════════════════${NC}"
echo ""

# ── Verify Ollama is running ──────────────────────────────
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo -e "  ${RED}✗${NC} Ollama is not running. Start it with: 'ollama serve'"
    echo ""
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Ollama API detected on port 11434"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "  ${GREEN}✓${NC} Virtual environment activated"
else
    echo -e "  ${RED}✗${NC} No venv found — run ./setup.sh first"
    exit 1
fi

# Kill any existing Alex Voice processes
echo "  Stopping any running Alex Voice servers..."
pkill -f 'python.*menu_server.py' 2>/dev/null
pkill -f 'python.*server.py.*PLAN_B_PORT' 2>/dev/null
pkill -f 'python.*conv_server.py' 2>/dev/null
pkill -f 'python.*translator.py' 2>/dev/null
sleep 1

# ── Cleanup function ──────────────────────────────────────
# Offloads model from VRAM via Ollama API + kills Python servers
cleanup() {
    echo ""
    echo -e "  ${RED}🛑 Stopping all Alex Voice servers...${NC}"
    # Offload model from GPU VRAM via Ollama
    curl -s http://localhost:11434/api/generate \
        -d '{"model":"prometheus-orchestrator","keep_alive":"0m"}' >/dev/null 2>&1
    pkill -f 'python.*menu_server.py' 2>/dev/null
    pkill -f 'python.*server.py.*PLAN_B_PORT' 2>/dev/null
    pkill -f 'python.*conv_server.py' 2>/dev/null
    pkill -f 'python.*translator.py' 2>/dev/null
    echo -e "  ${GREEN}✓${NC} All servers stopped, model offloaded from VRAM"
    echo ""
}

# Trap signals for cleanup
trap cleanup EXIT
trap 'exit 0' INT TERM

# Start menu server
echo "  Starting menu server..."
python3 menu_server.py &
MENU_PID=$!

# Wait for server to be ready
sleep 2

# Check if server started
if ! kill -0 $MENU_PID 2>/dev/null; then
    echo -e "  ${RED}✗${NC} Menu server failed to start"
    exit 1
fi

echo -e "  ${GREEN}✓${NC} Menu server ready at http://localhost:5000"
echo ""
echo -e "  ${BOLD}Select a mode from the menu:${NC}"
echo "    🎓 Teacher       — Language learning with structured output"
echo "    💬 Conversation  — Natural chat practice"
echo "    🌍 Translator    — Real-time speech translation"
echo ""
echo -e "  ${CYAN}Tip:${NC} Only ONE mode runs at a time to maximize VRAM."
echo -e "  ${CYAN}Tip:${NC} Use the Home button to switch modes."
echo ""

# Open browser
if command -v xdg-open &>/dev/null; then
    xdg-open http://localhost:5000 &>/dev/null &
elif command -v gnome-open &>/dev/null; then
    gnome-open http://localhost:5000 &>/dev/null &
fi

echo -e "  ${GREEN}🟢 Alex Voice ACTIVO${NC} — Press Ctrl+C to stop everything"
echo ""

# Wait for menu server to exit
wait $MENU_PID 2>/dev/null
echo -e "  ${GREEN}✓${NC} Menu server stopped"
