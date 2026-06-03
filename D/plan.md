# Plan D — Recomendación Final (Basada en Datos Reales)

## Objective
Seleccionar la arquitectura más robusta comparando los planes con datos empíricos.

## Evaluación Final (Junio 2026)

| Criterio | Plan A (LLM GPU + TTS CPU Python API) | Plan B (LLM GPU + TTS CPU) | Plan C (Pipeline completo) |
|:--------:|:-------------------------------------:|:--------------------------:|:-------------------------:|
| VRAM | ✅ 3.5 GB | ✅ 3.0 GB | ❌ ~4.0 GB con ASR |
| Latencia TTS | ✅ **~45ms** | ✅ ~45ms | ⚠️ +ASR overhead |
| TTS calidad | ✅ Piper ES/EN voces naturales | ✅ Piper | ✅ Piper |
| ASR | ✅ faster-whisper (tiny, CPU) | ✅ faster-whisper | ✅ faster-whisper |
| Complejidad | 🟢 Baja (2 procesos) | 🟢 Baja | 🔴 Alta |
| Mantenibilidad | 🟢 Alta | 🟢 Alta | 🟡 Media |

## Ganador: Plan A (LLM GPU + Piper Python API CPU)
**Motivo:** Qwen3.5-2B-GPU + Piper TTS-CPU (~45ms) = **mejor latencia + sin riesgo OOM.**

## Stack Final
| Componente | Tecnología | Detalle |
|:-----------|:-----------|:--------|
| **Runtime** | llama-server + python server.py | 2 procesos, un clic |
| **LLM** | Qwen3.5-2B-Q8 | 21-22 tok/s, ~3.0 GB VRAM |
| **TTS** | Piper Python API (piper-tts v1.4.2) | **~45ms**, CPU, ES/EN |
| **Monitor** | python server.py | Stats, logs, debug, proxy |
| **Frontend** | HTML+JS vanilla | 3 modos, debug UI |
| **ASR** | faster-whisper tiny (CPU ~300ms) | ✅ |

## Tradeoffs Aceptados
- Piper en CPU (~45ms) vs OuteTTS en GPU (~13000ms) → Piper gana por paliza
- faster-whisper tiny (CPU) vs modelos más grandes → suficiente precisión para comandos
- Sin streaming de audio TTS → carga completa del WAV

## Lecciones Aprendidas
1. **Piper Python API** es 40-50x más rápido que subprocess (~45ms vs ~2400ms)
2. **OuteTTS** es demasiado lento (~13s) para uso interactivo
3. **Python server.py** como orquestador central simplifica la arquitectura
4. **logger.py** como módulo separado mantiene server.py limpio
5. **start_server.bat** con un clic y cleanup es clave para UX
