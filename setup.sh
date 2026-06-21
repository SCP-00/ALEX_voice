#!/usr/bin/env bash
set -e

# ═══════════════════════════════════════════════════════════════
#  Alex Voice — Setup Script for Linux (Ubuntu/Debian)
# ═══════════════════════════════════════════════════════════════
#  v3.3 Architecture (June 2026):
#    - LLM: Ollama API → prometheus-orchestrator (Qwen3.5 4B Instruct, 64K ctx)
#    - TTS: Kokoro ONNX (CPU, 0 VRAM)
#    - Translation: Helsinki-NLP Opus-MT via transformers (~100ms)
#    - VAD: Silero VAD (CPU) — pre-filter before Whisper ASR
#    - Romanization: Cutlet (Japanese) — replaces LLM-based TTS_READING
#
#  Usage: chmod +x setup.sh && ./setup.sh
#
#  Requires:
#    - Ubuntu 22.04+ / Debian 12+ / Kali Linux
#    - NVIDIA GPU with 6GB+ VRAM
#    - Python 3.10+
#    - CUDA 12.4+ drivers installed
#    - Ollama 0.30+ (installed separately: curl -fsSL https://ollama.com/install.sh | sh)
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
echo "============================================="    echo "    ⚡ Alex Voice — Linux Setup (v3.3)"
echo "============================================="
echo ""

# ── 1. System packages ────────────────────────────────────
info "[1/5] Installing system packages..."
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
info "[2/5] Setting up Python virtual environment..."
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
info "[3/5] Installing Python packages..."

# PyTorch CUDA
python3 -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null && \
    ok "PyTorch CUDA already installed" || {
    info "Installing PyTorch CUDA 12.4..."
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
    ok "PyTorch CUDA installed"
}

# Core ML packages
info "Installing core ML packages..."
pip install faster-whisper \
            onnxruntime silero-vad \
            psutil pynvml numpy 2>&1 | tail -5
ok "Core ML packages installed"

# TTS: Kokoro ONNX (CPU, 0 VRAM)
info "Installing Kokoro ONNX TTS..."
pip install kokoro-onnx loguru scipy transformers num2words \
            piper-tts 2>&1 | tail -5
ok "Kokoro ONNX TTS installed"

# Cutlet: Japanese romanization (replaces LLM-based TTS_READING)
info "Installing Cutlet (Japanese romanization)..."
pip install cutlet unidic-lite 2>&1 | tail -5
ok "Cutlet installed"

# HuggingFace Hub (for model downloads)
pip install huggingface-hub -q 2>&1 | tail -3
ok "HuggingFace Hub installed"

# ── 4. Ollama + prometheus-orchestrator ─────────────────────
info "[4/5] Setting up Ollama + LLM model..."

# Check if Ollama is installed
if command -v ollama &>/dev/null; then
    ok "Ollama already installed"
else
    info "Ollama not found. Installing via official script..."
    warn "This will require sudo access."
    curl -fsSL https://ollama.com/install.sh | sh
    ok "Ollama installed"
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    info "Starting Ollama service..."
    ollama serve &
    sleep 3
fi

# Pull prometheus-orchestrator (Qwen3.5 4B Instruct, ~2.9 GB)
if ollama list 2>/dev/null | grep -q prometheus-orchestrator; then
    ok "prometheus-orchestrator already downloaded (~3GB VRAM, 262K ctx)"
else
    info "Downloading prometheus-orchestrator (Qwen3.5 4B Instruct, ~2.9 GB)..."
    info "This may take 5-10 minutes at 8MB/s..."
    ollama pull prometheus-orchestrator
    ok "prometheus-orchestrator downloaded"
fi

# ── 5. Download all model files via install_models.py ────
info "[5/5] Downloading model files (Kokoro, Piper, Translation)..."
python3 "$ROOT/scripts/install_models.py"

# ═══════════════════════════════════════════════════════════════
#  Verification
# ═══════════════════════════════════════════════════════════════
echo ""
info "Verifying installation..."

python3 -c "
import sys
print(f'Python: {sys.version}')

# Core deps
try:
    import torch
    print(f'PyTorch: {torch.__version__} CUDA={torch.cuda.is_available()}')
