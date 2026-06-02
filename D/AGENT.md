# AGENT — Folder D (Recomendación Final)

## Decisión Final
**Plan A: LLM + TTS combinados en GPU.** Qwen3.5-2B-Q8 + OuteTTS-500M caben en 5.28 GB VRAM.

## Stack Final
- **LLM:** Qwen3.5-2B-Q8 (21-22 tok/s, ~3.0 GB)
- **TTS:** OuteTTS-500M (~0.5 GB) o Piper TTS CPU
- **API:** llama-server.exe
- **Frontend:** HTML+JS vanilla
- **ASR:** whisper.cpp (futuro)

## Argumentos
1. VRAM suficiente para ambos modelos cargados
2. Sin overhead de swapping
3. Qwen3.5-2B rápido y multilingüe
4. OuteTTS ligero y multilingüe

## Limitaciones
- OuteTTS necesita debug de parámetros
- Sin ASR todavía
- Modo traductor no probado con japonés
