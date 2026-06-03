# Folder C — Full Speech Pipeline 🚧 EN CONSTRUCCIÓN

## Purpose
Pipeline completo: ASR → Ruteo → LLM → TTS. Destino final del proyecto.

## Estado Actual de Componentes (Junio 2026)

### ✅ LLM (LISTO)
| Modelo | VRAM | Tok/s | Modos |
|--------|:----:|:-----:|:------|
| Qwen3.5-2B-Q8 🥇 | ~3.0 GB | 21-22 | Teacher ✅ / Conversación ✅ / Traductor ✅ |

### ✅ TTS (LISTO — Piper Python API)
| Motor | Latencia | Modelos |
|:------|:--------:|:--------|
| **Piper Python API** 🥇 | **~45ms** | ES (`sharvard-medium`) + EN (`lessac-medium`) |
| PiperPersistentProcess | ~2100ms | Fallback pipe |
| Piper subprocess | ~2400ms | Fallback stdin |
| OuteTTS GPU | ~13000ms | Experimental |

### ✅ Routing / Language ID (LISTO — en server.py)
| Función | Estado |
|:--------|:------:|
| `detect_language(text)` | ✅ ES/EN/JA por Unicode + keywords |
| `split_by_language(text)` | ✅ Segmentación multilingüe con split de scripts mixtos |
| `_split_mixed_script(text)` | ✅ División carácter por carácter para JA+Latin |

### ✅ Monitor Server (LISTO)
| Componente | Puerto | Función |
|:-----------|:------:|:--------|
| Chat Proxy | 3000 | `/api/chat` → llama-server |
| TTS | 3000 | `/api/tts-piper` con auto-detect |
| ASR | 3000 | `/api/asr` (faster-whisper tiny, CPU ~300ms) |
| Stats | 3000 | `/api/stats`, `/api/hardware` |
| Logging | 3000 | `/api/logs`, `/api/logs/stats`, `/api/logs/export` |
| Debug | 3000 | `/debug` con 4 tabs |

### ✅ ASR (COMPLETADO)
- faster-whisper: instalado y cargado al iniciar server.py ✅
- Modelo tiny (~75 MB, CPU, ~300ms por transcripción) ✅
- Micrófono en frontend: Chrome ASR + Whisper ASR ✅
- Pipeline completo: Audio → ASR → LLM → TTS ✅

## Pipeline Propuesto
```
[Audio In] → VAD → ASR (Whisper tiny) → Language ID (CPU)
    → Router (CPU) → LLM (GPU) → TTS (CPU, ~45ms) → [Audio Out]
```

**Estado actual:** ✅ Pipeline COMPLETO. Audio → ASR → LLM → TTS funcional.

## Hardware Budget
| Componente | VRAM/RAM | Estado |
|-----------|:--------:|:------:|
| ASR (faster-whisper tiny) | ~150 MB RAM | ✅ |
| LLM (Qwen3.5-2B) | ~3.0 GB VRAM | ✅ |
| TTS (Piper CPU) | ~150 MB RAM | ✅ |
| Monitor Server | ~100 MB RAM | ✅ |
| **Total Pipeline** | **~3.0 GB VRAM + ~400 MB RAM** | ✅ Funcional |
