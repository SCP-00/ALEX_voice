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

## ✅ v3.2 Completado — Streaming SSE + Stale Ref Fixes + Tests

### 📡 Streaming SSE para Chat LLM
- ✅ **SSE Streaming** en Teacher (index.html) y Conversation (conv.html)
- ✅ Tokens aparecen en tiempo real via `ReadableStream` reader
- ✅ Teacher mode: `parseMultiOutput()` client-side + `renderTeacherCards()` para cards estructuradas post-stream
- ✅ Conversation voice flow: streaming también activo en `toggleMic()`
- ✅ Fallback automático a full JSON para respuestas cacheadas
- ✅ Botones Hablar/Copiar + timestamp al completar stream

### 🧹 Stale Refs Fixes
- ✅ **menu.html**: Qwen2.5-3B → Qwen3.5-4B, Llama-3.2-3B → Qwen3.5-4B, 128K→262K ctx
- ✅ **Desktop file**: ownership root→buendia001
- ✅ **test_alex_voice.sh**: URLs actualizadas (8081→11434/v1), llama-server→Ollama, python→python3

### 📊 Tests Actualizados
- ✅ URLs y comandos para Ollama API
- ✅ Coverage table refleja arquitectura v3.1

### 🔧 Optimizaciones
- ✅ Menos código duplicado: `addMsg()` simplificado, `renderTeacherCards()` reutilizable
- ✅ Status/pulse states correctos en todos los flujos

---

## 📊 Métricas v3.2

### VRAM Budget (sin cambios)
| Modo | Componentes | VRAM |
|:-----|:------------|:----:|
| Teacher | Ollama (~3.0GB) + Whisper small (GPU) | **~4.5 GB** |
| Conversation | Ollama (~3.0GB) + Whisper small (GPU) | **~4.5 GB** |
| Translator | Whisper small (GPU) + MarianMT (GPU) | **~1.7 GB** |

### UX Improvements (v3.2)
| Feature | Antes | Ahora |
|:--------|:------|:------|
| Respuesta LLM | Esperar texto completo | **Streaming en vivo token por token** |
| Teacher cards | Solo con full JSON | **Cards post-streaming** |
| Voice flow conv | Esperar texto completo | **Streaming en vivo** |
| Status voice conv | Podía quedarse "Generando..." | **✅ Listo siempre** |

## 🔜 Pendiente (v3.3)

### Prioridad Alta
- [ ] **Grammar exercises interactivos** — Ejercicios en Teacher mode con feedback
- [ ] **Progress tracking** — Historial de aprendizaje del usuario

### Prioridad Media
- [ ] **Multi-speaker Conversation** — Voces diferentes para usuario vs asistente
- [ ] **Mobile optimization** — Voice visualizer para bajo consumo

### Prioridad Baja
- [ ] **CI/CD** — GitHub Actions para lint + test
- [ ] **Grammar exercises** (continuación)

---

## 📐 Decisiones de Diseño v3.2

### ¿Por qué SSE streaming y no WebSocket?
- SSE es más simple: usa HTTP normal, no necesita protocolo especial
- `ReadableStream` reader funciona directamente con fetch API
- El servidor ya soportaba SSE (`stream: true`), solo faltaba el frontend
- WebSocket añadiría complejidad sin beneficio claro para chat de texto

### ¿Por qué parser client-side para Teacher cards?
- El servidor devuelve `parsed` solo en modo non-streaming
- Con streaming, los tokens llegan sin estructura
- Un parser JS simple (`【TAG】content`) funciona en milisegundos
- Evita tener que esperar el response completo para ver cards

### ¿Por qué streaming también en voice flow?
- Consistencia: misma UX para texto escrito y voz
- El usuario ve la respuesta aparecer mientras habla
- TTS puede empezar antes si se implementa chunked playback

---

## 📈 Roadmap

### v3.3 (Julio 2026)
- [ ] Grammar exercises interactivos
- [ ] Progress tracking
- [ ] Multi-speaker TTS

### v4 (Q4 2026)
- [ ] MCP integration — Servidor MCP para otros agentes
- [ ] Voice cloning — Clonar voz del usuario
- [ ] Cloud sync — Sincronizar progreso entre dispositivos

---

*Plan actualizado: Junio 2026*
*Proyecto: ALEX_voice v3.2*
*Autor: SCP-076 (Victor Buendia) + Buffy (AI Agent)*
