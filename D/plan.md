# Plan D — La Configuración Definitiva

## Objetivo
Unificar lo mejor de A, B y C en un solo plan optimizado para RTX 3050 6GB.
Máxima calidad de voz, mínimo uso de VRAM, máxima fluidez.

## Stack Final

```
start.bat
├── llama-server (Qwen3-2B-Q4_K_M, GPU, puerto 8081, 8K contexto)
│   └── --no-warmup → sin thinking tokens
└── python D/server.py (Monitor, CPU, puerto 3003)
    ├── /api/chat → llama-server /chat/completions (streaming)
    ├── /api/tts → Kokoro-82M + Piper (streaming)
    ├── /api/tts/clone → Qwen3-TTS voice cloning (experimental)
    ├── /api/asr → faster-whisper auto-switch
    ├── /api/stats → GPU/CPU/RAM/vram en vivo
    ├── /api/cache/* → LRU 200 + persistente
    └── /debug → Debug UI con 4 tabs
```

## Comparativa VRAM

| Componente | Plan A (Q8) | Plan B (Q8) | Plan C (Q8) | **Plan D (Q4_K_M)** |
|:-----------|:-----------:|:-----------:|:-----------:|:-------------------:|
| **LLM** | ~3.0 GB | ~3.0 GB | ~3.0 GB | **~1.5 GB** 🏆 |
| **KV Cache (4K)** | ~0.3 GB | ~0.3 GB | ~0.3 GB | **8K: ~0.5 GB** |
| **VRAM Libre** | ~2.0 GB | ~2.0 GB | ~2.0 GB | **~3.3 GB** 🏆 |

**3.3 GB de VRAM libre** permite:
- Ejecutar Qwen3-TTS en GPU si es necesario
- Mayor velocidad de prompt processing
- Múltiples slots en llama-server

## Benchmark Esperado

| Escenario | Latencia | Ganancia vs Plan A |
|:----------|:--------:|:------------------:|
| Chat streaming | ~200ms primer token | ✅ igual |
| TTS Kokoro (EN) | ~1.2s (3s audio, 2.5x) | 🆕 nuevo |
| TTS Kokoro (ES) | ~2.3s (2.3s audio, 1.0x) | 🆕 nuevo |
| TTS Piper (fallback) | **~45ms** | ✅ igual |
| TTS streaming | **~200-300ms** primer chunk | 🆕 nuevo |
| TTS Qwen3 cloning | ~3-5s (CPU, experimental) | 🆕 nuevo |
| ASR base (ES/EN) | **~36ms** | ✅ igual |
| Caché LRU hit | **0ms** | 🆕 nuevo |

## Mejoras por Modo

### 🎓 Modo Teacher (COMPLETAMENTE REDISEÑADO)
- Formato estructurado pero simple (el modelo 2B lo sigue mejor)
- 3 niveles: Principiante / Intermedio / Avanzado
- Ejercicios interactivos: "Traduce esta frase", "¿Qué significa X?"
- Sistema de progreso: el modelo recuerda lo que ya explicó

### 💬 Modo Conversación (MEJORADO)
- Memoria entre sesiones (caché persistente)
- Role-playing: "Actúa como un camarero en Madrid"
- Temas con contexto enriquecido
- Detección de despedida con cierre natural

### 🌍 Modo Traductor (COMPLETAMENTE REDISEÑADO)
- Few-shot examples en el system prompt
- Manejo de modismos y expresiones culturales
- Tono ajustable: formal / casual / neutro
- Preservación de formato (listas, código, poemas)

### 🎙️ Voice Cloning (NUEVO - Experimental)
- Qwen3-TTS con 3s de audio de referencia
- Clonar voces para personajes específicos
- Persistencia de voz clonada entre sesiones

## Hardware

| Recurso | Total | Usado por D | Libre |
|:--------|:-----:|:-----------:|:-----:|
| GPU VRAM | 5.28 GB | ~2.3 GB | **~3.0 GB** 🏆 |
| RAM | 16.5 GB | ~1.5 GB | ~5.5 GB |
| CPU | i5-13420H 8C/12T | — | — |

## Roadmap de Implementación

### Fase 1 ✅ — Núcleo (ESTA IMPLEMENTACIÓN)
- [x] D/server.py (puerto 3003)
- [x] Kokoro-82M + Piper streaming
- [x] Caché LRU 200 entradas
- [x] EchoGuard anti-loop
- [x] Debug UI
- [x] System prompts mejorados con few-shot
- [x] frontend/plan-d con todos los modos
- [x] D/start.bat con launcher unificado

### Fase 2 🚧 — Optimizaciones
- [ ] Caché persistente a disco (SQLite)
- [ ] Prompt caching en servidor
- [ ] Modo oscuro / claro en frontend

### Fase 3 🚧 — Voice Cloning
- [ ] Integración Qwen3-TTS
- [ ] UI para subir audio de referencia
- [ ] Persistencia de voces clonadas

### Fase 4 🚧 — Feature Completa
- [ ] VAD adaptativo con medidor visual
- [ ] Whisper ASR en GPU (VRAM libre permite)
- [ ] Streaming dual (chat + TTS simultáneo)
