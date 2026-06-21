# 🛡️ Alex Voice — AI Agent Guide (v3.3.1)

## Critical Rules

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

### Hardware
| Component | Spec |
|-----------|------|
| GPU | NVIDIA RTX 3050 Laptop 6GB (5.28 GB usable VRAM, CC 8.6) |
| CPU | Intel Core i5-13420H (8C/12T) |
| RAM | 16.5 GB |
| Disk | ~258 GB free |
| CUDA Driver | 610.47 (CUDA 13.3, compatible with PyTorch CUDA 12.4) |

### Architecture v3 (June 2026) — Ollama API + prometheus-orchestrator

```
┌───────────────────────────────────────────────────────────┐
│                     ALEX VOICE v3                           │
├───────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────┐                                      │
│  │  MENU (port 5000) │  ← http://localhost:5000             │
│  │  menu_server.py   │  Start/stop modes via Ollama API     │
│  └────────┬──────────┘                                      │
│           │                                                  │
│  ┌────────┴──────────┐    ┌──────────────────────────┐      │
│  │  Teacher + Conv   │    │  Translator (3003)       │      │
│  │  (3000 / 3001)    │    │  ASR: whisper small GPU  │      │
│  │  LLM: Ollama API  │    │  VAD: Silero CPU         │      │
│  │  TTS: Kokoro ONNX │    │  TRANS: MarianMT (GPU)   │      │
│  │  ASR: whisper sm. │    │  TTS: Kokoro ONNX CPU    │      │
│  │  VAD: Silero CPU  │    │  Pipeline: async 3-thrd  │      │
│  │  Cache: LRU 50    │    │  NO LLM (ligero)         │      │
│  └────────┬──────────┘    └──────────────────────────┘      │
│           │                                                  │
│  ┌────────┴──────────────────────────────────────────┐      │
│  │  Ollama API (localhost:11434/v1)                   │      │
│  │  Model: prometheus-orchestrator (Qwen3.5 4B Ins)  │      │
│  │  262K ctx, reasoning_format:none, ~3GB VRAM       │      │
│  │  Cleanup: keep_alive:0 → offload from VRAM        │      │
│  └───────────────────────────────────────────────────┘      │
└───────────────────────────────────────────────────────────┘
```

### Servers
| Port | Service | Script | LLM Backend |
|:----:|:--------|:-------|:------------|
| 5000 | Menu | `menu_server.py` | Ollama API (start/stop + cleanup) |
| 3000 | Teacher | `server.py` (mode=teacher) | Ollama API → prometheus-orchestrator |
| 3001 | Conversation | `conv_server.py` → server.py | Ollama API → prometheus-orchestrator |
| 3003 | Translator | `translator.py` | Sin LLM (ASR→MarianMT→Kokoro ONNX) |

### Main Model
| Model | Backend | VRAM | Context | Thinking |
|-------|:-------:|:----:|:-------:|:--------:|
| **prometheus-orchestrator** 🏆 | **Ollama API**:11434/v1 | ~3.0 GB | **262K** | **❌ Desactivado** (`reasoning_format: none`) |
| (Qwen3.5 4B Instruct, IQ4_XS, 4.3B params) | | | | |

### Benchmarks (prometheus-orchestrator vs old qwen2.5-coder:3b)
| Idioma | coder:3b | orchestrator (v3) | Mejora |
|:-------|:--------:|:-----------------:|:------:|
| **EN** | 14.9 tok/s | **39.0 tok/s** | 2.6x |
| **ES** | ❌ Alucinó | **45.4 tok/s** ✅ | 🔥 |
| **JA** | ❌ Self-intro | **45.2 tok/s** ✅ | 🔥 |
| **Contexto** | 32K | **262K** | 8x |

