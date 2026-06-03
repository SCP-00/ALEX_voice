# Folder D — Recomendación Final 📊 BASADA EN DATOS REALES

## ⚡ Decisión: Plan A — LLM (GPU) + TTS (CPU Python API ~45ms)

Después de probar todas las opciones en hardware real, la arquitectura ganadora es:

### 🏆 Arquitectura en Producción

```
start_server.bat
├── llama-server (Qwen3.5-2B-Q8, GPU, puerto 8081, 21-22 tok/s)
└── python server.py (Monitor, CPU, puerto 3000)
    ├── /api/chat → llama-server
    ├── /api/tts-piper → Piper Python API (~45ms, CPU)
    ├── /api/asr → faster-whisper (CPU, ~300ms) ✅
    ├── /api/stats → GPU/CPU/RAM en vivo
    ├── /api/logs → Logging enriquecido
    └── /debug → UI de depuración
```

### 📊 Evidencia Empírica

| Componente | Opción Elegida | Alternativa | Razón |
|:-----------|:--------------|:------------|:------|
| **LLM** | Qwen3.5-2B-Q8 (21 tok/s, ~3 GB) | Gemma-4-E2B-Q4 (24 tok/s, ~3.5 GB) | Qwen consume menos VRAM, dejando margen |
| **TTS** | **Piper Python API** (~45ms, CPU) 🥇 | OuteTTS GPU (~13s) ❌ | **40-50x más rápido**, mismo modelo de voz |
| **Monitor** | python server.py | — | Stats, logs, debug en un solo proceso |
| **ASR** | faster-whisper tiny (CPU ~300ms) | ✅ |

### 🗺️ Roadmap de Implementación

```text
Fase 0 ✅ Entorno listo
  ├── llama-server + Qwen3.5-2B-Q8 (21 tok/s)
  ├── Piper Python API (~45ms TTS)
  ├── server.py (monitor, proxy, stats, logs)
  ├── start_server.bat (inicio con un clic)
  └── debug.html (4 tabs de monitoreo)

Fase 1 ✅ Frontend + TTS (COMPLETADO)
  ├── Interfaz Plan A (HTML+JS, 3 modos)
  ├── TTS multilingüe (ES/EN/JA)
  ├── Split automático por idioma
  └── Chat streaming

Fase 2 ✅ Modos de interacción (COMPLETADO)
  ├── Modo Teacher: prompts educativos
  ├── Modo Conversación: chat libre
  └── 🚧 Modo Traductor: ES/EN/JA

Fase 3 ✅ Voice Input (COMPLETADO)
  ├── faster-whisper tiny (CPU, ~300ms)
  ├── Pipeline: Audio → ASR → LLM → TTS
  └── Micrófono en frontend (Chrome ASR + Whisper ASR)

Fase 4 📋 Optimización
  ├── Caché de respuestas
  ├── Streaming de audio TTS
  └── Voice cloning (OuteTTS speaker file)
```

### 💡 Stack Tecnológico Final

| Capa | Tecnología | Versión |
|:----:|:----------:|:--------|
| **Frontend** | HTML + CSS + JS | Vanilla, 3 modos, debug UI |
| **LLM Server** | `llama-server.exe` | v9479, CUDA 13.3 |
| **LLM Model** | Qwen3.5-2B-Q8 GGUF | 2 GB, 21 tok/s |
| **TTS** | `piper-tts` Python API | v1.4.2, ~45ms |
| **Monitor** | `python server.py` | puerto 3000 |
| **ASR** | faster-whisper tiny (CPU ~300ms) | ✅ |
| **Logging** | `logger.py` | 2000 entradas, stats, export |
| **Startup** | `start_server.bat` | Un clic, cleanup automático |

### 📐 Presupuesto de Memoria Final

| Componente | VRAM | RAM |
|:----------:|:----:|:---:|
| Qwen3.5-2B-Q8 | ~3.0 GB | — |
| KV Cache (2K ctx) | ~0.5 GB | — |
| Piper TTS | — | ~150 MB |
| Monitor Server | — | ~100 MB |
| **Total GPU** | **~3.5 GB** de 5.28 GB ✅ |
| **Total RAM** | **~250 MB** de 16.5 GB ✅ |
| **Margen** | **~1.8 GB** | **~5.5 GB** |

### 🎯 Decisión Final

**Piper Python API (~45ms, CPU) es superior a OuteTTS (~13000ms, GPU) para TTS.**
La latencia 40-50x menor y el uso de CPU (dejando VRAM para el LLM) hacen que esta sea la combinación óptima.
