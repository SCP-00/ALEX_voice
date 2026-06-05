# 🎙️ Alex Voice — Asistente Local con IA Multilingüe

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![CUDA](https://img.shields.io/badge/CUDA-12.4-green)](https://developer.nvidia.com/cuda-toolkit)

**Alex Voice** es un asistente de voz con inteligencia artificial que corre **100% local** en tu PC con GPU NVIDIA. Soporta múltiples idiomas con 3 modos de interacción especializados.

- 🌐 **Windows** (setup.bat) — Probado en Windows 11
- 🐧 **Linux** (setup.sh) — Migrado 2026-06-05

Creado por [SCP-076](https://github.com/SCP-00) · Coded with ❤️ by [Buffy](https://codebuff.com) (AI Agent)

---

## 🚀 Inicio Rápido

### 🪟 Windows

```bash
# 1. Descarga el ZIP desde GitHub
# 2. Haz doble clic en setup.bat (descarga modelos + instala dependencias)
# 3. Haz doble clic en run.bat (abre menú principal en el navegador)
# 4. Selecciona el modo deseado: 🎓 Teacher, 💬 Conversación o 🌍 Traductor
```

### 🐧 Linux (Ubuntu/Debian)

```bash
# 1. Clona el repositorio
git clone https://github.com/SCP-00/ALEX_voice.git
cd Alex_Voice

# 2. Setup automático (instala todo)
chmod +x setup.sh
./setup.sh

# 3. Iniciar menú
./run.sh
# O manual: python3 menu_server.py → http://localhost:5000
```

### ⚙️ Manual (Cross-platform)

```bash
# Requisitos: Python 3.10+, CUDA 12.4+, GPU NVIDIA 4GB+

# 1. Instalar dependencias
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install kokoro piper-tts faster-whisper qwen-tts argostranslate

# 2. Descargar llama-server desde:
#    https://github.com/ggml-org/llama.cpp/releases
#    Extraer llama-server a ./llama-server-bin/

# 3. Descargar modelo Qwen2.5-1.5B-Q4_K_M (~1.1GB):
mkdir -p models
curl -L -o models/qwen2.5-1.5b-q4_k_m.gguf \
  https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf

# 4. Iniciar menú principal
python menu_server.py                    # Abre http://localhost:5000
```

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    ALEX VOICE                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────┐                                           │
│  │  MENÚ PRINCIPAL   │  ← Abre http://localhost:5000             │
│  │  (menu_server.py) │  Gestión de ciclo de vida de modos       │
│  │  puerto 5000      │  API REST: /api/start, /api/stop         │
│  └────────┬──────────┘                                           │
│           │                                                      │
│  ┌────────┴──────────┐    ┌──────────────────────────┐          │
│  │  Teacher + Conv   │    │  Translator               │          │
│  │  (3000 / 3001)    │    │  (puerto 3003)            │          │
│  │                   │    │                           │          │
│  │  LLM: Qwen2.5-1.5B│    │  STT: whisper large GPU   │          │
│  │  TTS: Kokoro/Piper│    │  TRANS: argos CPU         │          │
│  │  ASR: whisper sm. │    │  TTS: Qwen3-TTS 0.6B GPU │          │
│  │  Caché: LRU 50    │    │  SIN LLM                  │          │
│  └───────────────────┘    └──────────────────────────┘          │
│                    ↕ (swap VRAM)                                 │
│  ┌────────────────────────────────────────────────────┐         │
│  │  llama-server (GPU, puerto 8081)                    │         │
│  │  Qwen2.5-1.5B-Q4_K_M ~1.2GB VRAM                    │         │
│  └────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Modos de Uso

### 🎓 Teacher
Enseñanza de idiomas con explicaciones estructuradas.
- Formato multi-output: **【TEXT】** / **【PRONUNCIATION】** / **【TRANSLATION】** / **【EXPLANATION】** / **【EXERCISE】**
- **【TTS_READING】** : el LLM genera una versión en Latin script para que Kokoro lea correctamente (romaji para JA, fonética para otros)
- TTS usa campo TTS_READING → TEXT → respuesta completa
- Ideal para aprender vocabulario y gramática

### 💬 Conversation
Charla natural para practicar idiomas con **memoria completa** (~20 mensajes de contexto).
- Responde SIEMPRE en el mismo idioma que escribes
- Cross-language probado: EN, ES, JA, FR
- Memoria conversacional enviada al backend en cada turno

### 🌍 Translator (servidor independiente)
Traducción profesional con audio de alta calidad.
- **STT:** faster-whisper large-v3-turbo (GPU) — ASR multilingüe de alta precisión
- **TRANS:** argos-translate (CPU) — traducción offline EN/ES/JA
- **TTS:** Qwen3-TTS-CustomVoice (GPU) — audio natural con 10 idiomas nativos. **Optimizado**: chunk 1500 chars, max_new_tokens 6144, pipeline CPU↔GPU paralelo, warmup 2-pasos, xformers integrado
- **VRAM:** ASR y TTS comparten GPU pero se swap automáticamente (solo 1 modelo a la vez)
- **Sliders de voz:** panel colapsable con control de calma, velocidad y calidez
- Selector manual de idiomas FROM/TO
- Sin LLM — servicio ligero y especializado

---

## 📋 Menú Principal

El sistema ahora tiene un **hub central** en `http://localhost:5000` que gestiona el ciclo de vida de todos los modos:

```
1️⃣  Tecla [1] → Inicia Teacher  (abre puerto 3000)
2️⃣  Tecla [2] → Inicia Conversación (abre puerto 3000)
3️⃣  Tecla [3] → Inicia Traductor (abre puerto 3003)
Esc        → Detiene el modo activo
```

- **Overlay de carga** con barra de progreso mientras se carga el modelo en GPU
- **Polling de estado** cada 3 segundos
- **Botón "← Volver al menú"** en cada modo — detiene servidores y regresa al hub
- **Gestión de procesos**: al detener un modo, se matan todos los subprocesos (llama-server incluido)

---

## 📊 VRAM Usage

| Modo | Componentes | VRAM |
|:-----|:------------|:----:|
| **Teacher/Conversation** | Qwen2.5-1.5B (GPU) + Kokoro (CPU) + Whisper small (GPU) | **~2.7 GB** |
| **Translator** | Whisper large-v3-turbo O Qwen3-TTS-0.6B (GPU, 1 a la vez) | **~3.5 GB** (carga bajo demanda) |

> ⚡ ASR y TTS nunca se usan simultáneamente. Al cambiar de ASR a TTS (o viceversa), el modelo anterior se libera de VRAM automáticamente.

---

## ⚡ Benchmarks Reales

### TTS: Qwen3-TTS 0.6B (RTX 3050 6GB)

| Texto | Audio generado | Tiempo GPU | RTF |
|:------|:--------------:|:----------:|:---:|
| Corto (~60 chars) | 3.4s | 8.9s | **2.6x** |
| Largo (~350 chars) | 21.4s | 57.7s | **2.7x** |

**Cold start** (1er request): ~26s (carga 6s + warmup 2× ~10s)
**Warm**: ~9-10s para texto corto
> RTF 2.6x = el TTS no es tiempo real en RTX 3050. Opciones de mejora: flash-attn (2-3x), Piper TTS (CPU, más rápido, menor calidad).

### ASR: Whisper large-v3-turbo (Translator) — WER estimado

| Idioma | WER | VRAM |
|:-------|:---:|:----:|
| Español | ~5% | 3.5 GB |
| Inglés | ~3% | 3.5 GB |
| Japonés | ~7% | 3.5 GB |

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

# 6. TTS ligero (CPU)
pip install kokoro piper-tts

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
├── server.py                   ← Servidor Teacher+Conversation (puerto 3000)
├── translator.py                ← Servidor Traductor (puerto 3003)
├── menu_server.py               ← Menú principal (puerto 5000) ★ NUEVO
├── launcher.py                  ← Lanzador legacy (reemplazado por menu_server)
│
├── frontend/
│   ├── index.html               ← UI de Teacher+Conversation
│   ├── translator.html          ← UI del Traductor
│   └── menu.html                ← Menú principal con 3 tarjetas ★ NUEVO
│
├── prompts.py                   ← Prompts y parsing multi-output
│
├── setup.bat                    ← Instalador automático (6 pasos) ★ REESCRITO
├── run.bat                      ← Inicio rápido → menú principal ★ REESCRITO
│
├── models/                      ← Modelos descargados por setup.bat
│   ├── qwen2.5-1.5b-q4_k_m.gguf ← LLM (~1.1GB)
│   ├── es_ES-sharvard-medium.onnx ← Piper TTS ES
│   └── en_US-lessac-medium.onnx ← Piper TTS EN
│
├── llama-server-bin/            ← llama-server.exe descargado por setup.bat
│
├── AGENT.md                     ← Instrucciones del sistema (para IA)
├── plan.md                      ← Plan de mejora y métricas
├── LICENSE                      ← Licencia MIT
└── README.md                    ← Esta documentación
```

---

## 🔌 API Endpoints

### Menú Principal (`localhost:5000`)

| Endpoint | Método | Descripción |
|:---------|:------:|:------------|
| `/` | GET | Sirve `menu.html` |
| `/api/status` | GET | Estado actual: modo activo, servidores, llama-server alive |
| `/api/start/teacher` | POST | Inicia Teacher (llama-server + server.py en modo teacher) |
| `/api/start/conv` | POST | Inicia Conversación (llama-server + server.py en modo conversation) |
| `/api/start/translator` | POST | Inicia Traductor (translator.py) |
| `/api/stop` | POST | Detiene todos los servidores y procesos |

### Servidor Principal (`localhost:3000`)

| Endpoint | Método | Descripción |
|:---------|:------:|:------------|
| `/api/chat` | POST | Chat con modo (teacher/conversation) + multi-output + **TTS_READING** |
| `/api/tts` | POST | TTS Kokoro → Piper (fallback) |
| `/api/tts/stream` | POST | TTS streaming |
| `/api/asr` | POST | Reconocimiento de voz (faster-whisper) |
| `/api/stats` | GET | Estadísticas en vivo (GPU/CPU/RAM) |
| `/api/cache/stats` | GET | Estadísticas de caché LRU |
| `/api/cache/clear` | GET | Limpiar caché |

### Servidor Traductor (`localhost:3003`)

| Endpoint | Método | Descripción |
|:---------|:------:|:------------|
| `/api/translate` | POST | Traducir texto (from_lang, to_lang, text) |
| `/api/tts` | POST | Audio Qwen3-TTS (text, language, speaker, instruct, max_new_tokens, temperature) |
| `/api/asr` | POST | Reconocimiento de voz |
| `/api/load` | POST | Precargar Qwen3-TTS en GPU |
| `/api/unload` | POST | Descargar Qwen3-TTS de GPU |
| `/api/status` | GET | Estado del servidor |

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
