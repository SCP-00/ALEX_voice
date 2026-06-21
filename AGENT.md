# 🛡️ Alex Voice — AI Agent Guide (v3.3.1)

## Critical Rules

## 🔴 CRITICAL RULE

On Linux, `nvidia-smi`, `llama-server`, and any GPU inference **MUST** be run inside `tmux`.
Running GPU commands directly in basher can crash the CLI process.

**Rules:**
1. **NEVER** run GPU/VRAM commands directly in basher — always inside tmux
2. **NEVER** use ^C — let commands finish naturally or use timeout
3. **ALWAYS** use generous timeouts (3 MB/s download speed)
4. **NEVER** run `nvidia-smi` while GPU processes are active
5. **NEVER** run `llama-server` / `llama-cli` outside tmux

**Safe outside tmux:** git, mkdir, curl, cat, cp, mv, sleep, echo, find, python scripts (CPU only)

**ALWAYS inside tmux:** nvidia-smi, llama-server, llama-cli, any GPU inference, model loading

---

## 📋 Project Context

### Hardware
| Component | Spec |
|-----------|------|
| GPU | NVIDIA RTX 3050 Laptop 6GB (5.28 GB usable VRAM, CC 8.6) |
| CPU | Intel Core i5-13420H (8C/12T) |
| RAM | 16.5 GB |
| Disk | ~258 GB free |
| CUDA Driver | 610.47 (CUDA 13.3, compatible with PyTorch CUDA 12.4) |

### Architecture v3.3.1 (Junio 2026) — 4 Subproyectos

