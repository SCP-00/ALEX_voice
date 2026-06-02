# AGENT — Folder A (Actualizado con datos reales)

## Role
Explorar la estrategia combinada LLM + TTS en GPU.

## Hallazgos Reales
- **VRAM Real:** 5.28 GB usable (antes: 5.1 GB estimado)
- **Qwen3.5-2B-Q8:** 21-22 tok/s, ~3.0 GB VRAM
- **OuteTTS-500M:** 385 MB descargado, necesita debug
- **Combinación:** Qwen + OuteTTS = ~3.5 GB ✅

## Loading Policy (Actualizada)
- Cargar LLM y mantenerlo siempre residente
- Cargar TTS junto al LLM (caben ambos)
- ❌ Sin necesidad de swapping entre modelos

## Memory Safety
- Reserva de 1.8 GB para KV cache y audio
- `--fit` de llama.cpp ajusta automáticamente

## Fallback Logic
- Si OuteTTS falla: usar Piper TTS en CPU
- Si el LLM es muy grande: reducir contexto con --fit
- Si hay presion de VRAM: reducir ngl o contexto

## Logging
- timestamp, modelo, VRAM, tok/s, latencia, modo
