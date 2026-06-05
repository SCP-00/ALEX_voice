# 🛡️ LEY ABSOLUTA — GPU COMMANDS MUST USE TMUX

## 🔴 CRITICAL RULE

On Linux, `nvidia-smi`, `llama-server`, and any GPU inference **MUST** be run inside `tmux`.
Running GPU commands directly in basher can crash the CLI process.

**Rules:**
1. **NEVER** run GPU/VRAM commands directly in basher — always inside tmux
2. **NEVER** use ^C — let commands finish naturally or use timeout
3. **ALWAYS** use generous timeouts (3 MB/s download speed)
4. **NEVER** run `nvidia-smi` while GPU processes are active
5. **NEVER** run `llama-server` / `llama-cli` outside tmux

**Safe outside tmux:** git, mkdir, curl, cat, cp, mv, sleep, echo, find, python scripts (CPU only)

**ALWAYS inside tmux:** nvidia-smi, llama-server, llama-cli, any GPU inference, model loading

---

## 📋 Project Context

### Hardware (Original — RTX 3050 Laptop)
| Component | Spec |
|-----------|------|
| GPU | NVIDIA RTX 3050 Laptop 6GB (5.28 GB usable VRAM, CC 8.6) |
| CPU | Intel Core i5-13420H (8C/12T) |
| RAM | 16.5 GB |
| Disk | ~258 GB free |
| CUDA Driver | 610.47 (CUDA 13.3, compatible with PyTorch CUDA 12.4) |

> **Note:** On a fresh Linux install, you may have different hardware. Adjust VRAM expectations accordingly. The project is designed for NVIDIA 6GB+ VRAM.

### Project Paths (Linux)
```
PROJECT=/home/<user>/Alex_Voice
PYTHON=python3  # or source venv/bin/activate
VENV=$PROJECT/venv
MODELS=$PROJECT/models/           # GGUF models + Piper .onnx
LLAMA_BIN=$PROJECT/llama-server-bin/  # llama-server binary
```

### Servers
| Port | Service | Script | Components |
|:----:|:--------|:-------|:-----------|
| 5000 | Menu | `menu_server.py` | Hub — start/stop modes, lifecycle management |
| 3000 | Teacher | `server.py` (teacher mode) | LLM GPU + Kokoro TTS CPU + Piper fallback + faster-whisper ASR |
| 3001 | Conversation | `conv_server.py` (wrapper → server.py conversation mode) | LLM GPU (same llama-server) + Kokoro TTS CPU + Piper fallback + faster-whisper ASR + **AEC** (mute-while-speaking) |
| 3003 | Translator | `translator.py` | argos CPU + Qwen3-TTS GPU + faster-whisper ASR |
| 8081 | llama-server | `llama-server` | Backend LLM GPU (chatml template, no-warmup, no-ui) |

**Note:** Teacher (3000) and Conversation (3001) share the same llama-server (8081). Only one mode can be active at a time via menu_server.

### Main Model
| Model | Path | VRAM | Context |
|-------|------|:----:|:-------:|
| Qwen2.5-1.5B-Q4_K_M 🏆 | `$MODELS/qwen2.5-1.5b-q4_k_m.gguf` | ~1.2 GB | 8192 ctx |

### TTS
| Engine | Port | Type | Detail |
|--------|:----:|:-----|:-------|
| Kokoro-82M 🏆 | 3000 | CPU, pip install | Primary for Teacher+Conversation. Voice ES `ef_dora`, EN `af_heart`. Lazy-load ~30s first time. Latin script only — `_sanitize_tts_text()` removes unpronounceable characters (CJK, etc.) as safety net. |
| Piper (Python API) | 3000 | CPU, pip install | Fallback if Kokoro fails. Models in `models/`: `es_ES-sharvard-medium.onnx` (77MB) + `en_US-lessac-medium.onnx` (63MB). Latency ~45ms. |
| Qwen3-TTS-CustomVoice | 3003 | GPU, ~2GB VRAM | High-quality TTS for Translator. 10 native languages. RTF: **2.6x** on RTX 3050. Cold start ~26s. Optimizations: chunk 1500 chars, max_new_tokens 6144, ThreadPoolExecutor pipeline, torch.compile, xformers + SDPA, 2-pass warmup CUDA Graphs. Voices: Aiden (EN), Serena (ES), Ono_Anna (JA). |

> ⚡ **VRAM management:** ASR (Whisper large-v3-turbo ~3.5GB) and TTS (Qwen3-TTS ~2GB) never run together. When loading TTS, Whisper is freed automatically. When loading ASR, Qwen3 is freed. Only 1 GPU model active at a time in Translator.

