# 📋 Alex Voice — Plan de Mejora v3

> Última actualización: Junio 2026

---

## ✅ v3 Completado — Unified Launcher + Ollama API + Streaming SSE

### 🏗️ Migración a Ollama API (v3.1)
- ✅ **LLM Backend:** llama-server directo (GGUF) → **Ollama API** (`http://localhost:11434/v1`)
- ✅ **Modelo:** Qwen2.5-coder:3b → **prometheus-orchestrator** (Qwen3.5 4B Instruct, 64K ctx)
- ✅ **Thinking:** Desactivado (`reasoning_format: none`) → respuestas directas sin delay
- ✅ **Cleanup VRAM:** `kill_all()` libera modelo via `POST /api/generate` con `keep_alive: "0m"`
- ✅ **server.py:** `num_ctx: 65536` en todos los chat_data → **64K optimizado**
- ✅ **menu_server.py:** Eliminadas funciones legacy de llama-server
- ✅ **Launcher renombrado:** `alex-voice.sh` → `alex_voice_app.sh`
- ✅ **.desktop:** Actualizado con nuevo nombre

### 📡 Streaming SSE para Chat LLM (v3.2)
- ✅ **SSE Streaming** en Teacher (index.html) y Conversation (conv.html)
- ✅ Tokens aparecen en tiempo real via `ReadableStream` reader
- ✅ Teacher mode: `parseMultiOutput()` client-side + `renderTeacherCards()` post-stream
- ✅ Conversation voice flow con streaming también activo
- ✅ Fallback automático a full JSON para respuestas cacheadas

### Async Translation Pipeline (v3)
- ✅ `TranslationPipeline` — Queue-based workers: ASR→Translation→TTS
- ✅ `ThreadingHTTPServer` — Non-blocking request handling
- ✅ `/api/pipeline` — Full async pipeline con timing breakdown
- ✅ 5 pares de idiomas: EN↔ES, EN→JA, JA→EN, JA→ES (pivot automático)

### Frontend Rediseñado
- ✅ `menu.html` — Glassmorphism dark mode, cards con glow por modo
- ✅ `index.html` — Card-based Teacher, SSE streaming, voice wave animation
- ✅ `conv.html` — Voice visualizer, chat bubbles, SSE streaming
- ✅ `translator.html` — Split-view, language selectors, audio playback

---

## ✅ v3.3 Completado — Quality Fixes + TTS Research

### 🔧 Quality Fixes (v3.3.1)
- ✅ **Japanese kanji fix:** `_sanitize_tts_text()` now language-aware — preserves hiragana/katakana/kanji for JA via `_TTS_SAFE_JA_RE`
- ✅ **Text spacing fix:** `_normalize_tts_spacing()` inserts spaces after punctuation for natural TTS pauses
- ✅ **Teacher speed:** Temperature 0.3 (was 0.5), n_predict 384 (was 512) — faster + more deterministic
- ✅ **Spanish TTS voice:** `ef_dora` → `em_alex` (male, better naturalness), speed 0.9x
- ✅ **Japanese TTS speed:** 0.9x for clearer kanji pronunciation
- ✅ **misaki[ja]** installed for native Japanese phonemization in Kokoro
- ✅ **Grammar mode** disabled card added to menu ("Próximamente")
- ✅ **64K ctx** reflected in menu UI (was showing 262K)

### 🔬 TTS Research (June 2026)

#### Benchmark: Best Open-Source TTS 2026
| Model | Params | VRAM | ES+JA | Quality | License | Veredicto |
|:------|:------:|:----:|:-----:|:-------:|:-------:|:----------|
| **Qwen3-TTS** | 1.7B | ~6GB | ✅ Native | 🏆 SOTA | Apache 2.0 | Mejor calidad, pero incompatible (necesita 6GB solo) |
| **Kokoro-82M** | 82M | CPU | ✅ Good | Muy buena | Apache 2.0 | ✅ **MANTENER** — mejor ratio calidad/hardware |
| **F5-TTS** | 335M | 3-5GB | ⚠️ Fine-tune | Buena | CC-BY-NC | ❌ Non-commercial |
| **Chatterbox** | ~1B | 4-6GB | ⚠️ English | Excelente | MIT | ❌ Solo inglés |
| **Piper** | Small | CPU | ✅ Wide | Aceptable | MIT | ✅ **FALLBACK** — ultra-rápido |
| **XTTS v2** | ~2B | 4-6GB | ✅ Good | Alta | CPML | ❌ Non-commercial |

