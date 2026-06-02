# AGENT — Folder B (Actualizado)

## Role
Operar el asistente local con LLM en GPU y TTS en CPU.

## Hallazgos Reales
- **Qwen3.5-2B-Q8:** 21-22 tok/s, ~3.0 GB VRAM ✅
- **Gemma-4-E2B-Q4:** 24.3 tok/s, ~3.5 GB VRAM ✅
- **VRAM Real:** 5.28 GB usable (margen de 2.3 GB con Qwen)
- **OuteTTS-500M:** Descargado, pendiente de debug

## Loading Policy (Actualizada)
- LLM cargado una vez, siempre residente en GPU
- TTS en CPU, cargado bajo demanda
- ASR solo cuando hay entrada de voz activa

## Fallback Logic
- Si TTS lento: solo texto
- Si VRAM sube: reducir contexto con --fit
- Si ASR falla: permitir entrada escrita

## Test Order
1. ✅ LLM baseline (COMPLETADO)
2. ⏳ CPU TTS baseline
3. ⏳ ASR baseline
4. ⏳ Full voice pipeline
