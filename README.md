# 🎙️ Alex Voice — Asistente Local con IA Multilingüe

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![CUDA](https://img.shields.io/badge/CUDA-12.4-green)](https://developer.nvidia.com/cuda-toolkit)

**Alex Voice** es un asistente de voz con inteligencia artificial que corre **100% local** en tu PC con GPU NVIDIA. Soporta **Español, Inglés y Japonés** con 3 modos de interacción especializados.

Creado por [SCP-076](https://github.com/SCP-00) · Coded with ❤️ by [Buffy](https://codebuff.com) (AI Agent)

---

## 🚀 Inicio Rápido

### Opción 1: Script automático (recomendado)

```bash
# 1. Descarga el ZIP desde GitHub
# 2. Ejecuta setup.bat (descarga e instala todo automáticamente)
# 3. Ejecuta run.bat y selecciona el modo deseado
```

### Opción 2: Manual

```bash
# Requisitos: Python 3.10+, CUDA 12.4+, GPU NVIDIA 4GB+

# 1. Instalar dependencias
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install argostranslate faster-whisper qwen-tts

# 2. Descargar llama-server desde:
#    https://github.com/ggml-org/llama.cpp/releases

# 3. Descargar modelo Qwen2.5-1.5B-Q4_K_M (~1.1GB):
#    https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF

# 4. Iniciar
python launcher.py                    # Teacher + Conversation (puerto 3000)
python translator_server.py           # Traductor (puerto 3003)
```

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    ALEX VOICE                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐    ┌──────────────────────────┐    │
│  │  Teacher + Conv     │    │  Translator               │    │
│  │  (puerto 3000)      │    │  (puerto 3003)            │    │
│  │                     │    │                          │    │
│  │  LLM: Qwen2.5-1.5B │    │  STT: faster-whisper CPU  │    │
│  │  TTS: Kokoro/Piper  │    │  TRANS: argos CPU        │    │
│  │  ASR: faster-w      │    │  TTS: Qwen3-TTS GPU      │    │
│  │  Caché: LRU 50      │    │  SIN LLM                 │    │
│  └─────────────────────┘    └──────────────────────────┘    │
│                                                             │
│  ┌──────────────────────────────────────────────────┐       │
│  │  llama-server (GPU, puerto 8081)                  │       │
│  │  Qwen2.5-1.5B-Q4_K_M ~1.2GB VRAM                  │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Modos de Uso

### 🎓 Teacher
Enseñanza de idiomas con explicaciones estructuradas.
- Formato multi-output: 【TEXT】/【PRONUNCIATION】/【TRANSLATION】/【EXPLANATION】/【EXERCISE】
- TTS solo lee 【TEXT】 — pronunciación y traducción se ven en pantalla
- Ideal para aprender vocabulario y gramática

### 💬 Conversation
Charla natural para practicar idiomas.
- Responde SIEMPRE en el mismo idioma que escribes
- Cross-language probado: EN, ES, JA, FR
- 100% de acierto en benchmarks

### 🌍 Translator (servidor independiente)
Traducción profesional con audio de alta calidad.
- **STT:** faster-whisper (CPU) — reconocimiento de voz
- **TRANS:** argos-translate (CPU) — traducción offline EN/ES/JA
- **TTS:** Qwen3-TTS-CustomVoice (GPU) — audio natural con voces pre-definidas
- Selector manual de idiomas FROM/TO
- Sin LLM — servicio ligero y especializado

---

## 📊 VRAM Usage

| Modo | Componentes | VRAM |
|:-----|:------------|:----:|
| **Teacher/Conversation** | Qwen2.5-1.5B (GPU) + Kokoro (CPU) | **~1.2 GB** |
| **Translator** | Qwen3-TTS-0.6B (GPU) + argos (CPU) | **~2.0 GB** |
| Ambos simultáneos | — | No recomendado |

### RTX 4060 8GB — Cabe todo sobrado
- LLM: ~1.2 GB
- Qwen3-TTS: ~2.0 GB
- Libre: ~4.8 GB ✅

---

## ⚡ Benchmarks

### TTFT (Time to First Token)

| Escenario | Cold (1ra vez) | Warm (2da vez) |
|:----------|:--------------:|:--------------:|
| Prompt corto | 0.38s | **0.26s** |
| Persona (~200 tok) | 1.38s | **0.41s** |
| Teacher (~500 tok) | 2.27s | **0.43s** |

### Cross-Language (22 pruebas)

| Modo | Aciertos | Tiempo |
|:-----|:--------:|:------:|
| **Conversation** | **5/5 (100%)** | 4.07s |
| **Translator** | **10/10 (100%)** | 3.14s |
| **Teacher** | 4/7 (57%) | 4.96s |

### Traducción argos-translate (CPU)

| Par | Tiempo | Resultado |
|:----|:------:|:----------|
| EN→ES | **2.3s** | Hola, ¿cómo estás? |
| ES→EN | **1.2s** | Good morning how are you? |
| EN→JA | **0.5s** | アニメが好き |

### Qwen3-TTS (GPU, 2GB VRAM)

| Idioma | Generación | Audio | Velocidad |
|:-------|:----------:|:-----:|:---------:|
| Inglés (Vivian) | 8.65s | 2.9s | ~3x RT |
| Español (Serena) | 7.02s | 2.7s | ~2.6x RT |

---

## 🔧 Requisitos

### Hardware

| Componente | Mínimo | Recomendado |
|:-----------|:------:|:-----------:|
| **GPU** | NVIDIA 4GB VRAM | RTX 3050 6GB / RTX 4060 8GB |
| **RAM** | 8 GB | 16 GB |
| **Disco** | 10 GB libres | 20 GB libres |
| **SO** | Windows 10/11 | Windows 11 |
| **CUDA Driver** | 12.4+ | Driver 610+ |

### Software

| Herramienta | Versión | Instalación |
|:------------|:-------:|:------------|
| Python | 3.10+ | [python.org](https://www.python.org/) |
| CUDA Toolkit | 12.4 | `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124` |
| CUDA Toolkit (compilación) | 12.4+ | [Descargar](https://developer.nvidia.com/cuda-downloads) - Necesario para flash-attn |
| llama.cpp | b9479+ | Descargar de [GitHub Releases](https://github.com/ggml-org/llama.cpp/releases) |
| Git | Cualquiera | [git-scm.com](https://git-scm.com/) (opcional) |

### Python Dependencies

```bash
# 1. Base
pip install wheel ninja

# 2. Core - PyTorch CUDA
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124

# 3. Traducción (CPU)
pip install argostranslate

# 4. TTS calidad (GPU)
pip install qwen-tts

# 5. Reconocimiento de voz (CPU)
pip install faster-whisper

# 6. TTS ligero (opcional)
pip install kokoro

# 7. Utilidades
pip install psutil pynvml numpy

# 8. [OPCIONAL] flash-attn (~2-3x aceleración Qwen3-TTS)
# Requiere: CUDA Toolkit 12.4+ (descargar de nvidia.com)
$env:CUDA_PATH = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4"
$env:CUDA_HOME = $env:CUDA_PATH
pip install flash-attn --no-build-isolation
```

---

## 📁 Estructura del Proyecto

```
Alex_Voice/
│
├── B/
│   ├── server.py              ← Servidor Teacher+Conversation (puerto 3000)
│   ├── AGENT.md               ← Instrucciones del agente
│   ├── plan.md                ← Plan de implementación
│   └── README.md              ← Documentación del servidor
│
├── shared/
│   └── translator.py          ← Módulo compartido (prompts en inglés, parsing multi-output)
│
├── frontend/
│   ├── plan-b/
│   │   └── index.html         ← UI de Teacher+Conversation
│   └── translator/
│       └── index.html         ← UI del Traductor
│
├── translator_server.py       ← Servidor traductor (puerto 3003)
├── launcher.py                ← Lanzador unificado (inicia todo)
│
├── setup.bat                  ← Instalación automática
├── run.bat                    ← Inicio rápido (menú interactivo)
│
├── CREDITS.md                 ← Créditos del proyecto
├── LICENSE                    ← Licencia MIT
└── README.md                  ← Esta documentación
```

---

## 🔌 API Endpoints

### Servidor Principal (`localhost:3000`)

| Endpoint | Método | Descripción |
|:---------|:------:|:------------|
| `/api/chat` | POST | Chat con modo (teacher/conversation) + multi-output |
| `/api/tts` | POST | TTS Kokoro → Piper (fallback) |
| `/api/tts/stream` | POST | TTS streaming |
| `/api/asr` | POST | Reconocimiento de voz |
| `/api/stats` | GET | Estadísticas en vivo (GPU/CPU/RAM) |
| `/api/cache/stats` | GET | Estadísticas de caché LRU |
| `/api/cache/clear` | GET | Limpiar caché |

### Servidor Traductor (`localhost:3003`)

| Endpoint | Método | Descripción |
|:---------|:------:|:------------|
| `/api/translate` | POST | Traducir texto (from_lang, to_lang, text) |
| `/api/tts` | POST | Audio Qwen3-TTS (text, language, speaker) |
| `/api/asr` | POST | Reconocimiento de voz |
| `/api/load` | POST | Precargar Qwen3-TTS en GPU |
| `/api/unload` | POST | Descargar Qwen3-TTS de GPU |
| `/api/status` | GET | Estado del servidor |

---

## 🧪 Benchmarks Realizados

| Benchmark | Archivo | Resultado |
|:----------|:--------|:----------|
| TTFT (tiempos reales) | `benchmark_ttft_real.py` | ~0.4s warm, ~2.3s cold |
| Cross-language matrix | `benchmark_crosslang.py` | 19/22 tests (86%) |
| Qwen3-TTS + NLLB | `benchmark_qwen3_nllb.py` | Qwen3-TTS 2GB VRAM ✅ |
| Planes A/B/C/D | `benchmark_plans_completo.py` | B y C ganadores (6/9) |

---

## 🤝 Contribuir

1. Fork el proyecto
2. Crea tu rama (`git checkout -b feature/mejora`)
3. Commit (`git commit -am 'feat: mejora'`)
4. Push (`git push origin feature/mejora`)
5. Abre un Pull Request

---

## 📝 Licencia

Este proyecto está bajo licencia MIT. Ver [LICENSE](LICENSE) para más detalles.

## 👤 Autor

**SCP-076** (Victor Buendia)

## 🤖 Créditos

Coded with ❤️ by **Buffy** — Asistente estratégico basado en DeepSeek-v4-flash.
[Codebuff](https://codebuff.com) · Arquitectura, implementación y optimización.

---

*Alex Voice — Asistente Local con IA Multilingüe · 2026*