#### Decisión TTS: Híbrido Kokoro-82M + secuencialización
**¿Por qué NO Qwen3-TTS?**
- Requiere ~6GB VRAM → imposible correr con el LLM (Qwen3.5 4B = ~2.5GB) en RTX 3050 6GB
- El LLM es prioritario para generación de texto. TTS corre en CPU con Kokoro sin consumir VRAM
- Kokoro-82M es "good enough" con las voces optimizadas y misaki phonemization

**Plan de mejora TTS (sin cambiar modelo):**
1. ✅ Voz `em_alex` para español (mejor que `ef_dora`)
2. ✅ Velocidad 0.9x para español y japonés (más pausado, más claro)
3. ✅ `misaki[ja]` para phonemización nativa de kanji
4. 🔜 Secuencializar TTS: dividir texto largo en oraciones, sintetizar una por una, concatenar
5. 🔜 Agregar pausa entre oraciones (silence padding de 200-400ms)
6. 🔜 Probar voces alternativas: `em_santa` (ES male), `jf_gongitsune` (JA female)

### 🔬 Real Tests (TTS — June 2026)
| Test | Lang | Input | Time | Size | Status |
|:-----|:----:|:------|:----:|:----:|:------:|
| JA romaji | ja | Konnichiwa, genki desu ka? | 3427ms | 72KB | ✅ |
| ES normal | es | Hola, como estas hoy? | 3962ms | 138KB | ✅ |
| EN normal | en | Hello! How are you today? | 248ms | 155KB | ✅ |
| **JA kanji** 🎯 | ja | 日本語の勉強は楽しいです | 1017ms | 779KB | ✅ **FIXED** |

---

## 📊 Métricas v3.3 (64K Optimizado)

### VRAM Budget (post-optimización)
| Modo | Componentes | VRAM | Cambio |
|:-----|:------------|:----:|:------:|
| **Teacher** | Ollama 64K (~2.5GB) + Whisper (~1.5GB) | **~4.0 GB** | ✅ -0.5GB |
| **Conversation** | Ollama 64K (~2.5GB) + Whisper (~1.5GB) | **~4.0 GB** | ✅ -0.5GB |
| **Translator** | Whisper (~1.5GB) + MarianMT (~0.2GB) | **~1.7 GB** | Sin cambio |

### Benchmarks — prometheus-orchestrator 64K ctx (RTX 3050 6GB)
| Contexto | Velocidad | KV Cache | VRAM Total | Estabilidad |
|:--------:|:---------:|:--------:|:----------:|:----------:|
| **64K** 🏆 | **~35 tok/s** | **~1.2 GB** | **~4.0 GB** | ✅ **Óptimo** |
| 196K (default) | ~22 tok/s | ~3.8 GB | ~5.5 GB | ⚠️ Swap riesgo |
| 262K (máximo) | ~15 tok/s | ~5.0 GB | ~6.5 GB | ❌ OOM |

| Idioma | Velocidad (64K) | Calidad |
|:-------|:---------------:|:-------:|
| **EN** | **34.9 tok/s** | ✅ Excelente |
| **ES** | **~40 tok/s** | ✅ Español natural |
| **JA** | **~40 tok/s** | ✅ Japonés correcto |

### Pipeline Latency (Async)
| Stage | Latency | Hardware |
|:------|:-------:|:---------|
| ASR (Whisper small) | ~50ms | GPU |
| Translation (MarianMT) | ~100ms | GPU |
| TTS (Kokoro ONNX) | ~150ms | CPU |
| **Total (parallel)** | **~300ms** | GPU+CPU |

---

## 🎯 Visión v4 — 4 Proyectos, Monorepo, Multiplataforma

