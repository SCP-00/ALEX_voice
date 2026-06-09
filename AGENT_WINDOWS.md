# 🪟 AGENT_WINDOWS.md — Alex Voice en Windows

## ⚠️ CRITICAL: Esta es la rama `windows` de Alex Voice

Esta rama contiene el código **optimizado para Windows 10/11**. La rama `linux-dev` contiene la versión para Linux (Ubuntu/Debian).

**NO** mezcles código entre ramas. Cada rama tiene su propio `setup.bat` o `setup.sh`, sus propias rutas de archivos, y sus propias instrucciones de instalación.

---

## 📋 Diferencias Clave Windows vs Linux

| Aspecto | Windows | Linux |
|:--------|:--------|:------|
| **Setup** | `setup.bat` (doble clic) | `setup.sh` |
| **Run** | `run.bat` (doble clic) | `run.sh` |
| **llama-server** | `llama-server.exe` en `llama-server-bin/` | Binario ELF en `llama-server-bin/` |
| **Rutas** | `C:\Users\<user>\Alex_Voice\` | `/home/<user>/Alex_Voice/` |
| **Separador rutas** | `\` (backslash) | `/` (forward slash) |
| **Python** | `python` (no `python3`) | `python3` |
| **VRAM GPU** | ~5.28 GB usable (RTX 3050 6GB) | Misma GPU, mismo VRAM |
| **CUDA** | CUDA 12.4 via PyTorch wheels | CUDA 12.4 via PyTorch wheels |
| **TTS principal** | Kokoro-82M (CPU) + Piper (CPU) | Kokoro-82M (CPU) + Piper (CPU) |
| **ASR** | faster-whisper (GPU via CUDA) | faster-whisper (GPU via CUDA) |
| **Contexto LLM** | 128k tokens (desde junio 2026) | 128k tokens |
| **Web Search** | DuckDuckGo vía `ddgs` | DuckDuckGo vía `ddgs` |
| **Desktop** | `.lnk` + `.bat` en Escritorio | `.desktop` + `.sh` en Escritorio |

---

## 🖥️ Windows Project Paths

```
PROJECT=C:\Users\<user>\Alex_Voice
PYTHON=python  (no python3)
VENV=  (opcional, no requerido en Windows)
MODELS=%PROJECT%\models\
LLAMA_BIN=%PROJECT%\llama-server-bin\
DESKTOP=%USERPROFILE%\Desktop\Voice_chat\
```

---

## 🚀 Cómo funciona en Windows

### Instalación desde cero

```cmd
:: 1. Descargar ZIP de GitHub (rama windows)
:: 2. Extraer a C:\Users\<user>\Alex_Voice\
:: 3. Ejecutar como Administrador:
setup.bat

:: 4. setup.bat hará TODO automáticamente:
::    - Verificar Python 3.10+
::    - Instalar PyTorch CUDA 12.4
::    - Instalar kokoro, piper-tts, faster-whisper, qwen-tts, argostranslate
::    - Instalar ddgs (DuckDuckGo search para web search)
::    - Descargar llama-server.exe (CUDA 13.3)
::    - Descargar Qwen2.5-1.5B Q4_K_M GGUF
::    - Descargar modelos Piper TTS (ES + EN)
::    - Instalar paquetes argos-translate EN↔ES↔JA
```

### Ejecución diaria

```cmd
:: Opción A: Menú principal (recomendado)
run.bat  → Abre http://localhost:5000

