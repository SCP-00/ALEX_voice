#!/usr/bin/env bash
set -e

# ═══════════════════════════════════════════════════════════════
#  ⚡ Alex Voice — Universal Installer
#  v3.3.1 (June 2026)
#
#  Hace TODO automáticamente:
#  1. Verifica hardware (GPU, RAM, disco)
#  2. Instala dependencias del sistema
#  3. Crea venv + pip install
#  4. Configura Ollama + descarga modelo
#  5. Descarga modelos (Kokoro, Piper)
#  6. Crea atajo de escritorio
#  7. Abre http://localhost:5000
#
#  Uso: curl -fsSL https://raw.githubusercontent.com/SCP-00/ALEX_voice/main/install.sh | sh
#  O:   git clone && cd ALEX_voice && chmod +x install.sh && ./install.sh
# ═══════════════════════════════════════════════════════════════

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${BLUE}  [INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}  [✔]${NC} $1"; }
warn()  { echo -e "${YELLOW}  [!]${NC} $1"; }
err()   { echo -e "${RED}  [✘]${NC} $1"; }
title() { echo -e "\n${CYAN}${BOLD}━━━ $1 ━━━${NC}"; }

echo ""
echo -e "${CYAN}${BOLD}╔════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║       ⚡ Alex Voice — Universal Installer      ║${NC}"
echo -e "${CYAN}${BOLD}║       v3.3.1 — 100% Local · Sin Internet      ║${NC}"
echo -e "${CYAN}${BOLD}╚════════════════════════════════════════════════╝${NC}"
echo ""

# ── Step 0: Detect OS ──────────────────────────────────
title "Detectando sistema operativo"
OS="unknown"
if [ "$(uname)" = "Linux" ]; then
    OS="linux"
    if command -v apt-get &>/dev/null; then
        PKG_MANAGER="apt"
    elif command -v pacman &>/dev/null; then
        PKG_MANAGER="pacman"
    elif command -v dnf &>/dev/null; then
        PKG_MANAGER="dnf"
    else
        warn "Package manager no detectado. Instala python3, pip, build-essential manualmente."
    fi
    ok "Sistema: Linux ($PKG_MANAGER)"
elif [ "$(uname -s | cut -c 1-10)" = "MINGW32_NT" ] || [ "$(uname -s | cut -c 1-10)" = "MINGW64_NT" ]; then
    OS="windows"
    warn "Windows detected. Run setup_windows.bat instead."
    exit 1
else
    warn "Sistema no detectado: $(uname). Probando instalación Linux..."
fi

# ── Step 1: Verify hardware ────────────────────────────
title "Verificando hardware"

# GPU NVIDIA
if command -v nvidia-smi &>/dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    VRAM_TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1 | awk '{print $1}')
    echo -e "  GPU: ${GREEN}${GPU_NAME} ($VRAM_TOTAL MB)${NC}"
    if [ "$VRAM_TOTAL" -lt 4096 ]; then
        warn "VRAM baja (${VRAM_TOTAL}MB). Solo Grammar App + Translator funcionarán."
    else
        ok "VRAM suficiente (${VRAM_TOTAL}MB)"
    fi
else
    warn "No se detectó GPU NVIDIA. Solo Grammar App funcionará."
    warn "Teacher/Conversation/Translator requieren NVIDIA con CUDA."
fi

# RAM
RAM_TOTAL=$(free -m | awk '/^Mem:/{print $2}')
if [ "$RAM_TOTAL" -gt 8000 ]; then
    ok "RAM: ${RAM_TOTAL}MB"
else
    warn "RAM baja (${RAM_TOTAL}MB). Mínimo recomendado: 16GB"
fi

# Disco
DISK_FREE=$(df -h . | awk 'NR==2{print $4}')
info "Disco libre: $DISK_FREE"

# ── Step 2: Install system packages ────────────────────
title "Instalando paquetes del sistema"
if [ "$PKG_MANAGER" = "apt" ]; then
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
        python3 python3-pip python3-venv \
        build-essential cmake \
        curl wget git unzip \
        libportaudio2 libsndfile1 \
        espeak-ng espeak-ng-data libespeak-ng-dev 2>&1 | tail -1
    ok "Paquetes del sistema instalados"
elif [ "$PKG_MANAGER" = "pacman" ]; then
    sudo pacman -S --noconfirm \
        python python-pip base-devel cmake \
        curl wget git unzip portaudio libsndfile espeak-ng 2>&1 | tail -1
    ok "Paquetes instalados (Arch)"
fi

# ── Step 3: Python venv + deps ─────────────────────────
title "Configurando Python virtual environment"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    ok "Virtual environment creado"
fi
source venv/bin/activate
pip install --upgrade pip -q

# PyTorch CUDA
if ! python3 -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
    info "Instalando PyTorch CUDA 12.4..."
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124 -q
    ok "PyTorch CUDA instalado"
else
    ok "PyTorch CUDA ya instalado"
fi

# Core deps
info "Instalando dependencias Python..."
pip install faster-whisper onnxruntime silero-vad psutil pynvml numpy kokoro-onnx \
    loguru scipy transformers num2words piper-tts cutlet unidic-lite \
    huggingface-hub flask requests -q 2>&1 | tail -3