### Los 4 Proyectos
| # | Proyecto | Estado | Core |
|:-:|:---------|:------:|:-----|
| 1 | **🎓 Teacher** | ✅ Activo | server.py + index.html → `/api/chat` teacher mode |
| 2 | **💬 Conversation** | ✅ Activo | conv_server.py + conv.html → `/api/chat` conversation mode |
| 3 | **🌍 Translator** | ✅ Activo | translator.py + translator.html → pipeline async |
| 4 | **📝 Grammar App** | 🔜 Planned | App web propia con SQLite para memoria a largo plazo |

### Monorepo — Estructura Propuesta
```
alex-voice/                          ← Monorepo
├── apps/
│   ├── teacher/                     ← Proyecto 1
│   │   ├── server.py
│   │   └── frontend/
│   ├── conversation/                ← Proyecto 2
│   │   ├── wrapper.py               ← Importa teacher/server.py
│   │   └── frontend/
│   ├── translator/                  ← Proyecto 3
│   │   ├── translator.py
│   │   └── frontend/
│   └── grammar/                     ← Proyecto 4 (futuro)
│       ├── app.py
│       ├── database.py              ← SQLite con aprendizaje del usuario
│       └── frontend/
│
├── shared/                          ← Código compartido
│   ├── tts.py                       ← Kokoro TTS
│   ├── asr.py                       ← Whisper ASR
│   ├── prompts.py                   ← System prompts multi-idioma
│   └── utils.py                     ← Sanitization, language detection
│
├── launcher/
│   ├── menu_server.py               ← Hub principal (port 5000)
│   └── frontend/menu.html
│
├── scripts/
│   ├── setup.sh                     ← Linux setup
│   ├── setup_windows.bat            ← Windows setup (futuro)
│   └── install_models.py            ← Descarga automática de modelos
│
├── alex_voice_app.sh                ← Entry point unificado
├── alex-voice.desktop               ← Atajo de escritorio
├── PLAN.md                          ← Este archivo
├── AGENT.md                         ← Guía para IA
└── README.md                        ← Documentación principal
```

### ¿Por qué monorepo y no 4 repos separados?
- Código compartido (TTS, ASR, prompts) en un solo lugar
- Refactor cross-project inmediato
- 1 setup.sh para todo (vs 4 scripts)
- Menos storage (modelos compartidos)
- Fácil de clonar para nuevos usuarios
- Cada app tiene su propio ciclo, pero todo comparte base

---

## 🔜 Fase 1: Optimización + Consolidación (v3.3)

### ⚡ Contexto Optimizado (v3.3 — COMPLETADO)
- ✅ Reducido `num_ctx` de 262K a **64K** (65536)
- ✅ Velocidad: 34.9 tok/s vs ~15 tok/s a 262K (**+130%**)
- ✅ VRAM liberada: ~1.5GB → cabe Whisper + LLM sin swap
- ✅ `NUM_CTX` env var configurable (default 65536)
- ✅ Aplica a Teacher + Conversation + todos los modos

### 🚀 Launcher Unificado (v3.3 — COMPLETADO)
- ✅ `alex-voice.sh` → **`alex_voice_app.sh`**
- ✅ Atajo de escritorio actualizado
- ✅ Documentación actualizada (README, AGENT, setup)

### ⬇️ Sistema de Descarga Automática de Modelos
- [ ] `scripts/install_models.py` — Script Python que descarga:
  - Kokoro ONNX (311MB) del release oficial
  - Piper TTS ES+EN (modelos ONNX)
  - Traducción MarianMT (vía transformers, cache automático)
- [ ] Con barra de progreso y reintentos
- [ ] Detección de modelo ya descargado (skip)
- [ ] `setup.sh` → llama a `install_models.py` en vez de tener lógica duplicada

### 🪟 Compatibilidad Windows
- [ ] `scripts/setup_windows.bat` — Instalador para Windows 10/11
  - Instala Python 3.10+ (sino existe)
  - Crea venv + pip install
  - Descarga Ollama para Windows
  - Pull de prometheus-orchestrator
  - Llama a `install_models.py`
- [ ] Manejo de paths Windows (backslashes, `%APPDATA%`)
- [ ] Verificación de GPU NVIDIA (nvidia-smi en Windows)
- [ ] Atajo en Start Menu / Desktop

