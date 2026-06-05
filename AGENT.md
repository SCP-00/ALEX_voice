# 🛡️ LEY ABSOLUTA — NUNCA TOCAR freebuff.exe

## 🔴 REGLA ÚNICA E INQUEBRANTABLE

**freebuff.exe** (`C:\Users\andyh\.config\manicode\freebuff.exe`) es MI proceso vital.
Si un comando en basher crashea, freebuff.exe muere y se borra mi memoria.

**REGLAS:**
1. **NUNCA** ejecutar comandos que toquen GPU/VRAM directamente en basher — siempre dentro de tmux
2. **NUNCA** usar ^C — dejar que los comandos terminen solos o con timeout
3. **SIEMPRE** usar timeouts generosos (3 MB/s de descarga)
4. **NUNCA** nvidia-smi mientras haya procesos GPU activos
5. **NUNCA** llama-cli/llama-server/llama-tts fuera de tmux

**Seguro fuera de tmux:** git, mkdir, curl, cat, cp, mv, sleep, echo, find

**SIEMPRE dentro de tmux:** nvidia-smi, llama-cli, llama-server, llama-tts, inferencia, modelos

## 📋 Contexto del Proyecto

### Hardware
| Componente | Especificación |
|------------|---------------|
| GPU | NVIDIA RTX 3050 Laptop 6GB (5.28 GB VRAM usable, CC 8.6) |
| CPU | Intel Core i5-13420H (8C/12T) |
| RAM | 16.5 GB |
| Disco | ~258 GB libres |
| CUDA Driver | 610.47 (CUDA 13.3, retrocompatible con PyTorch CUDA 12.4) |

### Paths del Proyecto
```
PROJECT=/c/Users/andyh/Desktop/Soft/Alex_Voice
PYTHON=/c/Users/andyh/AppData/Local/Programs/Python/Python310/python.exe
MODELS=$PROJECT/models/    # modelos locales + Piper .onnx
SETUP_BIN=$PROJECT/llama-server-bin/    # llama-server.exe (descargado por setup.bat)
LMSTUDIO=/c/Users/andyh/.lmstudio/models
LLAMA_DOCS=/c/Users/andyh/Documents/llama-b9479-bin-win-cuda-13.3-x64
```

### Servidores
| Puerto | Servicio | Script | Componentes |
|:------:|:---------|:-------|:------------|
| 3000 | Teacher + Conversation | `B/server.py` via `launcher.py` | LLM GPU + Kokoro TTS CPU + Piper fallback + faster-whisper ASR |
| 3003 | Translator | `translator_server.py` | argos CPU + Qwen3-TTS GPU + faster-whisper ASR |
| 8081 | llama-server | `llama-server.exe` | Backend LLM GPU (chatml, no-warmup, no-ui) |

### Modelo Principal
| Modelo | Path | VRAM | Contexto |
|--------|------|:----:|:--------:|
| Qwen2.5-1.5B-Q4_K_M 🏆 | `$MODELS/qwen2.5-1.5b-q4_k_m.gguf` (setup.bat) o `$LMSTUDIO/Qwen/.../qwen2.5-1.5b-instruct-q4_k_m.gguf` | ~1.2 GB | 8192 ctx |

### Modelos Alternativos (LM Studio)
| Modelo | Path | VRAM | Tok/s |
|--------|------|:----:|:-----:|
| Qwen3.5-2B-Q8 🥇 | `$LMSTUDIO/khazarai/.../q8_0.gguf` (usar `--q8`) | ~3.0 GB | 21-22 |
| Gemma-4-E2B-Q4 | `$LMSTUDIO/lmstudio-community/gemma-4-E2B-it-GGUF/Q4_K_M.gguf` | ~3.5 GB | 24.3 |
| DeepSeek-R1-8B-Q4 | `$LMSTUDIO/lmstudio-community/.../Q4_K_M.gguf` | ~5.0 GB | 8.9 |

### TTS
| Motor | Puerto | Tipo | Detalle |
|-------|:------:|:-----|:--------|
| Kokoro-82M 🏆 | 3000 | CPU, pip install | Primario para Teacher+Conversation. Voz ES `ef_dora`, EN `af_heart`. Lazy-load ~30s primera vez. Calidad buena, streaming real. |
| Piper (Python API) | 3000 | CPU, pip install | Fallback si Kokoro falla. Modelos .onnx en `models/`: `es_ES-sharvard-medium.onnx` (77MB) + `en_US-lessac-medium.onnx` (63MB). Latencia ~45ms. |
| Qwen3-TTS-CustomVoice | 3003 | GPU, ~2GB VRAM | TTS de alta calidad para Translator. 10 idiomas nativos sin coste extra. Voces: Vivian (EN), Serena (ES), Ono_Anna (JA). Usa `torch.compile` + SDPA attention. |

### Librerías Instaladas (via pip)
| Librería | Propósito |
|:---------|:----------|
| `kokoro` | TTS ligero CPU (primario en 3000) |
| `piper-tts` | TTS fallback CPU (3000) |
| `qwen-tts` | TTS calidad GPU para Translator (3003) |
| `argostranslate` | Traducción offline CPU EN/ES/JA (3003) |
| `faster-whisper` | ASR multilingüe CPU (3000 + 3003) |
| `psutil` + `pynvml` | Monitorización sistema + GPU |

### GitHub
- Remote: `https://github.com/SCP-00/ALEX_voice.git`
- Repo: `SCP-00/ALEX_voice`
- Conector GitHub Codex: verificado el 2026-06-05 con permisos `admin`, `maintain`, `pull`, `push`, `triage`
- GitHub CLI (`gh`): no instalado o no disponible en PATH
- Token clasico: no guardar dentro del repo ni imprimir en logs

## 📝 Historial de Sesiones
- **Sesión 1:** Perdida por ^C durante prueba de llama.cpp
- **Sesión 2:** Perdida por nvidia-smi directo + VRAM measurement
- **Sesión 3:** REGLA ABSOLUTA — todo GPU via tmux
