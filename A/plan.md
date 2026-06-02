# Plan A — Combined LLM + TTS ✅ VIABLE

## Objective
Validate whether a combined LLM + TTS architecture can operate safely under a 5.28 GB VRAM ceiling.

## Research Results (Verificado en hardware real)

### LLM Candidates — Probados con inferencia real
| Modelo | Tok/s | VRAM | ¿Recomendado? |
|--------|-------|------|:------------:|
| Qwen3.5-2B-Q8 | 21-22 | ~2.5-3.0 GB | ✅ Primera opción |
| Gemma-4-E2B-Q4 | 24.3 | ~3.5-4.0 GB | ✅ Alternativa |
| DeepSeek-R1-8B-Q4 | 8.9 | ~5.0 GB | ❌ Muy lento |
| Gemma-4-E4B-Q4 | — | ~5.5 GB | ❌ No cabe |

### TTS Candidate
| Modelo | Tamaño | Estado |
|--------|--------|--------|
| OuteTTS-0.2-500M-Q4_K_M | 385 MB | ✅ Descargado |
| Piper TTS (CPU) | ~200 MB | Pendiente |
| MeloTTS (CPU) | ~1 GB | Pendiente |

### Combinación Ganadora
**Qwen3.5-2B-Q8 + OuteTTS-500M** = ~3.5 GB VRAM total
Margen: ~1.8 GB para KV cache y buffers

## Implementation Phases (Actualizado)
### Phase 1 ✅ — Baseline (COMPLETADO)
- ✅ llama.cpp v9479 instalado con CUDA 13.3
- ✅ Qwen3.5-2B-Q8 probado: 21-22 tok/s en GPU
- ✅ Gemma-4-E2B-Q4 probado: 24.3 tok/s
- ✅ DeepSeek-R1-8B probado: 8.9 tok/s
- ✅ VRAM validada: 5.28 GB usable

### Phase 2 — Speech Output
- [ ] Debuggear OuteTTS (parámetro -m no funciona)
- [ ] Alternativa: Piper TTS en CPU
- [ ] Medir latencia de síntesis

### Phase 3 — Switching (No necesario - ambos caben)
- ❌ No requiere swapping — LLM + TTS residentes juntos

### Phase 4 — Stress Testing
- [ ] Prueba de contexto largo (>2048 tokens)
- [ ] Cambio de modos (teacher/conversation/translator)
- [ ] Sesiones prolongadas (>30 min)

## Benchmark Checklist (Actualizado)
- ✅ time to first token: ~3-5s (Qwen)
- ✅ tokens/second: 21-24 tok/s
- ⌛ peak VRAM: ~3.0-3.5 GB (estimado)
- ⌛ model load time: ~5-10s
- ⌛ response latency: ~3-8s end-to-end