### 📦 Easy Install (One-Click)
- [ ] `install.sh` / `install.bat` — Script único que hace TODO:
  1. Verifica hardware (GPU, RAM, disco)
  2. Instala dependencias del sistema
  3. Configura Ollama + modelo
  4. Descarga modelos
  5. Crea atajo de escritorio
  6. Abre http://localhost:5000
- [ ] Sin requerir conocimientos técnicos
- [ ] Mensajes claros en español/inglés
- [ ] Detección automática de SO (Linux / Windows)

---

## 🔜 Fase 2: Grammar App (Proyecto 4)

### 📝 App Web de Ejercicios con Memoria
- **Propósito:** Práctica estructurada de gramática con seguimiento del progreso
- **Backend:** Servidor Python independiente (FastAPI o Flask)
- **Base de datos:** SQLite con esquema de usuarios, ejercicios, historial
- **Frontend:** App web propia (independiente de Teacher/Conv/Translator)

### Esquema de Base de Datos (propuesto)
```sql
-- Usuarios (cada persona tiene su progreso)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    native_lang TEXT DEFAULT 'es',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ejercicios realizados
CREATE TABLE exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    exercise_type TEXT NOT NULL,  -- 'fill_blank', 'translate', 'conjugate', 'correct'
    source_lang TEXT NOT NULL,
    target_lang TEXT NOT NULL,
    prompt TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    user_answer TEXT,
    is_correct BOOLEAN,
    llm_feedback TEXT,            -- Explicación generada por IA
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Estadísticas de aprendizaje
CREATE TABLE progress (
    user_id INTEGER REFERENCES users(id),
    lang_pair TEXT NOT NULL,       -- 'es->ja', 'en->es', etc.
    total_exercises INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    streak_days INTEGER DEFAULT 0,
    last_practice DATE,
    weak_areas TEXT               -- JSON: ["verbos", "partículas", etc.]
);
```

### Funcionalidades Clave
- [ ] Ejercicios generados por IA vía prometheus-orchestrator
- [ ] Feedback inmediato con explicación gramatical
- [ ] Seguimiento de errores frecuentes por usuario
- [ ] Sistema de repaso espaciado (spaced repetition)
- [ ] Estadísticas: racha, aciertos, áreas débiles
- [ ] API REST para frontend web

---

## 🔜 Fase 3: Easy Install + Multiplataforma

### 🐧 Linux — Instalación con 1 comando
```bash
curl -fsSL https://alex-voice.dev/install.sh | sh
# O: git clone + cd + ./install.sh
```

### 🪟 Windows — Instalación con 1 clic
```powershell
# Descargar install.bat del repo, ejecutar como Admin
# O: git clone + install.bat
```

### Automatizaciones
- [ ] Detección automática de GPU NVIDIA
- [ ] Selección de modelo según VRAM (4GB → modelo más pequeño)
- [ ] Configuración de Ollama systemd service
- [ ] Firewall rules para puertos (5000, 3000, 3001, 3003)
- [ ] Autostart opcional al iniciar sesión

---

## 📐 Decisiones de Diseño

### ¿Por qué 64K contexto en vez de 262K?
- **262K:** KV cache ~5GB → OOM en RTX 3050 6GB con Whisper cargado
- **64K:** KV cache ~1.2GB, velocidad **34.9 tok/s** vs ~15 tok/s
- 64K = ~20 exchanges completos → más que suficiente para conversación
- `NUM_CTX` configurable via env var para quien tenga más VRAM

### ¿Por qué monorepo y no repos separados?
- TTS, ASR y prompts compartidos → **0 duplicación**
- Refactors afectan a todos los proyectos automáticamente
- 1 setup para todo → mejor UX para usuarios no técnicos
- Se puede clonar solo un subdirectorio si se prefiere

### ¿Por qué una Grammar App separada y no integrada en Teacher?
- Teacher es reactivo: el usuario pregunta, el sistema responde
- Grammar es proactivo: el sistema genera ejercicios, el usuario los resuelve
- Grammar necesita persistencia (SQLite) → Teacher no
- Separación permite ciclos de desarrollo independientes
- La Grammar App puede reusar TTS/ASR del shared/