:: Opción B: Directo
python menu_server.py              → Menú (puerto 5000)
python server.py --port 3000       → Teacher (puerto 3000)
python conv_server.py               → Conversation (puerto 3001)
python translator.py                → Translator (puerto 3003)
```

### Desktop Launchers (para crear accesos directos)

Crear accesos directos `.lnk` en el Escritorio que apunten a:

```cmd
:: alex-voice-home.lnk → python menu_server.py  (abre http://localhost:5000)
:: alex-voice-teacher.lnk → python server.py --port 3000 --mode teacher
:: alex-voice-chat.lnk → python conv_server.py
:: alex-voice-translate.lnk → python translator.py
```

O crear `.bat` files en `%USERPROFILE%\Desktop\Voice_chat\`:

**alex-voice-home.bat:**
```batch
@echo off
cd /d "%~dp0"
start "" http://localhost:5000
python menu_server.py
pause
```

**alex-voice-teacher.bat:**
```batch
@echo off
cd /d "%~dp0"
python server.py --port 3000 --mode teacher
pause
```

**alex-voice-chat.bat:**
```batch
@echo off
cd /d "%~dp0"
python conv_server.py
pause
```

**alex-voice-translate.bat:**
```batch
@echo off
cd /d "%~dp0"
python translator.py
pause
```

---

## 🔧 Detalles Técnicos Windows

### Servidores que se inician

| Puerto | Servicio | Script | Componentes |
|:------:|:---------|:-------|:------------|
| 5000 | Menú | `menu_server.py` | Hub — inicia/detiene modos |
| 3000 | Teacher | `server.py` (teacher mode) | LLM GPU + Kokoro CPU + Whisper GPU |
| 3001 | Conversation | `conv_server.py` → server.py conversation | LLM GPU (mismo llama-server) + Kokoro CPU + Whisper GPU |
| 3003 | Translator | `translator.py` | argos CPU + Qwen3-TTS GPU + Whisper GPU |
| 8081 | llama-server | `llama-server.exe` | Backend LLM GPU (128k contexto) |

> **Nota:** Teacher (3000) y Conversation (3001) comparten el mismo llama-server. Solo 1 modo a la vez (más Translator que es independiente).

### Modelos

| Modelo | Ruta | VRAM | Contexto |
|--------|------|:----:|:--------:|
| Qwen2.5-1.5B-Q4_K_M | `models\qwen2.5-1.5b-q4_k_m.gguf` | ~1.2 GB | **128k** 🚀 |
| Qwen3.5-2B-Q4_K_M (opcional) | `models\qwen3.5-2b-q4_k_m.gguf` | ~1.5 GB | 256k nativo |
| Piper ES | `models\es_ES-sharvard-medium.onnx` | CPU | — |
| Piper EN | `models\en_US-lessac-medium.onnx` | CPU | — |

### TTS

| Engine | Puerto | Tipo | Detalle |
|--------|:------:|:----|:--------|
| Kokoro-82M 🏆 | 3000 | CPU | Primario. ES→`ef_dora`, EN→`af_heart`. Latin script only. |
| Piper | 3000 | CPU | Fallback si Kokoro falla. ~45ms latencia. |
| Qwen3-TTS | 3003 | GPU, ~2GB VRAM | Alta calidad para Translator. RTF 2.6x en RTX 3050. |

### Web Search

- Implementado vía `ddgs` (DuckDuckGo Search, Python library)
- Botón 🔍 en Conversation mode
- Sin API key necesaria
- Caché de 5 minutos
- Thread-safe con lock

---

## 🐛 Problemas Conocidos en Windows

| Problema | Solución |
|:---------|:---------|
| **Python no encontrado** | Instalar Python 3.10+ desde python.org, **marcar "Add to PATH"** |
| **CUDA no disponible** | `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124` |
| **llama-server.exe no se descarga** | Descarga manual: https://github.com/ggml-org/llama.cpp/releases |
| **Kokoro tarda 30s en primera vez** | Normal — lazy-load del modelo |
| **Qwen3-TTS cold start lento** | ~26s primera vez. Las siguientes ~9-10s. |
| **Puerto en uso** | `taskkill -f -im python.exe` o `netstat -ano \| findstr :3000` y `taskkill /PID <pid> /F` |
| **argos-translate no descarga paquetes** | Ejecutar `python -c "import argostranslate.package as p; p.update_package_index()"` manualmente |
| **No hay audio** | Revisar dispositivo de salida en `mmsys.cpl` |
| **Error de permisos** | Ejecutar setup.bat como Administrador |
| **Antivirus bloquea** | Añadir exclusión a la carpeta `Alex_Voice` |

---

## 🔌 API Endpoints (idénticos a Linux)

### Menú (`localhost:5000`)
| Endpoint | Método | Descripción |
|:---------|:------:|:------------|
| `/` | GET | Sirve `menu.html` |
| `/api/status` | GET | Estado actual — modos activos, servidores en ejecución |
| `/api/start/teacher` | POST | Inicia Teacher (llama-server + server.py teacher mode) |
| `/api/start/conv` | POST | Inicia Conversation (llama-server + server.py conv mode) |
| `/api/start/translator` | POST | Inicia Translator (translator.py) — **independiente, corre en paralelo** |
| `/api/start/llama` | POST | Inicia solo llama-server (para debugging) |
| `/api/stop` | POST | Detiene todos los servidores |

### Teacher/Conversation (`localhost:3000/3001`)
| Endpoint | Método | Descripción |
|:---------|:------:|:------------|
| `/api/chat` | POST | Chat con modo + multi-output + web_search opcional |
| `/api/tts` | POST | TTS Kokoro (o Piper fallback) |
| `/api/tts/stream` | POST | TTS streaming |
| `/api/asr` | POST | Reconocimiento de voz |
| `/api/stats` | GET | Estadísticas GPU/CPU/RAM |
| `/api/web_search` | POST | Búsqueda DuckDuckGo (query, max) |

### Translator (`localhost:3003`)
| Endpoint | Método | Descripción |
|:---------|:------:|:------------|
| `/api/translate` | POST | Traducir texto |
| `/api/tts` | POST | Audio Qwen3-TTS (text, language, speed) |
| `/api/asr` | POST | Reconocimiento de voz |
| `/api/status` | GET | Estado del servidor |

---

## 📝 Convenciones de Código

- **System prompts en INGLÉS** — Qwen2.5-1.5B fue entrenado ~70% con datos en inglés
- **Multi-output format**: `【TEXT】`, `【TTS_READING】`, `【PRONUNCIATION】`, `【TRANSLATION】`, `【EXPLANATION】`, `【EXERCISE】`
- **TTS priority**: `【TTS_READING】` → `【TEXT】` → respuesta completa
- **Conversation**: responde SIEMPRE en el mismo idioma del usuario
- **Variables en snake_case** (Python estándar)
- **HTML/CSS/JS** en archivos separados dentro de `frontend/`

---

## 🏗️ Estructura del Proyecto (Windows)

```
Alex_Voice\
│
├── server.py                   ← Teacher + Conversation (puerto 3000/3001)
├── translator.py                ← Translator (puerto 3003)
├── menu_server.py               ← Menú principal (puerto 5000)
├── launcher.py                  ← Lanzador legacy
├── conv_server.py               ← Wrapper → Conversation mode
│
├── prompts.py                   ← System prompts + parsing
│
├── frontend\
│   ├── index.html               ← UI Teacher+Conversation
│   ├── translator.html          ← UI Translator
│   └── menu.html                ← Menú principal
│
├── setup.bat                    ← Instalador automático (6 pasos)
├── run.bat                      ← Inicio rápido → menú
│
├── models\                      ← Modelos (descargados por setup.bat)
│   ├── qwen2.5-1.5b-q4_k_m.gguf
│   ├── es_ES-sharvard-medium.onnx
│   └── en_US-lessac-medium.onnx
│
├── llama-server-bin\            ← llama-server.exe (descargado por setup.bat)
│
├── AGENT_WINDOWS.md             ← Este archivo
├── AGENT.md                     ← Instrucciones legacy (referencia)
├── knowledge.md                 ← Knowledge base actualizado
├── plan.md                      ← Plan de mejora
├── README.md                    ← Documentación principal
└── LICENSE                      ← Licencia MIT
```

---

## 🧪 Cómo Probar Cambios en Windows

```cmd
:: 1. Verificar sintaxis Python
python -m py_compile server.py
python -m py_compile translator.py
python -m py_compile menu_server.py

:: 2. Verificar imports
python -c "import server; print('server OK')"
python -c "import translator; print('translator OK')"

:: 3. Test rápido de endpoints
:: Abre menu en cmd separado: python menu_server.py
:: En otro cmd: curl http://localhost:5000/api/status

:: 4. Probar web search (requiere ddgs instalado)
python -c "from duckduckgo_search import DDGS; print('DDGS OK')"

:: 5. Probar TTS Kokoro
python -c "from kokoro import KPipeline; print('Kokoro OK')"

:: 6. Probar Whisper
python -c "from faster_whisper import WhisperModel; print('Whisper OK')"
```

---

## 🐙 GitHub

- **Remote:** `https://github.com/SCP-00/ALEX_voice.git`
- **Repo:** `SCP-00/ALEX_voice`
- **Rama Windows:** `windows` ← Estás aquí
- **Rama Linux:** `linux-dev`
- **Creado por:** SCP-076 (Victor Buendia)
- **Coded por:** Buffy (AI Agent en Codebuff.com)

---

*Alex Voice — Windows Edition · 2026*
