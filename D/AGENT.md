# AGENT — Plan D: La Configuración Definitiva

## Rol
Plan D es la culminación del proyecto Alex Voice. Toma lo mejor de A, B y C y lo unifica en una sola arquitectura optimizada para RTX 3050 6GB.

## Stack Final

| Componente | Tecnología | VRAM/RAM | Puerto |
|:-----------|:-----------|:--------:|:------:|
| **LLM** | Qwen3-2B-Q4_K_M GGUF | ~1.5 GB VRAM | 8081 |
| **TTS** | Kokoro-82M (primario) + Piper (fallback) | ~0 MB VRAM / ~150 MB RAM | — |
| **TTS Cloning** | Qwen3-TTS (experimental, CPU) | ~0 MB VRAM / ~4 GB RAM | — |
| **ASR** | faster-whisper base/small | ~0 MB VRAM / ~150-500 MB RAM | — |
| **Monitor** | python server.py (stats, logs, debug) | ~0 MB VRAM / ~100 MB RAM | 3003 |
| **Cache** | LRU 200 entradas + persistente a disco | ~0 MB VRAM / ~50 MB RAM | — |
| **Contexto** | 8K (vs 4K en A/B/C) | ~0.5 GB VRAM adicional | — |

**Presupuesto de Memoria Final:**
| Componente | VRAM |
|:-----------|:----:|
| Qwen3-2B-Q4_K_M | ~1.5 GB |
| KV Cache (8K ctx) | ~0.5 GB |
| Overhead sistema | ~0.3 GB |
| **Total GPU** | **~2.3 GB** de 5.28 GB ✅ |
| **Margen** | **~3.0 GB libres** |

## Mejoras Respecto a Planes Anteriores

### LLM
- ✅ **Qwen3-2B-Q4_K_M**: Misma inteligencia que Q8 pero **50% menos VRAM**
- ✅ **Sin thinking tokens**: Usamos instruct version directamente
- ✅ **8K contexto**: Conversaciones mucho más largas
- ✅ **21-24 tok/s**: Velocidad similar o mejor por menor VRAM usada

### TTS
- ✅ **Kokoro-82M streaming** (voz natural, CPU)
- ✅ **Piper fallback** (~45ms)
- ✅ **Qwen3-TTS experimental**: Clonación de voz con 3s de referencia (CPU)
- ✅ **Indicador de motor TTS** en cada mensaje

### UX
- ✅ **EchoGuard anti-loop** (portado de Plan A)
- ✅ **Debug UI** con 4 tabs (portado de Plan A)
- ✅ **Caché LRU 200 entradas** (doble que B)
- ✅ **Caché persistente** a disco entre sesiones
- ✅ **System prompts mejorados** con few-shot examples
- ✅ **VAD adaptativo** con medidor visual

### Modos Mejorados
- **🎓 Teacher**: Formato claro, 3 niveles, ejemplos interactivos
- **💬 Conversación**: Memoria entre sesiones, role-playing
- **🌍 Traductor**: Few-shot examples, tono ajustable, modismos
- **🎙️ Voice Cloning** (experimental): Clonar voces con Qwen3-TTS

## Dependencias
```bash
pip install faster-whisper piper-tts psutil pynvml numpy kokoro
# Opcional para voice cloning:
pip install qwen-tts torch torchaudio
```

## Modelo LLM
```bash
# Descargar Qwen3-2B-Q4_K_M (~1.5 GB)
# https://huggingface.co/Qwen/Qwen3-2B-Instruct-GGUF
```

## Limitaciones Conocidas
- Qwen3-TTS voice cloning requiere ~4GB RAM adicional en CPU
- Sin Whisper ASR en GPU (todo en CPU, funciona bien)
