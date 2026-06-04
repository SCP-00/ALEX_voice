# AGENT — Alex Voice (Plan Unificado)

## Role
Servidor principal para Teacher + Conversation modes.
LLM en GPU, TTS híbrido Kokoro/Piper en CPU, ASR en CPU.
Puerto 3000.

## Estado: ✅ COMPLETADO

### Arquitectura Actual (Junio 2026)

```
Usuario → Web UI (3000) → B/server.py → llama-server (GPU 8081)
                                    ↓
                              Kokoro-82M + Piper TTS (CPU)
                              faster-whisper ASR (CPU)
                              Caché LRU (50 entradas)
```

### Modos
- **🎓 Teacher** (temp 0.5) — Enseñanza multi-output con 【TEXT】/【PRONUNCIATION】/【TRANSLATION】/【EXPLANATION】/【EXERCISE】
- **💬 Conversation** (temp 0.7) — Charla natural, respeta el idioma del usuario
- ~~**🌍 Translator**~~ → Ahora es servidor independiente en puerto 3003

### Shared Module
`shared/translator.py` — Módulo compartido con prompts en INGLES (óptimo para Qwen2.5):
- TEACHER_PROMPT: Formato multi-output estructurado
- CONVERSATION_PROMPT: Responde en el mismo idioma del usuario
- TRANSLATOR_PROMPT: Traducción profesional (usado por translator_server.py)
- `parse_multi_output()`: Extrae TEXT/PRONUNCIATION/TRANSLATION/EXPLANATION/EXERCISE
- `get_tts_text()`: Extrae solo TEXT para TTS (ignora pronunciación y traducción)
- `build_llm_messages()`: Construye mensajes con idioma destino

### Translator Server (independiente)
`translator_server.py` (puerto 3003) — Servidor especializado:
- STT: faster-whisper (CPU)
- TRADUCCIÓN: argos-translate (CPU) EN/ES/JA
- TTS: Qwen3-TTS-CustomVoice (GPU, ~2GB VRAM)
- Selector manual FROM/TO + micrófono + auto-play

## Datos Clave
- **Puerto:** 3000
- **LLM:** Qwen2.5-1.5B-Q4_K_M (GPU, ~1.2 GB VRAM, ~20 tok/s)
- **TTS:** Kokoro-82M (CPU, primario) + Piper Python API (fallback)
- **ASR:** faster-whisper base (CPU, ~36ms)
- **Caché:** LRU 50 entradas
- **Frontend:** `frontend/plan-b/index.html`
- **Prompts:** Inglés (optimizado para Qwen2.5)
- **TTFT:** ~0.4s warm, ~2.3s cold (prompt caching activo)

## Benchmark Cross-Language (22 pruebas)
| Modo | Aciertos | Tiempo Promedio |
|:-----|:--------:|:---------------:|
| Teacher | 4/7 (mejorable) | 4.96s |
| Conversation | **5/5 (100%)** | 4.07s |
| Translator (LLM) | **10/10 (100%)** | 3.14s |

## Dependencias
```bash
pip install faster-whisper psutil pynvml numpy
# Kokoro-82M (TTS principal)
pip install kokoro
# argos-translate (traducción CPU)
pip install argostranslate
# Qwen3-TTS (audio calidad, servidor traductor)
pip install qwen-tts
```

## Notas
- Los prompts están en INGLÉS (no español) porque Qwen2.5 fue entrenado ~70% en inglés
- El módulo `shared/translator.py` es compartido entre B/server.py y translator_server.py
- Para modo traductor, NO se necesita el LLM — usa argos-translate en CPU
- Qwen3-TTS carga ~2GB en GPU bajo demanda y se puede descargar con /api/unload
- En RTX 4060 8GB cabe todo: LLM (~1.2GB) + Qwen3-TTS (~2GB) sobran ~4.8GB
