# Plan — Alex Voice (Unificado)

## Objetivo
Asistente de voz local con 3 modos especializados:
- **Teacher + Conversation**: Servidor principal con LLM en GPU (puerto 3000)
- **Translator**: Servidor independiente SIN LLM (puerto 3003)

## Estado Actual

### Servidor Principal (B/server.py, puerto 3000)

| Componente | Tecnología | Detalle |
|:-----------|:-----------|:--------|
| **LLM** | Qwen2.5-1.5B-Q4_K_M (GPU) | ~1.2 GB VRAM, ~20 tok/s |
| **TTS** | Kokoro-82M (CPU) + Piper (fallback) | Streaming ~100-300ms |
| **ASR** | faster-whisper base (CPU) | ~36ms |
| **Caché** | LRU 50 entradas thread-safe | Hit: 0ms |
| **Prompts** | Inglés (shared/translator.py) | Optimizado para Qwen2.5 |

### Servidor Traductor (translator_server.py, puerto 3003)

| Componente | Tecnología | Detalle |
|:-----------|:-----------|:--------|
| **STT** | faster-whisper base (CPU) | ~36ms |
| **TRANS** | argos-translate (CPU) | 0.5-2.3s EN/ES/JA |
| **TTS** | Qwen3-TTS-CustomVoice (GPU) | ~2GB VRAM, voces pre-definidas |

### VRAM Budget (RTX 3050 6GB)

| Modo | Componentes | VRAM |
|:-----|:------------|:----:|
| Teacher/Conversation | Qwen2.5-1.5B + Kokoro (CPU) | **~1.2 GB** ✅ |
| Translator | Qwen3-TTS-0.6B + argos (CPU) | **~2 GB** ✅ |
| Ambos simultáneos | — | No recomendado |

## Cross-Language (Benchmark 22 pruebas)

| Modo | Resultado | Detalle |
|:-----|:---------:|:--------|
| **Conversation** | **5/5 (100%)** | EN, ES, JA, FR — respeta idioma del usuario |
| **Translator** | **10/10 (100%)** | EN-ES, ES-EN, EN-JA, JA-EN, EN-FR, FR-EN, ES-FR, FR-ES, JA-ES, ES-JA |
| **Teacher** | 4/7 (57%) | Fallos: modelo a veces explica en inglés en vez de idioma objetivo |

## TTFT Benchmark

| Escenario | Cold (1ra vez) | Warm (2da vez) |
|:----------|:--------------:|:--------------:|
| Prompt corto (30+20 tok) | 0.38s | **0.26s** |
| Persona (200+40 tok) | 1.38s | **0.41s** |
| Teacher (~400+80 tok) | 2.27s | **0.43s** |

## Hardware Requerido

| Componente | Mínimo | Recomendado |
|:-----------|:------:|:-----------:|
| **GPU** | NVIDIA 4GB VRAM | RTX 3050 6GB / RTX 4060 8GB |
| **RAM** | 8 GB | 16 GB |
| **Disco** | 10 GB | 20 GB (modelos) |
| **SO** | Windows 10/11 | Windows 11 |
| **CUDA** | 12.4+ | Driver 610+ |

## Archivos del Proyecto

```
Alex_Voice/
├── B/server.py              ← Servidor principal (Teacher+Conversation)
├── translator_server.py      ← Servidor traductor independiente
├── shared/translator.py      ← Módulo compartido (prompts en inglés, parsing)
├── frontend/
│   ├── plan-b/index.html     ← UI de Teacher+Conversation
│   └── translator/index.html ← UI del Traductor
├── launcher.py               ← Lanzador unificado
├── setup.bat                 ← Instalación automática
├── run.bat                   ← Inicio rápido
├── CREDITS.md                ← Créditos
└── LICENSE                   ← MIT
```
