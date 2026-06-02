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
| GPU | NVIDIA RTX 3050 Laptop 6GB (5.28 GB VRAM usable) |
| CPU | Intel Core i5-13420H (8C/12T) |
| RAM | 16.5 GB |
| Disco | ~258 GB libres |

### Paths del Proyecto
```
PROJECT=/c/Users/andyh/Desktop/Soft/Alex_Voice
BIN=$PROJECT/bin/          # binarios descargados (whisper, piper, etc.)
MODELS=$PROJECT/models/    # modelos locales
LLAMA=/c/Users/andyh/Documents/llama-b9479-bin-win-cuda-13.3-x64
LMSTUDIO=/c/Users/andyh/.lmstudio/models
```

### Modelos Disponibles
| Modelo | Path | VRAM | Tok/s |
|--------|------|:----:|:-----:|
| Qwen3.5-2B-Q8 🥇 | `$LMSTUDIO/khazarai/.../q8_0.gguf` | ~3.0 GB | 21-22 |
| Gemma-4-E2B-Q4 | `$LMSTUDIO/lmstudio-community/gemma-4-E2B-it-GGUF/Q4_K_M.gguf` | ~3.5 GB | 24.3 |
| DeepSeek-R1-8B-Q4 | `$LMSTUDIO/lmstudio-community/.../Q4_K_M.gguf` | ~5.0 GB | 8.9 |

### TTS Descargados
| Motor | Estado | Archivo |
|-------|--------|---------|
| OuteTTS-500M | ✅ Descargado (bug llama-tts.exe) | `$PROJECT/llama-models/OuteTTS-0.2-500M-Q4_K_M.gguf` |
| Piper TTS | ❌ Pendiente de descargar | — |
| whisper.cpp | ❌ Pendiente de descargar | — |

### GitHub
- Token: configurado en conversación
- Remote: pendiente de añadir
- Repo: pendiente de crear en GitHub

## 📝 Historial de Sesiones
- **Sesión 1:** Perdida por ^C durante prueba de llama.cpp
- **Sesión 2:** Perdida por nvidia-smi directo + VRAM measurement
- **Sesión 3:** REGLA ABSOLUTA — todo GPU via tmux
