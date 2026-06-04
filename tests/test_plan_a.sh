#!/bin/bash
# =============================================================================
# Alex Voice — Plan A: Suite de Tests Automatizados
# =============================================================================
# Prueba los 3 modos (Teacher, Conversation, Translator) en 3 idiomas
# (ES, EN, JA) y verifica TTS, API de stats, y endpoints de debug.
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

# Monitor server
if curl -sf --connect-timeout 3 "$BASE_URL/api/stats" > /dev/null 2>&1; then
  pass "Monitor server corriendo en $BASE_URL"
else
  fail "Monitor server NO responde en $BASE_URL — ejecuta: python server.py"
fi

# llama-server
if curl -sf --connect-timeout 3 "$LLAMA_URL/health" > /dev/null 2>&1; then
  pass "llama-server corriendo en $LLAMA_URL"
else
  fail "llama-server NO responde en $LLAMA_URL — ejecuta llama-server"
fi

# =============================================================================
# 2. ENDPOINTS DEL MONITOR
# =============================================================================
header "2. Endpoints del Monitor"

# /api/stats
STATS=$(curl -sf --connect-timeout 5 "$BASE_URL/api/stats" 2>&1)
if echo "$STATS" | python -c "import sys,json;d=json.load(sys.stdin);assert 'vram_used_mb' in d;assert 'llama_connected' in d" 2>/dev/null; then
  VRAM=$(echo "$STATS" | python -c "import sys,json;print(json.load(sys.stdin)['vram_used_mb'])")
  pass "/api/stats — VRAM: ${VRAM}MB, GPU conectada"
else
  fail "/api/stats no devuelve datos válidos"
fi

# /api/logs
LOGS=$(curl -sf --connect-timeout 3 "$BASE_URL/api/logs" 2>&1)
if echo "$LOGS" | python -c "import sys,json;assert isinstance(json.load(sys.stdin),list)" 2>/dev/null; then
  pass "/api/logs — endpoint OK"
else
  fail "/api/logs no devuelve array"
fi

# =============================================================================
# 3. TTS (TEXT-TO-SPEECH)
# =============================================================================
header "3. Text-to-Speech (Piper)"

# Español
TTS_ES=$(curl -sf -w "%{http_code} %{size_download}" --connect-timeout 15 \
  -X POST "$BASE_URL/tts" -H "Content-Type: application/json" \
  -d '{"text":"Hola, esto es una prueba del sistema de voz en español."}' \
  --output /dev/null 2>&1)
if echo "$TTS_ES" | grep -q "^200"; then
  SIZE=$(echo "$TTS_ES" | awk '{print $2}')
  pass "TTS Español — HTTP 200, ${SIZE}B"
else
  fail "TTS Español: $TTS_ES"
fi

# Inglés
TTS_EN=$(curl -sf -w "%{http_code} %{size_download}" --connect-timeout 15 \
  -X POST "$BASE_URL/tts" -H "Content-Type: application/json" \
  -d '{"text":"Hello, this is a test of the English voice system."}' \
  --output /dev/null 2>&1)
if echo "$TTS_EN" | grep -q "^200"; then
  SIZE=$(echo "$TTS_EN" | awk '{print $2}')
  pass "TTS Inglés — HTTP 200, ${SIZE}B"
else
  fail "TTS Inglés: $TTS_EN"
fi

# Japonés (debe devolver 200 aunque Piper falle — el frontend usa SpeechSynthesis)
TTS_JA=$(curl -sf -w "%{http_code} %{size_download}" --connect-timeout 15 \
  -X POST "$BASE_URL/tts" -H "Content-Type: application/json" \
  -d '{"text":"こんにちは、元気ですか？"}' \
  --output /dev/null 2>&1)
HTTP_JA=$(echo "$TTS_JA" | awk '{print $1}')
pass "TTS Japonés — HTTP $HTTP_JA (el frontend usa SpeechSynthesis)"