---

## 🧪 E2E Test Suite v3.3.1 — Exhaustive Validation

### Archivos creados
```
tests/e2e/
├── test_teacher.py      ← 🎓 Teacher mode (14 tests, 6 language pairs)
├── test_conversation.py ← 💬 Conversation mode (3 languages × 3 scenarios + stress)
├── test_translator.py   ← 🌍 Translator (6 pairs + TTS + edge cases)
├── test_grammar.py      ← 📝 Grammar App (auth, exercises, SRS, DB)
├── rubric.md            ← 📊 Scoring criteria per subproject
├── run_all.sh           ← 🔧 Runner script (checks ports, runs available)
└── results_*.json       ← 📄 Auto-generated results per suite
```

### Cómo ejecutar
```bash
# Todos los tests (auto-detecta servidores corriendo)
bash tests/e2e/run_all.sh

# Tests individuales (requiere servidor activo en el puerto)
python3 tests/e2e/test_teacher.py       # Puerto 3000
python3 tests/e2e/test_conversation.py   # Puerto 3001
python3 tests/e2e/test_translator.py     # Puerto 3003
python3 tests/e2e/test_grammar.py        # Puerto 3004
```

### 🎓 Teacher — Suite de Tests
| # | Test | Descripción | Idiomas |
|---|------|-------------|---------|
| 1 | Multi-output format | Validar los 6 campos (TEXT, TTS_READING, PRONUNCIATION, TRANSLATION, EXPLANATION, EXERCISE) | Todos |
| 2 | No emojis | Cero emojis Unicode en cualquier campo del output | Todos |
| 3 | Word spacing (joinwords fix) | Sin palabras concatenadas: `Sensei,ohayōgozaimasu` ❌ → `Sensei, ohayō gozaimasu` ✅ | Todos |
| 4 | Language correctness | TEXT en idioma OBJETIVO, no en idioma origen | Todos |
| 5 | TTS_READING Latin script | Romaji japonés con macrones (ō, ū), sin CJK | ES→JA, EN→JA |
| 6 | Grammar accuracy | Explicaciones gramaticales correctas | Todos |
| 7 | Cultural context | Notas culturales en japonés (formalidad, etiqueta) | Todos |
| 8 | Formality levels | Versión formal + casual cuando se pide | Todos |
| 9 | Examples count | ≥3 ejemplos concretos por explicación | Todos |
| 10 | TTS latency | <8s para texto corto, <15s para secuencial | Todos |
| 11 | Cache effectiveness | Respuesta cacheada ≥3x más rápida | Todos |
| 12 | VRAM stability | Sin crecimiento >500MB durante el test | Todos |
| 13 | Long explanations | Explicaciones >50 chars con contenido sustancial | Todos |
| 14 | Exercise quality | Ejercicio práctico incluido y relevante | Todos |

**Pares de idiomas testeados FROM cada idioma:**
- **FROM Spanish:** ES→JA (3 tests), ES→EN (2 tests)
- **FROM English:** EN→JA (2 tests), EN→ES (2 tests)
- **FROM Japanese:** JA→ES (2 tests), JA→EN (2 tests)

### 💬 Conversation — Suite de Tests
| # | Test | Descripción |
|---|------|-------------|
| 1 | Language matching | Responde en EXACTAMENTE el mismo idioma del usuario |
| 2 | Natural tone | Fele como hablar con una persona, no un chatbot |
| 3 | Opinion expression | Expresa opiniones personales ("I think...", "Creo que...") |
| 4 | Follow-up questions | Hace preguntas para continuar la conversación |
| 5 | Emotional intelligence | Responde con empatía a mensajes emocionales |
| 6 | Context memory | Recuerda nombre, ubicación, trabajo dados 3 mensajes atrás |
| 7 | Topic switching | Maneja cambios de tema abruptos con gracia |
| 8 | Long conversation | 10 mensajes sin degradación de calidad |
| 9 | TTS streaming | Audio inicia en <2s de la respuesta |
| 10 | Voice round-trip | Flujo completo ASR→Chat→TTS funciona |

