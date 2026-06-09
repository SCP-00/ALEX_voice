# 🎙️ Alex Voice — Asistente Local con IA Multilingüe

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![CUDA](https://img.shields.io/badge/CUDA-12.4-green)](https://developer.nvidia.com/cuda-toolkit)

**Alex Voice** es un asistente de voz con inteligencia artificial que corre **100% local** en tu PC con GPU NVIDIA. Soporta múltiples idiomas con 3 modos de interacción especializados.

Creado por [SCP-076](https://github.com/SCP-00) · Coded with ❤️ by [Buffy](https://codebuff.com) (AI Agent)

---

## 🌿 Ramas del Proyecto

Este proyecto tiene **dos ramas principales** para soportar ambos sistemas operativos:

| Rama | SO | Setup | Últimas Features |
|:----:|:--:|:------|:-----------------|
| 🌐 **`windows`** | Windows 10/11 | `setup.bat` ✅ | 128k contexto, Web Search 🔍, Multi-modo, Kokoro Speed slider |
| 🐧 **`linux-dev`** | Ubuntu/Debian/Kali | `setup.sh` ✅ | 128k contexto, Web Search 🔍, Multi-modo, Kokoro Speed slider |

> **⚠️ Importante:** Cada rama tiene sus propios scripts de instalación, rutas de archivos, y configuraciones específicas del SO. No mezcles archivos entre ramas.
>
> Para instrucciones detalladas de Windows para agentes IA, ver [`AGENT_WINDOWS.md`](AGENT_WINDOWS.md).

---

## 🚀 Inicio Rápido

### 🪟 Windows (Rama: `windows`)

```bash
# 1. Clonar la rama Windows
git clone -b windows https://github.com/SCP-00/ALEX_voice.git
cd Alex_Voice

# 2. Ejecutar setup.bat (como Administrador)
#    Descarga modelos + instala dependencias automáticamente
setup.bat

# 3. Iniciar menú principal
run.bat
# → Abre http://localhost:5000
# → Selecciona: 🎓 Teacher, 💬 Conversación o 🌍 Traductor
```

### 🐧 Linux — Ubuntu/Debian (Rama: `linux-dev`)

```bash
# 1. Clonar la rama Linux
git clone -b linux-dev https://github.com/SCP-00/ALEX_voice.git
cd Alex_Voice

# 2. Setup automático
chmod +x setup.sh
./setup.sh

# 3. Iniciar menú
./run.sh
# O manual: python3 menu_server.py → http://localhost:5000
```

### ⚙️ Cross-platform (cualquier rama)

```bash
# Requisitos: Python 3.10+, CUDA 12.4+, GPU NVIDIA 4GB+

# 1. Instalar dependencias
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install kokoro piper-tts faster-whisper qwen-tts argostranslate duckduckgo-search

# 2. Descargar llama-server desde:
#    https://github.com/ggml-org/llama.cpp/releases
#    Extraer a ./llama-server-bin/

# 3. Descargar modelo Qwen2.5-1.5B-Q4_K_M (~1.1GB):
mkdir -p models
curl -L -o models/qwen2.5-1.5b-q4_k_m.gguf \
  https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf

# 4. Iniciar menú principal
python menu_server.py     # Abre http://localhost:5000
```

---

## 🆕 Novedades (Junio 2026)

| Feature | Descripción |
|:--------|:------------|
| 🧠 **128k contexto** | Conversaciones de 30+ minutos gracias al contexto ampliado de llama-server (`-c 131072`) |
| 🔍 **Web Search** | Botón toggle en Conversation mode que activa búsqueda DuckDuckGo — resultados inyectados en el prompt del LLM |
| 🔄 **Multi-modo** | Teacher + Translator pueden ejecutarse simultáneamente (Translator es independiente) |
| 🎤 **Speed slider** | Kokoro TSS ahora respeta el slider de velocidad (0.7x–1.3x) en Translator |
| 🎛️ **Sliders simplificados** | Eliminados Calma/Calidez (solo funcionaban con Qwen3-TTS). Solo velocidad en Kokoro. |
| 🧪 **Qwen3.5-2B opcional** | Soporte para modelo de 256k contexto nativo y tool calling |

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    ALEX VOICE                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────┐                                      │
│  │  MENÚ PRINCIPAL   │  ← Abre http://localhost:5000        │
│  │  (menu_server.py) │  Gestión de ciclo de vida de modos   │
│  │  puerto 5000      │  API: /api/start/*, /api/stop        │
│  └────────┬──────────┘                                      │
│           │                                                  │
│  ┌────────┴──────────┐    ┌──────────────────────────┐      │
│  │  Teacher + Conv   │    │  Translator (indep.)     │      │
│  │  (3000 / 3001)    │    │  (puerto 3003)           │      │
│  │                   │    │  ⚡ Corre en PARALELO     │      │
│  │  LLM: Qwen2.5-1.5B│    │  STT: Whisper large GPU  │      │
│  │  TTS: Kokoro/Piper│    │  TRANS: argos CPU        │      │
│  │  ASR: Whisper sm. │    │  TTS: Qwen3-TTS 0.6B    │      │
│  │  Web Search 🔍    │    │  Speed slider Kokoro    │      │
│  │  128k contexto 🧠 │    │  SIN LLM                 │      │
│  └───────────────────┘    └──────────────────────────┘      │
│                                                             │
│  ┌────────────────────────────────────────────────────┐     │
│  │  llama-server (GPU, puerto 8081)                    │     │
│  │  Qwen2.5-1.5B-Q4_K_M ~1.2GB VRAM | 128k contexto   │     │
│  │  Qwen3.5-2B-Q4_K_M (opcional) ~1.5GB | 256k ctx    │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
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
Charla natural para practicar idiomas con **memoria completa** (~20 mensajes de contexto, hasta 128k tokens).
- Responde SIEMPRE en el mismo idioma que escribes
- 🔍 **Web Search toggle** — activa búsqueda DuckDuckGo para información actualizada
- Cross-language probado: EN, ES, JA, FR
- Memoria conversacional enviada al backend en cada turno

### 🌍 Translator (servidor independiente)
Traducción profesional con audio de alta calidad. **Puede ejecutarse en paralelo** con Teacher/Conversation.
- **STT:** faster-whisper large-v3-turbo (GPU) — ASR multilingüe de alta precisión
- **TRANS:** argos-translate (CPU) — traducción offline EN/ES/JA
- **TTS:** Kokoro-82M (CPU, default) + **Qwen3-TTS 0.6B** (GPU, fallback no-latino). Speed slider solo para Kokoro (0.7x–1.3x); Qwen3-TTS usa instruct parameters.
- **Sliders simplificados:** solo velocidad (se eliminaron Calma/Calidez que requerían Qwen3-TTS)
- Selector manual de idiomas FROM/TO
- Sin LLM — servicio ligero y especializado

---

## 📋 Menú Principal

El sistema tiene un **hub central** en `http://localhost:5000` que gestiona el ciclo de vida de todos los modos:

```
1️⃣  Teacher     → Inicia Teacher (puerto 3000) — comparte llama-server con Conversation
2️⃣  Chat        → Inicia Conversación (puerto 3001) — comparte llama-server con Teacher
3️⃣  Traductor   → Inicia Traductor (puerto 3003) — ✅ CORRE EN PARALELO con Teacher/Conv
Esc           → Detiene todos los servidores
```

- **Multi-modo:** Teacher y Translator pueden estar activos simultáneamente 🚀
- **Overlay de carga** con barra de progreso mientras se cargan modelos en GPU
- **Polling de estado** cada 3 segundos
- **Botón "← Volver al menú"** en cada modo — detiene servidores y regresa al hub
- **Gestión de procesos**: al detener un modo, se matan todos los subprocesos (llama-server incluido)

---

## 📊 VRAM Usage

| Modo(s) | Componentes | VRAM |
|:--------|:------------|:----:|
| **Teacher o Conversation** | Qwen2.5-1.5B (GPU, llama-server) + Kokoro (CPU) + Whisper small (GPU) | **~2.7 GB** |
| **Teacher + Translator** | Qwen2.5-1.5B (GPU) + Kokoro (CPU) + Whisper small/large + Qwen3-TTS | **~4.5 GB** (comparten VRAM) |
| **Translator solo** | Whisper large-v3-turbo O Qwen3-TTS-0.6B (GPU, 1 a la vez) | **~3.5 GB** (swap automático) |

> ⚡ **Multi-modo:** Teacher/Conversation usan llama-server fijo (~1.2 GB). Translator usa VRAM bajo demanda con swap ASR↔TTS. Cuando ambos están activos, Translator usa la VRAM restante (~2.5 GB disponible).

---

## ⚡ Benchmarks

### TTS: Kokoro-82M (CPU — Teacher/Conversation)

| Voz | Texto | Tiempo | RTF |
|:----|:------|:------:|:---:|
| `ef_dora` (ES) | 100 chars | **3.2s** | 0.72x |
| `af_heart` (EN) | 100 chars | **0.93s** | 0.21x |

### TTS: Qwen3-TTS 0.6B (GPU — Translator)

| Texto | Audio generado | Tiempo GPU | RTF |
|:------|:--------------:|:----------:|:---:|
| Corto (~60 chars) | 3.4s | 8.9s | **2.6x** |
| Largo (~350 chars) | 21.4s | 57.7s | **2.7x** |

**Cold start:** ~26s (carga + warmup). **Warm:** ~9-10s.

### ASR: Whisper large-v3-turbo

| Idioma | WER | VRAM |
|:-------|:---:|:----:|
| Español | ~5% | 3.5 GB |
| Inglés | ~3% | 3.5 GB |
| Japonés | ~7% | 3.5 GB |

### Web Search: DuckDuckGo

| Acción | Tiempo |
|:-------|:------:|
| Búsqueda | ~1.5s |
| Caché | 5 minutos (thread-safe) |

---

## 🔧 Requisitos

### Hardware

| Componente | Mínimo | Recomendado |
|:-----------|:------:|:-----------:|
| **GPU** | NVIDIA 4GB VRAM | RTX 3050 6GB / RTX 4060 8GB |
| **RAM** | 8 GB | 16 GB |
| **Disco** | 10 GB libres | 20 GB libres |
| **SO** | Windows 10/11 | Windows 11 / Linux |
| **CUDA Driver** | 12.4+ | Driver 610+ |

### Python Dependencies

```bash
# Core
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install kokoro piper-tts faster-whisper qwen-tts argostranslate

# Web Search
pip install duckduckgo-search

# Utilidades
pip install psutil pynvml numpy

# [OPCIONAL] flash-attn (~2-3x Qwen3-TTS)
# pip install flash-attn --no-build-isolation
```

---

## 📁 Estructura del Proyecto

```
Alex_Voice/
│
├── server.py                   ← Teacher + Conversation (puerto 3000/3001)
├── translator.py                ← Translator (puerto 3003)
├── menu_server.py               ← Menú principal (puerto 5000)
├── conv_server.py               ← Wrapper → Conversation mode
├── launcher.py                  ← Lanzador legacy
│
├── prompts.py                   ← System prompts + parsing multi-output
│
├── frontend/
│   ├── index.html               ← Teacher + Conversation UI
│   ├── translator.html          ← Translator UI
│   └── menu.html                ← Menú principal
│
├── setup.bat / setup.sh         ← Instalador (según rama)
├── run.bat / run.sh             ← Inicio rápido (según rama)
│
├── models/                      ← Modelos descargados
│   ├── qwen2.5-1.5b-q4_k_m.gguf
│   └── *.onnx (Piper TTS)
│
├── llama-server-bin/            ← llama-server (según SO)
│
├── AGENT_WINDOWS.md             ← Instrucciones del sistema (Windows) 🆕
├── knowledge.md                 ← Knowledge base
├── plan.md                      ← Plan de mejora
├── README.md                    ← Esta documentación
└── LICENSE                      ← MIT
```

---

## 🔌 API Endpoints

### Menú (`localhost:5000`)

| Endpoint | Método | Descripción |
|:---------|:------:|:------------|
| `/` | GET | Sirve `menu.html` |
| `/api/status` | GET | Estado — modos activos, servidores en ejecución |
| `/api/start/teacher` | POST | Inicia Teacher (puerto 3000) |
| `/api/start/conv` | POST | Inicia Conversation (puerto 3001) |
| `/api/start/translator` | POST | Inicia Translator (puerto 3003) — corre en paralelo |
| `/api/start/llama` | POST | Inicia solo llama-server (debugging) |
| `/api/stop` | POST | Detiene todos los servidores |

### Teacher/Conversation (`localhost:3000/3001`)

| Endpoint | Método | Descripción |
|:---------|:------:|:------------|
| `/api/chat` | POST | Chat con modo + web_search opcional |
| `/api/tts` | POST | TTS Kokoro → Piper (fallback) |
| `/api/tts/stream` | POST | TTS streaming |
| `/api/asr` | POST | Reconocimiento de voz (faster-whisper) |
| `/api/web_search` | POST | Búsqueda DuckDuckGo 🆕 |
| `/api/stats` | GET | Estadísticas GPU/CPU/RAM |

### Translator (`localhost:3003`)

| Endpoint | Método | Descripción |
|:---------|:------:|:------------|
| `/api/translate` | POST | Traducir texto |
| `/api/tts` | POST | Audio (text, language, **speed**) |
| `/api/asr` | POST | Reconocimiento de voz |
| `/api/status` | GET | Estado del servidor |

---

## 🔍 Web Search (Conversation mode)

El botón 🔍 en la barra de entrada de Conversation activa la búsqueda web:

1. **Toggle** 🔍 → se enciende/apaga (desactivado por defecto)
2. Al enviar un mensaje con 🔍 activo, el backend busca en DuckDuckGo
3. Los resultados se inyectan en el prompt del LLM
4. El LLM responde con información actualizada (no hay límite de fecha de conocimiento)

> Sin API key necesaria, 0 requests a internet hasta que se activa, caché de 5 minutos.

---

## 🌿 Comparativa de Ramas

| Aspecto | `windows` | `linux-dev` |
|:--------|:---------:|:-----------:|
| **Script de instalación** | `setup.bat` (CMD) | `setup.sh` (Bash) |
| **Ejecución** | `run.bat` → doble clic | `run.sh` → `./run.sh` |
| **Python** | `python` | `python3` |
| **Rutas** | `\` backslash | `/` forward slash |
| **llama-server** | `.exe` (CUDA) | Binario ELF (CUDA/Vulkan/CPU) |
| **Desktop shortcuts** | `.lnk` + `.bat` | `.desktop` + `.sh` |
| **Setup automático** | Chocolatey opcional | `apt-get` / `pacman` |
| **ASR GPU** | faster-whisper (CUDA) | faster-whisper (CUDA o CPU) |
| **TTS** | Kokoro (CPU) + Qwen3-TTS (GPU) | Kokoro (CPU) + Qwen3-TTS (GPU) |
| **Contexto LLM** | 128k | 128k |
| **Web Search** | ✅ DuckDuckGo | ✅ DuckDuckGo |
| **Multi-modo** | ✅ Teacher + Translator | ✅ Teacher + Translator |
| **AGENT docs** | `AGENT_WINDOWS.md` | `AGENT.md` + `knowledge.md` |

---

## 🤝 Contribuir

1. Fork el proyecto desde la rama correspondiente (`windows` o `linux-dev`)
2. Crea tu rama (`git checkout -b feature/mejora`)
3. Commit (`git commit -am 'feat: mejora'`)
4. Push (`git push origin feature/mejora`)
5. Abre un Pull Request

> **Nota:** Las contribuciones de Windows deben hacerse desde la rama `windows`. Las de Linux desde `linux-dev`. No mezcles cambios entre ramas.

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
