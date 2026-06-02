# Plan C — Full Speech Pipeline 🚧

## Objective
Pipeline modular completo: ASR → Ruteo → LLM → TTS.

## Estado por Componente

### Phase 1 — Audio Entry (PENDIENTE)
- [ ] Voice capture + VAD
- [ ] whisper.cpp o faster-whisper para ASR
- [ ] Streaming ASR

### Phase 2 — Routing Layer (PENDIENTE)
- [ ] Language ID (es/en/ja)
- [ ] Mode detection (teacher/conversation/translator)
- [ ] Routing logic

### Phase 3 — Response Generation (LISTO ✅)
- ✅ Qwen3.5-2B-Q8: 21-22 tok/s, español perfecto
- ✅ Gemma-4-E2B-Q4: 24.3 tok/s, alternativa
- ⏳ System prompts para cada modo

### Phase 4 — Speech Output (EN PROGRESO)
- ✅ OuteTTS-500M descargado
- ⏳ Debuggear parámetros llama-tts.exe
- ⏳ Alternativa: Piper TTS

## Hardware Budget
| Componente | VRAM/RAM | Estado |
|-----------|:--------:|:------:|
| ASR (whisper tiny) | ~500 MB RAM | Pendiente |
| LLM (Qwen3.5-2B) | ~3.0 GB VRAM | ✅ |
| TTS (OuteTTS) | ~0.5 GB VRAM | Descargado |
| TTS (Piper CPU) | ~200 MB RAM | Alternativa |
| Total Pipeline | ~3.5 GB VRAM + ~700 MB RAM | ✅ Factible |
