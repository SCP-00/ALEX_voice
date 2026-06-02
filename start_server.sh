#!/bin/bash
# ====================================
# Alex Voice — Start llama-server
# ====================================
# Uso: ./start_server.sh [modelo] [puerto]
# Por defecto: Qwen3.5-2B-Q8 en puerto 8080

LLAMA_DIR="/c/Users/andyh/Documents/llama-b9479-bin-win-cuda-13.3-x64"
MODELS_DIR="/c/Users/andyh/.lmstudio/models"

MODEL="${1:-$MODELS_DIR/khazarai/Qwen3.5-2B-Qwen3.6-plus-Distilled-GGUF/Qwen3.5-2B-Qwen3.6-plus-Distilled-q8_0.gguf}"
PORT="${2:-8080}"

echo "========================================="
echo "  Alex Voice — Iniciando llama-server"
echo "========================================="
echo "  Modelo: $MODEL"
echo "  Puerto: $PORT"
echo "  GPU:    -ngl 99 (todas las capas)"
echo "========================================="
echo ""
echo "Abre frontend/index.html en tu navegador"
echo ""

"$LLAMA_DIR/llama-server.exe" \
  -m "$MODEL" \
  -ngl 99 \
  --host 0.0.0.0 \
  --port "$PORT" \
  -c 4096 \
  --mlock
