# AGENT — Folder A (Actualizado con estado real)

## Role
Ejecutar el asistente local con LLM en GPU y TTS optimizado.

## Estado Actual (Producción) — 100%
- **LLM:** Qwen3.5-2B-Q8, 21-22 tok/s, puerto 8081 ✅
- **Monitor Server:** python server.py, puerto 3000 ✅
- **TTS:** Piper Python API, ~45ms latencia ✅
- **ASR:** faster-whisper tiny, CPU, ~300ms ✅
- **Debug UI:** /debug con 4 tabs ✅
- **Micrófono:** Escucha Activa con Chrome ASR + Whisper ASR ✅
- **Pipeline completo:** Audio → ASR → LLM → TTS ✅

## Stack Final
- **Runtime:** python server.py + llama-server.exe
- **LLM:** Qwen3.5-2B-Q8 (~3.0 GB VRAM, 21-22 tok/s)
- **TTS:** Piper Python API (CPU, modelos ES/EN en memoria, ~45ms)
- **Monitor:** psutil + pynvml para stats en vivo
- **Logging:** logger.py (add_log, get_logs, get_log_stats, clear_logs)
- **Frontend:** HTML+JS vanilla
- **Debug:** 4 tabs (Timeline/Analytics/Hardware/TTS)

## Loading Policy
- LLM siempre residente en GPU (llama-server)
- Modelos Piper cargados al iniciar server.py (~1.8s)
- Fallback a pipe/subprocess si Python API no disponible

## Fallback Logic
- TTS: Python API → pipe persistente → subprocess → error
- Si whisper no instalado: solo entrada de texto
- Si VRAM insuficiente: reducir contexto con --fit

## Memoria Verificada
- Qwen3.5-2B-Q8: ~3.0 GB VRAM
- Piper: ~150 MB RAM (CPU)
- Monitor: ~100 MB RAM
- Total: ~3.5 GB VRAM + ~250 MB RAM de ~16.5 GB
- Margen: ~1.8 GB VRAM, ~5.5 GB RAM

## Estado Actual
- **ASR auto-switch**: base para ES/EN (~36ms, 150 MB), small lazy para JA (~82ms, +283 MB)
- **EchoGuard**: protección anti-loop TTS→micrófono implementada
- Todos los objetivos de Fase 1-3 completados y en producción.
