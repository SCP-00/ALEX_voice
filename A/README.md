# Folder A — Combined LLM + TTS ✅ VIABLE (EN PRODUCCIÓN)

## Purpose
Ejecutar LLM + TTS compartiendo GPU sin swapping. **Plan activo y funcional.**

## 🚀 Estado Actual del Sistema

```
start_server.bat ─→ llama-server (Qwen, puerto 8081) + python server.py (Monitor, puerto 3000)
```

### ✅ LLM — Qwen3.5-2B-Q8 (21-22 tok/s)
| Aspecto | Dato |
|:--------|:----:|
| Modelo | Qwen3.5-2B-Qwen3.6-plus-Distilled-q8_0.gguf |
| VRAM | ~3.0 GB |
| Velocidad | **21-22 tok/s** (68 tok/s prompt) |
| API | `/chat/completions` (OpenAI-compatible) vía llama-server |
| Modos | Teacher ✅ / Conversación ✅ / Traductor ✅ |

### ✅ TTS — Piper Python API (~45ms)
| Aspecto | Dato |
|:--------|:----:|
| Motor | `piper-tts` v1.4.2 Python bindings |
| Modelo ES | `es_ES-sharvard-medium.onnx` (voz femenina) |
| Modelo EN | `en_US-lessac-medium.onnx` (voz femenina) |
| Latencia | **~45-65ms** por síntesis (vs ~2400ms con subprocess) |
| Método | Modelos cargados en memoria, thread-safe |
| Fallback | PiperPersistentProcess (pipe) → subprocess stdin → subprocess file |

### ✅ Monitor Server (python server.py, puerto 3000)
| Componente | Estado |
|:-----------|:------:|
| Stats GPU/CPU/RAM | ✅ Tiempo real vía pynvml + psutil |
| Chat Proxy | ✅ `/api/chat` → llama-server `/chat/completions` |
| TTS Endpoint | ✅ `/api/tts-piper` con auto-detect de idioma |
| TTS GPU Endpoint | ✅ `/api/tts-gpu` (OuteTTS vía llama-tts.exe) |
| ASR Endpoint | ✅ `/api/asr` (faster-whisper tiny, CPU ~300ms) |
| Debug UI | ✅ `/debug` con 4 tabs (Timeline/Analytics/Hardware/TTS) |
| Logging | ✅ Sistema enriquecido con export JSON y estadísticas |
| Detección idioma | ✅ ES/EN/JA con split_by_language |

### ✅ ASR (Voice Input) — COMPLETADO
| Componente | Estado |
|:-----------|:------:|
| faster-whisper | ✅ Instalado y cargado al iniciar server.py |
| Transcribir audio WAV | ✅ ~200-500ms por transcripción (tiny, CPU) |
| Micrófono en frontend (Chrome ASR) | ✅ Funcional con toggle Escucha Activa |
| Micrófono en frontend (Whisper ASR) | ✅ Envía WAV a /api/asr |
| Fallback a whisper-cli.exe | ✅ Mantenido para compatibilidad |

## 📊 Benchmarks Reales (RTX 3050 6GB, 5.28 GB VRAM usable)

### Modelos LLM Probados
| Modelo | VRAM | Tok/s | Prompt | Veredicto |
|--------|:----:|:-----:|:------:|:---------:|
| **Qwen3.5-2B-Q8** 🥇 | ~3.0 GB | **21-22** | 68 tok/s | ✅ En uso |
| **Gemma-4-E2B-Q4** 🥈 | ~3.5 GB | **24.3** | 109 tok/s | ✅ Alternativa |
| **DeepSeek-R1-8B-Q4** | ~5.0 GB | **8.9** | 5.1 tok/s | ⚠️ Lento |

### TTS — Comparativa de Métodos
| Método | Latencia | Estado |
|:-------|:--------:|:------:|
| **Piper Python API** 🥇 | **~60ms** | ✅ Activo |
| PiperPersistentProcess (pipe) | ~2100ms | Fallback |
| Piper subprocess stdin | ~2400ms | Fallback |
| OuteTTS GPU (llama-tts.exe) | ~13000ms | Experimental |

### Hardware Real
- CPU: Intel Core i5-13420H (8 núcleos, 12 hilos)
- RAM: 16.5 GB total (~5.7 GB libre con apps)
- GPU: NVIDIA RTX 3050 Laptop 6 GB
- VRAM usable real: **5.28 GB** (735 MB en reposo)

### Presupuesto de Memoria
| Componente | VRAM | RAM |
|:----------:|:----:|:---:|
| Qwen3.5-2B-Q8 | ~3.0 GB | — |
| Piper TTS (ONNX CPU) | — | ~150 MB |
| KV Cache | ~0.5 GB | — |
| Monitor Server | — | ~100 MB |
| **Total** | **~3.5 GB** | **~250 MB** |
| **Margen** | **~1.8 GB** | **~5.5 GB libre** |

## 🎯 Estado de la Implementación

### Fase 1 ✅ — Núcleo texto (COMPLETADO)
- ✅ llama-server con Qwen3.5-2B-Q8
- ✅ Monitor server (python server.py)
- ✅ Chat proxy (OpenAI-compatible)
- ✅ Frontend Plan A (HTML+JS)
- ✅ Debug UI (/debug)
- ✅ Sistema de logs enriquecido

### Fase 2 ✅ — TTS (COMPLETADO)
- ✅ Piper Python API (~45ms latencia)
- ✅ Modelos ES y EN precargados en memoria
- ✅ Detección automática de idioma
- ✅ Split multilingüe (ES/EN/JA)
- ✅ Endpoint /api/tts-piper

### Fase 3 ✅ — Pipeline de Voz (COMPLETADO)
- ✅ faster-whisper integrado (Python API, modelo tiny en CPU)
- ✅ ASR endpoint /api/asr con faster-whisper como primario
- ✅ Micrófono en frontend con ambas opciones (Chrome ASR y Whisper ASR)
- ✅ Pipeline: Audio → ASR → LLM → TTS (completo)

### Fase 4 📋 — Mejoras Futuras
- [ ] Caché de respuestas frecuentes
- [ ] Streaming de audio TTS
- [ ] Voice cloning (OuteTTS speaker file)
- [ ] Modo Traductor mejorado (pares de idiomas dinámicos)

## 🔧 Cómo Usar

```bash
# 1. Iniciar todo con un clic
start_server.bat

# 2. Abrir en navegador
# Interfaz principal: frontend/plan-a/index.html
# Debug: http://localhost:3000/debug

# 3. Endpoints útiles
# Chat:      POST http://localhost:3000/api/chat
# TTS:       POST http://localhost:3000/api/tts-piper
# Stats:     GET  http://localhost:3000/api/stats
# Logs:      GET  http://localhost:3000/api/logs
# Hardware:  GET  http://localhost:3000/api/hardware
```