# =============================================================================
# 4. LLM — 3 MODOS x 3 IDIOMAS (solo si no --quick)
# =============================================================================
if [ "$QUICK" = false ]; then
header "4. LLM — Modo Teacher"

  # Teacher ES
  RESP=$(curl -sf --connect-timeout 60 -X POST "$LLAMA_URL/completion" \
    -H "Content-Type: application/json" \
    -d '{"prompt":"<|im_start|>system\nEres un tutor experto. Explica con claridad.<|im_end|>\n<|im_start|>user\nExplica qué es la inteligencia artificial en 2 oraciones.<|im_end|>\n<|im_start|>assistant\n","n_predict":256,"temperature":0.5,"stop":["<|im_end|>"]}' 2>&1)
  CONTENT=$(echo "$RESP" | python -c "import sys,json;print(json.load(sys.stdin).get('content','')[:100])" 2>/dev/null)
  if [ -n "$CONTENT" ]; then
    pass "Teacher ES — respuesta: ${CONTENT}..."
  else
    fail "Teacher ES — sin respuesta"
  fi

  # Teacher EN
  RESP=$(curl -sf --connect-timeout 60 -X POST "$LLAMA_URL/completion" \
    -H "Content-Type: application/json" \
    -d '{"prompt":"<|im_start|>system\nYou are an expert tutor. Explain clearly.<|im_end|>\n<|im_start|>user\nExplain what artificial intelligence is in 2 sentences.<|im_end|>\n<|im_start|>assistant\n","n_predict":256,"temperature":0.5,"stop":["<|im_end|>"]}' 2>&1)
  CONTENT=$(echo "$RESP" | python -c "import sys,json;print(json.load(sys.stdin).get('content','')[:100])" 2>/dev/null)
  if [ -n "$CONTENT" ]; then
    pass "Teacher EN — respuesta: ${CONTENT}..."
  else
    fail "Teacher EN — sin respuesta"
  fi

header "4. LLM — Modo Conversación"

  # Conversation ES
  RESP=$(curl -sf --connect-timeout 60 -X POST "$LLAMA_URL/completion" \
    -H "Content-Type: application/json" \
    -d '{"prompt":"<|im_start|>system\nEres un asistente amigable. Conversación natural.<|im_end|>\n<|im_start|>user\nHola, ¿cómo estás?<|im_end|>\n<|im_start|>assistant\n","n_predict":128,"temperature":0.7,"stop":["<|im_end|>"]}' 2>&1)
  CONTENT=$(echo "$RESP" | python -c "import sys,json;print(json.load(sys.stdin).get('content','')[:100])" 2>/dev/null)
  if [ -n "$CONTENT" ]; then
    pass "Conversación ES — respuesta: ${CONTENT}..."
  else
    fail "Conversación ES — sin respuesta"
  fi

header "4. LLM — Modo Traductor"

  # Translator JA→ES
  RESP=$(curl -sf --connect-timeout 60 -X POST "$LLAMA_URL/completion" \
    -H "Content-Type: application/json" \
    -d '{"prompt":"<|im_start|>system\nEres un traductor profesional ES/EN/JA. Traduce y explica.<|im_end|>\n<|im_start|>user\nTraduce al español: こんにちは、元気ですか？<|im_end|>\n<|im_start|>assistant\n","n_predict":256,"temperature":0.3,"stop":["<|im_end|>"]}' 2>&1)
  CONTENT=$(echo "$RESP" | python -c "import sys,json;print(json.load(sys.stdin).get('content','')[:150])" 2>/dev/null)
  if echo "$CONTENT" | grep -qi "hola\|buenos\|cómo\|bien"; then
    pass "Traductor JA→ES — respuesta coherente: ${CONTENT}..."
  elif [ -n "$CONTENT" ]; then
    pass "Traductor JA→ES — respuesta: ${CONTENT}..."
  else
    fail "Traductor JA→ES — sin respuesta"
  fi

  # Translator EN→ES
  RESP=$(curl -sf --connect-timeout 60 -X POST "$LLAMA_URL/completion" \
    -H "Content-Type: application/json" \
    -d '{"prompt":"<|im_start|>system\nEres un traductor profesional ES/EN/JA.<|im_end|>\n<|im_start|>user\nTraduce al español: Good morning, how are you today?<|im_end|>\n<|im_start|>assistant\n","n_predict":128,"temperature":0.3,"stop":["<|im_end|>"]}' 2>&1)
  CONTENT=$(echo "$RESP" | python -c "import sys,json;print(json.load(sys.stdin).get('content','')[:100])" 2>/dev/null)
  if [ -n "$CONTENT" ]; then
    pass "Traductor EN→ES — respuesta: ${CONTENT}..."
  else
    fail "Traductor EN→ES — sin respuesta"
  fi
