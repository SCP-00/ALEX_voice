# Plan A — Combined LLM + TTS ✅ VIABLE

## Objective
Ejecutar LLM + TTS compartiendo GPU sin swapping. Plan activo y en producción.

## Sistema Actual (Funcionando)

### Componentes

| Componente | Estatus | Detalle |
|:-----------|:-------:|:--------|
| **LLM** | ✅ | Qwen3.5-2B-Q8, 21-22 tok/s, llama-server puerto 8081 |
| **Monitor** | ✅ | python server.py puerto 3000 con stats GPU/CPU/RAM en vivo |
| **Chat Proxy** | ✅ | /api/chat → llama-server /chat/completions |
| **TTS Piper** | ✅ | Python API (~45ms), modelos ES/EN en memoria |
| **TTS GPU** | ⚠️ | OuteTTS vía llama-tts.exe (~13s, experimental) |
| **ASR** | ✅ | faster-whisper auto-switch: base (ES/EN) + small lazy (JA), CPU ~36-82ms |
| **Debug UI** | ✅ | /debug con 4 tabs (Timeline/Analytics/Hardware/TTS) |
| **Logging** | ✅ | logger.py con stats y export JSON |
| **Idiomas** | ✅ | ES/EN detectados, JA por caracteres Unicode |

### Benchmark TTS (Verificado en hardware real)
| Método | Latencia | Notas |
|:-------|:--------:|:------|
| Piper Python API | **~45-65ms** | 🥇 Modelos en memoria vía piper-tts |
| Piper pipe persistente | ~2100ms | Fallback si no hay piper-tts |
| Piper subprocess | ~2400ms | Último fallback |
| OuteTTS GPU | ~13000ms | Experimental, muy lento |

### Rendimiento LLM
| Modelo | Tok/s | VRAM | Prompt | 
|--------|:-----:|:----:|:------:|
| Qwen3.5-2B-Q8 | 21-22 | ~3.0 GB | 68 tok/s |
| Gemma-4-E2B-Q4 | 24.3 | ~3.5 GB | 109 tok/s |

## Implementation Phases (Actualizado)

### Phase 1 ✅ — LLM + Monitor (COMPLETADO)
- ✅ llama-server con Qwen3.5-2B-Q8
- ✅ Monitor server con stats en tiempo real
- ✅ Frontend HTML+JS funcional
- ✅ Debug UI (/debug)

### Phase 2 ✅ — TTS (COMPLETADO)
- ✅ Piper Python API con modelos en memoria (45ms)
- ✅ Detección de idioma y split multilingüe
- ✅ Fallback progresivo (API → pipe → subprocess)
- ✅ Endpoint /api/tts-piper

### Phase 3 ✅ — Voice Input Pipeline (COMPLETADO)
- [x] faster-whisper instalado con auto-switch base/small
- [x] ASR endpoint /api/asr con auto-switch por idioma
- [x] Micrófono integrado en frontend (Chrome ASR + Whisper ASR)
- [x] EchoGuard anti-loop TTS→micrófono
- [x] Pipeline completo: Audio → ASR → LLM → TTS

### Phase 4 📋 — Mejoras Futuras
- [ ] Caché de respuestas
- [ ] Streaming TTS
- [ ] Voice cloning (OuteTTS speaker file)

## Stack Tecnológico Final
- **LLM:** Qwen3.5-2B-Q8 (GPU, llama-server)
- **TTS:** Piper Python API (CPU, ~45ms)
- **Monitor:** python server.py (CPU)
- **Frontend:** HTML+JS vanilla
- **ASR:** faster-whisper (CPU, ~300ms)
- **OS:** Windows 11

## Criterios de Aceptación (100%)
- ✅ Sin OOM events
- ✅ Conversación natural en español/inglés/japonés
- ✅ TTS < 100ms de latencia
- ✅ Pipeline de voz completo: Audio → ASR → LLM → TTS
- ✅ Debug UI con monitoreo en vivo
- ✅ Logging de todas las operaciones
- ✅ Modo Traductor con system prompt refinado
