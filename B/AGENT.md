# AGENT — Plan B (Completado)

## Role
Plan independiente: LLM en GPU, TTS en CPU, ASR en CPU.
Puerto 3001. No depende de Plan A.

## Estado: ✅ COMPLETADO

### Fase 1 ✅ — Text Core
- Servidor propio: `B/server.py` (puerto 3001)
- Chat proxy a llama-server con caché LRU
- Frontend plan-b con 3 modos (Teacher/Conversación/Traductor)

### Fase 2 ✅ — CPU TTS
- Piper Python API (~45ms, modelos en memoria)
- Streaming TTS (primer chunk ~45ms)
- Fallback a subprocess

### Fase 3 ✅ — Voice Input
- faster-whisper (base + small con auto-switch)
- Pipeline: Audio → ASR → LLM → TTS

### Fase 4 ✅ — Optimización (Plan B exclusivo)
- Caché LRU de respuestas (50 entradas, thread-safe)
- Streaming TTS (raw PCM chunked transfer)

## Datos Clave
- **Puerto:** 3001
- **LLM:** Qwen3.5-2B-Q8 (GPU, ~3.0 GB VRAM, 21-22 tok/s)
- **TTS:** Piper Python API (~45ms, CPU)
- **ASR:** faster-whisper base/small (~36-162ms, CPU)
- **Caché:** LRU 50 entradas (hit rate configurable vía /api/cache/stats)
- **Frontend:** `frontend/plan-b/index.html`
- **Lanzador:** `start_plan_b.bat` en B/ o `Alex_Plan_B.bat` en escritorio

## Dependencias
```bash
pip install faster-whisper piper-tts psutil pynvml numpy
```

## Notas
- Cada plan es completamente independiente
- Los modelos (Piper, Whisper) y binarios se comparten desde el proyecto raíz
- Al terminar los 4 planes, se optimizarán todos con la experiencia acumulada
