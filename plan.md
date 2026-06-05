# 📋 Alex Voice — Plan de Mejora (KISS)

**Hardware original:** RTX 3050 Laptop 6GB · i5-13420H · 16.5 GB RAM
**Objetivo:** Máxima naturalidad, velocidad y calidad con hardware disponible.
**Última migración:** Windows → Linux (2026-06-05)

---

## ✅ Completado

### Fase 1: Conversación Independiente + AEC
- `conv_server.py` wrapper (~10 líneas) con `--mode conversation --port 3001`
- `server.py` parsea `--mode` y `--port`
- AEC híbrido: `autoGainControl` + `isTtsPlaying` + mute-while-speaking

### Fase 2: Translator — Whisper Large-v3-Turbo + Optimizaciones TTS
- ASR: `base`(CPU) → `large-v3-turbo`(GPU, INT8). ~5% WER ES, ~7% JA
- TTS chunk size: 600 → 1500 chars (menos chunks = menos overhead)
- max_new_tokens: 2048 → 6144
- Warmup 2-pasos con CUDA Graphs (torch.compile + reduce-overhead)
- Pipeline paralelo ThreadPoolExecutor (overlap CPU↔GPU)
- Gestión VRAM: ASR y TTS se swap automáticamente (nunca juntos en VRAM)
- xformers detectado + SDPA attention

### Fase 3: Documentación y Migración a Linux
- `setup.sh` — Script de instalación para Linux (Ubuntu/Debian)
- `run.sh` — Script de inicio rápido para Linux
- `AGENT.md` actualizado con paths Linux y guía de reinstalación
- `README.md` actualizado con instrucciones Linux + arquitectura actualizada
- `plan.md` actualizado con estado actual

---

## 📊 Métricas Reales (RTX 3050 6GB)

| Componente | Métrica | Valor |
|:-----------|:--------|:-----:|
| Qwen3-TTS cold start | Carga + warmup | ~26s |
| Qwen3-TTS warm | Texto corto (~60ch) | RTF **2.6x** (8.9s para 3.4s audio) |
| Qwen3-TTS warm | Texto largo (~350ch) | RTF **2.7x** (57.7s para 21.4s audio) |
| Whisper large-v3-turbo | Carga inicial | ~4-5s |
| VRAM swap ASR→TTS | Libera Whisper, carga Qwen3 | Automático |

---

## 🎯 Objetivo Final

**Naturalidad:** Respuesta de voz fluida, sin cortes (AEC funcional).
**Velocidad:** TTS a <1x RTF idealmente (requiere flash-attn o modelo alternativo).
**Calidad:** Voz natural con Qwen3-TTS, ASR preciso con large-v3-turbo.
**KISS:** Código mínimo, sin duplicación, sin dependencias innecesarias.
**Portabilidad:** Documentación completa para reinstalación en Linux.
