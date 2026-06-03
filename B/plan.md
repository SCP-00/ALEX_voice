# Plan B — LLM on GPU, TTS on CPU ✅

## Objective
Validar arquitectura de LLM en GPU con TTS en CPU como fallback de Plan A.

## Research Results (Verificado)

### LLM — Resultados de Inferencia Real
| Modelo | Tok/s | VRAM | Prompt Proc | Veredicto |
|--------|:-----:|:----:|:-----------:|:---------:|
| Qwen3.5-2B-Q8 | 21-22 | ~3.0 GB | 68 tok/s | ✅ Elegido |
| Gemma-4-E2B-Q4 | 24.3 | ~3.5 GB | 109 tok/s | ✅ Alternativa |
| DeepSeek-R1-8B-Q4 | 8.9 | ~5.0 GB | 5.1 tok/s | ❌ Lento |

### TTS en CPU — Piper Python API (~45ms) 🥇
| Método | Latencia | Estado |
|:-------|:--------:|:------:|
| Piper Python API (piper-tts v1.4.2) | **~45ms** | ✅ Activo |
| PiperPersistentProcess (pipe) | ~2100ms | Fallback |
| Piper subprocess stdin | ~2400ms | Fallback |

### OuteTTS GPU (Experimental)
- **Latencia:** ~13000ms — demasiado lento para uso interactivo
- Solo usar si se necesita calidad superior y la latencia no importa

## Implementation Phases (Actualizado)

### Phase 1 ✅ — Text Core (COMPLETADO)
- ✅ llama-server con Qwen3.5-2B-Q8
- ✅ Monitor server (python server.py)
- ✅ Chat proxy — /api/chat
- ✅ Debug UI — /debug

### Phase 2 ✅ — CPU TTS (COMPLETADO)
- ✅ Piper Python API funcional (~45ms)
- ✅ Modelos ES y EN cargados en memoria
- ✅ Detección automática de idioma
- ✅ Fallback progresivo

### Phase 3 ✅ — Voice Input (COMPLETADO)
- [x] faster-whisper integrado (modelo tiny, CPU)
- [x] Pipeline: Audio → ASR → LLM → TTS
- [x] Micrófono en frontend (Chrome ASR + Whisper ASR)

### Phase 4 📋 — Optimization
- [ ] Caché de respuestas frecuentes
- [ ] Streaming TTS
