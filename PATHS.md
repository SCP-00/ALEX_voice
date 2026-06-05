# 📍 Alex Voice — Rutas y Referencias

> Archivo de referencia creado el 2026-06-04.
> Ultima auditoria: 2026-06-05.
> ⚠️ **MANTENER ACTUALIZADO** — especialmente rutas de modelos y CUDA toolkit.

---

## 📊 Hardware

| Componente | Especificación |
|:-----------|:---------------|
| **GPU** | NVIDIA GeForce RTX 3050 6GB Laptop GPU |
| **Compute Capability** | 8.6 (Ampere) |
| **VRAM** | 6 GB (6144 MiB) |
| **Driver NVIDIA** | 610.47 (CUDA Driver Version: 13.3) |
| **RAM** | — |
| **SO** | Windows |

> ⚠️ El driver soporta CUDA 13.3, pero PyTorch usa CUDA 12.4. Es compatible hacia atrás.

---

## 🐍 Python

| Componente | Ruta / Versión |
|:-----------|:---------------|
| **Python** | `C:\Users\andyh\AppData\Local\Programs\Python\Python310\python.exe` |
| **Versión** | 3.10.x |
| **Pip** | `C:\Users\andyh\AppData\Local\Programs\Python\Python310\Scripts\pip.exe` |
| **Site-packages** | `C:\Users\andyh\AppData\Local\Programs\Python\Python310\lib\site-packages\` |

---

## 🔥 PyTorch y CUDA

| Componente | Estado | Ruta / Versión |
|:-----------|:------:|:---------------|
| **PyTorch** | ✅ | `torch 2.6.0+cu124` |
| **CUDA soporte** | ✅ | `torch.cuda.is_available() = True` |
| **GPU detectada** | ✅ | NVIDIA GeForce RTX 3050 6GB Laptop GPU |
| **CUDA Toolkit (nvcc)** | ✅ | `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin\nvcc.exe` |
| **CUDA_PATH / CUDA_HOME** | ⚠️ | El CUDA Toolkit completo (nvcc.exe) **NO está instalado**. Solo existe el runtime de PyTorch CUDA 12.4. Sin nvcc.exe no se puede compilar flash-attn. |
| **xformers** | ✅ | `xformers 0.0.29.post3` (sin Triton en Windows) |
| **flash-attn** | ❌ | **NO INSTALADO** — necesita `cl.exe` + `nvcc.exe` (CUDA Toolkit completo). VS C++ ya instalado, pero CUDA Toolkit 12.4 con nvcc falta. |

### Atención backend (translator_server.py)

Jerarquía automática en `translator_server.py`:
1. `flash_attention_2` → si flash-attn instalado
2. `sdpa` → SDPA nativo de PyTorch 2.0+ (por defecto ✅)
3. `eager` → fallback manual

### Idiomas disponibles

| Código | Idioma | Traducción | TTS (Qwen3) | ASR (whisper) |
|:------:|:-------|:----------:|:-----------:|:-------------:|
| `en` | 🇬🇧 Inglés | ✅ Directo | ✅ Nativo | ✅ 99+ idiomas |
| `es` | 🇪🇸 Español | ✅ Directo | ✅ Nativo | ✅ |
| `ja` | 🇯🇵 Japonés | ✅ Directo | ✅ Nativo | ✅ |
| `fr` | 🇫🇷 Francés | 🔄 Lazy-load | ✅ Nativo | ✅ |
| `ko` | 🇰🇷 Coreano | 🔄 Lazy-load | ✅ Nativo | ✅ |
| `zh` | 🇨🇳 Chino | 🔄 Lazy-load | ✅ Nativo | ✅ |
| `de` | 🇩🇪 Alemán | 🔄 Lazy-load | ✅ Nativo | ✅ |
| `pt` | 🇵🇹 Portugués | 🔄 Lazy-load | ✅ Nativo | ✅ |

> 🔄 Lazy-load = se descarga el paquete argos solo cuando se usa por primera vez.
> ES↔JA usa traducción pivote vía EN (argos no tiene el par directo).

---

## 🛠️ Visual Studio Build Tools

| Componente | Estado | Ruta |
|:-----------|:------:|:------|
| **VS 2022 BuildTools** | ⚠️ Instalado | `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools` |
| **vcvarsall.bat** | ❌ | **NO ENCONTRADO** — el workload C++ no está instalado |
| **cl.exe** | ❌ | **NO ENCONTRADO** en el PATH |

> Sin `cl.exe` y `vcvarsall.bat`, NO se puede compilar flash-attn.
> La instalación de VS BuildTools que hiciste no incluye el workload de C++.

---

## ⚡ Instalación Completa (CUDA Toolkit + flash-attn)

Si decides instalar flash-attn, necesitas estos 3 pasos en orden desde **PowerShell como Administrador**:

### Paso 1: Reparar VS Build Tools (agregar workload C++)

```powershell
winget install Microsoft.VisualStudio.2022.BuildTools --silent --override "--add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
```

Esto agrega el compilador `cl.exe` y las herramientas de C++ necesarias (~2-3 GB adicionales).

### Paso 2: Descargar e instalar CUDA Toolkit 12.4.1

```powershell
# URL verificada (HTTP 200 OK)
Invoke-WebRequest -Uri "https://developer.download.nvidia.com/compute/cuda/12.4.1/local_installers/cuda_12.4.1_551.78_windows.exe" -OutFile "$env:USERPROFILE\Downloads\cuda_12.4.1.exe"

