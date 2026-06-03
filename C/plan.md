# Plan C — Full Speech Pipeline 🚧

## Objective
Pipeline modular completo: ASR → Ruteo → LLM → TTS.

## Estado por Componente (Junio 2026)

### Phase 1 — Audio Entry (COMPLETADO ✅)
- [x] faster-whisper instalado y cargado al iniciar server.py
- [x] ASR endpoint /api/asr con faster-whisper (tiny, CPU)
- [x] Micrófono en frontend (Chrome ASR + Whisper ASR)
- [x] Pipeline: grabación → WAV → ASR → texto

### Phase 2 — Routing Layer (LISTO ✅ en server.py)
- ✅ Language ID: `detect_language()` para ES/EN/JA
- ✅ Segmentación: `split_by_language()` con split de scripts mixtos
- ✅ Mode detection: teacher/conversation/translator (frontend)

### Phase 3 — Response Generation (LISTO ✅)
- ✅ Qwen3.5-2B-Q8: 21-22 tok/s, español perfecto
- ✅ Chat proxy: `/api/chat` → llama-server `/chat/completions`
- ✅ System prompts para cada modo (frontend)
- ✅ Logging de tokens, latencia, idioma

### Phase 4 — Speech Output (LISTO ✅)
- ✅ Piper Python API: ~45ms latencia, modelos en memoria
- ✅ Detección automática de idioma para TTS
- ✅ Fallback progresivo (API → pipe → subprocess)
- ✅ Endpoint `/api/tts-piper`

## Hardware Budget
| Componente | VRAM/RAM | Estado |
|-----------|:--------:|:------:|
| ASR (faster-whisper tiny) | ~150 MB RAM | ✅ |
| LLM (Qwen3.5-2B) | ~3.0 GB VRAM | ✅ |
| TTS (Piper CPU) | ~150 MB RAM | ✅ |
| Monitor Server | ~100 MB RAM | ✅ |
| **Total Pipeline** | **~3.0 GB VRAM + ~400 MB RAM** | ✅ Funcional |

## Próximo Paso
**Optimizar ASR:** Probar modelo small/medium si la latencia lo permite, o integrar VAD más preciso.
