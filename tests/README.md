# Alex Voice — Tests del Plan B

## 📋 Cobertura de Tests

| # | Test | Tipo | Automático | Descripción |
|:-:|:-----|:----:|:----------:|:------------|
| 1 | Servidores activos | ✅ | Sí | Verifica que B/server.py (3000) y llama-server (8081) respondan |
| 2 | API /api/stats | ✅ | Sí | VRAM, RAM, GPU, CPU, temperatura, tokens/s |
| 3 | API /api/cache/stats | ✅ | Sí | Estadísticas de caché LRU |
| 4 | TTS Español | ✅ | Sí | Kokoro-82M genera WAV para español |
| 5 | TTS Inglés | ✅ | Sí | Kokoro-82M genera WAV para inglés |
| 6 | Modo Teacher | ✅ | Sí* | Prompt educativo multi-output con 【TEXT】/【PRONUNCIATION】/【TRANSLATION】 |
| 7 | Modo Conversación | ✅ | Sí* | Charla natural respetando el idioma del usuario |

*Tests con LLM se saltan con `--quick`

## 🚀 Cómo Ejecutar

```bash
# 1. Asegúrate de que los servidores estén corriendo
python launcher.py                # Teacher+Conversation (puerto 3000)
# llama-server se inicia automáticamente desde launcher.py

# 2. Ejecuta los tests
bash tests/test_alex_voice.sh              # Todos los tests (incluye LLM)
bash tests/test_alex_voice.sh --quick      # Solo tests rápidos (sin LLM)
bash tests/test_alex_voice.sh --verbose    # Output detallado
```

## 🎯 Pruebas Subjetivas (Manuales)

Además de los tests automáticos, verifica manualmente:

### Calidad de Voz
- **Español**: Kokoro-82M debe sonar natural y clara (fallback: Piper)
- **Inglés**: Kokoro-82M con voz inglesa, sin acento español

### Modos
1. **🎓 Teacher**: Pide una explicación → debe responder con formato estructurado
2. **💬 Conversación**: Conversación natural → debe ser fluido y contextual

### Traductor (servidor independiente, puerto 3003)
3. **🌍 Traductor**: Abre `http://localhost:3003` para traducción con Qwen3-TTS + argos

### Rendimiento
- TTS debe generar en <3 segundos para textos normales (Kokoro carga ~30s la primera vez)
- Tokens/s debe mostrar valores no-cero durante generación
- VRAM debe reflejar el uso real del modelo Qwen (+ Kokoro lazy-load)

## 📊 APIs

### Teacher+Conversation (`localhost:3000`)
| Endpoint | Método | Descripción |
|:---------|:------:|:------------|
| `/api/chat` | POST | Chat con modo (teacher/conversation) + multi-output |
| `/api/tts` | POST | TTS Kokoro → Piper (fallback) |
| `/api/tts/stream` | POST | TTS streaming |
| `/api/asr` | POST | Reconocimiento de voz |
| `/api/stats` | GET | Estadísticas en vivo (GPU/CPU/RAM) |
| `/api/cache/stats` | GET | Estadísticas de caché LRU |
| `/api/cache/clear` | GET | Limpiar caché |

### Traductor (`localhost:3003`)
| Endpoint | Método | Descripción |
|:---------|:------:|:------------|
| `/api/translate` | POST | Traducir texto (from_lang, to_lang, text) |
| `/api/tts` | POST | Audio Qwen3-TTS |
| `/api/asr` | POST | Reconocimiento de voz |
| `/api/load` | POST | Precargar Qwen3-TTS en GPU |
| `/api/unload` | POST | Descargar Qwen3-TTS de GPU |
| `/api/status` | GET | Estado del servidor |

## 📁 Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    ALEX VOICE                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐    ┌──────────────────────────┐    │
│  │  Teacher + Conv     │    │  Translator               │    │
│  │  (puerto 3000)      │    │  (puerto 3003)            │    │
│  │                     │    │                          │    │
│  │  LLM: Qwen2.5-1.5B │    │  STT: faster-whisper CPU  │    │
│  │  TTS: Kokoro/Piper  │    │  TRANS: argos CPU        │    │
│  │  ASR: faster-whisper│    │  TTS: Qwen3-TTS GPU      │    │
│  │  Caché: LRU 50      │    │  SIN LLM                 │    │
│  └─────────────────────┘    └──────────────────────────┘    │
│                                                             │
│  ┌──────────────────────────────────────────────────┐       │
│  │  llama-server (GPU, puerto 8081)                  │       │
│  │  Qwen2.5-1.5B-Q4_K_M ~1.2GB VRAM                  │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```
