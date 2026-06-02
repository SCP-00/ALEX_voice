# Plan B — LLM on GPU, TTS on CPU ✅

## Objective
Validar arquitectura de LLM en GPU con TTS en CPU como opción de menor riesgo.

## Research Results (Verificado)

### LLM — Resultados de Inferencia Real
| Modelo | Tok/s | VRAM | Prompt Proc | Veredicto |
|--------|-------|------|:-----------:|:---------:|
| Qwen3.5-2B-Q8 | 21-22 | ~3.0 GB | 68 tok/s | ✅ Elegido |
| Gemma-4-E2B-Q4 | 24.3 | ~3.5 GB | 109 tok/s | ✅ Alternativa |
| DeepSeek-R1-8B-Q4 | 8.9 | ~5.0 GB | 5.1 tok/s | ❌ Lento |

### TTS en CPU — Pendientes
- OuteTTS-500M: descargado (385 MB), necesita debug
- Piper TTS: pendiente de instalar
- MeloTTS: pendiente de instalar

## Implementation Phases
### Phase 1 ✅ — Text Core (COMPLETADO)
- ✅ llama.cpp v9479 con CUDA
- ✅ Modelos probados y verificados
- ✅ Velocidades medidas

### Phase 2 — CPU TTS (PENDIENTE)
- [ ] Probar OuteTTS-500M (debug parámetros)
- [ ] Instalar Piper TTS (fallback)
- [ ] Medir latencia TTS en CPU

### Phase 3 — Voice Input (FUTURO)
- [ ] whisper.cpp para ASR
- [ ] Pipeline voz completa

### Phase 4 — Optimization
- [ ] Caché de respuestas frecuentes
- [ ] Ajuste de contexto según VRAM
