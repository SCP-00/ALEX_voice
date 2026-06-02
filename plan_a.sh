#!/bin/bash
# ============================================
# Alex Voice — Plan A: Combined LLM + TTS on GPU
# ============================================
# Lanza llama-server con Qwen, abre la interfaz,
# y gestiona el ciclo de vida del Plan A.
#
# Uso: ./plan_a.sh
# ============================================

LLAMA_DIR="/c/Users/andyh/Documents/llama-b9479-bin-win-cuda-13.3-x64"
MODELS_DIR="/c/Users/andyh/.lmstudio/models"
MODEL="$MODELS_DIR/khazarai/Qwen3.5-2B-Qwen3.6-plus-Distilled-GGUF/Qwen3.5-2B-Qwen3.6-plus-Distilled-q8_0.gguf"
PORT=8081
INTERFACE="frontend/plan-a/index.html"

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║     Alex Voice — Plan A              ║"
echo "  ║     LLM + TTS en GPU                 ║"
echo "  ║     Qwen3.5-2B-Q8 · 21 tok/s         ║"
echo "  ╚══════════════════════════════════════╝"
echo ""
echo "  📦 Modelo: Qwen3.5-2B-Q8"
echo "  🎯 Router: llama-server (puerto $PORT)"
echo "  🖥️  UI:     $INTERFACE"
echo "  💾 VRAM:   ~3.0 GB (de 5.28 GB disponibles)"
echo ""

# Verificar que el modelo existe
if [ ! -f "$MODEL" ]; then
  echo "  ❌ ERROR: Modelo no encontrado en $MODEL"
  echo "  📥 Descárgalo desde:"
  echo "     https://huggingface.co/khazarai/Qwen3.5-2B-Qwen3.6-plus-Distilled-GGUF"
  echo ""
  read -p "  Presiona Enter para salir..."
  exit 1
fi

echo "  ✅ Modelo encontrado"
echo ""

# Iniciar llama-server dentro de tmux (aislado por seguridad)
SESSION="alex_voice_plan_a"
echo "  🚀 Iniciando llama-server en tmux (sesión: $SESSION)..."
echo ""

tmux new-session -d -s "$SESSION" 2>/dev/null
tmux send-keys -t "$SESSION" "\"$LLAMA_DIR/llama-server.exe\" -m \"$MODEL\" -ngl 99 --host 0.0.0.0 --port 8081 -c 4096 --mlock 2>&1 | tee /tmp/alex_server.log" Enter

# Esperar a que el servidor arranque
echo "  ⏳ Esperando a que el servidor arranque..."
sleep 5

# Verificar que el servidor esté corriendo
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "  ✅ Servidor iniciado en tmux (sesión: $SESSION)"
else
  echo "  ❌ Error: el servidor no arrancó"
  exit 1
fi

echo ""
echo "  🌐 Abriendo interfaz Plan A..."
echo "     Abre este archivo en tu navegador:"
echo "     file:///C:/Users/andyh/Desktop/Soft/Alex_Voice/$INTERFACE"
echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║  Plan A ACTIVO                        ║"
echo "  ║                                       ║"
echo "  ║  • Server:   http://localhost:8081   ║"
echo "  ║  • UI:       $INTERFACE               ║"
echo "  ║  • tmux:     tmux attach -t $SESSION  ║"
echo "  ║                                       ║"
echo "  ║  Para detener:                        ║"
echo "  ║    tmux kill-session -t $SESSION      ║"
echo "  ╚══════════════════════════════════════╝"
echo ""
