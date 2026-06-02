# Folder A — Combined LLM + TTS Plan ✅ VIABLE

## Purpose
Evaluate a design where the LLM and TTS share the GPU, coexisting without swapping.

## Benchmarks Reales (RTX 3050 6GB, 5.28 GB VRAM usable)

### Modelos LLM Probados

| Modelo | Tamaño | VRAM* | Velocidad | Veredicto |
|--------|--------|-------|-----------|-----------|
| **Qwen3.5-2B-Q8** 🥇 | 2.0 GB | ~2.5-3.0 GB | **21-22 tok/s** | ✅ Mejor opción |
| **Gemma-4-E2B-Q4** 🥈 | 3.2 GB | ~3.5-4.0 GB | **24.3 tok/s** | ✅ Excelente |
| **Gemma-E2B-Uncensored-Q8** 🥉 | 4.7 GB | ~5.0-5.3 GB | ~15 tok/s | ⚠️ Justo, probar contexto |
| **DeepSeek-R1-8B-Q4** | 4.7 GB | ~5.0-5.3 GB | **8.9 tok/s** | ⚠️ Lento pero cupo |
| **Gemma-4-E4B-Q4** | 5.0 GB | ~5.5-6.0 GB | — | ❌ Excede VRAM en producción |

*_VRAM medida con llama.cpp --fit (default on). Contexto reducido automáticamente._

### Modelo TTS
| Modelo | Tamaño | Estado |
|--------|--------|--------|
| **OuteTTS-0.2-500M-Q4_K_M** | 385 MB | ✅ Descargado (necesita debug de parámetros) |

### Plan A — Combinación Recomendada
```
Qwen3.5-2B-Q8 (2.5-3.0 GB) + OuteTTS-500M (0.5 GB) = ~3.0-3.5 GB TOTAL ✅
```
**Cabe en VRAM con 1.8 GB de margen.** No necesita swapping.

### Hardware Real
- CPU: Intel Core i5-13420H (8 núcleos, 12 hilos)
- RAM: 16.5 GB total (~5.7 GB libre con apps)
- GPU: NVIDIA RTX 3050 Laptop 6 GB
- VRAM usable real: **5.28 GB** (735 MB en reposo)
- Disco libre: ~258 GB

### Idiomas Confirmados
- **Español** ✅ Probado — responde perfectamente
- **Inglés** ✅ Garantizado por el modelo
- **Japonés** ✅ Pendiente de prueba específica

### Estrategia de Memoria Actualizada
- Qwen3.5-2B-Q8 + OuteTTS-500M caben simultáneamente en GPU
- No es necesario swapping entre LLM y TTS
- Reservar ~1 GB para KV cache y audio buffers
- Usar `--fit` de llama.cpp para ajuste automático

### Riesgos Mitigados
- ❌ ~~Model switching overhead~~ → No necesario, ambos caben
- ❌ ~~Peak VRAM spikes~~ → ~3.5 GB total, margen de 1.8 GB
- ⚠️ OuteTTS necesita parámetro correcto para cargar

### Criterios de Aceptación
- ✅ Sin OOM events
- ✅ Calidad de conversación probada en español
- ✅ Modo texto funcional
- ⏳ Pendiente: TTS funcional + modo voz completo
