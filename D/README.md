# Plan D — La Configuración Definitiva 🏆

> **Estado:** ✅ COMPLETADO — La culminación de Alex Voice
> **Puerto:** `3003` — Independiente, con lo mejor de A+B+C + innovaciones

## 🚀 Arquitectura

```
start.bat
├── llama-server (Qwen3-2B-Q4_K_M, GPU, ~1.5 GB VRAM, 8K contexto)
│   └── Sin thinking tokens · 21-24 tok/s
└── python D/server.py (CPU, puerto 3003)
    ├── /api/chat → llama-server (streaming)
    ├── /api/tts → Kokoro-82M (primario) + Piper (fallback)
    ├── /api/tts/stream → Streaming TTS en vivo
    ├── /api/tts/clone → Qwen3-TTS voice cloning (experimental)
    ├── /api/asr → faster-whisper auto-switch
    ├── /api/stats → GPU/CPU/RAM en tiempo real
    ├── /api/cache/* → LRU 200 entradas + persistente
    └── /debug → Debug UI con 4 tabs
```

## 🏆 Por qué Plan D es el Definitivo

### 1. LLM más eficiente: Qwen3-2B-Q4_K_M
| Aspecto | Antes (Qwen3.5-2B-Q8) | Ahora (Qwen3-2B-Q4_K_M) | Mejora |
|:--------|:---------------------:|:------------------------:|:------:|
| VRAM | **~3.0 GB** | **~1.5 GB** | ✅ **50% menos** |
| Contexto | 4K | **8K** | ✅ **2x más** |
| Velocidad | 21-22 tok/s | 21-24 tok/s | ✅ similar |
| VRAM Libre | ~2.0 GB | **~3.3 GB** | ✅ **+65%** |
| Thinking | ❌ A veces | ✅ **Nunca** | ✅ |

### 2. TTS con Kokoro-82M (voz natural, CPU)
| Aspecto | Pipeline | Latencia |
|:--------|:---------|:--------:|
| 🥇 Kokoro-82M streaming | Voz natural, ~2.5x EN, 1.0x ES | ~200-300ms primer chunk |
| 🥈 Piper Python API | Fallback rápido, ~45ms | ~45ms |
| 🥉 Piper subprocess | Último recurso | ~2400ms |
| 🎙️ Qwen3-TTS (exp.) | Clonación de voz con 3s de audio | ~3-5s (CPU) |

### 3. Caché Inteligente
| Tipo | Capacidad | Persistencia |
|:-----|:---------:|:------------|
| LRU en memoria | **200** respuestas | Sesión actual |
| Disco (SQLite) | Ilimitado | **Entre sesiones** 🆕 |
| Prompt caching | Automático | Por conversación |

### 4. VRAM Libre: 3.3 GB
Con ~3.3 GB libres en GPU, podemos:
- ✅ **8K contexto** para conversaciones largas
- ✅ **Qwen3-TTS en GPU** experimental
- ✅ **Múltiples slots** en llama-server
- ✅ **Whisper ASR en GPU** (futuro)
- ✅ **Sin riesgo de OOM**

## 🎯 Modos de Interacción

### 🎓 Teacher (REDISEÑADO)
```
Formato simple que el modelo 2B sigue perfectamente:
📖 Texto original
🔤 Pronunciación
🌍 Traducción
🎯 Nivel: Principiante/Intermedio/Avanzado
💪 Ejercicio: "Traduce esta frase..."
```

### 💬 Conversación (MEJORADO)
```
- Memoria entre sesiones
- Role-playing: "Actúa como..."
- Temas con contexto enriquecido
- Detección de despedida natural
- Caché LRU para respuestas frecuentes
```

### 🌍 Traductor (REDISEÑADO)
```
- Few-shot examples en system prompt
- Modismos: "llover a cántaros" → "raining cats and dogs"
- Tono: formal / casual / neutro
- Preserva formato (listas, código)
- 10 idiomas (ES/EN/JA/KO/DE/FR/RU/PT/IT/ZH)
```

### 🎙️ Voice Cloning (NUEVO - Experimental)
```
- Qwen3-TTS: 3 segundos de audio para clonar una voz
- Perfecto para personajes o voces personalizadas
- Se ejecuta en CPU (GPU libre pero Qwen3-TTS es grande)
```

## 📊 Presupuesto de Memoria

| Componente | VRAM | RAM |
|:-----------|:----:|:---:|
| Qwen3-2B-Q4_K_M | ~1.5 GB | — |
| KV Cache (8K) | ~0.5 GB | — |
| Overhead sistema | ~0.3 GB | — |
| Kokoro TTS | — | ~150 MB |
| Piper TTS | — | ~150 MB |
| ASR (whisper) | — | ~150-500 MB |
| Monitor Server | — | ~100 MB |
| **Total GPU** | **~2.3 GB** de 5.28 GB ✅ | |
| **Total RAM** | | **~1 GB** de 16.5 GB ✅ |
| **Libre GPU** | **~3.0 GB** 🏆 | |
| **Libre RAM** | | **~5.5 GB** ✅ |

## 🔧 Cómo Usar

### 1. Requisitos
```bash
pip install faster-whisper piper-tts psutil pynvml numpy kokoro
# Opcional (voice cloning):
pip install qwen-tts torch torchaudio
```

### 2. Descargar modelo LLM optimizado
```bash
# Qwen3-2B-Instruct en Q4_K_M (~1.5 GB)
# https://huggingface.co/Qwen/Qwen3-2B-Instruct-GGUF
```

### 3. Iniciar
```bash
# Doble clic en D/start.bat — TODO automático:
# 1. llama-server con Qwen3-2B-Q4_K_M (8K contexto)
# 2. D/server.py en puerto 3003
# 3. Chrome abre http://localhost:3003
```

### 4. Endpoints
| Endpoint | Método | Descripción |
|:---------|:------:|:-----------|
| `/api/chat` | POST | Chat streaming a llama-server |
| `/api/tts` | POST | TTS Kokoro + Piper (WAV) |
| `/api/tts/stream` | POST | TTS streaming (PCM chunks) |
| `/api/tts/clone` | POST | Voice cloning (Qwen3-TTS, exp.) |
| `/api/asr` | POST | Speech-to-text |
| `/api/stats` | GET | Stats GPU/CPU/RAM |
| `/api/cache/*` | GET | Cache stats/clear |
| `/debug` | GET | Debug UI |

## 🗺️ Roadmap

### ✅ Fase 1 — Núcleo (COMPLETADA)
- D/server.py con Kokoro+Piper+Cache+EchoGuard
- Frontend plan-d con todos los modos mejorados
- System prompts con few-shot examples
- Launcher unificado D/start.bat

### 🚧 Fase 2 — Optimización
- Caché persistente a disco (SQLite)
- Prompt caching del lado del servidor
- Modo oscuro/claro

### 🚧 Fase 3 — Voice Cloning
- Integración completa Qwen3-TTS
- UI para subir/subir audio de referencia
- Persistencia de voces clonadas

### 🚧 Fase 4 — Feature Completa
- VAD adaptativo con medidor visual
- Whisper ASR en GPU (aprovechando VRAM libre)
- Streaming dual (chat + TTS simultáneo)
