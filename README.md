# 🎙️ Alex Voice — Asistente Local con IA Multilingüe

Asistente de voz con inteligencia artificial que corre **100% local** en tu PC.
Soporta **Español, Inglés y Japonés** con 3 modos de interacción:
🎓 Teacher (enseñanza), 💬 Conversación (charla libre), 🌍 Traductor (ES/EN/JA).

## 🚀 Inicio Rápido

```bash
# 1. Clonar el repositorio
git clone https://github.com/SCP-00/Alex_Voice.git
cd Alex_Voice

# 2. Descargar los modelos necesarios (ver sección Modelos)
# 3. Iniciar el servidor
./start_server.sh        # Git Bash
start_server.bat         # Windows (doble clic)

# 4. Abrir el navegador en frontend/plan-a/index.html
```

## 📦 Modelos — Descargar Manualmente

No se incluyen modelos en el repositorio por su tamaño.
Debes descargarlos y colocarlos en las rutas indicadas.

### 🤖 LLM (Requerido)
**Recomendado:** `Qwen3.5-2B-Q8` (~2 GB)

```
URL: https://huggingface.co/khazarai/Qwen3.5-2B-Qwen3.6-plus-Distilled-GGUF
Archivo: Qwen3.5-2B-Qwen3.6-plus-Distilled-q8_0.gguf
Meter en: C:\Users\<tu_usuario>\.lmstudio\models\khazarai\Qwen3.5-2B-Qwen3.6-plus-Distilled-GGUF\
```

**Alternativas probadas:**
| Modelo | Tamaño | Velocidad | VRAM |
|--------|:------:|:---------:|:----:|
| Qwen3.5-2B-Q8 | ~2.0 GB | **21-22 tok/s** | ~3.0 GB |
| Gemma-4-E2B-Q4 | ~3.2 GB | **24.3 tok/s** | ~3.5 GB |
| DeepSeek-R1-8B-Q4 | ~4.7 GB | 8.9 tok/s | ~5.0 GB |

### 🗣️ TTS — Piper (Recomendado)
**Descargar ejecutable:**
```
URL: https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip
Extraer en: bin/piper/  (el .exe queda en bin/piper/piper/piper.exe)
```

**Descargar voz en español (sharvard):**
```
URL ONNX: https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx
URL JSON: https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx.json
Meter en: models/
```

**Descargar voz en inglés (lessac):**
```
URL ONNX: https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
URL JSON: https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
Meter en: models/
```

**Uso básico de Piper (una vez descargado):**
```bash
bin/piper/piper/piper.exe --model models/es_ES-sharvard-medium.onnx --output_file salida.wav
# Escribe el texto por stdin y presiona Ctrl+D/Ctrl+Z
```

### 🎙️ TTS Multilingüe Inteligente

El sistema detecta automáticamente el idioma de cada oración y cambia la voz TTS según corresponda:

| Idioma | Motor | Modelo de voz |
|:------:|:-----:|:-------------|
| **Español** 🇪🇸 | Piper | `es_ES-sharvard-medium` (voz femenina) |
| **Inglés** 🇺🇸 | Piper | `en_US-lessac-medium` (voz femenina) |
| **Japonés** 🇯🇵 | SpeechSynthesis (navegador) | Voz JA nativa del sistema |

**Cómo funciona la segmentación:**
1. Divide el texto por **saltos de línea** (límites fuertes entre idiomas)
2. Dentro de cada línea, divide por **puntuación final** (`. ! ? ¡ ¿`)
3. Si una oración mezcla **scripts** (ej. "Hello こんにちは"), se divide carácter por carácter en el punto de transición
4. Segmentos consecutivos del **mismo idioma** se fusionan para minimizar switches de modelo

**Ejemplo de respuesta multilingüe de Qwen:**
```
Input del usuario: "Give me a greeting in three languages"

Respuesta de Qwen:
  Hello! Good morning!
  ¡Hola! Buenos días!
  こんにちは！おはようございます！

Segmentación TTS:
  [EN] "Hello! Good morning!"       → Piper (voz inglesa)   ✅
  [ES] "¡Hola! Buenos días!"         → Piper (voz española)  ✅
  [JA] "こんにちは！おはようございます！"  → SpeechSynthesis JA   ✅
```

### 🔌 Endpoint `/api/tts-piper`

Endpoint para generar audio TTS con selección explícita de idioma.

**Request:**
```json
POST /api/tts-piper
Content-Type: application/json

{
  "text": "Texto a sintetizar",
  "lang": "es"      // "es" | "en" | "auto" (default: auto)
}
```

**Response:** `audio/wav` (16-bit mono, 22050 Hz)
- Header RIFF válido
- ~80-110 KB por ~3 segundos de audio
- Latencia: ~200-800ms (según largo del texto)

**Ejemplo con curl:**
```bash
# Español
curl -X POST http://localhost:3000/api/tts-piper \
  -H "Content-Type: application/json" \
  -d '{"text":"Hola, como estas hoy?","lang":"es"}' \
  -o salida_es.wav

# Inglés
curl -X POST http://localhost:3000/api/tts-piper \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello! How are you today?","lang":"en"}' \
  -o salida_en.wav

# Auto-detect (selecciona modelo según el contenido)
curl -X POST http://localhost:3000/api/tts-piper \
  -H "Content-Type: application/json" \
  -d '{"text":"Buenos dias! Como estas?","lang":"auto"}' \
  -o salida_auto.wav
```

