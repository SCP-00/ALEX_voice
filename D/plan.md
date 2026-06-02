# Plan D — Recomendación Final (Basada en Datos Reales)

## Objective
Seleccionar la arquitectura más robusta comparando los 3 planes con datos empíricos.

## Evaluación Final

| Criterio | Plan A (Combinado) | Plan B (LLM GPU + TTS CPU) | Plan C (Pipeline) |
|:--------:|:------------------:|:--------------------------:|:-----------------:|
| VRAM | ✅ 3.5-4.0 GB | ✅ 2.5-3.0 GB | ❌ 4.5-5.0 GB |
| Latencia | ✅ 21 tok/s | ✅ 21 tok/s + TTS CPU | ⚠️ Pipeline depth |
| TTS calidad | ⚠️ OuteTTS debug | ⚠️ Piper/MeloTTS | ⚠️ OuteTTS debug |
| Complejidad | 🟢 Baja | 🟢 Baja | 🔴 Alta |
| Mantenibilidad | 🟢 Alta | 🟢 Alta | 🟡 Media |

## Ganador: Plan A (Combined LLM + TTS)
**Motivo:** Qwen3.5-2B-Q8 + OuteTTS-500M = ~3.5 GB VRAM. Cabe todo.

## Fallback: Plan B (LLM GPU + TTS CPU)
**Motivo:** Si OuteTTS no funciona, Piper TTS en CPU.

## Stack Recomendado
- **Runtime:** llama.cpp v9479 (llama-server como API HTTP)
- **LLM:** Qwen3.5-2B-Q8 (21-22 tok/s, ~3.0 GB VRAM)
- **TTS:** OuteTTS-500M (GPU) o Piper (CPU)
- **ASR:** whisper.cpp tiny (pendiente)
- **Frontend:** HTML+JS vanilla (llama-server API)
- **Orquestación:** Bash scripts simples

## Tradeoffs Aceptados
- OuteTTS puede no cargar → fallback a Piper en CPU
- DeepSeek-R1-8B es muy lento (8.9 tok/s) → no usarlo
- Gemma-4-E2B-Q4 es buena alternativa (24.3 tok/s) pero pesa más
