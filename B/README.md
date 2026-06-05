# Servidor Principal - Teacher + Conversation

> Estado: Parcialmente completado, con arranque y prompts corregidos el 2026-06-05.
> Puerto por defecto: `3000`.

## Arquitectura

```text
Usuario -> frontend/plan-b -> B/server.py -> llama-server (8081)
                                  |
                                  +-> Kokoro-82M TTS (CPU)
                                  +-> Piper TTS fallback (CPU)
                                  +-> faster-whisper ASR (CPU)
                                  +-> Cache LRU
```

## Componentes

| Componente | Tecnologia | Estado |
|:--|:--|:--|
| LLM | llama-server + Qwen GGUF | Requerido para chat |
| UI | `frontend/plan-b/index.html` | Funcional; pendiente rediseño |
| TTS | Kokoro -> Piper Python -> Piper subprocess | Implementado |
| ASR | faster-whisper base/small | Implementado |
| Cache | LRU 50 entradas | Implementado |

## Cambios importantes

- `launcher.py` ahora encuentra `llama-server.exe` en `llama-server-bin/`, `llama.cpp/`, `LLAMA_EXE`, `LLAMA_DIR` o ruta legacy de Documents.
- `launcher.py` ahora encuentra el modelo local `models/qwen2.5-1.5b-q4_k_m.gguf`.
- Se corrigio el bug que dejaba `args` de `llama-server` sin definir.
- `B/server.py` vuelve a insertar el system prompt cuando la UI envia `messages`.
- La UI ya no muestra "Plan B" como marca principal y se corrigio un bug CSS del layout.

## Ejecucion recomendada

Desde la raiz del proyecto:

```bat
setup.bat
run.bat
```

O directo:

```bat
python launcher.py
```

URL:

```text
http://localhost:3000
```

## Endpoints

| Endpoint | Metodo | Descripcion |
|:--|:--:|:--|
| `/api/chat` | POST | Proxy a llama-server con prompt por modo y cache |
| `/api/tts` | POST | TTS no streaming |
| `/api/tts/stream` | POST | TTS streaming |
| `/api/asr` | POST | ASR con faster-whisper |
| `/api/stats` | GET | CPU/RAM/GPU/llama stats |
| `/api/cache/stats` | GET | Estadisticas de cache |
| `/api/cache/clear` | GET | Limpia cache |

## Cambios recientes

* [2026-06-05] Modo Translator removido de la UI 3000 — ahora solo en puerto 3003.
* [2026-06-05] Tests actualizados de Plan A a Plan B endpoints (`/api/chat`, `/api/tts`, `/api/asr`).
* [2026-06-05] Lanzadores legacy eliminados: `start_server.bat`, `B/start.bat`, `B/start_plan_b.bat`, `_start_teacher.bat`.
* [2026-06-05] Ahora `run.bat` y `launcher.py` son las únicas entradas recomendadas.
