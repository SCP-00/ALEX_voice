# 📋 Alex Voice — Plan de Mejora (KISS)

**Hardware actual (Linux):** RTX 3050 6GB Laptop · i5-13420H · 15.3 GB RAM · 214 GB libres
**VRAM real en Linux:** 5.79 GB (vs 5.28 GB en Windows — **~500 MB más!**)
**Última migración:** Windows → Linux (2026-06-05)

---

## ✅ Completado

### Fase 1-3: Funcionalidad base
- Teacher + Conversation modes
- AEC híbrido (autoGainControl + isTtsPlaying + mute-while-speaking)
- Translator con Whisper Large-v3-Turbo, argos-translate, Qwen3-TTS
- Optimizaciones TTS: chunk 1500 chars, max_new_tokens 6144, pipeline paralelo

### Fase 4: Migración completa a Linux (Junio 2026)
- `setup.sh` — Script de instalación Linux (Ubuntu/Debian)
- `run.sh` / `start_alex.sh` — Inicio rápido para Linux
- `conv_server.py` — Creado (faltaba en el repo)
- `launcher.py` — Adaptado con detección automática Windows/Linux
- `menu_server.py` — Ruta CUDA dinámica (ya no hardcodea python3.13)
- `server.py` — Kokoro API v0.7.16 fix, Piper path Linux, IS_LINUX constant
- `pynvml` reemplazado por `nvidia-ml-py` (elimina FutureWarning)
- argos-translate EN↔ES↔JA instalado y probado

---

## 📊 Benchmarks Reales (Linux — RTX 3050 6GB)

### VRAM
| Prueba | Resultado |
|:-------|:---------:|
| VRAM total detectada | **5.79 GB** (6144 MiB) |
| VRAM libre (inicio) | 5.84 GB (95%) |
| Bloque contiguo máximo | **4.0 GB** ✅ |
| Bloque 3.5 GB | ✅ (suficiente para Whisper large-v3-turbo) |
| Bloque 2.0 GB | ✅ (suficiente para Qwen3-TTS) |
| Bloque 1.2 GB | ✅ (suficiente para Qwen2.5-1.5B Q4) |

### TTS: Kokoro-82M (CPU)
| Métrica | Valor |
|:--------|:-----:|
| Carga inicial (cold) | **1.6s** |
| EN TTS ("Hello...") | **466ms** para 1.95s audio → **RTF 0.24x** 🚀 |

### Traducción: argos-translate
| Par | Tiempo |
|:---:|:------:|
| EN→ES | 1.9s |
| ES→EN | 1.3s |
| EN→JA | 1.0s |
| JA→EN | 0.7s |

### Diferencia clave con Windows
| Métrica | Windows (original) | Linux (actual) | Diferencia |
|:--------|:------------------:|:--------------:|:----------:|
| VRAM usable | 5.28 GB | 5.79 GB | **+9.7%** 🚀 |
| RAM | 16.5 GB | 15.3 GB | -7% (similar) |
| Python | 3.10 | 3.13.12 | Más moderno |

---

## 📊 Comparativa Completa: Linux vs Windows

### Kokoro TTS (RTF — más bajo = mejor)
| Texto | Windows (original) | Linux (actual) | Mejora |
|:------|:-------:|:-----:|:------:|
| EN corto | ~2.50x | **0.21x** | **~12x más rápido** 🚀 |
| EN medio | ~2.50x | **0.03x** | **~80x más rápido** 🚀🚀 |
| ES corto | ~1.00x | **0.10x** | **~10x más rápido** 🚀 |
| ES medio | ~1.00x | **0.03x** | **~33x más rápido** 🚀🚀 |

### argos-translate
| Par | Tiempo |
|:---:|:------:|
| EN→ES | 1.9s |
| ES→EN | 1.3s |
| EN→JA | 1.0s |
| JA→EN | 0.7s |

### VRAM (max contiguo)
| Bloque | Resultado |
|:------:|:---------:|
| 512 MB | ✅ |
| 1 GB | ✅ |
| 2 GB | ✅ |
| 3 GB | ✅ |
| 3.5 GB | ✅ |
| **4 GB** | **✅ Máximo** |

---

## ⚠️ Pendiente (mejora futura)

| Tarea | Por qué |
|:------|:--------|
| Instalar CUDA Toolkit (`nvcc`) | Necesario para compilar `flash-attn` (2-3x más rápido Qwen3-TTS) |
| `sudo apt install nvidia-cuda-toolkit` o descargar de NVIDIA | Luego: `pip install flash-attn --no-build-isolation` |
| Probar modelo Q8 (Qwen3.5-2B) | Con 5.79 GB VRAM hay espacio para un modelo más grande y preciso |

---

## 🏗️ Arquitectura Actual

```
┌───────────────────────────────────────────────────────────┐
│                     ALEX VOICE                              │
├───────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────┐                                      │
│  │  MENU (port 5000) │  ← http://localhost:5000             │
│  │  menu_server.py   │  Start/stop modes, lifecycle mgmt   │
│  └────────┬──────────┘                                      │
│           │                                                  │
│  ┌────────┴──────────┐    ┌──────────────────────────┐      │
│  │  Teacher + Conv   │    │  Translator (3003)       │      │
│  │  (3000 / 3001)    │    │  ASR: whisper large GPU  │      │
│  │  LLM: Qwen2.5-1.5B│    │  TRANS: argos CPU        │      │
│  │  TTS: Kokoro/Piper│    │  TTS: Qwen3-TTS GPU      │      │
│  │  ASR: whisper sm. │    │  NO LLM                  │      │
│  │  Cache: LRU 50    │    │  ↕ VRAM swap (ASR↔TTS)   │      │
│  └───────────────────┘    └──────────────────────────┘      │
│                                                             │
│  ┌────────────────────────────────────────────────────┐     │
│  │  llama-server (GPU, port 8081)                     │     │
│  │  Qwen2.5-1.5B-Q4_K_M ~1.2GB VRAM                   │     │
│  └────────────────────────────────────────────────────┘     │
└───────────────────────────────────────────────────────────┘
```

---

## 📌 Estado del Proyecto

**100% funcional en Linux.** Todos los modos operativos:
- ✅ Teacher (3000)
- ✅ Conversation (3001)
- ✅ Translator (3003)
- ✅ Menú principal (5000)

**Rendimiento mejorado** gracias a:
- ~500 MB más de VRAM disponible en Linux
- Kokoro-82M con RTF 0.24x (tiempo real holgado)
- argos-translate funcional EN↔ES↔JA
- Gestión de VRAM automática ASR↔TTS en Translator