ok "Dependencias instaladas"

# ── Step 4: Ollama + model ────────────────────────────
title "Configurando Ollama + modelo LLM"

if command -v ollama &>/dev/null; then
    ok "Ollama ya instalado"
else
    info "Instalando Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    ok "Ollama instalado"
fi

# Start Ollama if not running
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    info "Iniciando Ollama..."
    ollama serve &
    for i in $(seq 1 15); do
        if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
fi

# Pull model
if ollama list 2>/dev/null | grep -q prometheus-orchestrator; then
    ok "Modelo prometheus-orchestrator ya descargado"
else
    info "Descargando prometheus-orchestrator (Qwen3.5 4B, ~2.9 GB)..."
    info "Esto puede tomar 5-10 minutos..."
    ollama    pull prometheus-orchestrator
    ok "Modelo descargado"

# Auto-chmod scripts
chmod +x "$ROOT/alex_voice_app.sh" 2>/dev/null || true
chmod +x "$ROOT/install.sh" 2>/dev/null || true
chmod +x "$ROOT/setup.sh" 2>/dev/null || true
ok "Scripts marcados como ejecutables"
fi

# ── Step 5: Download ONNX models ──────────────────────
title "Descargando modelos Kokoro (TTS)"

python3 -c "
import os, requests
models_dir = os.path.join('$ROOT', 'models', 'onnx')
os.makedirs(models_dir, exist_ok=True)

files = {
    'kokoro-v1.0.onnx': 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx',
    'voices-v1.0.bin': 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin',
}

for name, url in files.items():
    path = os.path.join(models_dir, name)
    if os.path.exists(path) and os.path.getsize(path) > 1000000:
        print(f'  ✔ {name} ya existe ({os.path.getsize(path)//1024//1024} MB)')
        continue
    print(f'  Descargando {name}...')
    r = requests.get(url, timeout=300)
    with open(path, 'wb') as f:
        f.write(r.content)
    print(f'  ✔ {name} descargado ({len(r.content)//1024//1024} MB)')

print('  Modelos Kokoro listos.')
" 2>&1 || warn "No se pudieron descargar modelos Kokoro. Ejecuta scripts/install_models.py después."

# ── Step 6: Desktop shortcut ──────────────────────────
title "Creando acceso directo"

DESKTOP_FILE="$HOME/.local/share/applications/alex-voice.desktop"
mkdir -p "$(dirname "$DESKTOP_FILE")"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=Alex Voice
Comment=Aprende idiomas con IA local
Exec=$ROOT/alex_voice_app.sh
Icon=$ROOT/frontend/icon.png
Terminal=true
Type=Application
Categories=Education;Utility;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"
ok "Atajo de escritorio creado: Alex Voice"

# ── Step 7: First-run setup (Grammar App DB) ──────────
title "Inicializando bases de datos"

python3 -c "
import sys
sys.path.insert(0, '$ROOT')
from grammar_app.backend.database import init_db, seed_default_data
init_db()
seed_default_data()
print('  ✔ Grammar App database initialized')
" 2>&1 || warn "No se pudo inicializar Grammar App DB"

# ── Verification ──────────────────────────────────────
title "Verificando instalación"

python3 -c "
import sys
checks = {
    'Python': f'{sys.version_info.major}.{sys.version_info.minor}',
}
try:
    import torch
    checks['PyTorch CUDA'] = f'{\"✔\" if torch.cuda.is_available() else \"✘\"}'
except: checks['PyTorch CUDA'] = '✘'
try: import faster_whisper; checks['Whisper'] = '✔'
except: checks['Whisper'] = '✘'
try: from kokoro_onnx import Kokoro; checks['Kokoro ONNX'] = '✔'
except: checks['Kokoro ONNX'] = '✘'
try: import flask; checks['Flask'] = '✔'
except: checks['Flask'] = '✘'
try: import onnxruntime; checks['ONNX Runtime'] = '✔'
except: checks['ONNX Runtime'] = '✘'
try: import cutlet; checks['Cutlet'] = '✔'
except: checks['Cutlet'] = '✘'
try: from transformers import MarianMTModel; checks['Transformers'] = '✔'
except: checks['Transformers'] = '✘'

for name, status in checks.items():
    print(f'  {status} {name}')
" 2>&1

# ── Done ──────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║       ✅ Alex Voice instalado con éxito        ║${NC}"
echo -e "${GREEN}${BOLD}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Para iniciar:"
echo "    ./alex_voice_app.sh              → Menú en http://localhost:5000"
echo ""
echo "  O modos directos:"
echo "    python3 server.py --port 3000    → Teacher"
echo "    python3 conv_server.py            → Conversation"
echo "    python3 translator.py             → Translator"
echo "    cd grammar_app/backend && python3 app.py  → Grammar App"
echo ""
echo "  Atajo de teclado:"
echo "    1=Teacher  2=Conversation  3=Translator  4=Grammar  Esc=Detener"
echo ""
echo -e "${YELLOW}  💡 Tip: Si la barra de tareas no muestra icono, corre el setup:${NC}"
echo "    chmod +x setup.sh && ./setup.sh"
echo ""
