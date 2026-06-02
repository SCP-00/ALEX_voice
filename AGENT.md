# 🛡️ REGLA IRROMPIBLE — NO MATAR freebuff.exe

## ⚠️ LEY SUPREMA: NUNCA MATAR freebuff.exe

**freebuff.exe ES MI PROCESO VITAL.** Está en:
`C:\Users\andyh\.config\manicode\freebuff.exe`

Este proceso es el que lanza mi agente. Matarlo = matar la sesión de chat.
Esto incluye, pero no se limita a:
- `^C` (Ctrl+C) durante comandos largos — usar `timeout` en su lugar
- `kill` commands
- `taskkill`
- Cualquier señal de terminación

**SIEMPRE dejar que los comandos terminen naturalmente o con timeout.**

---

## 📋 Contexto del Entorno

### Sistema
- **OS:** Windows 11 (Git Bash MINGW64)
- **Shell:** bash en Git Bash
- **Proyecto:** `C:\Users\andyh\Desktop\Soft\Alex_Voice`

### Hardware
| Componente | Especificación |
|------------|---------------|
| GPU | NVIDIA GeForce RTX 3050 Laptop 6GB |
| VRAM usable | ~5.28 GB (735 MB en reposo) |
| CPU | Intel Core i5-13420H (8 núcleos, 12 hilos) |
| RAM | 16.5 GB (~5.7 GB libre en reposo) |
| Disco libre | ~258 GB |

### Red
- **Velocidad de descarga:** ~3 MB/s promedio
- **Ajustar timeouts** para descargas grandes en consecuencia:
  - Modelo GGUF 4GB → ~22 minutos (timeout mínimo: 1800s)
  - Modelo GGUF 2GB → ~11 minutos (timeout mínimo: 900s)
  - Modelo GGUF 1GB → ~6 minutos (timeout mínimo: 360s)

### Estado de Instalaciones
- **llama.cpp v9479:** ✅ Instalado en `C:\Users\andyh\Documents\llama-b9479-bin-win-cuda-13.3-x64`
  - Binarios CUDA 12.4 + DLLs runtime CUDA 13.3
  - Compilado con Clang 19.1.5, soporte completo GPU (-ngl, -sm, --fit)
  - PATH añadido a `~/.bashrc`
- **CUDA Toolkit:** No instalado (solo driver UMD 13.3, driver v610.47)
- **Ollama:** Binario `ollama.exe` visible en PATH, pero directorio de instalación no encontrado

---

## 🚨 Política de Seguridad de Procesos

### 🛡️ NIVEL 1 — Regla Oro (Absoluta)
1. **NUNCA** usar `^C` o señales de terminación en procesos que puedan tener freebuff.exe como ancestro.
2. **Usar timeouts explícitos** en lugar de interrupción manual.
3. **Para procesos de descarga larga:** usar `timeout_seconds` en basher con valores adecuados (~1800s para modelos grandes).
4. **Para procesos de inferencia:** dejar que terminen naturalmente o timeout después de 300s.
5. **Si un comando parece colgado:** usar timeout progresivo o tmux, NUNCA `^C`.

### 🧪 NIVEL 2 — Aislamiento con tmux (Comandos Peligrosos)
**tmux instalado:** `C:\Users\andyh\AppData\Local\Microsoft\WinGet\Links\tmux` (v3.6a)

**CUÁNDO USAR tmux:**
- Cualquier comando que cargue un modelo en GPU (inferencia con llama-cli)
- Pruebas de VRAM con modelos grandes (>3 GB)
- Procesos de los que no se sabe si van a colgarse o petar
- Cualquier operación que pueda causar OOM (Out of Memory)
- **SIEMPRE** que haya duda sobre la estabilidad de un comando

**CÓMO USARLO — Opción A: Agente tmux-cli (Recomendada)**
Usar el agente `tmux-cli` integrado en el sistema. Este agente:
- Crea sesiones tmux automáticamente
- Captura la salida de forma segura
- Limpia sesiones huérfanas
- **No puede matar freebuff.exe** porque ejecuta en proceso separado