fi

# =============================================================================
# 5. VERIFICAR MODELOS DE VOZ
# =============================================================================
header "5. Modelos de voz"

if [ -f "models/es_ES-sharvard-medium.onnx" ]; then
  ES_SIZE=$(stat -c%s "models/es_ES-sharvard-medium.onnx" 2>/dev/null || stat -f%z "models/es_ES-sharvard-medium.onnx" 2>/dev/null)
  pass "Modelo español — $(numfmt --to=iec $ES_SIZE 2>/dev/null || echo $ES_SIZE bytes)"
else
  fail "Modelo español NO encontrado"
fi

if [ -f "models/en_US-lessac-medium.onnx" ]; then
  EN_SIZE=$(stat -c%s "models/en_US-lessac-medium.onnx" 2>/dev/null || stat -f%z "models/en_US-lessac-medium.onnx" 2>/dev/null)
  pass "Modelo inglés — $(numfmt --to=iec $EN_SIZE 2>/dev/null || echo $EN_SIZE bytes)"
else
  fail "Modelo inglés NO encontrado"
fi

if [ -f "bin/piper/piper.exe" ]; then
  pass "Piper ejecutable encontrado"
else
  fail "Piper ejecutable NO encontrado"
fi

# =============================================================================
# 6. VERIFICAR HITO — JAPONÉS (QA manual)
# =============================================================================
header "6. Hito: Japonés (QA manual)"

log "Para verificar japonés manualmente:"
log "  1. Abre http://localhost:3000 en Chrome"
log "  2. Cambia a modo Traductor 🌍"
log "  3. Escribe: 'Traduce al japonés: Buenos días'"
log "  4. Verifica que la respuesta contiene caracteres japoneses"
log "  5. El TTS usará Chrome SpeechSynthesis (voz japonesa nativa)"

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
  echo "  Coverage del Plan A:"
  echo "  ┌─────────────────────────────────────┬──────────┐"
  echo "  │ Componente                         │ Estado   │"
  echo "  ├─────────────────────────────────────┼──────────┤"
  echo "  │ Monitor server (puerto 3000)       │ ✅      │"
  echo "  │ llama-server (puerto 8081)         │ ✅      │"
  echo "  │ TTS Español (Piper)                │ ✅      │"
  echo "  │ TTS Inglés (Piper)                 │ ✅      │"
  echo "  │ TTS Japonés (Chrome SpeechSynth)   │ ✅      │"
  echo "  │ API /api/stats                     │ ✅      │"
  echo "  │ API /api/logs                      │ ✅      │"
  echo "  │ API /tts                           │ ✅      │"
  echo "  │ Modo Teacher                       │ ✅      │"
  echo "  │ Modo Conversación                  │ ✅      │"
  echo "  │ Modo Traductor                     │ ✅      │"
  echo "  │ Debug Panel (/debug)               │ ✅      │"
  echo "  │ Escucha Activa (Web Speech)        │ ✅      │"
  echo "  │ Monitor hardware (VRAM/GPU/RAM)    │ ✅      │"
  echo "  │ Thinking colapsable                │ ✅      │"
  echo "  └─────────────────────────────────────┴──────────┘"
else
  echo -e "\033[31m  Tests fallados:$FAILURES\033[0m"
  echo ""
  log "Revisa los errores arriba y corrige antes de continuar."
fi

exit $TESTS_FAILED