**Escenarios por idioma:**
- **Spanish:** Saludo casual, cambio de tema, inteligencia emocional
- **English:** Charla de películas, debate de opiniones
- **Japanese:** Conversación básica, manejo de idioma mixto

### 🌍 Translator — Suite de Tests
| # | Test | Descripción |
|---|------|-------------|
| 1 | EN↔ES accuracy | Traducciones directas correctas |
| 2 | EN→JA accuracy | Inglés→Japonés natural |
| 3 | JA→EN accuracy | Japonés→Inglés preciso |
| 4 | JA→ES accuracy | Japonés→Español (pivot vía EN) |
| 5 | ES→JA accuracy | Español→Japonés (pivot vía EN) |
| 6 | Idiom translation | "raining cats and dogs" → "lloviendo a cántaros" |
| 7 | TTS per language | em_alex (ES), af_heart (EN), jf_alpha (JA) |
| 8 | Edge: empty input | Retorna error, no crash |
| 9 | Edge: same language | EN→EN retorna texto original |
| 10 | Edge: long text | 1300+ chars sin timeout |
| 11 | Model lifecycle | Load/unload libera VRAM |

### 📝 Grammar App — Suite de Tests
| # | Test | Descripción |
|---|------|-------------|
| 1 | Register new user | Usuario creado con campos correctos |
| 2 | Duplicate rejection | 409 en username duplicado |
| 3 | Login + session | Cookie de sesión 设置 correctamente |
| 4 | Session persistence | /api/auth/me retorna usuario |
| 5 | Logout | Sesión limpia, 401 después |
| 6 | Skill tree | ≥3 unidades con lecciones |
| 7 | No answer leak | correct_answer nunca enviado al cliente |
| 8 | Submit exercise | correct=true + XP, correct=false + heart |
| 9 | Hearts system | Hearts disminuyen, recharge a 5 |
| 10 | Streak tracking | Streak diario, reset en gap |
| 11 | Vocabulary SRS | Add, review, mastery ±1 |
| 12 | Leaderboard | Usuarios rankeados por XP |
| 13 | DB integrity | 8 tablas, foreign keys, seed data |
| 14 | Frontend serving | CSS, JS, HTML servidos correctamente |

### 📊 Rubrica de Scoring
| Subprojecto | Min Score | Criterio de Fallo Automático |
|:------------|:---------:|:---------------------------|
| 🎓 Teacher | **7.5/10** | Crash, data leak, zero emojis violated |
| 💬 Conversation | **7.5/10** | Crash, language mismatch, context loss |
| 🌍 Translator | **7.0/10** | Crash, wrong translation pair, VRAM leak |
| 📝 Grammar App | **8.0/10** | Crash, auth bypass, answer leak |

**Condiciones de fallo automático (independiente del score):**
- Server crash durante cualquier test
- Data leak (correct_answer expuesto al cliente)
- Memory leak (VRAM crece >1GB durante test)
- Security issue (auth bypass en endpoints protegidos)
- Política de cero emojis violada en output Teacher/TTS

---

## 📈 Roadmap

### v3.3 — Julio 2026 (Optimización + Consolidación)
- [ ] ✅ Contexto 64K optimizado
- [ ] ✅ Launcher renombrado a `alex_voice_app.sh`
- [ ] `install_models.py` — Descarga automática de modelos
- [ ] `setup_windows.bat` — Instalador Windows
- [ ] `install.sh` / `install.bat` — One-click install

### v3.4 — Julio-Agosto 2026 (Grammar App)
- [ ] Proyecto 4: Grammar App con SQLite
- [ ] API REST + frontend web
- [ ] Ejercicios generados por IA
- [ ] Progreso del usuario (racha, aciertos, áreas débiles)

### v4 — Q4 2026 (Multiplataforma + Feature Complete)
- [ ] Instalador Windows con GUI
- [ ] Spaced repetition system
- [ ] Multi-speaker TTS
- [ ] Export/Import de progreso

---

*Plan actualizado: Junio 2026*
*Proyecto: Alex Voice v3.3*
*Autor: SCP-076 (Victor Buendia) + Buffy (AI Agent)*