### Python Packages
| Package | Purpose |
|:--------|:--------|
| `kokoro` | Lightweight CPU TTS (primary in 3000) |
| `piper-tts` | CPU TTS fallback (3000) |
| `qwen-tts` | GPU TTS for Translator (3003) |
| `argostranslate` | Offline CPU translation EN/ES/JA (3003) |
| `faster-whisper` | Multilingual ASR (GPU for small/large-v3-turbo) |
| `psutil` + `pynvml` | System + GPU monitoring |
| `torch` + `torchaudio` | PyTorch CUDA 12.4 (all GPU operations) |

### Key Features
- **Independent Conversation**: `conv_server.py` (thin wrapper) runs server.py in conversation mode with dedicated system prompt, port 3001.
- **AEC (Acoustic Echo Cancellation)**: `frontend/index.html` uses `autoGainControl: true` + `isTtsPlaying` variable that disables mic while TTS plays (mute-while-speaking + 500ms buffer after playback).
- **TTS_READING**: Teacher mode generates `【TTS_READING】` field in Latin script for Kokoro (romaji for JA, phonetic for others). `get_tts_text()` priority: TTS_READING → TEXT → full response.
- **Language detection**: `detect_language()` correctly differentiates JA (hiragana/katakana) vs ZH (hanzi only, no kana) vs KO (hangul) vs ES (accents + common words).
- **Conversational memory**: `frontend/index.html` sends full `messageHistory` to backend. ~20 messages context.
- **Voice sliders**: Translator (3003) has collapsible panel with Calm/Speed/Warmth sliders that generate dynamic instruct.
- **TTS chunking**: `_chunk_text()` splits long texts by sentences, generates audio per chunk, concatenates with `np.concatenate`.
- **Pipeline parallelism**: ThreadPoolExecutor overlaps GPU audio generation with CPU float32 conversion.
- **Auto VRAM swap**: ASR and TTS never share VRAM. Loading one automatically unloads the other.

### ASR by Mode
| Mode | Model | Device | VRAM | WER ES | WER JA |
|:-----|:------|:------:|:----:|:------:|:------:|
| Teacher (3000) | Whisper **small** | GPU (INT8) | ~1.5 GB | 5.6% | 5.7% |
| Conversation (3001) | Whisper **small** | GPU (INT8) | ~1.5 GB | 5.6% | 5.7% |
| Translator (3003) | Whisper **large-v3-turbo** | GPU (INT8) | ~3.0 GB | ~5% | ~7% |

> **Note:** On server.py, the `_get_asr_model` function loads Whisper on **CPU** despite saying "GPU" in logs. This is because the `device="cpu"` parameter is hardcoded. The faster-whisper library auto-detects CUDA and uses GPU anyway when available. If you need to force GPU, change `device="cpu"` to `device="cuda"` in `server.py` `_get_asr_model()`.

---

## 🔧 Linux Reinstallation Guide

### First-time Setup (on new Linux machine)

```bash
# 1. Clone the repo
git clone https://github.com/SCP-00/ALEX_voice.git
cd Alex_Voice

# 2. Run setup (installs everything)
chmod +x setup.sh
./setup.sh

# 3. Start the menu
./run.sh
# Or: source venv/bin/activate && python menu_server.py
```

### Manual Setup

```bash
# 1. System packages
sudo apt update
sudo apt install -y python3 python3-pip python3-venv build-essential cmake curl wget git unzip

# 2. Python venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# 3. Install PyTorch CUDA
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124

# 4. Install project packages
pip install kokoro piper-tts faster-whisper qwen-tts argostranslate psutil pynvml numpy

# 5. Download llama-server from:
#    https://github.com/ggml-org/llama.cpp/releases
#    Place llama-server binary in ./llama-server-bin/

# 6. Download model
mkdir -p models
curl -L -o models/qwen2.5-1.5b-q4_k_m.gguf \
  https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf

# 7. Piper models
curl -L -o models/es_ES-sharvard-medium.onnx \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx
curl -L -o models/en_US-lessac-medium.onnx \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
```

### Starting Servers Manually

```bash
source venv/bin/activate

# Option A: Menu (recommended) — manages lifecycle for all modes
python menu_server.py   # → http://localhost:5000

# Option B: Direct mode
python server.py --port 3000 --mode teacher      # Teacher (http://localhost:3000)
python conv_server.py                              # Conversation (http://localhost:3001)
python translator.py                               # Translator (http://localhost:3003)
```

