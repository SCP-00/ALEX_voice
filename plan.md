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

| Tarea | Por qué | Estado |
|:------|:--------|:------|
## ✅ Optimizaciones 2026-06-08

### Fase 5: Precarga Dual en Translator (OPTIMIZACIÓN PRINCIPAL)

**Antes:** Whisper y Qwen3-TTS se cargaban bajo demanda con VRAM swap (~26s cold start).
**Ahora:** Ambos modelos se precargan al inicio y PERMANECEN en VRAM. Latencia ~0 en primera request.

| Componente | Antes | Ahora | Mejora |
|:-----------|:-----:|:-----:|:------:|
| Whisper large-v3-turbo | Lazy-load (~3s) | Precarga en startup | **Cold start eliminado** |
| Qwen3-TTS 0.6B | Lazy-load + swap (~26s) | Precarga + CUDA warmup | **Cold start eliminado** |
| VRAM swap ASR↔TTS | Sí, ~2s de latencia | **No swap** | **Latencia ~0** |
| /api/load, /api/unload | Endpoints separados | Eliminados | **Menos complejidad** |
| Pipeline paralelo | ThreadPoolExecutor | Secuencial simplificado | **-50% lineas** |

### Fase 6: Sistema de Logging Global

Formato consistente en **los 3 servicios**: `[HH:MM:SS] [SERVICE] [LEVEL] mensaje`

| Archivo | Nivel | Servicio |
|:--------|:-----:|:---------|
| `translator.py` | `log_ok/log_warn/log_err/log_info/log_debug` | `[Translator]` |
| `server.py` | `_log(OK/WARN/ERROR/INFO)` + helpers | `[Server]` |
| `conv_server.py` | `log_info()` | `[Conversation]` |
| `menu_server.py` | `log()` (sin timestamp) | `[Menu]` |

### Modelos Descargados y Verificados

| Modelo | Tamaño | VRAM | Estado |
|:-------|:------:|:----:|:------:|
| Qwen2.5-1.5B Q4_K_M | 1.1 GB | 1.2 GB | ✅ Funcional (Vulkan 49 tok/s) |
| **Qwen3.5-2B Q4_K_M** | **1.2 GB** | **~1.5-2.0 GB** | ✅ **DESCARGADO** — pendiente de benchmark vs 1.5B |
| Qwen3-TTS 0.6B-CustomVoice | ~2.3 GB | **2.0 GB** | ✅ Descargado, warmup CUDA Graphs OK |
| Qwen3-TTS **1.7B**-CustomVoice | ~4.0 GB | **NO Cabe** (OOM) | ❌ Requiere 4.1GB+ VRAM, excede 5.79GB total — **no usar** |
| Whisper small | cacheado | 1.5 GB | ✅ Teacher/Conversation |
| Whisper large-v3-turbo | cacheado | 3.0 GB | ✅ Translator (precargado) |
| Kokoro-82M + Piper | 2.3 GB | CPU | ✅ TTS Teacher/Conv |
| Piper (EN+ES) | 135 MB | CPU | ✅ Fallback TTS |
| argos-translate EN↔ES↔JA | — | CPU | ✅ Instalado y verificado |

### Dependencias Corregidas

| Problema | Solución |
|:---------|:---------|
| numpy 1.26.4 rompía Whisper large-v3-turbo (RecursionError en Python 3.13) | ⬆️ numpy 2.4.6 — Whisper carga en **3.1s** ✅ |
| Kokoro requiere misaki>=0.7.16 pero no disponible para Python 3.13 | Funciona con misaki 0.7.4 — warning inofensivo |
| Kokoro requiere numpy==1.26.4 | Funciona con numpy 2.4.6 — warning inofensivo |

### VRAM Usage Post-Optimización

| Escenario | Componentes | VRAM Total |
|:----------|:------------|:----------:|
| Teacher/Conversation activo | llama-server (1.2G) + Whisper small (1.5G) | **~2.7 GB** ✅ |
| Translator activo | Whisper large (3.0G) + Qwen3-TTS 0.6B (2.0G) | **~5.0 GB** ✅ |

---

## 📊 GPU Benchmarks: CPU vs Vulkan vs CUDA

### Resultados (Qwen2.5-1.5B Q4_K_M, RTX 3050 6GB)

| Backend | Prompt (tok/s) | Generación (tok/s) | VRAM | TTFT | vs CPU | Estado |
|:--------|:--------------:|:------------------:|:----:|:----:|:------:|:------:|
| 🖥️ **CPU** (baseline) | **93.2** | **41.9** | 0 MB | ~300ms | — | ✅ Siempre disponible |
| ⚡ **Vulkan** (GPU) | **91.4** | **49.0** | 1246 MB | ~230ms | **+17%** 🏆 | ✅ **GANADOR** |
| 🎮 **CUDA** (GPU) | ❌ | ❌ | ❌ | ❌ | ❌ | ⛔ Incompatible con glibc 2.41 |

