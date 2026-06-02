# Folder C — Full Speech Pipeline 🚧 EN CONSTRUCCIÓN

## Purpose
Pipeline completo: ASR → Ruteo → LLM → TTS. El destino final del proyecto.

## Estado Actual de Componentes

### ✅ LLM (LISTO)
| Modelo | VRAM | Tok/s | Modos |
|--------|------|-------|-------|
| Qwen3.5-2B-Q8 🥇 | ~3.0 GB | 21-22 | Teacher ✅ / Conversación ✅ / Traductor ⏳ |
| Gemma-4-E2B-Q4 🥈 | ~3.5 GB | 24.3 | Teacher ✅ / Conversación ✅ / Traductor ⏳ |

### ✅ TTS (DESCARGADO, necesita debug)
- OuteTTS-0.2-500M-Q4_K_M: 385 MB
- Pip install Piper TTS: pendiente
- Pip install MeloTTS: pendiente

### ❌ ASR (PENDIENTE)
- whisper.cpp: no instalado
- faster-whisper: no instalado
- Qwen3-ASR: pendiente de investigar

### ❌ Ruteo / Language ID (PENDIENTE)
- Clasificador de idioma CPU: pendiente
- Romanización japonés: pendiente

### Hardware
- GPU: RTX 3050 6GB (5.28 GB usable)
- CPU: i5-13420H (8C/12T)
- RAM: 16.5 GB

### Pipeline Propuesto
```
[Audio In] → VAD → ASR (Whisper tiny) → Language ID (CPU)
    → Router (CPU) → LLM (GPU) → TTS (CPU/GPU) → [Audio Out]
```

### Estrategia de Memoria
- ASR: whisper tiny ~500 MB RAM
- LLM: Qwen3.5-2B-Q8 ~3.0 GB VRAM
- TTS: OuteTTS-500M ~0.5 GB VRAM (o CPU)
- Sin cargar ASR y TTS simultáneamente