```
┌──────────────────────────────────────────────────────────────────┐
│                      ALEX VOICE v3.3.1                            │
│                    Launcher Unificado (port 5000)                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌───────────────────┐   ┌───────────────────┐                    │
│  │  🎓 TEACHER       │   │  💬 CONVERSATION  │                    │
│  │  Puerto 3000      │   │  Puerto 3001      │                    │
│  │  LLM: Ollama API  │   │  LLM: Ollama API  │                    │
│  │  TTS: Kokoro CPU  │   │  TTS: Kokoro CPU  │                    │
│  │  ASR: Whisper GPU │   │  ASR: Whisper GPU │                    │
│  │  VAD: Silero CPU  │   │  VAD: Silero CPU  │                    │
│  │  Cache: LRU 50    │   │  Context: 64K     │                    │
│  │  PRODUCTION ⭐⭐⭐⭐⭐│   │  PRODUCTION ⭐⭐⭐⭐  │                    │
│  └────────┬──────────┘   └────────┬──────────┘                    │
│           │                       │                                │
│  ┌────────┴───────────────────────┴──────────┐                    │
│  │  Ollama API (localhost:11434/v1)           │                    │
│  │  Modelo: prometheus-orchestrator           │                    │
│  │  (Qwen3.5 4B Instruct, IQ4_XS)            │                    │
│  │  64K ctx, ~35 tok/s, ~2.5GB VRAM          │                    │
│  │  reasoning_format: none                    │                    │
│  └────────────────────────────────────────────┘                    │
│                                                                    │
│  ┌───────────────────┐   ┌───────────────────┐                    │
│  │  🌍 TRANSLATOR    │   │  📝 GRAMMAR APP   │                    │
│  │  Puerto 3003      │   │  Puerto 3004      │                    │
│  │  ASR: Whisper GPU │   │  SQLite (no GPU)  │                    │
│  │  MarianMT GPU     │   │  Flask backend    │                    │
│  │  Kokoro TTS CPU   │   │  Vanilla JS front │                    │
│  │  Pipeline async   │   │  Duolingo-style   │                    │
│  │  PRODUCTION ⭐⭐⭐⭐  │   │  BETA ⭐⭐⭐        │                    │
│  └───────────────────┘   └───────────────────┘                    │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### Servidores
| Port | Servicio | Script | Backend | Estado |
|:----:|:---------|:-------|:--------|:------:|
| 5000 | Menu | `menu_server.py` | Flask + HTML | ✅ Activo |
| 3000 | Teacher | `server.py` (mode=teacher) | Ollama API → Qwen3.5 4B | ✅ PRODUCTION |
| 3001 | Conversation | `conv_server.py` → server.py | Ollama API → Qwen3.5 4B | ✅ PRODUCTION |
| 3003 | Translator | `translator.py` | Whisper + MarianMT + Kokoro | ✅ PRODUCTION |
| 3004 | Grammar App | `grammar_app/backend/app.py` | Flask + SQLite | ✅ BETA |

### Modelo Principal
| Modelo | Backend | VRAM | Contexto | Thinking | Velocidad |
|--------|:-------:|:----:|:-------:|:--------:|:---------:|
| **prometheus-orchestrator** 🏆 | **Ollama API** :11434/v1 | ~2.5 GB | **64K** | ❌ Desactivado | **~35 tok/s** |
| (Qwen3.5 4B Instruct, IQ4_XS, 4.3B params) | | | | | |

### VRAM Budget (v3.3.1 — 64K optimizado)
| Modo | Componentes | VRAM |
|:-----|:-----------|:----:|
| Teacher | Ollama 64K (~2.5GB) + Whisper (~1.5GB) | **~4.0 GB** |
| Conversation | Ollama 64K (~2.5GB) + Whisper (~1.5GB) | **~4.0 GB** |
| Translator | Whisper (~1.5GB) + MarianMT (~0.2GB) | **~1.7 GB** |
| Grammar App | Solo SQLite (0 VRAM) | **~0 GB** |

### Benchmarks Reales (RTX 3050 6GB, Junio 2026)
| Idioma | Velocidad (64K) | Calidad |
|:-------|:---------------:|:-------:|
| **EN** | **34.9 tok/s** | ✅ Excelente — respuestas naturales |
| **ES** | **~40 tok/s** | ✅ Español natural sin alucinaciones |
| **JA** | **~40 tok/s** | ✅ Japonés correcto con kanji |

### TTS (All CPU, 0 VRAM)
| Engine | Detail |
|:-------|:-------|
| **Kokoro ONNX** 🏆 | Primary. 54 voices, 5 languages (ES/EN/JA/FR/DE). Singleton lazy-load. |
| **Piper** | Fallback. ES + EN models. Latency ~45ms. |
| **Voces optimizadas:** | ES: `em_alex` (male, speed 0.9x), EN: `af_heart`, JA: `jf_alpha` (speed 0.9x) |
| **Phonemización:** | `misaki[ja]` para kanji nativo → pronunciación correcta |

### Translation
| Engine | Type | Detail |
|:-------|:-----|:-------|
| **Helsinki-NLP Opus-MT** 🏆 | GPU, ~100ms | Via transformers MarianMT. EN↔ES, EN→JA, JA→EN, JA→ES (pivot). |

### Python Packages
| Package | Purpose |
|:--------|:--------|
| `kokoro-onnx` | CPU TTS (54 voices, 5 langs) |
| `piper-tts` | CPU TTS fallback |
| `transformers` | MarianMT translation |
| `silero-vad` | VAD pre-filter for ASR |
| `cutlet` | Japanese romanization |
| `faster-whisper` | Multilingual ASR (GPU) |
| `psutil` + `pynvml` | System + GPU monitoring |
| `torch` | PyTorch CUDA 12.4 |
| `flask` + `flask-cors` | Grammar App backend |

---

## 📊 Evaluación Cualitativa de los 4 Subproyectos

### 1️⃣ 🎓 Teacher (PRODUCTION ⭐⭐⭐⭐⭐)
**Qué hace:** Tutor de idiomas con IA. El usuario escribe en su idioma nativo y obtiene: traducción, pronunciación (romaji), explicación gramatical, ejemplos y un ejercicio. Soporta ES/EN/JA con detección automática.

**Calidad como usuario:**
- ✅ **Multi-output estructurado** — 6 campos claros: texto objetivo, lectura TTS, pronunciación, traducción, explicación, ejercicio
- ✅ **Velocidad excelente** — Respuesta completa en ~3-5 segundos (vs ~15s en v2)
- ✅ **Cero emojis** — Output limpio, profesional, sin distracciones
- ✅ **TTS integrado** — Audio generado automáticamente al cargar la respuesta
- ✅ **Cache inteligente** — Preguntas repetidas responden en <1s
- ✅ **Idiomas reales** — Japonés con kanji + romaji, español natural, inglés fluido
- ❌ **Sin streaming en modo texto** — Toda la respuesta llega de una vez (mejorable)

### 2️⃣ 💬 Conversation (PRODUCTION ⭐⭐⭐⭐)
**Qué hace:** Chat conversacional donde la IA actúa como hablante nativo. Mantiene contexto, expresa opiniones, hace preguntas de seguimiento.

**Calidad como usuario:**
- ✅ **Streaming SSE en tiempo real** — Los tokens aparecen mientras se generan
- ✅ **Memoria de contexto** — Recuerda nombre, ubicación, temas anteriores (64K de contexto)
- ✅ **Inteligencia emocional** — Responde con empatía, no como robot
- ✅ **TTS automático** — Audio generado al completar cada respuesta
- ✅ **Voice round-trip** — Hablas → ASR → Chat → TTS → Escuchas (flujo completo)
- ⚠️ **Calidad variable** — Depende del idioma y tema; japonés conversacional es más lento
- ❌ **Sin personalidad configurable** — No se puede elegir "tutor formal" vs "amigo casual"

### 3️⃣ 🌍 Translator (PRODUCTION ⭐⭐⭐⭐)
**Qué hace:** Traductor de voz y texto con pipeline asíncrono. Soporta 5 pares de idiomas con TTS automático por idioma destino.

**Calidad como usuario:**
- ✅ **Pipeline async ultrarrápido** — Traducción completa en ~300ms (ASR + MarianMT + TTS en paralelo)
- ✅ **5 pares de idiomas** — EN↔ES, EN→JA, JA→EN, JA→ES (pivot automático)
- ✅ **TTS por idioma destino** — Voz diferente para cada idioma (em_alex ES, af_heart EN, jf_alpha JA)
- ✅ **Edge cases manejados** — Texto vacío, mismo idioma, texto largo 1300+ chars
- ✅ **Sin LLM** — No consume VRAM del modelo principal, funciona independientemente
- ❌ **Sin JA→ES directo** — Usa pivot vía EN, pierde matices en traducciones complejas
- ❌ **Sin detección automática de idioma** — El usuario debe seleccionar origen/destino

### 4️⃣ 📝 Grammar App (BETA ⭐⭐⭐)
**Qué hace:** App tipo Duolingo para práctica de gramática con ejercicios interactivos, sistema SRS (spaced repetition), gamificación (XP, corazones, rachas) y leaderboard.

**Calidad como usuario:**
- ✅ **6 tipos de ejercicio** — Multiple choice, fill blank, translate, word bank, listen type, match
- ✅ **Skill tree** — Árbol de habilidades con 3+ unidades y lecciones progresivas
- ✅ **SRS de vocabulario** — Repaso espaciado con 4 niveles de maestría
- ✅ **Gamificación** — XP, corazones (5 max, recarga cada 30 min), rachas diarias
- ✅ **Sin GPU** — Funciona en cualquier hardware (Flask + SQLite)
- ✅ **35/35 tests E2E pasados** — Verificado contra servidor real
- ⚠️ **BETA — En desarrollo activo** — UI básica, sin ejercicios generados por IA todavía
- ❌ **Sin integración con Teacher** — Los ejercicios son estáticos (no generados por LLM)
- ❌ **Sin TTS integrado** — Los ejercicios no tienen audio
- ❌ **Sin multi-idioma real** — Solo ejercicios ES→EN actualmente

---

## 🧪 E2E Test Suite (v3.3.1)

### Resultados Reales (ejecutado contra servidores activos)

| Suite | Tests | Resultado | Tiempo |
|:------|:-----:|:---------:|:------:|
| **test_grammar.py** | 35/35 | ✅ **PASS** | ~8s |
| **test_teacher.py** | 13 tests | ⏱️ Timeout (180s) | Necesita ~200-400s por 13 prompts LLM |
| **test_conversation.py** | — | ❌ No ejecutado | Puerto 3001 no activo |
| **test_translator.py** | — | ❌ No ejecutado | Puerto 3003 no activo |

**Cómo ejecutar:**
```bash
# Todos los tests disponibles
bash tests/e2e/run_all.sh