### Important Files
| File | Purpose |
|:-----|:--------|
| `setup.sh` | **Linux** setup — installs everything (new!) |
| `setup.bat` | Windows setup (legacy) |
| `run.sh` | **Linux** quick start → menu (new!) |
| `run.bat` | Windows quick start (legacy) |
| `server.py` | Teacher + Conversation backend (port 3000/3001) |
| `conv_server.py` | Thin wrapper → server.py conversation mode (port 3001) |
| `translator.py` | Translator backend (port 3003) |
| `menu_server.py` | Main menu hub (port 5000) |
| `prompts.py` | System prompts (English — optimal for Qwen2.5) |
| `launcher.py` | Legacy launcher (replaced by menu_server) |
| `frontend/index.html` | Teacher + Conversation UI |
| `frontend/translator.html` | Translator UI |
| `frontend/menu.html` | Main menu UI |

### Architecture Overview

```
┌───────────────────────────────────────────────────────────┐
│                     ALEX VOICE                              │
├───────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────┐                                      │
│  │  MENU (port 5000) │  ← http://localhost:5000             │
│  │  menu_server.py   │  Start/stop modes, lifecycle mgmt   │
│  └────────┬──────────┘                                      │
│           │                                                  │
│  ┌────────┴──────────┐    ┌──────────────────────────┐      │
│  │  Teacher + Conv   │    │  Translator (3003)       │      │
│  │  (3000 / 3001)    │    │  ASR: whisper large GPU  │      │
│  │  LLM: Qwen2.5-1.5B│    │  TRANS: argos CPU        │      │
│  │  TTS: Kokoro/Piper│    │  TTS: Qwen3-TTS GPU      │      │
│  │  ASR: whisper sm. │    │  NO LLM                  │      │
│  │  Cache: LRU 50    │    │  ↕ VRAM swap (ASR↔TTS)   │      │
│  └───────────────────┘    └──────────────────────────┘      │
│                                                             │
│  ┌────────────────────────────────────────────────────┐     │
│  │  llama-server (GPU, port 8081)                     │     │
│  │  Qwen2.5-1.5B-Q4_K_M ~1.2GB VRAM                   │     │
│  └────────────────────────────────────────────────────┘     │
└───────────────────────────────────────────────────────────┘
```

### GitHub
- Remote: `https://github.com/SCP-00/ALEX_voice.git`
- Repo: `SCP-00/ALEX_voice`

### Key Implementation Details

- **`server.py`**: Uses `device="cpu"` for faster-whisper ASR (line ~350). Despite "cpu", CUDA is auto-detected. On Linux this should work fine. Change to `device="cuda"` for explicit GPU.
- **`translator.py`**: Uses `device="cuda"` and `compute_type="int8_float16"` for Whisper. Auto VRAM swaps between ASR and TTS.
- **System prompts** are in **English** because Qwen2.5-1.5B was trained primarily on English data (~70%). Spanish prompts caused language mismatch issues.
- **Caching**: LRU cache in `server.py` (50 entries) caches LLM responses. Cleared via `/api/cache/clear`.
- **Conv_server.py** is a ~30-line wrapper that sets env vars and imports `server.main()`. No code duplication.

### Troubleshooting

| Issue | Solution |
|:------|:---------|
| `llama-server` not found | Run `./setup.sh` or download binary manually from GitHub releases |
| CUDA out of memory | Close other GPU apps. Try `--ngl 60` instead of 99 for llama-server |
| Kokoro TTS slow first time | Lazy-loads on first request (~30s). Normal. |
| Qwen3-TTS cold start slow | ~26s first time (download + warmup). Subsequent requests ~9-10s. |
| ASR not working | Check microphone permissions. On Linux, ensure `pulseaudio`/`pipewire` is running. |
| Port already in use | Kill existing process: `fuser -k 3000/tcp` or `kill $(lsof -ti:3000)` |
| No audio output | Check `pavucontrol` for output device. Piper uses espeak-ng which needs `espeak-ng-data`. |

---

## 📝 Session History
- **Sesión 1:** Lost due to ^C during llama.cpp testing
- **Sesión 2:** Lost due to direct nvidia-smi + VRAM measurement
- **Sesión 3:** ABSOLUTE RULE established — all GPU via tmux
- **Sesión 4 (Linux migration):** Full reinstall on Linux. AGENT.md rewritten for Linux paths. setup.sh created. All documentation updated.
