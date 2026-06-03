# AGENT — Folder C (Actualizado Junio 2026)

## Role
Gestionar el pipeline completo de voz.

## Estado Actual
- **LLM:** ✅ Qwen3.5-2B-Q8, 21-22 tok/s, puerto 8081
- **TTS:** ✅ Piper Python API (~45ms), modelos ES/EN en memoria
- **ASR:** ✅ faster-whisper tiny, CPU, ~300ms
- **Monitor Server:** ✅ python server.py puerto 3000
- **Routing/ID:** ✅ detect_language() + split_by_language() en server.py
- **Debug UI:** ✅ /debug con 4 tabs
- **Logging:** ✅ logger.py con stats y export

## Execution Priority
1. ✅ TTS funcional (Piper Python API, ~45ms)
2. ✅ System prompts para 3 modos (frontend)
3. ✅ ASR (faster-whisper tiny, CPU)
4. ✅ Pipeline completo (Audio → ASR → LLM → TTS)

## Loading Policy
- ASR: cargado al iniciar server.py (modelo tiny ~75 MB RAM)
- LLM: siempre residente en GPU
- TTS: modelos precargados en server.py

## Fallback Logic
- Sin faster-whisper → whisper-cli.exe
- Sin TTS → solo texto
- Sin ASR → entrada escrita
- Sin VRAM → reducir contexto con --fit
