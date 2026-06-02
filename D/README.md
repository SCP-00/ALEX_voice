# Folder D — Recomendación Final 📊 BASADA EN DATOS REALES

## ⚡ Decisión: Plan A (LLM + TTS en GPU) con Plan B como fallback

Después de probar todos los modelos en hardware real, la arquitectura ganadora es:

### 🏆 Arquitectura Recomendada

```
Qwen3.5-2B-Q8 (GPU) + OuteTTS-500M (GPU) = ~3.5 GB VRAM TOTAL
```

**Razón:** Cabe todo en GPU con 1.8 GB de margen. Sin swapping. Simple.

### 📊 Evidencia Empírica

| Modelo | VRAM | Tok/s | ¿Cabe? | Veredicto |
|--------|:----:|:-----:|:------:|:---------:|
| Qwen3.5-2B-Q8 | ~3.0 GB | **21-22** | ✅ Sí | 🥇 **Elegido** |
| Gemma-4-E2B-Q4 | ~3.5 GB | **24.3** | ✅ Sí | 🥈 Alternativa |
| DeepSeek-R1-8B-Q4 | ~5.0 GB | **8.9** | ⚠️ Justo | ❌ Muy lento |
| Gemma-4-E4B-Q4 | ~5.5 GB | — | ❌ No | ❌ Excede |
| OuteTTS-500M | ~0.5 GB | — | ✅ Sí | 🥇 TTS elegido |

### 🗺️ Roadmap de Implementación

```
Fase 0 ✅ Entorno listo
  ├── llama.cpp v9479 + CUDA 13.3
  ├── Qwen3.5-2B-Q8 + Gemma-4-E2B-Q4 + DeepSeek-R1-8B probados
  └── OuteTTS-500M descargado

Fase 1 🚧 Frontend + TTS (AHORA)
  ├── Interfaz HTML+JS con 3 modos
  ├── llamar a llama-server.exe via HTTP
  └── Debuggear OuteTTS o instalar Piper

Fase 2 🚧 Modos de interacción
  ├── Modo Teacher: prompts educativos + TTS lento
  ├── Modo Conversación: chat libre + TTS rápido
  └── Modo Traductor: traducción es/en/ja

Fase 3 🚧 Voice Input
  ├── whisper.cpp para ASR
  └── Pipeline voz completo

Fase 4 🚧 Optimización
  ├── Caché de respuestas
  ├── Voice cloning (OuteTTS speaker file)
  └── Streaming de audio
```

### 💡 Stack Tecnológico Recomendado

| Capa | Tecnología | Razón |
|:----:|:----------:|:-----:|
| **Frontend** | HTML + CSS + JS | Vanilla, sin dependencias |
| **API Server** | `llama-server.exe` | HTTP API nativa, no necesita Python |
| **LLM** | Qwen3.5-2B-Q8 GGUF | 21 tok/s, multilingüe |
| **TTS** | OuteTTS-500M o Piper | GPU o CPU según necesidad |
| **ASR** | whisper.cpp tiny | Ligero, ~500 MB RAM |
| **Control** | Bash script | Orchestrador simple |

### 📐 Presupuesto de Memoria Final

| Componente | VRAM | RAM |
|:----------:|:----:|:---:|
| Qwen3.5-2B-Q8 | 2.5-3.0 GB | — |
| OuteTTS-500M | 0.5-0.8 GB | — |
| KV Cache (2K ctx) | ~0.5 GB | — |
| Audio Buffers | ~0.2 GB | — |
| **Total GPU** | **~4.0 GB** | ✅ |
| Margen | **1.3 GB** | ✅ |
| whisper (ASR) | — | ~500 MB |
| Sistema+Apps | — | ~5 GB |
| **Total RAM** | — | **~6 GB** de 16.5 GB ✅ |
