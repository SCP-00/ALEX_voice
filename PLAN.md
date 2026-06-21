# 📋 Alex Voice — Plan de Mejora v3

> Última actualización: Junio 2026

---

## ✅ v3 Completado — Unified Launcher + Ollama API + prometheus-orchestrator

### 🏗️ Migración a Ollama API (v3.1)
- ✅ **LLM Backend:** llama-server directo (GGUF) → **Ollama API** (`http://localhost:11434/v1`)
- ✅ **Modelo:** Qwen2.5-coder:3b → **prometheus-orchestrator** (Qwen3.5 4B Instruct, 262K ctx)
- ✅ **Thinking:** Desactivado (`reasoning_format: none`) → respuestas directas sin delay
- ✅ **Cleanup VRAM:** `kill_all()` ahora libera modelo via `POST /api/generate` con `keep_alive: "0m"`
- ✅ **menu_server.py:** Eliminadas funciones legacy (`find_llama`, `find_model`, `start_llama`, `wait_for_llama`, `check_llama_alive`)
- ✅ **server.py:** `LLAMA_HOST` default → `localhost:11434/v1`, agregado `model` + `reasoning_format` a todos los `chat_data`
- ✅ **conv_server.py:** Env vars `OLLAMA_LLAMA_MODEL` + `LLAMA_HOST` para Ollama
- ✅ **alex-voice.sh:** Verifica Ollama en puerto 11434, cleanup via API

### Launcher Unificado
- ✅ `alex-voice.sh` — Punto de entrada único, menú web, cleanup automático
- ✅ Solo UNO activo a la vez (Teacher, Conversation, Translator)
- ✅ Home button para cambiar de modo (offload + reload)

### Modelo LLM Seleccionado (v3.1)
| Modelo | Backend | VRAM | Contexto | Thinking | Velocidad |
|--------|:------:|:----:|:--------:|:--------:|:---------:|
| **prometheus-orchestrator** 🏆 | Ollama API | ~3.0 GB | 262K | ❌ Desactivado | **~43 tok/s** |
| (Qwen3.5 4B Instruct, IQ4_XS, 4.3B params) | | | | | |

### Async Translation Pipeline (v3)
- ✅ `TranslationPipeline` — Queue-based workers: ASR→Translation→TTS
- ✅ While TTS plays sentence N, GPU transcribes sentence N+1
- ✅ `ThreadingHTTPServer` — Non-blocking request handling
- ✅ `/api/pipeline` — Full async pipeline endpoint with timing breakdown
- ✅ 5 pares de idiomas: EN↔ES, EN→JA, JA→EN, JA→ES (pivot automático)

### TTS Sanitization (v2.1)
- ✅ `_sanitize_tts_text()` — Elimina thinking tags, emojis, descripciones de emojis
- ✅ Prompts prohíben emojis explícitamente
- ✅ Pipeline: thinking→emojis→emoji words→CJK→normalize spaces

### Frontend Rediseñado
- ✅ `menu.html` — Glassmorphism dark mode, cards con glow por modo
- ✅ `index.html` — Card-based Teacher, voice wave animation, responsive
- ✅ `conv.html` — Voice visualizer, chat bubbles, 128K context
- ✅ `translator.html` — Split-view, language selectors, audio playback

---

## 📊 Métricas v3.1

### VRAM Budget
| Modo | Componentes | VRAM |
|:-----|:------------|:----:|
| Teacher | Ollama (~3.0GB) + Whisper small (GPU) | **~4.5 GB** |
| Conversation | Ollama (~3.0GB) + Whisper small (GPU) | **~4.5 GB** |
| Translator | Whisper small (GPU) + MarianMT (GPU) | **~1.7 GB** |

### Benchmarks — prometheus-orchestrator (Qwen3.5 4B Instruct)

