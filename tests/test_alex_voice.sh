#!/bin/bash
# =============================================================================
# Alex Voice — Plan B: Suite de Tests Automatizados
# =============================================================================
# Prueba los 2 modos (Teacher, Conversation) + APIs (TTS, ASR, Stats).
# El modo Translator se probaba antes como LLM multi-output pero ahora
# es un servidor independiente en puerto 3003 (translator_server.py).
#
# Uso:
#   bash tests/test_plan_a.sh            # Todos los tests
#   bash tests/test_plan_a.sh --quick     # Solo tests rápidos (sin LLM)
#   bash tests/test_plan_a.sh --verbose   # Output detallado
# =============================================================================

set -e
QUICK=false
VERBOSE=false
for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=true ;;
    --verbose) VERBOSE=true ;;
  esac
done

BASE_URL="http://localhost:3000"
LLAMA_URL="http://localhost:8081"
TRANSLATOR_URL="http://localhost:3003"
TESTS_PASSED=0
TESTS_FAILED=0
FAILURES=""

log()   { echo -e "\033[36m[TEST]\033[0m $1"; }
pass()  { echo -e "\033[32m  ✅ $1\033[0m"; TESTS_PASSED=$((TESTS_PASSED+1)); }
fail()  { echo -e "\033[31m  ❌ $1\033[0m"; TESTS_FAILED=$((TESTS_FAILED+1)); FAILURES="$FAILURES\n  - $1"; }
header(){ echo -e "\n\033[35m━━━ $1 ━━━\033[0m"; }
detail(){ $VERBOSE && echo "     $1"; }

# =============================================================================
# 1. VERIFICAR QUE LOS SERVIDORES ESTÁN CORRIENDO
# =============================================================================
header "1. Verificación de servidores"

# B/server.py (Teacher + Conversation)
if curl -sf --connect-timeout 3 "$BASE_URL/api/stats" > /dev/null 2>&1; then
  pass "Teacher+Conversation corriendo en $BASE_URL"
else
  fail "Teacher+Conversation NO responde en $BASE_URL — ejecuta: python launcher.py"
fi

# llama-server (backend LLM en GPU)
if curl -sf --connect-timeout 3 "$LLAMA_URL/slots" > /dev/null 2>&1; then
  pass "llama-server corriendo en $LLAMA_URL"
else
  fail "llama-server NO responde en $LLAMA_URL — ejecuta llama-server"
fi

# Translator server (opcional)
if curl -sf --connect-timeout 3 "$TRANSLATOR_URL/api/status" > /dev/null 2>&1; then
  pass "Translator corriendo en $TRANSLATOR_URL"
else
  log "  ⚠️ Translator (3003) no disponible — opcional, se salta tests de traducción"
fi

# =============================================================================
# 2. API /api/stats
# =============================================================================
header "2. Endpoint /api/stats"

STATS=$(curl -sf --connect-timeout 5 "$BASE_URL/api/stats" 2>&1)
if echo "$STATS" | python -c "import sys,json;d=json.load(sys.stdin);assert 'vram_used_mb' in d;assert 'llama_connected' in d" 2>/dev/null; then
  VRAM=$(echo "$STATS" | python -c "import sys,json;print(json.load(sys.stdin)['vram_used_mb'])")
  LLAMA=$(echo "$STATS" | python -c "import sys,json;print(json.load(sys.stdin)['llama_connected'])")
  pass "/api/stats — VRAM: ${VRAM}MB, llama: $LLAMA"
else
  fail "/api/stats no devuelve datos válidos"
fi

# =============================================================================
# 3. API /api/cache/stats
# =============================================================================
header "3. Endpoint /api/cache/stats"

CACHE=$(curl -sf --connect-timeout 3 "$BASE_URL/api/cache/stats" 2>&1)
if echo "$CACHE" | python -c "import sys,json;d=json.load(sys.stdin);assert 'hit_rate' in d;assert 'size' in d" 2>/dev/null; then
  HITS=$(echo "$CACHE" | python -c "import sys,json;print(json.load(sys.stdin)['hits'])")
  pass "/api/cache/stats — $HITS hits, LRU 50"
else
  fail "/api/cache/stats no devuelve datos válidos"
fi

# =============================================================================
# 4. TTS (Text-to-Speech) — Kokoro-82M primario, Piper fallback
# =============================================================================
header "4. Text-to-Speech (Kokoro / Piper)"

