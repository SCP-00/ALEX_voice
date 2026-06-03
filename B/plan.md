# Plan B — LLM on GPU, TTS on CPU ✅ COMPLETADO

## Objetivo
Plan independiente: LLM en GPU con TTS en CPU + ASR en CPU + Caché LRU + Streaming TTS.
Puerto 3001. No depende de Plan A (puerto 3000).

## Resultados Reales

### LLM — Qwen3.5-2B-Q8 (GPU)
| Aspecto | Dato |
|:--------|:----:|
| Tok/s | 21-22 |
| VRAM | ~3.0 GB |
| Prompt Proc | 68 tok/s |
| API | /chat/completions (OpenAI-compatible) |

### TTS — Piper Python API (CPU)
| Método | Latencia | Estado |
|:-------|:--------:|:------:|
| Piper Python API (piper-tts v1.4.2) | **~45ms** | ✅ Producción |
| Piper Streaming (chunked transfer) | **~45ms** primer chunk | ✅ Producción |
| Piper subprocess (fallback) | ~2400ms | ⚠️ Fallback |

### ASR — faster-whisper (CPU)
| Modelo | Latencia | RAM | Uso |
|:-------|:--------:|:---:|:----|
| base | ~36ms | 150 MB | ES/EN (default) |
| small | ~82ms | 500 MB | JA (auto-switch) |

### Caché LRU
| Aspecto | Valor |
|:--------|:------|
| Capacidad | 50 entradas |
| Thread-safe | ✅ Lock |
| Key | Hash de últimos 4 mensajes (truncados 200 chars) |
| Hit rate | Variable según patrón de uso |

## Fases

### Phase 1 ✅ — Text Core
- [x] Servidor `B/server.py` (puerto 3001)
- [x] Chat proxy a llama-server
- [x] Frontend plan-b con 3 modos

### Phase 2 ✅ — CPU TTS
- [x] Piper Python API funcional (~45ms)
- [x] Modelos ES y EN cargados en memoria
- [x] Streaming TTS (raw PCM chunked)
- [x] Detección automática de idioma

### Phase 3 ✅ — Voice Input
- [x] faster-whisper integrado (base + small)
- [x] Auto-switch: base (ES/EN), small (JA)
- [x] Pipeline: Audio → ASR → LLM → TTS

### Phase 4 ✅ — Optimization (Completada)
- [x] Caché LRU de respuestas frecuentes
- [x] Streaming TTS (primer chunk ~45ms)
- [x] /api/cache/stats y /api/cache/clear
- [x] Auto-speak de respuestas cortas en frontend

## Benchmark

| Escenario | Latencia | Ganancia |
|:----------|:--------:|:--------:|
| Chat con caché (saludos, FAQs) | **0ms** | ∞ |
| Chat sin caché (LLM GPU) | ~2-5s | — |
| TTS Piper (modelos en memoria) | **~45ms** | 40-50x vs subprocess |
| TTS streaming (primer chunk) | **~45ms** | Percepción 0 |
| ASR ES/EN (base) | **~36ms** | — |
| ASR JA (small, 1ra vez) | ~1.4s (carga) | 8.6x en 2da vez |

## Cómo Ejecutar
1. Iniciar llama-server con Qwen3.5-2B-Q8 en puerto 8081
2. `cd B && python server.py` (o doble clic en `Alex_Plan_B.bat` del escritorio)
3. Abrir `http://localhost:3001`
