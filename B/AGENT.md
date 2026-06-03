# AGENT — Folder B (Actualizado)

## Role
Fallback de Plan A: LLM en GPU, TTS en CPU.

## Hallazgos Reales
- **Qwen3.5-2B-Q8:** 21-22 tok/s, ~3.0 GB VRAM ✅
- **Piper Python API:** ~45ms latencia, modelos en memoria ✅
- **Piper subprocess:** ~2400ms — evitar, usar Python API
- **OuteTTS GPU:** ~13000ms — demasiado lento
- **Monitor Server:** python server.py con debug UI, stats, logs ✅

## Loading Policy
- LLM cargado una vez, siempre residente en GPU
- Modelos Piper cargados al iniciar server.py
- Fallback a pipe/subprocess si Python API no instalada

## Test Order (Actualizado)
1. ✅ LLM baseline (COMPLETADO)
2. ✅ CPU TTS baseline (COMPLETADO — Piper Python API 45ms)
3. ✅ ASR baseline (faster-whisper tiny, CPU ~300ms)
4. ✅ Full voice pipeline (Audio → ASR → LLM → TTS)