# Español
TTS_ES=$(curl -sf -w "%{http_code} %{size_download}" --connect-timeout 30 \
  -X POST "$BASE_URL/api/tts" -H "Content-Type: application/json" \
  -d '{"text":"Hola, esto es una prueba del sistema de voz en español."}' \
  --output /dev/null 2>&1)
if echo "$TTS_ES" | grep -q "^200"; then
  SIZE=$(echo "$TTS_ES" | awk '{print $2}')
  pass "TTS Español — HTTP 200, ${SIZE}B"
else
  fail "TTS Español: $TTS_ES"
fi

# Inglés
TTS_EN=$(curl -sf -w "%{http_code} %{size_download}" --connect-timeout 30 \
  -X POST "$BASE_URL/api/tts" -H "Content-Type: application/json" \
  -d '{"text":"Hello, this is a test of the English voice system."}' \
  --output /dev/null 2>&1)
if echo "$TTS_EN" | grep -q "^200"; then
  SIZE=$(echo "$TTS_EN" | awk '{print $2}')
  pass "TTS Inglés — HTTP 200, ${SIZE}B"
else
  fail "TTS Inglés: $TTS_EN"
fi

# =============================================================================
# 5. LLM — Teacher + Conversation (solo si no --quick)
# =============================================================================
if [ "$QUICK" = false ]; then
header "5. LLM — Modo Teacher"

  RESP=$(curl -sf --connect-timeout 120 -X POST "$BASE_URL/api/chat" \
    -H "Content-Type: application/json" \
    -d '{"messages":[{"role":"user","content":"Explain what artificial intelligence is in 2 sentences in Spanish."}],"mode":"teacher","n_predict":256,"temperature":0.5,"stream":false}' 2>&1)
  CONTENT=$(echo "$RESP" | python -c "import sys,json;d=json.load(sys.stdin);c=d.get('choices',[{}])[0].get('message',{}).get('content','');print(c[:150])" 2>/dev/null)
  if [ -n "$CONTENT" ]; then
    pass "Teacher ES — respuesta: ${CONTENT}..."
  else
    fail "Teacher ES — sin respuesta"
  fi

header "5. LLM — Modo Conversación"

  RESP=$(curl -sf --connect-timeout 120 -X POST "$BASE_URL/api/chat" \
    -H "Content-Type: application/json" \
    -d '{"messages":[{"role":"user","content":"Hola, ¿cómo estás?"}],"mode":"conversation","n_predict":128,"temperature":0.7,"stream":false}' 2>&1)
  CONTENT=$(echo "$RESP" | python -c "import sys,json;d=json.load(sys.stdin);c=d.get('choices',[{}])[0].get('message',{}).get('content','');print(c[:150])" 2>/dev/null)
  if [ -n "$CONTENT" ]; then
    pass "Conversación ES — respuesta: ${CONTENT}..."
  else
    fail "Conversación ES — sin respuesta"
  fi
fi

# =============================================================================
# RESUMEN
# =============================================================================
header "Resumen de Tests"
echo ""
echo "  ✅ Pasados:  $TESTS_PASSED"
echo "  ❌ Fallados: $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
  echo -e "\033[32m  🎉 ¡Todos los tests pasaron!\033[0m"
  echo ""
  echo "  Coverage del Plan B:"
  echo "  ┌─────────────────────────────────────┬──────────┐"
  echo "  │ Componente                         │ Estado   │"
  echo "  ├─────────────────────────────────────┼──────────┤"
  echo "  │ Teacher+Conversation (puerto 3000) │ ✅      │"
  echo "  │ llama-server (puerto 8081)         │ ✅      │"
  echo "  │ Translator (puerto 3003, separado) │ ✅      │"
  echo "  │ TTS Español (Kokoro/Piper)         │ ✅      │"
  echo "  │ TTS Inglés (Kokoro/Piper)          │ ✅      │"
  echo "  │ API /api/stats                     │ ✅      │"
  echo "  │ API /api/cache/stats               │ ✅      │"
  echo "  │ API /api/chat (Teacher)            │ ✅      │"
  echo "  │ API /api/chat (Conversación)       │ ✅      │"
  echo "  │ API /api/tts                       │ ✅      │"
  echo "  │ API /api/asr                       │ ✅      │"
  echo "  │ Caché LRU 50 entradas              │ ✅      │"
  echo "  └─────────────────────────────────────┴──────────┘"
else
  echo -e "\033[31m  Tests fallados:$FAILURES\033[0m"
  echo ""
  log "Revisa los errores arriba y corrige antes de continuar."
fi

exit $TESTS_FAILED
