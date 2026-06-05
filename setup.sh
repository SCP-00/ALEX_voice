#!/usr/bin/env bash
set -e

# ═══════════════════════════════════════════════════════════════
#  Alex Voice — Setup Script for Linux (Ubuntu/Debian)
# ═══════════════════════════════════════════════════════════════
#  Usage: chmod +x setup.sh && ./setup.sh
#
#  Requires:
#    - Ubuntu 22.04+ / Debian 12+
#    - NVIDIA GPU with 6GB+ VRAM
#    - Python 3.10+
#    - CUDA 12.4+ drivers installed
# ═══════════════════════════════════════════════════════════════

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[SETUP]${NC} $1"; }
ok()    { echo -e "${GREEN}[✔]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✘]${NC} $1"; }

echo ""
echo "============================================="
echo "    ⚡ Alex Voice — Linux Setup"
echo "============================================="
echo ""

# ═══════════════════════════════════════════════════════
#  Helper: build llama-server from source (CUDA required)
# ═══════════════════════════════════════════════════════
build_llama_from_source() {
    if ! command -v nvcc &>/dev/null && ! command -v nvidia-smi &>/dev/null; then
        warn "CUDA not found. llama-server build will use CPU only (slow!)"
        CMAKE_CUDA_FLAG="-DLLAMA_CUDA=OFF"
    else
        CMAKE_CUDA_FLAG="-DLLAMA_CUDA=ON"
        ok "CUDA detected for llama.cpp build"
    fi

    if [ ! -d "llama.cpp" ]; then
        info "Cloning llama.cpp..."
        git clone --depth 1 https://github.com/ggml-org/llama.cpp.git
    fi

    cd llama.cpp
    mkdir -p build && cd build
    cmake .. $CMAKE_CUDA_FLAG -DCMAKE_BUILD_TYPE=Release
    make -j$(nproc) llama-server
    cp bin/llama-server "$ROOT/llama-server-bin/"
    cd "$ROOT"
    ok "llama-server built from source"
}

# ═══════════════════════════════════════════════════════
#  Helper: download Piper TTS model
# ═══════════════════════════════════════════════════════
download_piper() {
    local url="$1"
    local out="$2"
    if [ -f "$out" ]; then
        ok "$(basename $out) already downloaded"
    else
        info "Downloading $(basename $out)..."
        curl -sL "$url" -o "$out" && ok "$(basename $out) downloaded" || warn "Failed to download $(basename $out)"
    fi
}

# ── 1. System packages ────────────────────────────────────
info "[1/6] Installing system packages..."
if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
        python3 python3-pip python3-venv \
        build-essential cmake \
        curl wget git unzip \
        libportaudio2 libsndfile1 \
        espeak-ng espeak-ng-data \
        libespeak-ng-dev \
        2>&1 | tail -1
    ok "System packages installed"
elif command -v pacman &>/dev/null; then
    sudo pacman -S --noconfirm \
        python python-pip base-devel cmake \
        curl wget git unzip \
        portaudio libsndfile espeak-ng
    ok "System packages installed (Arch)"
else
    warn "Unknown package manager. Install manually: python3, pip, build-essential, cmake, espeak-ng"
fi

# ── 2. Python venv ────────────────────────────────────────
info "[2/6] Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    ok "Virtual environment created"
else
    ok "Virtual environment already exists"
fi
source venv/bin/activate
pip install --upgrade pip -q
ok "pip updated"

# ── 3. Python dependencies ────────────────────────────────
info "[3/6] Installing Python packages..."
# PyTorch CUDA
python3 -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null && \
    ok "PyTorch CUDA already installed" || {
    info "Installing PyTorch CUDA 12.4..."
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
    ok "PyTorch CUDA installed"
}

# Core packages
pip install kokoro piper-tts faster-whisper qwen-tts argostranslate \
            psutil pynvml numpy 2>&1 | tail -5
ok "Core packages installed"

# ── 4. llama-server ───────────────────────────────────────
info "[4/6] Setting up llama-server..."
LLAMA_VERSION="b4746"  # Latest stable CUDA build for Linux
LLAMA_DIR="$ROOT/llama-server-bin"
mkdir -p "$LLAMA_DIR"

if [ -f "$LLAMA_DIR/llama-server" ]; then
    ok "llama-server already downloaded"
else
    info "Downloading llama.cpp ($LLAMA_VERSION) for Linux..."
    LLAMA_URL="https://github.com/ggml-org/llama.cpp/releases/download/$LLAMA_VERSION/llama-$LLAMA_VERSION-bin-ubuntu-x64.zip"
    TMP_DIR=$(mktemp -d)

    if curl -sL "$LLAMA_URL" -o "$TMP_DIR/llama.zip"; then
        unzip -q -o "$TMP_DIR/llama.zip" -d "$TMP_DIR/extracted"
        find "$TMP_DIR/extracted" -name "llama-server" -exec cp {} "$LLAMA_DIR/" \;
        chmod +x "$LLAMA_DIR/llama-server" 2>/dev/null || true
        rm -rf "$TMP_DIR"

        if [ -f "$LLAMA_DIR/llama-server" ]; then
            ok "llama-server downloaded and extracted"
        else
            warn "llama-server binary not found in release — building from source"
            build_llama_from_source
        fi
    else
        warn "Could not download — building llama-server from source..."
        build_llama_from_source
    fi
fi

# ── 5. Model ───────────────────────────────────────────────
info "[5/6] Downloading LLM model..."
mkdir -p "$ROOT/models"

if [ -f "$ROOT/models/qwen2.5-1.5b-q4_k_m.gguf" ]; then
    ok "Qwen2.5-1.5B Q4_K_M already downloaded"
else
    info "Downloading Qwen2.5-1.5B Q4_K_M (~1.1 GB)..."
    curl -L -o "$ROOT/models/qwen2.5-1.5b-q4_k_m.gguf" \
        "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
    ok "Model downloaded"
fi

# ── 6. Piper models ───────────────────────────────────────
info "[6/6] Downloading Piper TTS models..."
download_piper \
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx" \
    "$ROOT/models/es_ES-sharvard-medium.onnx"

download_piper \
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" \
    "$ROOT/models/en_US-lessac-medium.onnx"

# ── Argos packages ─────────────────────────────────────────
info "[Extra] Installing argos-translate packages (EN↔ES↔JA)..."
# venv already active from step 2
python3 -c "
import argostranslate.package as p
p.update_package_index()
avail = p.get_available_packages()
installed = {(x.from_code, x.to_code) for x in p.get_installed_packages()}
pairs = [('en','es'),('es','en'),('en','ja'),('ja','en')]
for fc, tc in pairs:
    if (fc, tc) not in installed:
        pkg = next((x for x in avail if x.from_code == fc and x.to_code == tc), None)
        if pkg:
            path = pkg.download()
            p.install_from_path(path)
            print(f'  ✔ {fc}->{tc} installed')
        else:
            print(f'  ⚠ {fc}->{tc} not available')
print('  ✔ argos EN/ES/JA ready')
" 2>&1

echo ""
echo "============================================="
echo -e "    ${GREEN}✅ Setup Complete${NC}"
echo "============================================="
echo ""
echo "   Next steps:"
echo "     1. ./run.sh          — Opens menu at http://localhost:5000"
echo "     2. source venv/bin/activate"
echo "        python3 menu_server.py"
echo ""
echo "   Or run modes directly:"
echo "     python3 server.py --port 3000           # Teacher (port 3000)"
echo "     python3 conv_server.py                   # Conversation (port 3001)"
echo "     python3 translator.py                    # Translator (port 3003)"
echo ""
