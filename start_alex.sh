#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  Alex Voice — Linux Quick Start
#  Carga nvidia-uvm + inicia menú principal
# ═══════════════════════════════════════════════════════════════

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "============================================="
echo "    ⚡ Alex Voice — Linux Start"
echo "============================================="
echo ""

# 1. Verify nvidia-uvm module is loaded (auto-loaded via modules-load.d + udev)
if ! lsmod 2>/dev/null | grep -q nvidia_uvm; then
    echo -e "  ${YELLOW}[!]${NC} nvidia-uvm not loaded — attempting to load..."
    sudo modprobe nvidia-current-uvm 2>/dev/null || echo -e "  ${YELLOW}[!]${NC} Could not load module (reboot may be needed)"
fi

# 2. Set CUDA library path (needed for PyTorch CUDA)
CUDA_LIB="$ROOT/venv/lib/python3.13/site-packages/nvidia/cuda_runtime/lib"
if [ -d "$CUDA_LIB" ]; then
    export LD_LIBRARY_PATH="$CUDA_LIB:$LD_LIBRARY_PATH"
fi

# 3. Activate virtual environment
VENV_PYTHON="$ROOT/venv/bin/python3"
if [ -f "$VENV_PYTHON" ]; then
    echo -e "  ${GREEN}✓${NC} Virtual environment ready"
else
    echo -e "  ${YELLOW}[!]${NC} No venv found — run ./setup.sh first"
    exit 1
fi

# 4. Check CUDA
$VENV_PYTHON -c "import torch; print(f'  GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"NOT AVAILABLE\"}')" 2>/dev/null || echo -e "  ${YELLOW}[!]${NC} GPU not available (CPU fallback)"

# 5. Start menu server
echo ""
echo "  Opening menu: http://localhost:5000"
echo "  Press Ctrl+C to stop all servers."
echo ""

$VENV_PYTHON menu_server.py &

sleep 2

if command -v xdg-open &>/dev/null; then
    xdg-open http://localhost:5000
elif command -v gnome-open &>/dev/null; then
    gnome-open http://localhost:5000
else
    echo "  Open http://localhost:5000 in your browser."
fi

trap 'kill \$(jobs -p) 2>/dev/null' EXIT
wait
