# AGENT — Folder D (Recomendación Final)

## Decisión Final
**Plan A: LLM (GPU) + Piper TTS (CPU Python API ~45ms).**
Qwen3.5-2B-Q8 + Piper = mejor latencia TTS + VRAM para LLM.

## Stack Final
- **LLM:** Qwen3.5-2B-Q8 (21-22 tok/s, ~3.0 GB VRAM)
- **TTS:** Piper Python API (~45ms, CPU, ES/EN en memoria)
- **Monitor:** python server.py (stats, logs, debug, proxy)
- **Frontend:** HTML+JS vanilla (Plan A, 3 modos)
- **ASR:** whisper.cpp (pendiente, endpoint listo)
- **Startup:** start_server.bat (un clic)

## Argumentos
1. Piper Python API **40-50x más rápido** que subprocess Piper
2. Piper en CPU deja toda la VRAM para el LLM
3. OuteTTS (~13s) no es viable para uso interactivo
4. Monitor server unifica proxy, stats, logs, debug en un proceso
5. logger.py modulariza sin afectar latencia

## Siguiente Paso
**Optimizar ASR:** Probar modelo small/medium para mejor precisión, o integrar VAD más preciso para reducir falsos positivos.

## Limitaciones Actuales
- Sin streaming de audio TTS (carga completa del WAV)
- Modo Traductor puede mejorar con ejemplos específicos
- Sin VAD (Voice Activity Detection) avanzado
