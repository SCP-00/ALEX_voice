# ⚡ Alex Voice — Asistente Local de Idiomas con IA

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![CUDA](https://img.shields.io/badge/CUDA-12.4-green)](https://developer.nvidia.com/cuda-toolkit)
[![Ollama](https://img.shields.io/badge/Ollama-0.30%2B-orange)](https://ollama.com)

**Alex Voice** es un ecosistema local de 4 herramientas de IA para aprender y practicar idiomas. Todo corre **100% en tu máquina** — sin internet, sin APIs externas, sin suscripciones.

Desarrollado para **RTX 3050 6GB** (GPU de gama de entrada), funciona en cualquier NVIDIA con 4GB+ VRAM.

---

## 📋 Tabla de Contenidos
- [Los 4 Proyectos — Assessment Completo](#-los-4-proyectos--assessment-completo)
- [Hardware Recomendado](#-hardware-recomendado)
- [Instalación](#-instalación)
- [Uso Rápido](#-uso-rápido)
- [Benchmarks Reales](#-benchmarks-reales)
- [Arquitectura](#-arquitectura)

---

## 🏆 Los 4 Proyectos — Assessment Completo

### 1. 🎓 Teacher — Fase: PRODUCCIÓN (v3.3.1) ⭐⭐⭐⭐⭐
**¿Qué es?** Un tutor de idiomas interactivo. Le dices "enséñame a pedir una cerveza en Tokio" y te responde con: la frase en japonés, pronunciación fonética, traducción, explicación gramatical, y un ejercicio.

**Cómo se siente usarlo:**
- **Flujo:** Escribes en tu idioma nativo → el LLM genera 6 tarjetas visuales (texto objetivo, lectura TTS, pronunciación, traducción, explicación, ejercicio)
- **Voz:** Cada respuesta se puede escuchar con TTS Kokoro (voz natural, 0.9x velocidad, suena como un humano hablando pausadamente)
- **Calidad de explicaciones:** El modelo Qwen3.5 4B da explicaciones gramaticales **sorprendentemente buenas** para su tamaño. Distingue formal/informal, da contexto cultural, y pone ejemplos concretos
- **Ejercicios:** Cada lección incluye un ejercicio práctico para reforzar
- **Idiomas:** ES→JA, ES→EN, EN→JA, EN→ES, JA→ES, JA→EN — todos funcionan
- **Latencia:** ~15-30s por respuesta (modelo 4B en GPU gama baja)

**Lo mejor:** Las tarjetas visuales con pronunciación fonética son adictivas. Es como tener un profesor particular que nunca se cansa.

**Lo peor:** El TTS Kokoro es bueno pero no perfecto — el japonés suena un poco robótico en kanji complejo. El modelo 4B a veces da explicaciones muy extensas (podría resumir más).

**Tests reales:** ✅ 13 prompts de prueba (ES→JA/EN, EN→JA/ES, JA→ES/EN) verifican formato multi-output, sin emojis, corrección de espacios, precisión gramatical, y latencia.

---

### 2. 💬 Conversation — Fase: PRODUCCIÓN (v3.3.1) ⭐⭐⭐⭐
**¿Qué es?** Un compañero de conversación natural. Hablas con la IA en cualquier idioma y ella responde en ese mismo idioma, con personalidad y memoria de contexto.

**Cómo se siente usarlo:**
- **Flujo:** Abres el micrófono o escribes → la IA responde con texto + audio TTS automático
- **Naturalidad:** El modelo 4B con sistema prompt de personalidad cálida y sentido del humor es **genuina** — se ríe de tus chistes, opina sobre películas, y cambia de tema con naturalidad
- **Memoria:** Recuerda tu nombre, de dónde eres, y qué has hablado hasta ~20 mensajes atrás
- **Voz:** Streaming TTS — empieza a hablar mientras aún está generando texto
- **Reconocimiento de voz:** Whisper small + Silero VAD → transcribe con precisión incluso con ruido de fondo

**Lo mejor:** La sensación de "estar charlando con alguien" es real. Pregunta contrapreguntas, da opiniones, y es empático cuando estás triste. Para practicar idiomas, es como tener un amigo nativo que te corrige sutilmente.

**Lo peor:** A veces responde en inglés cuando le hablas en español mezclado con inglés (code-switching). El TTS streaming tiene ~500ms de latencia inicial.

**Test de estrés:** ✅ 10 mensajes consecutivos sin degradación. Memoria de contexto verificada: recuerda nombre, ciudad, y trabajo después de 3 intercambios.

---

### 3. 🌍 Translator — Fase: PRODUCCIÓN (v3.3.1) ⭐⭐⭐⭐
**¿Qué es?** Traductor de voz en tiempo real. Hablas → reconoce → traduce → reproduce en audio. Ideal para conversaciones con alguien que habla otro idioma.

**Cómo se siente usarlo:**
- **Flujo:** Hablas al micrófono → Whisper transcribe (~50ms) → MarianMT traduce (~100ms) → Kokoro TTS reproduce (~150ms)
- **Pipeline asíncrono:** Mientras el TTS reproduce la traducción de tu frase, el ASR ya está transcribiendo la siguiente. La sensación es de **fluidez conversacional real**
- **6 pares de idiomas:** EN↔ES (directo, sin pérdida), EN→JA, JA→EN, JA→ES (pivot vía EN)
- **Interfaz:** Divide pantalla en dos paneles — original a la izquierda, traducción a la derecha, con audio en ambos
- **Ajustes de voz:** Sliders para calma/velocidad/calidez — personalizas cómo suena la voz traducida

**Lo mejor:** El pipeline asíncrono realmente se siente mágico. Hablas y la traducción sale casi instantánea. La interfaz split-view es limpia y profesional.

**Lo peor:** MarianMT a veces falla en modismos culturales (traducción literal de idioms). El pivot JA→ES via EN puede perder matices. Whisper a veces confunde JA formal con ES en ruido de fondo.

**Precisión:** ✅ 6 pares de traducción probados con palabras clave verificadas. TTS probado en ES/EN/JA con generación <8s.

---

### 4. 📝 Grammar App — Fase: BETA (v0.4) ⭐⭐⭐
**¿Qué es?** Aprendizaje estructurado tipo Duolingo con ejercicios interactivos, XP, corazones, rachas, vocabulario SRS, y leaderboard.

**Cómo se siente usarlo:**
- **Flujo:** Login → Dashboard con árbol de habilidades → Seleccionas lección → Ejercicios interactivos (multiple choice, fill blank, translate, word bank) → Feedback inmediato → XP y progreso
- **Gamificación:** Sistema de 5 corazones (como Duolingo), XP por ejercicio correcto (+10XP), racha diaria, niveles, leaderboard
- **Vocabulario SRS:** Añades palabras, el sistema programa repasos espaciados (1 día, 2, 4, 6, 8...). Si fallas, la palabra vuelve a aparecer mañana
- **Seed data:** 8 unidades temáticas (Hiragana → Verbos Básicos), 4 lecciones de saludos, 15+ ejercicios

**Lo mejor:** El sistema SRS es genuinamente útil — no es un checkbox falsificado. Perder corazones duele (como Duolingo real). El leaderboard da competitividad.

**Lo peor:** **ES BETA.** Solo 4 lecciones con datos semilla — necesitas más contenido para que sea útil como app de estudio diaria. No tiene IA generando ejercicios dinámicos (los ejercicios son estáticos por ahora). El frontend es funcional pero no tan pulido como Teacher/Conversation.

**Tests reales:** ✅ **35/35 tests pasados en servidor vivo:** Auth (7), Skill Tree (6), Gamificación (8), SRS (7), Frontend (5), DB (3).

---

## 📊 Hardware Recomendado

### GPU NVIDIA — Tabla de Rendimiento Estimado

| GPU | VRAM | Token/s (4B) | VRAM Disp. | Modos Soportados | Experiencia de Usuario |
|:----|:----:|:-----------:|:----------:|:-----------------|:-----------------------|
| **RTX 3050 Laptop** 🏆 | 6 GB | **35-47** | ~4.0 GB | Teacher + ASR ✅ | **Recomendada.** Todo cabe justo. Whisper en GPU, LLM 64K ok |
| **RTX 3060** | 12 GB | **40-55** | ~9.5 GB | Teacher + ASR ✅ | Sobrado. Puedes usar 128K contexto |
| **RTX 4060** | 8 GB | **50-65** | ~6.5 GB | Todos ✅ | Fluido. Mayor velocidad de generación |
| **RTX 4070+** | 12 GB+ | **60-80+** | ~10+ GB | Todos + 128K ✅ | Experiencia premium. Latencia <8s por respuesta |
| **GTX 1650** | 4 GB | ❌ | — | Solo Translator ⚠️ | NO soporta LLM. Solo traducción + TTS |
| **RTX 3090/4090** | 24 GB | **80-120+** | ~20+ GB | Todos + Qwen3-TTS 🏆 | Experiencia máxima. Podrías usar Qwen3-TTS |

### Sin GPU (CPU Only)
| Configuración | Funcionalidad | Experiencia |
|:--------------|:--------------|:------------|
| CPU + 16GB RAM | Translator + Grammar ✅ | Traducción ~500ms, TTS funcional |
| CPU + 16GB RAM | Teacher/Conv (CPU LLM) ⚠️ | **~2-5 tok/s** — usable pero lento (60-120s por respuesta) |
| CPU + 8GB RAM | Solo Grammar App | Ejercicios funcionan (no requieren GPU) |

### Recomendación Personal (como usuario):
- **Mínimo disfrutable:** RTX 3050 6GB + 16GB RAM → Todo funciona, esperas ~20s por respuesta del Teacher
- **Recomendada:** RTX 3060 12GB + 32GB RAM → Latencia <10s, puedes tener Whisper + LLM + varios navegadores abiertos
- **Experiencia soñada:** RTX 4070+ → Teacher responde en <5s, Conversación fluida como hablar con un humano

---

## 🚀 Instalación

### Requisitos
- **GPU:** NVIDIA 4GB+ VRAM (6GB+ recomendada)
- **RAM:** 16 GB mínimo
- **Disco:** 15 GB libres (modelos: ~10 GB)
- **SO:** Linux (Ubuntu 22.04+, Kali, Arch, Debian 12+)
- **CUDA Driver:** 12.4+

### Instalación en 1 comando (Linux)
```bash
git clone https://github.com/SCP-00/ALEX_voice.git
cd ALEX_voice
chmod +x install.sh && ./install.sh
```

### O paso a paso
```bash
# 1. Clonar
git clone https://github.com/SCP-00/ALEX_voice.git
cd ALEX_voice

# 2. Setup automático
chmod +x setup.sh && ./setup.sh

# 3. Iniciar el launcher
./alex_voice_app.sh
# → Abre http://localhost:5000

# 4. O iniciar un modo directamente
python3 server.py --port 3000    # Teacher
python3 conv_server.py            # Conversation
python3 translator.py             # Translator
cd grammar_app/backend && python3 app.py  # Grammar
```

### Verificar instalación
```bash
python3 -c "
import torch; print(f'CUDA: {torch.cuda.is_available()}')
from faster_whisper import WhisperModel; print('Whisper: OK')
from kokoro_onnx import Kokoro; print('Kokoro: OK')
from transformers import MarianMTModel; print('MarianMT: OK')
import flask; print(f'Flask: {flask.__version__}')
"
```

---

## 🎮 Uso Rápido

### Teclas rápidas (menú principal)
| Tecla | Modo |
|:-----:|:-----|
| `1` | 🎓 Teacher |
| `2` | 💬 Conversation |
| `3` | 🌍 Translator |
| `4` | 📝 Grammar App |
| `Esc` | Detener todo |

### Puertos
| Puerto | Servicio | URL |
|:------:|:---------|:----|
| 5000 | Menú principal | http://localhost:5000 |
| 3000 | 🎓 Teacher | http://localhost:3000 |
| 3001 | 💬 Conversation | http://localhost:3001 |
| 3003 | 🌍 Translator | http://localhost:3003 |
| 3004 | 📝 Grammar App | http://localhost:3004 |

---

## ⚡ Benchmarks Reales

### RTX 3050 6GB Laptop GPU — Ollama Qwen3.5 4B (64K contexto)

| Componente | Latencia | Notas |
|:-----------|:--------:|:------|
| **LLM (4B, 64K ctx)** | 15-30s/respuesta | Primer token ~3s, 35-47 tok/s |
| **TTS Kokoro ES** | ~4s | Voz em_alex, 0.9x |
| **TTS Kokoro EN** | ~250ms | Voz af_heart |
| **TTS Kokoro JA** | ~3.5s | Voz jf_alpha, 0.9x, con misaki |
| **ASR Whisper small** | ~50ms | GPU, Silero VAD pre-filtro |
| **Traducción MarianMT** | ~100ms | GPU, Helsinki-NLP Opus-MT |
| **Pipeline completo** | ~300ms | ASR→Trans→TTS async |

### VRAM Usage
| Modo | VRAM | RAM |
|:-----|:----:|:---:|
| Teacher | ~4.0 GB | ~2.5 GB |
| Conversation | ~4.0 GB | ~2.5 GB |
| Translator | ~1.7 GB | ~1.2 GB |
| Grammar App | 0 GB (CPU) | ~200 MB |
| Reposo (menú) | 0 GB | ~300 MB |

---

## 🏗️ Arquitectura

```
┌─────────────── Alex Voice ───────────────┐
│                                            │
│  🎓 Teacher  💬 Conv  🌍 Translator  📝 Grammar │
│  (3000)       (3001)   (3003)        (3004)  │
│       │          │         │            │      │
│       └────┬─────┘         │            │      │
│            │               │            │      │
│      ┌─────┴─────┐    ┌───┴────┐       │      │
│      │  Ollama   │    │ MarianMT│       │      │
│      │ Qwen3.5-4B│    │ Opus-MT │       │      │
│      │ 64K ctx   │    │ ~100ms  │       │      │
│      └───────────┘    └────────┘       │      │
│            │               │            │      │
│      ┌─────┴───────────────┴────────┐   │      │
│      │       Kokoro ONNX TTS        │   │      │
│      │    (CPU, 0 VRAM, 5 idiomas) │   │      │
│      └──────────────────────────────┘   │      │
│            │                            │      │
│      ┌─────┴──────────────────────┐     │      │
│      │   Whisper ASR (GPU)        │     │      │
│      │   faster-whisper small     │     │      │
│      │   + Silero VAD (CPU)       │     │      │
│      └────────────────────────────┘     │      │
│                                          │      │
│      📝 Grammar App (Flask + SQLite) ────┘      │
│      8 tablas, SRS, XP, leaderboard              │
└──────────────────────────────────────────────────┘
```

---

## 📁 Estructura del Proyecto

```
ALEX_voice/
├── server.py, prompts.py         ← Teacher + Conversation backend
├── conv_server.py                ← Wrapper conversación
├── translator.py                 ← Traductor + pipeline async
├── menu_server.py                ← Launcher principal (port 5000)
├── alex_voice_app.sh             ← Entry point unificado
├── setup.sh / install.sh         ← Instalación
├── frontend/                     ← UIs (menu, index, conv, translator)
├── grammar_app/                  ← Proyecto 4 (Beta)
│   ├── backend/
│   │   ├── app.py                ← Flask API
│   │   └── database.py           ← SQLite schema + SRS
│   └── frontend/                 ← HTML/CSS/JS
├── grammar_app/data/             ← SQLite database
├── models/                       ← Modelos ONNX
├── tests/e2e/                    ← Tests E2E (35+ tests)
├── scripts/                      ← Instalación automática
├── plans/                        ← Planes de mejora
├── README.md, AGENT.md, PLAN.md  ← Documentación
└── .gitignore                    ← Archivos ignorados
```

---

## 🔬 Tests E2E

Ver `tests/e2e/` para los 4 test suites:
- `test_teacher.py` — 14 checks × 6 pares de idiomas
- `test_conversation.py` — 3 idiomas × escenarios + stress
- `test_translator.py` — 6 pares + TTS + edge cases
- `test_grammar.py` — 35 tests: auth, SRS, DB, frontend

Ejecutar:
```bash
bash tests/e2e/run_all.sh
```

---

## 📜 Licencia

MIT License — usa y modifica libremente.

Creado por [SCP-00](https://github.com/SCP-00) · Asistido por [Buffy](https://codebuff.com) (AI Agent)

---

*Alex Voice v3.3.1 — Junio 2026*
*"Aprende idiomas sin que nadie se entere. Todo local, todo privado."*
