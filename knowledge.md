# Alex Voice — Project Knowledge

## What This Is
AI voice assistant running **100% locally** on GPU. 3 specialized modes:
- **Teacher** (port 3000) — language tutoring with structured multi-output
- **Conversation** (port 3001) — natural chat with memory
- **Translator** (port 3003) — speech→translation→TTS pipeline
- **Menu hub** (port 5000) — lifecycle management for all modes

**GPU:** NVIDIA RTX 3050 6GB (5.79 GB usable VRAM on Linux)  
**LLM:** Qwen2.5-1.5B Q4_K_M (~1.2 GB VRAM) via llama-server  
**Author:** SCP-076 · Coded by Buffy (AI Agent on Codebuff.com)

---

## Where Key Code Lives

| File | Purpose |
|------|---------|
| `server.py` | Teacher + Conversation backend (LLM GPU + Kokoro TTS CPU + Whisper ASR GPU) |
| `translator.py` | Translator backend (Whisper GPU + argos CPU + Qwen3-TTS GPU) |
| `menu_server.py` | Menu hub — start/stop modes, backend detection |
| `prompts.py` | System prompts (English only!) + multi-output parsing |
| `launcher.py` | Legacy launcher (replaced by menu_server) |
| `conv_server.py` | Thin wrapper (~30 lines) → server.py in conversation mode |
| `setup.sh` | Linux setup script (CUDA→Vulkan→CPU build, models, venv) |
| `frontend/index.html` | Teacher + Conversation UI |
| `frontend/menu.html` | Main menu UI |
| `frontend/translator.html` | Translator UI |
| `models/` | GGUF model + Piper ONNX files |
| `llama-server-bin/` | llama-server binaries (CPU, Vulkan, shared libs) |

### Backend Detection Priority
`llama-server-cuda` (CUDA) → `llama-server-vulkan` (Vulkan) → `llama-server` (CPU)  
Both `launcher.py` and `menu_server.py` have this logic.

---

## Commands

### Setup (first time on Linux)
```bash
./setup.sh    # Installs everything: system deps, venv, models, llama-server
```

### Run (dev/use)
```bash
# Menu hub (recommended) — manages lifecycle
python3 menu_server.py              # → http://localhost:5000

# Direct mode
python3 server.py --port 3000 --mode teacher       # Teacher
python3 conv_server.py                             # Conversation (port 3001)
python3 translator.py                              # Translator (port 3003)

# Legacy launcher
./launcher.py
```

### Desktop launchers
```bash
~/Desktop/Voice_chat/alex-voice-home.sh      # Menu (port 5000)
~/Desktop/Voice_chat/alex-voice-teacher.sh   # Teacher (port 3000)
~/Desktop/Voice_chat/alex-voice-chat.sh      # Conversation (port 3001)
~/Desktop/Voice_chat/alex-voice-translate.sh # Translator (port 3003)
```

### Test
Manual testing via API endpoints (no test framework):
```bash
# Check llama-server
curl http://localhost:8081/health

# Chat
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"mode":"teacher","text":"Hello","target_lang":"es"}'

# Stats
curl http://localhost:3000/api/stats
```

### Build llama-server
```bash
cd llama.cpp && mkdir build && cd build
cmake .. -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release
make -j$(nproc) llama-server
cp bin/llama-server ~/Alex_Voice/llama-server-bin/llama-server-vulkan
```

---

## Conventions & Patterns

### Language
- **All system prompts in English** — Qwen2.5-1.5B was trained ~70% on English data. Spanish prompts cause language mismatch.
- **Multi-output format** — Teacher/Translator use structured format:
  `【TEXT】` `【TTS_READING】` `【PRONUNCIATION】` `【TRANSLATION】` `【EXPLANATION】` `【EXERCISE】`
- **TTS priority**: `【TTS_READING】` → `【TEXT】` → full response
- **Conversation** must respond in same language as user input

### TTS Strategy
1. **Kokoro-82M** (CPU, primary) — Latin script only, RTF 0.24x
2. **Piper Python API** (CPU, fallback) — ~45ms latency
3. **Piper subprocess** (last resort)
- Sanitizer removes non-Latin characters (CJK etc.) before TTS

### GPU/VRAM Management
- **llama-server** always on GPU (Vulkan/CUDA), ~1.2 GB VRAM
- **Translator**: ASR (Whisper large-v3-turbo ~3.5 GB) and TTS (Qwen3-TTS ~2 GB) **never share VRAM** — auto-swap via `_unload_asr()` / `_unload_qwen3()`
- **Teacher/Conversation**: Whisper small stays on GPU (~1.5 GB)

### Caching
- LRU cache (50 entries) in `server.py` — caches LLM responses
- Cache cleared via `/api/cache/clear`

---

## Gotchas & Constraints

### ⚠️ ABSOLUTE RULE — GPU in tmux
On Linux, `nvidia-smi`, `llama-server`, and any GPU inference **MUST** run inside `tmux`. Running directly in basher can crash the CLI process. Never use ^C — let commands finish naturally.

### CUDA + Kali Linux
CUDA 12.4 is **incompatible** with glibc 2.41 (Kali 2026.2). Use **Vulkan backend** instead.  
`llama-server-vulkan` gives **49.0 tok/s** (+17% vs CPU at 41.9 tok/s, 24% lower latency).  
If a new CUDA runfile (≥12.6, ~4 GB) becomes available, it may work.

### Kokoro TTS Limitations
- Only supports Latin script + Spanish extensions
- CJK, Arabic, Cyrillic characters cause "Caracter japones" error
- First load is lazy (~30s)
- Voice mapping: ES→`ef_dora`, EN→`af_heart`

### Whisper ASR Device
`server.py` uses `device="cpu"` in `_get_asr_model()` but auto-detects CUDA anyway. To force GPU, change to `device="cuda"` in that function.

### Qwen3-TTS Performance
- Cold start: ~26s (download + 2-pass warmup)
- Warm: ~9-10s for short text
- Chunk size: 1500 chars (reduces invocation overhead)
- `flash-attn` not yet installed (would give 2-3x speedup)
- Pipeline parallelism: GPU generates while CPU serializes previous chunk

### Python
- Python 3.13.12 on Kali
- Virtual environment in `venv/`
- Key packages: `kokoro`, `piper-tts`, `faster-whisper`, `qwen-tts`, `argostranslate`
- `pynvml` replaced `nvidia-ml-py` to avoid FutureWarning

### Ports
| Port | Service | Notes |
|:----:|:--------|:------|
| 5000 | Menu hub | Lifecycle manager |
| 3000 | Teacher | Shares llama-server with Conversation |
| 3001 | Conversation | Thin wrapper via conv_server.py |
| 3003 | Translator | Independent server |
| 8081 | llama-server | Shared LLM backend |