### Análisis

**Vulkan — 🏆 Ganador**
- **17% más rápido** que CPU en generación (49.0 vs 41.9 tok/s)
- **24% menor latencia** (TTFT 230ms vs 300ms)
- **Libera CPU** para TTS (Kokoro), ASR (Whisper) y otras tareas
- **VRAM:** 1.2 GB de 6 GB disponibles — queda espacio para Whisper small
- **GPU Temp:** 41°C — fresco y eficiente
- **Setup:** sin dependencias extra (vulkan-tools ya instalado)

**CUDA — ⛔ No disponible en Kali 2026.2**
- **Causa:** CUDA 12.4 usa `noexcept(true)` en funciones math, glibc 2.41 declara las mismas → conflicto de ABI
- **Solución:** CUDA 12.6+ necesario, pero el runfile no está disponible (solo 48 MB de redirección)
- **nvcc instalado:** `/usr/local/cuda-12.4/bin/nvcc` (V12.4.99) pero incompatible
- **Estimado:** CUDA daría ~80-120 tok/s (~2-3x CPU), pero requiere glibc más antigua (Ubuntu 22.04/24.04)

### Decisión Final

```
╔══════════════════════════════════════════════════════╗
║             🏆 VULKAN ES LA MEJOR OPCIÓN             ║
╠══════════════════════════════════════════════════════╣
║  ✅ Funciona perfectamente en Kali Linux             ║
║  ✅ 17% más rápido que CPU en generación             ║
║  ✅ 24% menor latencia (TTFT)                       ║
║  ✅ Libera CPU para TTS y traducción                 ║
║  ✅ Sin problemas de compatibilidad                  ║
║  ✅ Ya compilado y listo para usar                   ║
║                                                      ║
║  📦 Binario: llama-server-bin/llama-server-vulkan    ║
║  📦 Librería: libggml-vulkan.so.0 (56 MB)           ║
╚══════════════════════════════════════════════════════╝
```

### Backend Inteligente

El sistema ahora detecta automáticamente el mejor backend:

```python
BACKEND_PRIORITY = [
    ("llama-server-cuda",   "🎮 CUDA"),   # GPU nativa NVIDIA
    ("llama-server-vulkan", "⚡ Vulkan"),  # GPU via Vulkan
    ("llama-server",        "🖥️ CPU"),     # CPU fallback
]
```

**Scripts actualizados:** `launcher.py`, `menu_server.py`, `setup.sh`

---

## 🏗️ Arquitectura Actual

```
┌─────────────────────────────────────────────────────────────┐
│                     ALEX VOICE                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────┐                                       │
│  │  MENU (port 5000) │  ← http://localhost:5000              │
│  │  menu_server.py   │  Start/stop modes, lifecycle mgmt    │
│  └────────┬──────────┘                                       │
│           │                                                  │
│  ┌────────┴──────────┐    ┌──────────────────────────┐      │
│  │  Teacher + Conv   │    │  Translator (3003)       │      │
│  │  (3000 / 3001)    │    │  ASR: whisper large GPU  │      │
│  │  LLM: Qwen2.5-1.5B│    │  TRANS: argos CPU        │      │
│  │  TTS: Kokoro/Piper│    │  TTS: Qwen3-TTS GPU      │      │
│  │  ASR: whisper sm. │    │  NO LLM                  │      │
│  │  Cache: LRU 50    │    │  ↕ VRAM swap (ASR↔TTS)   │      │
│  └────────├──────────┘    └──────────────────────────┘      │
│           │                                                  │
│  ┌────────┴─────────────────────────────────────────────┐   │
│  │  llama-server (port 8081)  — BACKEND INTELLIGENTE    │   │
│  │  ┌─────────────────────────────────────────────────┐ │   │
│  │  │  Prioridad:                                      │ │   │
│  │  │  1. 🎮 llama-server-cuda  (CUDA, ~80-120 tok/s) │ │   │
│  │  │  2. ⚡ llama-server-vulkan (Vulkan, ~49 tok/s)   │ │   │
│  │  │  3. 🖥️ llama-server        (CPU, ~42 tok/s)     │ │   │
│  │  └─────────────────────────────────────────────────┘ │   │
│  │  Qwen2.5-1.5B-Q4_K_M ~1.2GB VRAM (Vulkan/CUDA)     │   │
│  └─────────────────────────────────────────────────────┘   │
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
- **Vulkan GPU backend** (+17% generación vs CPU, menor latencia)
- Kokoro-82M con RTF 0.24x (tiempo real holgado)
- argos-translate funcional EN↔ES↔JA
- Gestión de VRAM automática ASR↔TTS en Translator
- **Backend inteligente:** detecta y usa el mejor backend disponible (Vulkan > CPU)