# Tests individuales (requiere servidor activo)
python3 tests/e2e/test_grammar.py       # Puerto 3004
python3 tests/e2e/test_teacher.py       # Puerto 3000 (timeout: 300s+)
```

---

## 🔧 Linux Installation Guide

### First-time Setup
```bash
# 1. Clone + install (1 comando)
git clone https://github.com/SCP-00/ALEX_voice.git
cd ALEX_voice
chmod +x install.sh
./install.sh

# 2. O manual:
chmod +x setup.sh
./setup.sh
ollama pull prometheus-orchestrator

# 3. Iniciar launcher
./alex_voice_app.sh
# O: source venv/bin/activate && python menu_server.py
```

### Keyboard Shortcuts (Menu)
| Tecla | Modo | Puerto |
|:-----:|:-----|:------:|
| `1` | 🎓 Teacher | 3000 |
| `2` | 💬 Conversation | 3001 |
| `3` | 🌍 Translator | 3003 |
| `4` | 📝 Grammar | 3004 |

### Hardware Recomendado
| GPU | VRAM | tok/s | Modelo | Veredicto |
|:----|:----:|:-----:|:-------|:----------|
| **RTX 3050 6GB** 🏆 | 5.28 GB usable | **~35 tok/s** | Qwen3.5 4B 64K | ✅ **Óptimo — setup actual** |
| RTX 4060+ 8GB | 7+ GB | ~50 tok/s | Qwen3.5 9B 96K | 🚀 Mejor, más inteligente |
| GTX 1650 4GB | 3.5 GB | ~15 tok/s | Qwen3.5 3B 32K | ⚠️ Mínimo, más lento |
| iGPU / CPU only | 0 GB | ~5 tok/s | Modelo 1-2B | ❌ Muy lento, no recomendado |
| RTX 3090 24GB | 22+ GB | ~90 tok/s | Qwen3.5 32B 128K | 🔥 Experiencia premium |

### Troubleshooting
| Issue | Solution |
|:------|:---------|
| Ollama not found | Install: `curl -fsSL https://ollama.com/install.sh \| sh` |
| Model not found | `ollama pull prometheus-orchestrator` |
| CUDA OOM | Close other GPU apps. Check `ollama ps` for loaded models. |
| Port in use | `fuser -k 5000/tcp` or `kill $(lsof -ti:5000)` |
| Translation fails | `rm -rf ~/.cache/huggingface/hub/` → re-downloads |
| Grammar DB error | `rm grammar_app/backend/grammar.db` → recreates on restart |