### Key Changes v2→v3
- **LLM Backend:** llama-server directo (GGUF) → **Ollama API** (OpenAI-compatible)
- **Modelo:** Qwen2.5-3B-Instruct GGUF → **prometheus-orchestrator** (Qwen3.5 4B) via Ollama
- **Thinking:** No disponible → **Desactivado** (`reasoning_format: none`)
- **menu_server.py:** Eliminado find_llama/find_model/start_llama → `check_ollama_alive()` + cleanup via API
- **translator.py:** HTTP server ahora arranca ANTES de cargar modelos (no más HTML vacío en port 3003)
- **launcher:** run.sh → alex_voice_app.sh que verifica Ollama + offload via API

### TTS (All CPU, 0 VRAM)
| Engine | Detail |
|:-------|:-------|
| **Kokoro ONNX** 🏆 | Primary. 54 voices, 5 languages (ES/EN/JA/FR/DE). Singleton lazy-load. |
| **Piper** | Fallback. ES + EN models. Latency ~45ms. |

### Translation
| Engine | Type | Detail |
|:-------|:-----|:-------|
| **Helsinki-NLP Opus-MT** 🏆 | GPU, ~100ms | Via transformers MarianMT. EN↔ES, EN→JA, JA→EN, JA→ES (pivot). |

### Python Packages
| Package | Purpose |
|:--------|:--------|
| `kokoro-onnx` | CPU TTS (54 voices, 5 langs) |
| `piper-tts` | CPU TTS fallback |
| `transformers` | MarianMT translation |
| `silero-vad` | VAD pre-filter for ASR |
| `cutlet` | Japanese romanization |
| `faster-whisper` | Multilingual ASR (GPU) |
| `psutil` + `pynvml` | System + GPU monitoring |
| `torch` | PyTorch CUDA 12.4 |

### VRAM Budget (v3)
| Mode | Components | VRAM |
|:-----|:-----------|:----:|
| Teacher | Ollama (~3.0GB) + Whisper ~1.5GB | **~4.5 GB** |
| Conversation | Ollama (~3.0GB) + Whisper ~1.5GB | **~4.5 GB** |
| Translator | Whisper ~1.5GB + MarianMT ~0.2GB | **~1.7 GB** |

---

## 🔧 Linux Reinstallation Guide

### First-time Setup

```bash
# 1. Clone the repo
git clone https://github.com/SCP-00/ALEX_voice.git
cd Alex_Voice
git checkout linux

# 2. Run setup
chmod +x setup.sh
./setup.sh

# 3. Ensure Ollama has the model
ollama pull prometheus-orchestrator

# 4. Start the launcher
./alex_voice_app.sh
# Or: source venv/bin/activate && python menu_server.py
```

### Starting Servers
```bash
source venv/bin/activate

# Option A: Launcher (recommended)
./alex_voice_app.sh                      # Verifica Ollama → http://localhost:5000

# Option B: Direct menu
python menu_server.py                # → http://localhost:5000

# Option C: Direct mode
python server.py --port 3000 --mode teacher        # Teacher
python conv_server.py                                # Conversation
python translator.py                                 # Translator
```

### GitHub
- Remote: `https://github.com/SCP-00/ALEX_voice.git`
- Branch: `linux`
- Repo: `SCP-00/ALEX_voice`

### Troubleshooting
| Issue | Solution |
|:------|:---------|
| Ollama not found | Install: `curl -fsSL https://ollama.com/install.sh | sh` |
| Model not found | `ollama pull prometheus-orchestrator` |
| CUDA OOM | Close other GPU apps. Check `ollama ps` for loaded models. |
| Port in use | `fuser -k 5000/tcp` or `kill $(lsof -ti:5000)` |
| Translation fails | `rm -rf ~/.cache/huggingface/hub/` → re-downloads |

### Session History
- **Sesión 7 (v3 Ollama migration):** Replaced direct llama-server with Ollama API. Switched from qwen2.5-coder:3b to prometheus-orchestrator (Qwen3.5 4B instruct). Disabled thinking mode. Fixed translator.py startup (async model loading). Benchmarks: 43 tok/s avg, correct JA/ES/EN.
