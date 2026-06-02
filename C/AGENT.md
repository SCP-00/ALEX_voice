# AGENT — Folder C (Actualizado)

## Role
Gestionar el pipeline completo de voz.

## Estado Actual
- **LLM:** ✅ Listo (Qwen3.5-2B-Q8, 21-22 tok/s)
- **TTS:** ⏳ OuteTTS descargado, necesita debug
- **ASR:** ❌ Pendiente de instalar
- **Routing:** ❌ Pendiente de implementar

## Execution Priority
1. ✅ TTS funcional (debug OuteTTS o instalar Piper)
2. ⏳ System prompts para 3 modos
3. ⏳ ASR (whisper.cpp)
4. ⏳ Pipeline completo

## Loading Policy
- ASR: solo durante entrada de audio
- LLM: siempre residente en GPU
- TTS: bajo demanda (CPU o GPU)

## Fallback Logic
- Sin TTS → solo texto
- Sin ASR → entrada escrita
- Sin VRAM → reducir contexto con --fit
