# 🎙️ Alex Voice — Asistente Local con IA Multilingüe (v3)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![CUDA](https://img.shields.io/badge/CUDA-12.4-green)](https://developer.nvidia.com/cuda-toolkit)

**Alex Voice** es un asistente de voz con IA que corre **100% local** en tu PC con GPU NVIDIA. Soporta múltiples idiomas con 3 modos especializados.

- 🐧 **Linux** — Probado en Kali Linux con RTX 3050 6GB
- 🌐 **Ollama API** — Modelo: `prometheus-orchestrator` (Qwen3.5 4B Instruct, 262K ctx, ~3GB VRAM)
- 🚫 Thinking desactivado — Respuestas directas sin delay de razonamiento

Creado por [SCP-076](https://github.com/SCP-00) · Coded with ❤️ by [Buffy](https://codebuff.com) (AI Agent)

---

## 🚀 Inicio Rápido

### 🐧 Linux

```bash
# 1. Clona el repositorio
git clone https://github.com/SCP-00/ALEX_voice.git
cd Alex_Voice

# 2. Setup
git checkout linux
chmod +x setup.sh && ./setup.sh

# 3. Asegúrate de que Ollama esté corriendo con el modelo:
ollama run prometheus-orchestrator  # primera vez (descarga si no existe)

# 4. Inicia el launcher
./alex-voice.sh
```

### ⚙️ Manual

```bash
# 1. Python venv y dependencias
python3 -m venv venv
source venv/bin/activate
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install faster-whisper onnxruntime silero-vad kokoro-onnx piper-tts cutlet unidic-lite
pip install transformers sentencepiece psutil pynvml numpy

# 2. Asegúrate de tener Ollama y el modelo
ollama serve &
ollama pull prometheus-orchestrator

# 3. Inicia el menú
python3 menu_server.py  # → http://localhost:5000
```

---

## 🏗️ Arquitectura v3

```
┌─────────────────────────────────────────────────────────────┐
│                    ALEX VOICE v3                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────┐                                      │
│  │  MENÚ PRINCIPAL   │  ← http://localhost:5000             │
│  │  menu_server.py   │  Start/stop modes + cleanup          │
│  └────────┬──────────┘                                      │
│           │                                                  │
│  ┌────────┴──────────┐    ┌──────────────────────────┐      │
│  │  Teacher + Conv   │    │  Translator (3003)       │      │
│  │  (3000 / 3001)    │    │  ASR: whisper small GPU  │      │
│  │                   │    │  VAD: Silero CPU         │      │
│  │  LLM via Ollama   │    │  TRANS: MarianMT GPU     │      │
│  │  TTS: Kokoro ONNX │    │  TTS: Kokoro ONNX CPU    │      │
│  │  ASR: whisper sm. │    │  Pipeline: async queue   │      │
│  │  VAD: Silero CPU  │    │  NO LLM (ligero)         │      │
│  └────────┬──────────┘    └──────────────────────────┘      │
│           │                                                  │
│  ┌────────┴──────────────────────────────────────────┐      │
│  │  Ollama API (localhost:11434/v1)                   │      │
│  │  Modelo: prometheus-orchestrator (Qwen3.5 4B)      │      │
│  │  262K contexto, thinking desactivado, ~3GB VRAM    │      │
│  └───────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Cambios v3 vs v2

| Componente | v2 | v3 | Beneficio |
|:-----------|:---|:---|:----------|
| **LLM Backend** | llama-server directo (GGUF) | Ollama API | Gestión de VRAM automática, thinking desactivado |
| **Modelo** | Qwen2.5-coder:3b (coder) | prometheus-orchestrator (Qwen3.5 4B Instruct) | JA/ES/EN correctos, 3x más rápido |
| **Contexto** | 8K tokens | 262K tokens | Conversaciones mucho más largas |
| **Thinking** | N/A | Desactivado (reasoning_format: none) | Respuestas directas sin delay |
| **Launcher** | run.sh | alex-voice.sh + alex-voice.desktop | Verifica Ollama, cleanup via API |
| **Pipeline** | Secuencial | Async threading (3 workers) | Percepción de fluidez ~150ms |

---

## 🎯 Modos de Uso

### 🎓 Teacher — Qwen3.5 4B Instruct via Ollama
Enseñanza de idiomas con explicaciones estructuradas.
- Formato multi-output: **【TEXT】** / **【PRONUNCIATION】** / **【TRANSLATION】** /* 【EXPLANATION】** / **【EXERCISE】**
- Thinking desactivado → respuestas directas sin delay
- Cutlet romanization para japonés (romaji automático)
- TTS: Kokoro ONNX con 54 voces y 5 idiomas

### 💬 Conversation — Qwen3.5 4B Instruct via Ollama
Charla natural para practicar idiomas con memoria completa (~20 mensajes).
- Thinking desactivado → fluidez máxima
- Cross-language probado: EN, ES, JA, FR, DE
- Silero VAD pre-filtro para mejor ASR

### 🌍 Translator (servidor independiente, sin LLM)
Traducción profesional con audio de alta calidad.
- Async Pipeline: ASR→Translation→TTS en 3 workers threading
- Mientras TTS reproduce oración N, GPU ya transcribe oración N+1
- Latencia percibida: ~150ms (vs 300ms secuencial)

---

## 📊 VRAM Budget (v3)

| Modo | Componentes | VRAM |
|:-----|:------------|:----:|
| **Teacher** | Ollama + Whisper small | **~4.5 GB** |
| **Conversation** | Ollama + Whisper small | **~4.5 GB** |
| **Translator** | Whisper small + MarianMT | **~1.7 GB** |

---

## ⚡ Benchmarks (v3, RTX 3050 6GB)

### Modelo: prometheus-orchestrator (Qwen3.5 4B Instruct)

| Idioma | Velocidad | Calidad |
|:-------|:---------:|:-------:|
| **EN** | **39.0 tok/s** | ✅ Correcto y estructurado |
| **ES** | **45.4 tok/s** | ✅ Español natural y correcto |
| **JA** | **45.2 tok/s** | ✅ Japonés correcto |

### Comparativa: coder vs instruct

| Métrica | qwen2.5-coder:3b | prometheus-orchestrator | Mejora |
|:--------|:----------------:|:----------------------:|:------:|
| EN quality | ✅ Buena | ✅ Excelente | — |
| ES quality | ❌ Alucinación | ✅ Español natural | 🔥 |
| JA quality | ❌ Self-intro | ✅ Japonés correcto | 🔥 |
| Speed avg | ~15 tok/s | **~43 tok/s** | **3x** |
| Contexto | 32K | **262K** | **8x** |

---

## 🔧 Requisitos

### Hardware

| Componente | Mínimo |
|:-----------|:------:|
| GPU | NVIDIA 4GB+ VRAM |
| RAM | 16 GB |
| Disco | 10 GB libres |
| SO | Linux (Ubuntu 22.04+, Kali, Arch) |

### Software

| Herramienta | Versión |
|:------------|:-------:|
| Python | 3.10+ |
| Ollama | 0.30+ |
| CUDA Driver | 12.4+ |

---

## 📁 Estructura del Proyecto

```
Alex_Voice/
├── server.py                   ← Teacher+Conversation backend (3000/3001)
├── translator.py                ← Translator backend (3003) + async pipeline
├── menu_server.py               ← Menu hub (5000) + lifecycle via Ollama API
├── conv_server.py               ← Wrapper → server.py conversation mode
├── alex-voice.sh                ← Unified launcher (verifica Ollama + cleanup)
├── prompts.py                   ← System prompts + multi-output parsing
├── frontend/                    ← UIs: menu.html, index.html, conv.html, translator.html
├── models/                      ← GGUF, Kokoro ONNX, Piper, Translation HF cache
├── setup.sh                     ← Linux setup script
├── README.md                    ← Esta documentación
├── AGENT.md                     ← Sistema de instrucciones (para IA)
└── PLAN.md                      ← Plan de mejora y métricas
```

---

## 🔌 API Endpoints

### Menú (`localhost:5000`)
| Endpoint | Descripción |
|:---------|:------------|
| `/api/status` | Estado: modo activo, ollama_alive |
| `/api/start/teacher` | Inicia Teacher (server.py + Ollama) |
| `/api/start/conv` | Inicia Conversation (conv_server.py + Ollama) |
| `/api/start/translator` | Inicia Translator (translator.py) |
| `/api/stop` | Detiene todo + libera VRAM vía Ollama API |

### Teacher/Conversation (`localhost:3000/3001`)
| Endpoint | Descripción |
|:---------|:------------|
| `/api/chat` | Chat via Ollama API (model + reasoning_format:none) |
| `/api/tts` | TTS Kokoro ONNX (CPU, 0 VRAM) |
| `/api/asr` | ASR faster-whisper small + Silero VAD |
| `/api/stats` | Stats GPU/CPU en vivo |

### Translator (`localhost:3003`)
| Endpoint | Descripción |
|:---------|:------------|
| `/api/translate` | MarianMT GPU (100ms) |
| `/api/pipeline` | Async pipeline: audio → ASR → Translation → TTS |
| `/api/tts` | Kokoro ONNX |
| `/api/asr` | ASR faster-whisper small |
| `/api/status` | Estado: whisper/transformers/kokoro loaded |

---

*Alex Voice v3 — Asistente Local Multilingüe · Linux · Junio 2026*