# Instalar SOLO nvcc (mínimo para compilar, ~2.5GB)
Start-Process -Wait -FilePath "$env:USERPROFILE\Downloads\cuda_12.4.1.exe" -ArgumentList "-s nvcc_12.4"
```

### Paso 3: Configurar entorno y compilar flash-attn

```powershell
# Configurar variables (importante: MISMA sesión que pip)
$env:CUDA_PATH = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4"
$env:CUDA_HOME = $env:CUDA_PATH
$env:PATH = "$env:CUDA_PATH\bin;$env:PATH"

# Activar compilador C++ de VS 2022
& "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" amd64

# Compilar e instalar flash-attn (~10-30 min)
pip install flash-attn --no-build-isolation
```

> 💡 **Sin flash-attn también funciona.** Ya tienes `xformers` + `SDPA nativo` + `torch.compile`. La diferencia es pequeña para Qwen3-TTS (modelo pequeño de 0.6B).

---

## 📦 Paquetes Python Instalados

| Paquete | Versión | Propósito |
|:--------|:-------:|:----------|
| `torch` | 2.6.0+cu124 | Deep learning + CUDA |
| `torchaudio` | 2.6.0+cu124 | Audio processing (CUDA) |
| `argostranslate` | ✓ | Traducción offline CPU |
| `faster-whisper` | ✓ | Speech-to-text CPU |
| `qwen-tts` | ✓ | Qwen3-TTS GPU |
| `kokoro` | ✓ | TTS ligero CPU |
| `xformers` | 0.0.29.post3 | Atención optimizada Windows |
| `psutil` | ✓ | Monitorización |
| `pynvml` | ✓ | Monitorización GPU |
| `wheel` | ✓ | Build de paquetes |
| `ninja` | ✓ | Build system |
| `flash-attn` | **❌** | No instalado |

---

## 🧠 Modelos de IA

| Modelo | Estado | Ruta / Nota |
|:-------|:------:|:------------|
| **Qwen2.5-1.5B-Q4_K_M** (~1.1GB) | Requerido para 3000 | `models\qwen2.5-1.5b-q4_k_m.gguf` — `setup.bat` lo descarga si falta |
| **Qwen3-TTS-CustomVoice** (~2GB) | — | Se descarga automáticamente al primer uso |
| **faster-whisper base** (~150MB) | — | Se descarga automáticamente al primer uso |
| **faster-whisper small** (~466MB) | Bajo demanda | Se usa para ASR `es`/`ja` si seleccionas el idioma |

---

## 🌐 Servidores

| Servidor | Puerto | Script | Descripción |
|:---------|:------:|:-------|:------------|
| **Teacher+Conversation** | `3000` | `B/server.py` | LLM + TTS híbrido |
| **llama-server** | `8081` | `llama-server-bin\llama-server.exe` | Backend LLM GPU; fallback: `llama.cpp\llama-server.exe`, `LLAMA_EXE`, `LLAMA_DIR` |
| **Translator** | `3003` | `translator_server.py` | Traducción + TTS calidad |

---

## 📁 Estructura del Proyecto

| Ruta | Descripción |
|:-----|:------------|
| `C:\Users\andyh\Desktop\Soft\Alex_Voice\` | Raíz del proyecto |
| `translator_server.py` | Servidor traductor (puerto 3003) |
| `launcher.py` | Lanzador unificado |
| `B/server.py` | Servidor Teacher+Conversation (puerto 3000) |
| `frontend/translator/index.html` | UI del traductor |
| `frontend/plan-b/index.html` | UI de Teacher+Conversation |
| `shared/translator.py` | Módulo compartido (prompts en inglés) |
| `setup.bat` | Instalador/verificador idempotente |
| `run.bat` | Menú de inicio interactivo |
| `models/` | Modelos LLM descargados |
| `llama-server-bin/` | Binario de llama.cpp descargado por setup |
| `PATHS.md` | **Este documento — rutas y referencias** |

---

## Lanzadores `.bat`

| Archivo | Estado recomendado |
|:--|:--|
| `setup.bat` | Mantener |
| `run.bat` | Mantener como entrada principal |
| `start_server.bat` | Legacy de Plan A; no recomendado |
| `B\start.bat` | Duplicado de launcher; opcional |
| `B\start_plan_b.bat` | Duplicado de launcher; opcional |
| `_start_teacher.bat` | Local no trackeado; no recomendado porque no arranca `llama-server` |

---

*Documento mantenido por Buffy (AI Agent) · Alex Voice Project · 2026*