**CÓMO USARLO — Opción B: Manual**
```bash
# Crear sesión aislada
tmux new-session -d -s inference

# Ejecutar comando (no puede matar freebuff.exe aunque crashee)
tmux send-keys -t inference 'llama-cli.exe -m modelo.gguf -ngl 99 -p "Hola" --no-display-prompt' Enter

# Esperar y capturar resultado
sleep 60 && tmux capture-pane -t inference -p

# Terminar sesión
tmux kill-session -t inference
```

**⚠️ MODO SEGURO:** Si no estás seguro del impacto en VRAM/RAM de un comando, NO lo ejecutes directamente. Usa tmux-cli o consulta al usuario primero.

**BENEFICIO:** Si el comando dentro de tmux crashea, solo mata tmux. freebuff.exe no se ve afectado.

### ⏱️ NIVEL 3 — Timeouts por Tipo de Operación
| Operación | Timeout | Razón |
|-----------|---------|-------|
| Descarga zip llama.cpp | 120s | ~250 MB / ~3 MB/s |
| Descarga modelo GGUF 1-2 GB | 900s (15 min) | ~2 GB / ~3 MB/s |
| Descarga modelo GGUF 4-5 GB | 1800s (30 min) | ~5 GB / ~3 MB/s |
| Inferencia pequeña (1-2 prompts) | 180s | Incluye carga de modelo en GPU |
| Inferencia larga (chat continuo) | 600s | Conversación extendida |
| Benchmarks / estrés | Depende del test | Usar tmux siempre |

---

## 📦 Inventario de Modelos

### 📍 LM Studio — `~/.lmstudio/models/`

| Modelo | Tamaño | Tipo | Integridad |
|--------|--------|------|:----------:|
| `khazarai/Qwen3.5-2B-Qwen3.6-plus-Distilled-q8_0.gguf` | ~2.0 GB | 2B Q8 | ✅ Cargó sin errores |
| `lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-Q4_K_M.gguf` | ~4.7 GB | 8B Q4_K_M | ✅ Cargó sin errores |
| `lmstudio-community/gemma-4-E2B-it-Q4_K_M.gguf` | ~3.2 GB | E2B Q4_K_M | ✅ Cargó sin errores |
| `lmstudio-community/Gemma-4-E2B-Uncensored-Q8_K_P.gguf` | ~4.7 GB | E2B Q8_K_P | ✅ Cargó sin errores |
| `lmstudio-community/gemma-4-E4B-it-Q4_K_M.gguf` | ~5.0 GB | E4B Q4_K_M | ✅ Cargó sin errores |
| `lmstudio-community/nomic-embed-text-v1.5-Q4_K_M.gguf` | ~84 MB | Embedding Q4 | ❌ Error GGML_ASSERT — incompatible con llama-cli.exe o corrupto |

> ⚠️ **Nota sobre modelos corruptos:** Verificación completada con tmux. **5 de 6 modelos cargaron correctamente.** El que falló (nomic-embed-text) requiere más investigación. Si el usuario tenía modelos corruptos de la Sesión 1, esos ya no existen en disco. Los modelos actuales parecen íntegros.

> ⚠️ **Importante:** La verificación se hizo con `-n 0` (0 tokens generados), lo que significa que **no se allocó KV cache**. Durante inferencia real con contexto >0 tokens, el uso de VRAM será mayor. Modelos como Gemma-4-E4B (5.0 GB) podrían fallar con OOM al generar texto aunque hayan cargado en seco.

### Modelos MMProj (Multimodales)
| Archivo | Tamaño | Uso |
|---------|--------|-----|
| `mmproj-gemma-4-E2B-it-BF16.gguf` | ~942 MB | Proyección multimodal Gemma E2B |
| `mmproj-Gemma-4-E2B-Uncensored-f16.gguf` | ~940 MB | Proyección multimodal Gemma E2B Uncensored |
| `mmproj-gemma-4-E4B-it-BF16.gguf` | ~946 MB | Proyección multimodal Gemma E4B |