**Optimización de latencia:**
- El endpoint usa stdin/stdout (no archivos temporales) para minimizar I/O
- Si stdin falla, fallback automático a archivos temporales
- Consecutive same-language segments se fusionan antes de enviar al TTS
- Japonés usa SpeechSynthesis del navegador (0ms de latencia de red)

### 🔊 ASR — Whisper (Opcional)
**Modelo tiny:**
```
URL: https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin
Meter en: models/ggml-tiny.bin
```
**Nota:** whisper.cpp necesita compilarse desde source (no hay .exe precompilado oficial para Windows).
Alternativa: `pip install faster-whisper` (Python) para ASR sin compilar.

**Descargar whisper.cpp (para compilar):**
```
URL: https://github.com/ggml-org/whisper.cpp
```

### 🎵 TTS Alternativo — OuteTTS (Experimental)
```
URL: https://huggingface.co/OuteAI/OuteTTS-0.2-500M-GGUF/resolve/main/OuteTTS-0.2-500M-Q4_K_M.gguf
Meter en: models/OuteTTS-0.2-500M-Q4_K_M.gguf
```

## 🔧 Requisitos de Hardware

| Componente | Mínimo | Recomendado |
|:----------:|:------:|:-----------:|
| **GPU** | NVIDIA 4 GB VRAM | RTX 3050 6GB |
| **RAM** | 8 GB | 16 GB |
| **Disco** | 10 GB libres | 50 GB libres |
| **SO** | Windows 10/11 | Windows 11 |

Probado en: **RTX 3050 6GB Laptop** · **i5-13420H** · **16 GB RAM**
VRAM usable: **5.28 GB** · Velocidad de descarga: ~3 MB/s

## 🏗️ Planes Disponibles

Cada plan tiene su propia interfaz HTML en `frontend/plan-*/index.html`

| Plan | Arquitectura | Tema |
|:----:|:------------|:----:|
| **A** 🟣 | LLM + TTS en GPU (recomendado) | Purple neon |
| **B** 🔵 | LLM en GPU, TTS en CPU | Blue tech |
| **C** 🟢 | Pipeline completo ASR→LLM→TTS | Green cyber |
| **D** 🟡 | Arquitectura ganadora (Plan A) | Gold premium |

### 🎯 Recomendación Final
**Qwen3.5-2B-Q8** (GPU) + **OuteTTS-500M** (GPU) = ~3.5 GB VRAM total.
Cabe todo en GPU. Sin swapping. 21 tok/s.

## 🖥️ Cómo Usar

1. **Editar rutas en scripts de inicio** (solo la primera vez):
   Los scripts `start_server.sh` y `start_server.bat` contienen rutas absolutas.
   Edítalos para que apunten a la ubicación de tu modelo GGUF.

   ```bash
   # Ejemplo (start_server.sh):
   MODEL="/ruta/a/tu/modelo.gguf"
   ```

2. **Iniciar el servidor:**
   ```bash
   ./start_server.sh   # Git Bash
   # o doble clic en start_server.bat (Windows)
   ```
   Esto levanta `llama-server.exe` con el modelo en puerto 8080.

3. **Abrir la interfaz:**
   - Plan A (recomendado): `frontend/plan-a/index.html`
   - Plan B (fallback TTS CPU): `frontend/plan-b/index.html`
   - Plan C (pipeline completo): `frontend/plan-c/index.html`
   - Plan D (recomendación final): `frontend/plan-d/index.html`

3. **Seleccionar modo:**
   - 🎓 **Teacher:** Explicaciones detalladas, tono educativo
   - 💬 **Conversación:** Charla natural y fluida
   - 🌍 **Traductor:** ES ↔ EN ↔ JA con romaji

## 🛡️ Seguridad

Todo comando que toque la GPU se ejecuta dentro de **tmux** para
proteger el proceso principal (`freebuff.exe`). Ver `AGENT.md`.

## 📁 Estructura del Proyecto

```
Alex_Voice/
├── A/                  # Plan A - Combined LLM+TTS GPU
│   ├── README.md, plan.md, AGENT.md
├── B/                  # Plan B - LLM GPU, TTS CPU
├── C/                  # Plan C - Pipeline completo
├── D/                  # Plan D - Recomendación final
├── frontend/
│   ├── plan-a/         # Interfaz Plan A (purple)
│   ├── plan-b/         # Interfaz Plan B (blue)
│   ├── plan-c/         # Interfaz Plan C (green)
│   └── plan-d/         # Interfaz Plan D (gold)
├── bin/
│   └── piper/          # Piper TTS ejecutable
├── models/             # Modelos descargados
├── start_server.sh     # Inicio (Git Bash)
├── start_server.bat    # Inicio (Windows)
└── AGENT.md            # Reglas de seguridad
```

## 📊 Benchmarks (Hardware Real)

| Modelo | Tok/s | VRAM | Prompt |
|--------|:-----:|:----:|:------:|
| Qwen3.5-2B-Q8 | 21-22 | ~3.0 GB | 68 tok/s |
| Gemma-4-E2B-Q4 | 24.3 | ~3.5 GB | 109 tok/s |
| DeepSeek-R1-8B-Q4 | 8.9 | ~5.0 GB | 5.1 tok/s |

## 🌐 Idiomas Verificados
- ✅ **Español** — Conversación natural, responde en español
- ✅ **Inglés** — Soporte nativo del modelo
- ✅ **Japonés** — Caracteres kanji/hiragana/katakana correctos