| Idioma | Velocidad | Calidad | VS coder:3b |
|:-------|:---------:|:-------:|:-----------:|
| **EN** | **39.0 tok/s** | ✅ Excelente | +2.6x |
| **ES** | **45.4 tok/s** | ✅ Español natural | 🔥 Antes alucinaba |
| **JA** | **45.2 tok/s** | ✅ Japonés correcto | 🔥 Antes se presentaba |
| **Promedio** | **~43 tok/s** | — | **3x más rápido** |

### Pipeline Latency (Async)
| Stage | Latency | Hardware |
|:------|:-------:|:---------|
| ASR (Whisper small) | ~50ms | GPU |
| Translation (MarianMT) | ~100ms | GPU |
| TTS (Kokoro ONNX) | ~150ms | CPU |
| **Total (parallel)** | **~300ms** | GPU+CPU |

### Translation Models
| Par | Latencia | Método |
|:----|:--------:|:-------|
| EN→ES | ~100ms | Direct |
| ES→EN | ~100ms | Direct |
| EN→JA | ~180ms | Direct |
| JA→EN | ~100ms | Direct |
| JA→ES | ~200ms | Pivot EN |

---

## 🔜 Pendiente (v3.2)

### Prioridad Alta
- [ ] **Streaming pipeline** — WebSocket/SSE para audio chunk-by-chunk en vez de esperar resultado completo
- [ ] **Fix translator.html stale refs** — CT2→MarianMT, qwen3_loaded→transformers_loaded

### Prioridad Media
- [ ] **Grammar exercises interactivos** — Ejercicios en Teacher mode con feedback
- [ ] **Progress tracking** — Historial de aprendizaje del usuario
- [ ] **Multi-speaker Conversation** — Voces diferentes para usuario vs asistente

### Prioridad Baja
- [ ] **Tests unitarios** — translator.py pipeline, prompts.py parsing, server.py TTS
- [ ] **CI/CD** — GitHub Actions para lint + test
- [ ] **Mobile optimization** — Voice visualizer para bajo consumo

---

## 📐 Decisiones de Diseño v3

### ¿Por qué solo UNO activo a la vez?
- RTX 3050 6GB: Teacher/Conversation usan ~4.5GB, Translator ~1.7GB
- Dos modos simultáneos = ~6.2GB — no cabe en VRAM
- Un solo modo = VRAM completa disponible = máxima fluidez

### ¿Por qué async pipeline?
- Secuencial: ASR(50ms) + Trans(100ms) + TTS(150ms) = **300ms por oración**
- Async: TTS de oración N + ASR de oración N+1 = **~150ms percepción**
- El usuario escucha respuesta casi inmediata mientras el GPU procesa el siguiente chunk

### ¿Por qué Ollama API en vez de llama-server directo?
- Ollama gestiona automáticamente carga/descarga de modelos en VRAM
- `keep_alive: "0m"` libera VRAM inmediatamente al cambiar de modo
- OpenAI-compatible API → mismo código que para APIs cloud
- No más binarios de llama-server compilados sin CUDA
- Thinking mode desactivado evita timeouts en JA

### ¿Por qué prometheus-orchestrator (Qwen3.5 4B Instruct) sobre Qwen2.5-3B/4B?
- **Instruct** (no coder) entiende y genera texto correctamente en 3 idiomas
- Qwen3.5 es #1 en multilingüe (100+ idiomas soportados)
- 4.3B params cabe en ~3GB VRAM con margen para Whisper
- 262K contexto = conversaciones mucho más largas que 32K
- 43 tok/s promedio = 3x más rápido que coder:3b

---

## 📈 Roadmap

### v3.2 (Julio 2026)
- [ ] Streaming pipeline con WebSocket
- [ ] Grammar exercises interactivos
- [ ] Tests unitarios

### v4 (Q4 2026)
- [ ] MCP integration — Servidor MCP para otros agentes
- [ ] Voice cloning — Clonar voz del usuario
- [ ] Cloud sync — Sincronizar progreso entre dispositivos

---

*Plan actualizado: Junio 2026*
*Proyecto: ALEX_voice v3.1*
*Autor: SCP-076 (Victor Buendia) + Buffy (AI Agent)*