### 💡 Recomendaciones para nuestro hardware (5.28 GB VRAM usable)

| Prioridad | Modelo | Tamaño disco | VRAM estimada* | OK? |
|-----------|--------|-------------|----------------|-----|
| 🥇 | **Qwen3.5-2B-Q8** | ~2.0 GB | ~2.5-3.0 GB | ✅ Sobra VRAM para TTS |
| 🥈 | **Gemma-4-E2B-Q4** | ~3.2 GB | ~3.8-4.2 GB | ✅ Cabe con margen |
| 🥉 | **Gemma-4-E2B-Uncensored-Q8** | ~4.7 GB | ~5.0-5.3 GB | ⚠️ Cargó — justo pero cupo |
| 4 | **DeepSeek-R1-8B-Q4** | ~4.7 GB | ~5.0-5.5 GB | ✅ Cargó — cupo con --fit |
| 5 | **Gemma-4-E4B-Q4** | ~5.0 GB | ~5.5-6.0 GB | ✅ Cargó — sorprendentemente cupo |

*_La VRAM real depende del contexto usado (KV cache), cuantización y overhead del runtime. Usar tmux para probar._

### 🎯 Bonus: llama-tts.exe — Investigación Completa
Dentro de `llama-b9479-bin-win-cuda-13.3-x64` se incluye `llama-tts.exe` (351 KB).

**¿Qué es?** Es un binario de síntesis de voz nativa basado en **OuteTTS** — un "audio language model" que genera tokens de audio directamente, sin vocoder externo.

**Idiomas:** OuteTTS 1.0 soporta **20+ idiomas** — inglés, español y japonés incluidos.

**Modelos necesarios (descargar de Hugging Face):**
- [`OuteAI/OuteTTS-0.2-500M-GGUF`](https://huggingface.co/OuteAI/OuteTTS-0.2-500M-GGUF): ~403 MB (Q4_K_M) — recomendado por ligereza
- [`OuteAI/Llama-OuteTTS-1.0-1B-GGUF`](https://huggingface.co/OuteAI/Llama-OuteTTS-1.0-1B-GGUF): ~818 MB (Q4_K_M) — mejor calidad

**Compatibilidad con los planes del proyecto:**
- **Plan A** (LLM + TTS en GPU): 🟢 El modelo 500M (~500 MB VRAM) cabe junto al LLM (~3 GB) = ~3.5 GB total. Sin swapping.
- **Plan B** (LLM en GPU, TTS en CPU): 🟢 OuteTTS puede ejecutarse en CPU con `-ngl 0`. Alternativamente Piper/MeloTTS.
- **Plan C** (Pipeline completo): 🟢 OuteTTS encaja como módulo TTS del pipeline.

**Uso básico (cuando se descargue el modelo):**
```bash
llama-tts.exe -m OuteTTS-0.2-500M-Q4_K_M.gguf -p "Hola, soy Alex" -o salida.wav
```

**Voice cloning:** Incluye flag `--tts-speaker-file` para clonar voces zero-shot.

---

## 📝 Historial de Sesiones

### Sesión 1 (Histórica — perdida por ^C)
- Se descargó `llama-b9334-bin-win-cuda-13.1-x64`
- Se añadió al PATH
- Se interrumpió con `^C` → se mató freebuff.exe → pérdida de sesión

### Sesión 2 (Actual)
- ✅ Regla irrompible creada (NO matar freebuff.exe)
- ✅ Hardware validado (GPU 5.28 GB VRAM usable, CPU 8C/12T, RAM 16.5 GB)
- ✅ llama.cpp v9479 instalado con CUDA 13.3
- ✅ tmux-windows 3.6a instalado para aislamiento de procesos
- ✅ Modelos inventariados en LM Studio (~15 GB total en discos)
- ⏳ Pendiente: Verificar integridad de modelos con llama.cpp

### Lección aprendida
**NUNCA interrumpir procesos.** Usar tmux para aislar comandos peligrosos.
Usar timeouts generosos y dejar que los comandos terminen solos.
