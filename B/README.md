# Plan B — LLM en GPU · TTS en CPU

> **Estado:** ✅ COMPLETADO — Todas las fases implementadas
> **Puerto:** `3001` — Independiente de Plan A (puerto 3000)

## 🚀 Arquitectura

```
Usuario → Web UI (plan-b) → B/server.py (proxy) → llama-server (GPU)
                                        ↓                 ↓
                                   Piper TTS (CPU)   Qwen3.5-2B-Q8
                                   faster-whisper (CPU)
                                   Caché LRU (memoria)
```

### Componentes

| Componente | Tecnología | Latencia | Estado |
|:-----------|:-----------|:--------:|:------:|
| **LLM** | Qwen3.5-2B-Q8 (GPU, ~3.0 GB VRAM) | 21-22 tok/s | ✅ |
| **TTS** | Piper Python API (CPU, modelos en memoria) | **~45ms** | ✅ |
| **TTS Streaming** | Piper chunked transfer (CPU) | Primer chunk ~45ms | ✅ |
| **ASR** | faster-whisper base/small (CPU, auto-switch) | ~36-162ms | ✅ |
| **Caché** | LRU (50 entradas, thread-safe) | Hit: 0ms | ✅ |
| **Frontend** | plan-b/index.html (puerto 3001) | — | ✅ |

## 📊 Hardware

| Recurso | Total | Usado por B | Libre |
|:--------|:-----:|:-----------:|:-----:|
| GPU VRAM | 5.3 GB | ~3.0 GB (LLM) | ~2.3 GB |
| RAM | 16.5 GB | ~1.5 GB (TTS+ASR+server) | ~5.5 GB |
| CPU | i5-13420H 8C/12T | — | — |

## 🎯 Fases Completadas

### Fase 1 ✅ — Text Core
- [x] llama-server con Qwen3.5-2B-Q8 (GPU)
- [x] Servidor Plan B (`B/server.py`, puerto 3001)
- [x] Chat proxy a llama-server (OpenAI-compatible)
- [x] Frontend plan-b con 3 modos (Teacher/Conversación/Traductor)

### Fase 2 ✅ — CPU TTS
- [x] Piper Python API (modelos en memoria, ~45ms latencia)
- [x] Modelos ES (`es_ES-sharvard-medium`) y EN (`en_US-lessac-medium`)
- [x] Detección automática de idioma
- [x] Fallback a subprocess Piper si Python API no disponible

### Fase 3 ✅ — Voice Input
- [x] faster-whisper integrado (modelo base, CPU)
- [x] Auto-switch: base para ES/EN, small para JA
- [x] Detección de japonés en modo auto → re-ejecuta con small
- [x] Micrófono en frontend → ASR → texto → chat
- [x] Pipeline completo: Audio → ASR → LLM → TTS

### Fase 4 ✅ — Optimización (Plan B exclusivo)
- [x] **Caché LRU** de respuestas frecuentes (50 entradas, thread-safe)
- [x] **Streaming TTS** (primer chunk audible en ~45ms)
- [x] `/api/cache/stats` — monitoreo de hits/misses
- [x] `/api/cache/clear` — invalidación manual

## 🏆 Benchmark

| Escenario | Sin Caché | Con Caché | Mejora |
|:----------|:---------:|:---------:|:------:|
| Saludo ("Hola") | ~2-5s (LLM) | **0ms** (caché) | ∞ |
| Pregunta frecuente | ~2-5s (LLM) | **0ms** (caché) | ∞ |
| Traducción corta | ~2-5s (LLM) | **0ms** (caché) | ∞ |
| TTS normal | ~45ms | — | — |
| TTS streaming | **~45ms** primer chunk | — | — |
| ASR (ES/EN) | ~36ms | — | — |
| ASR (JA, primera vez) | ~1.4s (carga small) | ~162ms (subsecuente) | 8.6x |

## 🚀 Cómo Ejecutar

### 1. Requisitos
```bash
pip install faster-whisper piper-tts psutil pynvml numpy
```

### 2. Iniciar llama-server (GPU)
```bash
llama-server -m Qwen3.5-2B-Q8.gguf -ngl 99 -c 4096 --port 8081
```

### 3. Iniciar Plan B
Opción A — Doble clic en el escritorio: `Alex_Plan_B.bat`
Opción B — Desde la terminal:
```bash
cd C:\Users\andyh\Desktop\Soft\Alex_Voice\B
python server.py
```

### 4. Abrir navegador
```
http://localhost:3001
```

## 🔧 API Endpoints

| Endpoint | Método | Descripción |
|:---------|:------:|:-----------|
| `/api/chat` | POST | Chat proxy a llama-server con caché LRU |
| `/api/tts` | POST | TTS Piper (~45ms, devuelve WAV) |
| `/api/tts/stream` | POST | TTS streaming (raw PCM chunked) |
| `/api/asr` | POST | ASR faster-whisper (base/small auto-switch) |
| `/api/stats` | GET | Estadísticas en vivo (GPU/CPU/RAM/LLM) |
| `/api/cache/stats` | GET | Estadísticas de caché LRU |
| `/api/cache/clear` | GET | Limpiar caché |

## 📁 Estructura

```
Alex_Voice/
├── B/
│   ├── server.py          ← Servidor Plan B (puerto 3001)
│   ├── start_plan_b.bat   ← Lanzador local
│   ├── AGENT.md           ← Instrucciones para el agente
│   ├── plan.md            ← Plan de implementación
│   └── README.md          ← Esta documentación
├── frontend/
│   └── plan-b/
│       └── index.html     ← UI de Plan B
├── models/                ← Modelos compartidos (Piper, Whisper)
├── bin/                   ← Binarios compartidos
└── ... (otros planes: A, C, D — independientes)
```

## ⚡ Rendimiento

| Operación | Latencia | Notas |
|:----------|:--------:|:------|
| Chat (caché hit) | **0ms** | Preguntas frecuentes |
| Chat (LLM) | ~2-5s | Depende de longitud |
| TTS Piper | **~45ms** | Modelos en memoria |
| TTS streaming | **~45ms** | Primer chunk |
| ASR base (ES/EN) | **~36ms** | faster-whisper |
| ASR small (JA) | **~82ms** | Auto-switch |
| End-to-end (típico) | **~1.2s** | LLM ~1s + TTS ~45ms |

## 🧠 Modos de Chat

- **🎓 Teacher** (temp 0.5) — Explicaciones claras y estructuradas
- **💬 Conversación** (temp 0.7) — Charla natural y fluida
- **🌍 Traductor** (temp 0.3) — Traducciones precisas ES/EN/JA
