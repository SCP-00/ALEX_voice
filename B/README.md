# Folder B — LLM on GPU, TTS on CPU ✅ RECOMENDADO COMO FALLBACK

## Purpose
Arquitectura de menor riesgo: LLM en GPU, TTS en CPU.

## Benchmarks Reales

### LLM en GPU — Probados
| Modelo | VRAM | Tok/s | Español |
|--------|------|-------|:-------:|
| **Qwen3.5-2B-Q8** 🥇 | ~2.5-3.0 GB | **21-22 tok/s** | ✅ Excelente |
| **Gemma-4-E2B-Q4** 🥈 | ~3.5-4.0 GB | **24.3 tok/s** | ✅ Excelente |
| **Gemma-E2B-Uncensored-Q8** | ~5.0 GB | ~15 tok/s | ✅ |
| **DeepSeek-R1-8B-Q4** | ~5.0 GB | **8.9 tok/s** | ✅ |

### TTS en CPU — Pendientes de probar
| Motor | RAM | Latinoamérica | Velocidad |
|-------|-----|:------------:|:---------:|
| **OuteTTS-500M** (GPU/CPU) | ~500 MB | ✅ 20+ idiomas | Descargado |
| **Piper TTS** | ~200 MB | ✅ ES/EN/JA | Muy rápida |
| **MeloTTS** | ~1 GB | ✅ ES/EN/JA | Rápida |

### Hardware
- CPU: i5-13420H (8C/12T)
- RAM: 16.5 GB (5.7 GB libre)
- GPU: RTX 3050 6GB (5.28 GB VRAM usable)

### Estrategia
- LLM siempre en GPU (Qwen3.5-2B-Q8 recomendado)
- TTS en CPU (Piper o MeloTTS)
- Sin riesgo de OOM en GPU
- ~2.8 GB de VRAM libre para contexto

### Riesgos
- ⚠️ TTS en CPU añade 1-3s de latencia
- ⚠️ RAM puede ser cuello de botella si ASR + TTS corren juntos
- ✅ GPU siempre estable por debajo del límite
