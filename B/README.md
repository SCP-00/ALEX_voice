# Folder B — LLM on GPU, TTS on CPU ✅ RECOMENDADO COMO FALLBACK

## Purpose
Arquitectura de menor riesgo: LLM en GPU, TTS en CPU. **Fallback de Plan A.**

## 🚀 Estado Actual

### ✅ LLM en GPU (Probado)
| Modelo | VRAM | Tok/s | Español |
|--------|:----:|:-----:|:-------:|
| **Qwen3.5-2B-Q8** 🥇 | ~3.0 GB | **21-22 tok/s** | ✅ Excelente |
| **Gemma-4-E2B-Q4** 🥈 | ~3.5 GB | **24.3 tok/s** | ✅ Excelente |

### ✅ TTS en CPU — Piper Python API (Activo)
| Aspecto | Dato |
|:--------|:------|
| Motor | `piper-tts` v1.4.2 Python bindings |
| Latencia | **~45-65ms** por síntesis |
| Modelo ES | `es_ES-sharvard-medium.onnx` |
| Modelo EN | `en_US-lessac-medium.onnx` |
| RAM | ~150 MB |

### ✅ Monitor Server (python server.py, puerto 3000)
El monitor server sirve como orquestador central:
- Proxy de chat a llama-server
- Endpoint TTS (/api/tts-piper)
- Endpoint ASR (/api/asr, faster-whisper CPU ~300ms)
- Debug UI (/debug)
- Stats en vivo de GPU/CPU/RAM/LLM
- Logging de eventos

### ✅ ASR (Voice Input) — COMPLETADO
| Componente | Estado |
|:-----------|:------:|
| faster-whisper (modelo tiny, CPU) | ✅ Cargado al iniciar server.py |
| Transcripción WAV | ✅ ~200-500ms |
| Micrófono en frontend | ✅ Chrome ASR + Whisper ASR |
| Pipeline: Audio → ASR → LLM → TTS | ✅ Completo |

## Hardware
- CPU: i5-13420H (8C/12T)
- RAM: 16.5 GB (5.7 GB libre)
- GPU: RTX 3050 6GB (5.28 GB VRAM usable)

## Estrategia
- LLM siempre en GPU (Qwen3.5-2B-Q8 recomendado)
- TTS en CPU via Piper Python API (~45ms)
- ASR en CPU via faster-whisper (~300ms)
- Piper modelos cargados en memoria al iniciar server.py
- Sin riesgo de OOM en GPU
- ~2.3 GB de VRAM libre para contexto

## Riesgos Mitigados
- ✅ TTS en CPU es muy rápido (~45ms) con Piper Python API
- ✅ Sin riesgo de OOM en GPU
- ⚠️ OuteTTS GPU es lento (~13s) — no recomendado
- ⚠️ Piper.exe nativo (subprocess) es lento (~2400ms) — usar Python API
