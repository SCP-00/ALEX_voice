#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  Alex Voice — E2E Test Runner
#  v3.3.1 — Runs all 4 subproject test suites
# ══════════════════════════════════════════════════════════════


SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ALEX_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   🧪 ALEX VOICE — E2E TEST RUNNER                      ║${NC}"
echo -e "${CYAN}║   v3.3.1 — All subprojects                             ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"

cd "$ALEX_DIR"

# Check which servers are running
check_server() {
    local port=$1
    local name=$2
    if curl -s --max-time 2 "http://localhost:$port" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅${NC} $name (port $port) — running"
        return 0
    else
        echo -e "  ${YELLOW}⏭️${NC} $name (port $port) — not running, skipping"
        return 1
    fi
}

echo ""
echo -e "${CYAN}Checking servers...${NC}"
check_server 3000 "Teacher" && TEACHER_OK=1 || TEACHER_OK=0
check_server 3001 "Conversation" && CONV_OK=1 || CONV_OK=0
check_server 3003 "Translator" && TRANS_OK=1 || TRANS_OK=0
check_server 3004 "Grammar App" && GRAM_OK=1 || GRAM_OK=0

PASSED=0
FAILED=0
SKIPPED=0

run_test() {
    local name=$1
    local script=$2
    local enabled=$3

    if [ "$enabled" != "1" ]; then
        echo -e "\n${YELLOW}⏭️  Skipping $name (server not running)${NC}"
        SKIPPED=$((SKIPPED + 1))
        return
    fi

    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  Running: $name${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if python3 "$script" 2>&1; then
        echo -e "${GREEN}✅ $name: PASSED${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}❌ $name: FAILED${NC}"
        FAILED=$((FAILED + 1))
    fi
}

# Run enabled test suites
run_test "🎓 Teacher" "$SCRIPT_DIR/test_teacher.py" "$TEACHER_OK"
run_test "💬 Conversation" "$SCRIPT_DIR/test_conversation.py" "$CONV_OK"
run_test "🌍 Translator" "$SCRIPT_DIR/test_translator.py" "$TRANS_OK"
run_test "📝 Grammar App" "$SCRIPT_DIR/test_grammar.py" "$GRAM_OK"

# ── Summary ──
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   📊 E2E TEST RUNNER — SUMMARY                         ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  ${GREEN}Passed:${NC}   $PASSED                                           ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${RED}Failed:${NC}   $FAILED                                           ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${YELLOW}Skipped:${NC}  $SKIPPED                                           ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"

# Results files
echo ""
echo -e "📄 Results saved to:"
ls -la "$SCRIPT_DIR"/results_*.json 2>/dev/null || echo "  (no results files yet)"

exit $FAILED
