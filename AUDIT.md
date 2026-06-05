# Auditoria tecnica - Alex Voice

Fecha: 2026-06-05

## Resumen

El proyecto tiene dos superficies principales:

| Servicio | Puerto | Archivo | Estado observado |
|:--|:--:|:--|:--|
| Teacher + Conversation | `3000` | `B/server.py` via `launcher.py` | Tenia fallos claros de arranque y prompt; corregido |
| Traductor | `3003` | `translator_server.py` | Funcional; ASR en espanol mejorado |
| llama-server | `8081` | `llama-server.exe` | Backend requerido por el puerto 3000 |

## Cambios aplicados

- `launcher.py`
  - Corregido el bug que dejaba `args` de `llama-server` sin definir cuando el modelo existia.
  - Ahora busca `llama-server.exe` donde lo deja `setup.bat`: `llama-server-bin/`.
  - Tambien acepta `LLAMA_EXE`, `LLAMA_DIR`, `llama.cpp/` y la ruta legacy de `Documents`.
  - Ahora busca el modelo local `models/qwen2.5-1.5b-q4_k_m.gguf`, que es el que descarga `setup.bat`.
  - El puerto se pasa correctamente al servidor por `PLAN_B_PORT`.

- `B/server.py`
  - La UI 3000 enviaba `messages`, pero el servidor no insertaba el system prompt de Teacher/Conversation. Corregido.
  - Esto deberia estabilizar el modo Teacher y Conversation porque el LLM vuelve a recibir las reglas del modo.

- `translator_server.py`
  - Para ASR en `es` y `ja`, usa `small` en vez de `base` cuando el idioma viene seleccionado.
  - Whisper usa `beam_size=5` y `condition_on_previous_text=False` para reducir transcripciones inventadas.
  - La respuesta ASR usa el idioma detectado por Whisper cuando esta disponible.

- `frontend/translator/index.html`
  - El mic ahora manda al backend el idioma seleccionado en `Desde`.
  - El modo conversacion tambien pasa el idioma real del turno.
  - El resampleo WebM -> WAV cambio de salto de muestras a promedio por ventana, que conserva mejor la voz.

- `frontend/plan-b/index.html`
  - Corregido CSS invalido: `flex-direction:min-width:0`.
  - Quitadas etiquetas visibles de "Plan B" en la interfaz principal.
  - Aplicado el mismo resampleo de audio mas estable para ASR.

- `setup.bat`
  - Reescrito como setup idempotente.
  - Comprueba modulos antes de instalar.
  - Usa `python -m pip`.
  - Descarga `llama-server` y el modelo Qwen local en rutas compatibles con `launcher.py`.
  - `flash-attn` ya no se compila por defecto; se intenta solo con `ALEX_INSTALL_FLASH_ATTN=1`.

- `.gitignore`
  - Ignora artefactos locales: `tmp/`, ZIPs, `llama.cpp/`, `llama-server-bin/`, modelos `.gguf/.bin`, runtime extra de Piper y `nul`.

## Por que se caia o no arrancaba localhost:3000

1. `launcher.py` construia los argumentos de `llama-server` dentro del bloque `if not model_path.exists()`, justo despues de un `return False`. Cuando el modelo si existia, `args` nunca se asignaba.
2. `setup.bat` descargaba `llama-server` en `llama-server-bin/`, pero `launcher.py` lo buscaba en `C:\Users\andyh\Documents\...`.
3. `setup.bat` descargaba el GGUF en `models/`, pero `launcher.py` solo buscaba modelos en LM Studio.
4. `start_plan_server()` preparaba variables de entorno, pero no se las pasaba a `subprocess.Popen`.
5. La UI 3000 mandaba `messages`, y esa rama no anadia el system prompt del modo.

## ASR en espanol

El problema mas probable no era solo Whisper, sino la combinacion de:

- idioma enviado como `auto` aunque el usuario habla espanol;
- modelo `base` para frases cortas/ruidosas;
- resampleo del navegador a 16 kHz por salto de muestras.

Acciones tomadas:

- seleccionar `Desde: Espanol` ahora fuerza `lang: es` en `/api/asr`;
- para `es`, el backend usa `small`;
- el WAV generado por el navegador conserva mejor la senal.

Coste esperado: la primera transcripcion en espanol puede tardar mas porque descarga/carga `small`. Despues queda cacheado en memoria.

## Sobre los `.bat`

Recomendacion actual (verificado 2026-06-05):

| Archivo | Necesario | Comentario |
|:--|:--:|:--|
| `setup.bat` | ✅ Si | Instalacion/verificacion inicial |
| `run.bat` | ✅ Si | Entrada principal para usuario |
| `start_server.bat` | ~~No~~ ❌ | **ELIMINADO** — era legacy de Plan A |
| `B/start.bat` | ~~Opcional~~ ❌ | **ELIMINADO** — duplicaba `run.bat` |
| `B/start_plan_b.bat` | ~~Opcional~~ ❌ | **ELIMINADO** — duplicaba `B/start.bat` |
| `_start_teacher.bat` | ~~No~~ ❌ | **ELIMINADO** — arrancaba sin llama-server |

Se eliminaron los 4 lanzadores legacy. `setup.bat` y `run.bat` son las únicas entradas.

## Opinion de UI

El traductor de `localhost:3003` funciona mejor visualmente porque es una pantalla enfocada: selector de idiomas, input, resultado y audio. La UI de `localhost:3000` se sentia peor por tres razones:

- exponia nombres internos como "Plan B";
- mezclaba Teacher, Conversation y Translator aunque Translator ya tiene app propia en 3003;
- tenia un bug CSS que podia romper el layout principal.

Primer ajuste aplicado: limpieza de etiquetas internas y correccion de layout. Siguiente mejora recomendada: dejar 3000 solo para Teacher/Conversation, con dos tabs claras, y mover stats/cache a un panel secundario menos dominante.

## GitHub

Estado verificado:

- Remoto local: `https://github.com/SCP-00/ALEX_voice.git`.
- `git ls-remote` responde correctamente.
- El conector GitHub de Codex puede acceder a `SCP-00/ALEX_voice`.
- Permisos reportados por el conector: `admin`, `maintain`, `pull`, `push`, `triage`.
- `gh` CLI no esta instalado o no esta en `PATH`.
- No encontre token en variables de entorno ni archivos `.env`/token visibles del proyecto. No se debe guardar un token clasico dentro del repo.

## Pendientes (actualizado 2026-06-05)

| # | Pendiente | Estado |
|:-:|:----------|:------:|
| 1 | Probar `run.bat` opcion 2 y confirmar `http://localhost:3000/api/stats` | ⏳ Manual |
| 2 | Probar traductor con `Desde: Espanol` y grabar 3 frases cortas | ⏳ Manual |
| 3 | Redisenar UI 3000 como Teacher/Conversation, sin Translator | ✅ Hecho (modo Translator removido) |
| 4 | Convertir tests de Plan A a endpoints actuales | ✅ Hecho (`test_alex_voice.sh` con endpoints `/api/chat`, `/api/tts`, `/api/cache/stats`) |
| 5 | Eliminar lanzadores legacy | ✅ Hecho (4 archivos `.bat` eliminados) |