except: print('PyTorch: MISSING')

try:
    import faster_whisper
    print('faster-whisper: OK')
except: print('faster-whisper: MISSING')

try:
    from transformers import MarianMTModel
    print('transformers (MarianMT): OK')
except: print('transformers: MISSING')

try:
    from kokoro_onnx import Kokoro
    print('kokoro-onnx: OK')
except: print('kokoro-onnx: MISSING')

try:
    import onnxruntime
    print(f'onnxruntime: {onnxruntime.__version__}')
except: print('onnxruntime: MISSING')

try:
    from silero_vad import load_silero_vad
    print('silero-vad: OK')
except: print('silero-vad: MISSING')

try:
    import cutlet
    print('cutlet: OK')
except: print('cutlet: MISSING')

try:
    import piper
    print('piper-tts: OK')
except: print('piper-tts: MISSING')

print()
print('=== Model files ===')
import os
models_dir = os.environ.get('MODELS_DIR', '$ROOT/models')
onnx_dir = os.path.join(models_dir, 'onnx')

# Ollama (LLM)
import subprocess
result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
if 'prometheus-orchestrator' in result.stdout:
    print('LLM (Ollama): prometheus-orchestrator ✅')
else:
    print('LLM (Ollama): prometheus-orchestrator ❌ NOT FOUND — run: ollama pull prometheus-orchestrator')

# Kokoro ONNX
kokoro_onnx = os.path.join(onnx_dir, 'kokoro-v1.0.onnx')
kokoro_voices = os.path.join(onnx_dir, 'voices-v1.0.bin')
print(f'Kokoro ONNX: {\"OK\" if os.path.exists(kokoro_onnx) else \"MISSING\"}')
print(f'Kokoro voices: {\"OK\" if os.path.exists(kokoro_voices) else \"MISSING\"}')

# Piper
piper_es = os.path.join(models_dir, 'es_ES-sharvard-medium.onnx')
piper_en = os.path.join(models_dir, 'en_US-lessac-medium.onnx')
print(f'Piper ES: {\"OK\" if os.path.exists(piper_es) else \"MISSING\"}')
print(f'Piper EN: {\"OK\" if os.path.exists(piper_en) else \"MISSING\"}')

# Translation (Helsinki-NLP Opus-MT via transformers)
print('Translation models: Cached by transformers (Helsinki-NLP/opus-mt-*)')
"

echo ""
echo "============================================="
echo -e "    ${GREEN}✅ Setup Complete (v3.1)${NC}"
echo "============================================="
echo ""
echo ""
echo "   ℹ️  This setup no longer uses direct llama-server or GGUF files."
echo "      You can free ~5GB by removing old files from v2:"
echo "      rm -rf llama-server-bin models/qwen2.5-3b-instruct* models/qwen3.5-4b-instruct*"
echo ""
echo "   Architecture v3.3:"
echo "     • LLM:      Ollama API → prometheus-orchestrator (Qwen3.5 4B Instruct, 64K ctx)"
echo "     • TTS:      Kokoro ONNX (CPU, 0 VRAM) — 54 voices, 5 languages"
echo "     • Translation: Opus-MT via transformers (~100ms)"
echo "     • VAD:      Silero VAD (CPU) — pre-filter before Whisper ASR"
echo "     • Romanization: Cutlet (Japanese)"
echo ""
echo "   VRAM Budget:"
echo "     • Teacher/Conversation: Ollama (~3.0GB) + ASR (~1.5GB) = ~4.5GB"
echo "     • Translator:          ASR (~1.5GB) + Opus-MT (GPU) = ~1.7GB"
echo "     • TTS: 0 VRAM (CPU only — Kokoro ONNX + Piper)"
echo ""
echo "   Next steps:"
echo "     1. ./alex_voice_app.sh    — Opens menu at http://localhost:5000"
echo "     2. source venv/bin/activate"
echo "        python3 menu_server.py"
echo ""
echo "   Or run modes directly:"
echo "     python3 server.py --port 3000           # Teacher (port 3000)"
echo "     python3 conv_server.py                   # Conversation (port 3001)"
echo "     python3 translator.py                    # Translator (port 3003)"
echo ""