---

## 📦 Estructura del Repositorio
```
ALEX_voice/
├── menu_server.py              ← Hub principal (port 5000)
├── server.py                   ← Teacher + Conversation backend
├── conv_server.py              ← Conversation wrapper
├── translator.py               ← Translator pipeline
├── prompts.py                  ← System prompts multi-idioma
├── grammar_app/                ← Proyecto 4: Grammar App (BETA)
│   ├── backend/
│   │   ├── app.py              ← Flask server (port 3004)
│   │   └── database.py         ← SQLite schema + SRS
│   └── frontend/
│       ├── index.html          ← 5 pantallas (login, dashboard, lesson, etc.)
│       ├── css/style.css       ← Duolingo-inspired dark theme
│       └── js/
│           ├── api.js          ← API client
│           └── app.js          ← App logic
├── frontend/                   ← Launcher frontend
│   ├── menu.html               ← Menu principal + cards
│   ├── index.html              ← Teacher UI
│   ├── conv.html               ← Conversation UI
│   └── translator.html         ← Translator UI
├── models/                     ← Modelos descargados (gitignored)
├── tests/e2e/                  ← E2E test suite
├── setup.sh / install.sh       ← Instaladores
├── alex_voice_app.sh           ← Entry point unificado
├── PLAN.md / AGENT.md / README.md
└── .gitignore
```

---

## GitHub
- **Remote:** `https://github.com/SCP-00/ALEX_voice.git`
- **Branches:** `linux` (actualizada), `master` (default en GitHub)
- **Branch recomendada:** `linux` (contiene Grammar App + tests + docs)
- ⚠️ Para clonar con la última versión: `git clone -b linux https://github.com/SCP-00/ALEX_voice.git`
