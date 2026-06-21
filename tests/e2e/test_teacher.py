#!/usr/bin/env python3
"""
E2E Test Suite — 🎓 Teacher Mode
=================================
Alex Voice v3.3.1 — Exhaustive testing from ALL 3 source languages.

Rubric:
- Output quality (multi-output format, no joined words, no emojis)
- Card visualization (6 card types rendered correctly)
- Generation speed (TTS + LLM latency benchmarks)
- Memory (VRAM usage stays under budget)
- Explanation quality (grammar accuracy, cultural context)
- Translation accuracy (all 3 language pairs)
- Word spacing fix validation (joinwords bug)

Language pairs tested FROM each source language:
  ES→JA, ES→EN  (Spanish native speaker)
  EN→JA, EN→ES  (English native speaker)
  JA→ES, JA→EN  (Japanese native speaker)
"""

import json
import time
import sys
import re
import urllib.request
import urllib.error
from pathlib import Path

BASE_URL = "http://localhost:3000"
TIMEOUT = 60  # seconds per request — generous for cold LLM
RESULTS = []


# ══════════════════════════════════════════════════════════════
#  TEST DATA — Exigent prompts from each source language
# ══════════════════════════════════════════════════════════════

TEST_PROMPTS = {
    # ── FROM SPANISH (native) ──
    "es_to_ja": [
        {
            "prompt": "Enseñame a presentarme en japonés formal. Quiero decir 'Buenos días, me llamo Carlos, mucho gusto'",
            "target_lang": "ja",
            "checks": ["contains_kanji", "has_tts_reading", "has_pronunciation", "has_translation",
                        "no_emojis", "word_spacing", "formal_register"],
            "quality_min_score": 8,
        },
        {
            "prompt": "¿Cómo pido una cerveza en un bar en Tokio? Enseñame la frase y la pronunciación",
            "target_lang": "ja",
            "checks": ["contains_kanji_or_kana", "has_tts_reading", "has_cultural_context",
                        "has_exercise", "no_emojis", "word_spacing"],
            "quality_min_score": 8,
        },
        {
            "prompt": "Explica la diferencia entre は y が. Dame ejemplos simples",
            "target_lang": "ja",
            "checks": ["has_explanation", "has_examples", "contains_kana",
                        "has_tts_reading", "grammar_accuracy"],
            "quality_min_score": 9,
        },
    ],
    "es_to_en": [
        {
            "prompt": "Enséñame a pedir directions en inglés. Quiero ir al metro más cercano",
            "target_lang": "en",
            "checks": ["has_english_text", "has_tts_reading", "has_pronunciation",
                        "has_explanation", "no_emojis", "word_spacing"],
            "quality_min_score": 8,
        },
        {
            "prompt": "¿Cuál es la diferencia entre 'make' y 'do'? Dame 5 ejemplos de cada uno",
            "target_lang": "en",
            "checks": ["has_explanation", "has_examples", "at_least_5_examples",
                        "grammar_accuracy", "word_spacing"],
            "quality_min_score": 9,
        },
    ],

    # ── FROM ENGLISH (native) ──
    "en_to_ja": [
        {
            "prompt": "How do I say 'I love Japanese food' in Japanese? Teach me polite and casual versions",
            "target_lang": "ja",
            "checks": ["contains_kanji_or_kana", "has_tts_reading", "has_pronunciation",
                        "polite_and_casual", "has_explanation", "no_emojis", "word_spacing"],
            "quality_min_score": 8,
        },
        {
            "prompt": "Explain Japanese particles に, で, and を with simple examples",
            "target_lang": "ja",
            "checks": ["has_explanation", "contains_kana", "has_examples",
                        "particle_accuracy", "has_tts_reading"],
            "quality_min_score": 9,
        },
    ],
    "en_to_es": [
        {
            "prompt": "Teach me how to order food at a restaurant in Spanish. I want to order paella and wine",
            "target_lang": "es",
            "checks": ["has_spanish_text", "has_tts_reading", "has_pronunciation",
                        "has_cultural_context", "no_emojis", "word_spacing"],
            "quality_min_score": 8,
        },
        {
            "prompt": "What's the difference between 'ser' and 'estar'? Give me a mnemonic to remember",
            "target_lang": "es",
            "checks": ["has_explanation", "has_mnemonic", "grammar_accuracy",
                        "has_examples", "word_spacing"],
            "quality_min_score": 9,
        },
    ],

    # ── FROM JAPANESE (native) ──
    "ja_to_es": [
        {
            "prompt": "「すみません、道に迷いました」をスペイン語で教えてください。丁寧な言い方も",
            "target_lang": "es",
            "checks": ["has_spanish_text", "has_tts_reading", "formal_and_informal",
                        "has_explanation", "no_emojis", "word_spacing"],
            "quality_min_score": 8,
        },
        {
            "prompt": "スペイン語のserとestarの違いを教えてください。簡単な例文で",
            "target_lang": "es",
            "checks": ["has_spanish_text", "has_explanation", "has_examples",
                        "grammar_accuracy", "word_spacing"],
            "quality_min_score": 9,
        },
    ],
    "ja_to_en": [
        {
            "prompt": "お元気ですか？は英語で何ですか？polite versionで教えてください",
            "target_lang": "en",
            "checks": ["has_english_text", "has_tts_reading", "has_pronunciation",
                        "polite_version", "no_emojis", "word_spacing"],
            "quality_min_score": 8,
        },
        {
            "prompt": "日本語の敬語（Keigo）の基本を英語で説明してください",
            "target_lang": "en",
            "checks": ["has_explanation", "keigo_concepts", "has_examples",
                        "grammar_accuracy", "word_spacing"],
            "quality_min_score": 9,
        },
    ],
}

# Speed benchmarks (ms) — generous but strict
MAX_TTS_LATENCY_MS = 8000
MAX_LLM_FIRST_TOKEN_MS = 15000
MAX_TOTAL_RESPONSE_MS = 60000


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════

def api_post(path: str, data: dict, timeout: int = TIMEOUT) -> dict:
    """POST to API and return JSON response."""
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def api_get(path: str) -> dict:
    """GET from API."""
    req = urllib.request.Request(f"{BASE_URL}{path}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def has_kanji(text: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in text)


def has_kana(text: str) -> bool:
    return any("\u3040" <= c <= "\u309f" or "\u30a0" <= c <= "\u30ff" for c in text)


def has_latin(text: str) -> bool:
    return any("a" <= c.lower() <= "z" for c in text)


def count_emojis(text: str) -> int:
    """Count Unicode emojis in text."""
    emoji_re = re.compile(
        "[\u2600-\u27BF\U0001F000-\U0001FFFF\u200D]", re.UNICODE
    )
    return len(emoji_re.findall(text))


def check_word_spacing(text: str) -> list:
    """Check for joined words (the joinwords bug). Returns list of issues."""
    issues = []
    # Check: letter immediately after punctuation with no space
    for match in re.finditer(r'([.!?,;:])([A-Za-zÀ-ÿ\u0100-\u024F])', text):
        issues.append(f"Missing space after '{match.group(1)}' before '{match.group(2)}'")
    # Check: letter immediately before opening paren with no space
    for match in re.finditer(r'([A-Za-zÀ-ÿ\u0100-\u024F])\(', text):
        if match.group(1) not in (' ', '\n'):
            issues.append(f"Missing space before '(' after '{match.group(1)}'")
    return issues


# ══════════════════════════════════════════════════════════════
#  CHECK FUNCTIONS
# ══════════════════════════════════════════════════════════════

def check_multi_output(parsed: dict) -> dict:
    """Validate multi-output format structure."""
    results = {"pass": True, "issues": []}
    required_fields = ["text", "tts_reading", "pronunciation", "translation",
                       "explanation", "exercise"]
    for field in required_fields:
        if not parsed.get(field):
            results["issues"].append(f"Missing field: {field}")
            results["pass"] = False
    return results


def check_no_emojis(text: str) -> dict:
    results = {"pass": True, "issues": []}
    emoji_count = count_emojis(text)
    if emoji_count > 0:
        results["pass"] = False
        results["issues"].append(f"Found {emoji_count} emojis in output")
    return results


def check_word_spacing_result(text: str) -> dict:
    results = {"pass": True, "issues": check_word_spacing(text)}
    if results["issues"]:
        results["pass"] = False
    return results


def check_contains_kanji(text: str) -> dict:
    results = {"pass": has_kanji(text), "issues": []}
    if not results["pass"]:
        results["issues"].append("Expected kanji but none found")
    return results


def check_contains_kana(text: str) -> dict:
    results = {"pass": has_kana(text), "issues": []}
    if not results["pass"]:
        results["issues"].append("Expected kana but none found")
    return results


# ══════════════════════════════════════════════════════════════
#  TEST RUNNER
# ══════════════════════════════════════════════════════════════

def run_single_test(pair_name: str, test_data: dict, test_idx: int) -> dict:
    """Run a single teacher test and return results."""
    prompt = test_data["prompt"]
    target_lang = test_data["target_lang"]
    checks = test_data["checks"]
    min_score = test_data.get("quality_min_score", 7)

    print(f"\n{'='*60}")
    print(f"  TEST {pair_name}#{test_idx}: {prompt[:70]}...")
    print(f"  Target: {target_lang} | Min score: {min_score}/10")
    print(f"{'='*60}")

    result = {
        "pair": pair_name,
        "test_idx": test_idx,
        "prompt": prompt[:80],
        "target_lang": target_lang,
        "checks": {},
        "scores": {},
        "latency": {},
        "passed": False,
        "quality_score": 0,
    }

    # ── 1. Send chat request ──
    t0 = time.time()
    try:
        response = api_post("/api/chat", {
            "messages": [
                {"role": "user", "content": f"{prompt}\n[User language: {pair_name.split('_to_')[0]}]"}
            ],
            "mode": "teacher",
            "target_lang": target_lang,
            "n_predict": 512,
            "temperature": 0.3,
            "stream": False,
        })
    except Exception as e:
        result["checks"]["api_call"] = {"pass": False, "issues": [str(e)]}
        return result

    llm_time_ms = (time.time() - t0) * 1000
    result["latency"]["llm_total_ms"] = round(llm_time_ms)

    if "error" in response:
        result["checks"]["api_call"] = {"pass": False, "issues": [response["error"]]}
        return result

    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
    parsed = response.get("parsed", {})

    # ── 2. Multi-output format ──
    result["checks"]["multi_output"] = check_multi_output(parsed)

    # ── 3. No emojis ──
    all_text = " ".join(parsed.values()) if parsed else content
    result["checks"]["no_emojis"] = check_no_emojis(all_text)

    # ── 4. Word spacing fix ──
    tts_reading = parsed.get("tts_reading", "")
    pronunciation = parsed.get("pronunciation", "")
    explanation = parsed.get("explanation", "")
    result["checks"]["word_spacing_tts"] = check_word_spacing_result(tts_reading)
    result["checks"]["word_spacing_pron"] = check_word_spacing_result(pronunciation)
    result["checks"]["word_spacing_expl"] = check_word_spacing_result(explanation)

    # ── 5. Specific checks ──
    if "contains_kanji" in checks:
        result["checks"]["contains_kanji"] = check_contains_kanji(parsed.get("text", content))
    if "contains_kanji_or_kana" in checks:
        text = parsed.get("text", content)
        r = {"pass": has_kanji(text) or has_kana(text), "issues": []}
        if not r["pass"]:
            r["issues"].append("Expected kanji or kana but none found")
        result["checks"]["contains_kanji_or_kana"] = r
    if "formal_register" in checks:
        # Check if explanation mentions formal/polite forms
        expl = parsed.get("explanation", "").lower()
        r = {"pass": any(w in expl for w in ["formal", "polite", "丁寧", "です", "ます"]),
             "issues": []}
        if not r["pass"]:
            r["issues"].append("Explanation should mention formal/polite register")
        result["checks"]["formal_register"] = r
    if "has_cultural_context" in checks:
        expl = parsed.get("explanation", "").lower()
        cultural_words = ["culture", "cultural", "custom", "japan", "japanese", "etiquette",
                          "used in", "common in", "tradition"]
        r = {"pass": any(w in expl for w in cultural_words), "issues": []}
        if not r["pass"]:
            r["issues"].append("Explanation should include cultural context")
        result["checks"]["cultural_context"] = r
    if "has_exercise" in checks:
        r = {"pass": bool(parsed.get("exercise", "").strip()), "issues": []}
        if not r["pass"]:
            r["issues"].append("No exercise provided")
        result["checks"]["has_exercise"] = r
    if "has_examples" in checks:
        expl = parsed.get("explanation", "")
        r = {"pass": expl.count("e.g.") >= 1 or expl.count("例") >= 1 or
             expl.count("example") >= 1 or "for example" in expl.lower(),
             "issues": []}
        if not r["pass"]:
            r["issues"].append("Explanation should include examples")
        result["checks"]["has_examples"] = r
    if "polite_and_casual" in checks:
        all_text = " ".join(parsed.values())
        polite_words = ["polite", "formal", "丁寧", "です", "ます"]
        casual_words = ["casual", "informal", "casual form", "informal form"]
        r = {"pass": any(w in all_text.lower() for w in polite_words) and
             any(w in all_text.lower() for w in casual_words),
             "issues": []}
        if not r["pass"]:
            r["issues"].append("Should explain both polite and casual forms")
        result["checks"]["polite_casual"] = r
    if "polite_version" in checks:
        all_text = " ".join(parsed.values()).lower()
        r = {"pass": any(w in all_text for w in ["polite", "formal", "could you"]),
             "issues": []}
        if not r["pass"]:
            r["issues"].append("Should provide polite version")
        result["checks"]["polite_version"] = r
    if "grammar_accuracy" in checks:
        # Basic: explanation exists and is non-trivial
        expl = parsed.get("explanation", "")
        r = {"pass": len(expl) > 50, "issues": []}
        if not r["pass"]:
            r["issues"].append("Explanation too short for grammar explanation")
        result["checks"]["grammar_accuracy"] = r
    if "at_least_5_examples" in checks:
        expl = parsed.get("explanation", "")
        # Count bullet points or numbered items
        import re
        bullets = len(re.findall(r'[\-•]\s', expl))
        numbers = len(re.findall(r'\d+[\.\)]\s', expl))
        r = {"pass": bullets + numbers >= 5, "issues": []}
        if not r["pass"]:
            r["issues"].append(f"Only {bullets + numbers} examples found, need ≥5")
        result["checks"]["examples_count"] = r
    if "particle_accuracy" in checks:
        expl = parsed.get("explanation", "")
        particles = ["に", "で", "を"]
        r = {"pass": all(p in expl for p in particles), "issues": []}
        if not r["pass"]:
            missing = [p for p in particles if p not in expl]
            r["issues"].append(f"Missing particles in explanation: {missing}")
        result["checks"]["particle_accuracy"] = r
    if "formal_and_informal" in checks:
        all_text = " ".join(parsed.values()).lower()
        r = {"pass": any(w in all_text for w in ["formal", "informal", "formal", "casual"]),
             "issues": []}
        if not r["pass"]:
            r["issues"].append("Should provide both formal and informal translations")
        result["checks"]["formal_informal"] = r
    if "keigo_concepts" in checks:
        all_text = " ".join(parsed.values()).lower()
        r = {"pass": any(w in all_text for w in ["keigo", "honorific", "humble", "respectful",
                                                  "sonkeigo", "kenjougo", "teineigo"]),
             "issues": []}
        if not r["pass"]:
            r["issues"].append("Should explain keigo concepts")
        result["checks"]["keigo_concepts"] = r
    if "has_mnemonic" in checks:
        all_text = " ".join(parsed.values()).lower()
        r = {"pass": any(w in all_text for w in ["remember", "mnemonic", "tip", "trick",
                                                  "think of", "helps to"]),
             "issues": []}
        if not r["pass"]:
            r["issues"].append("Should include a mnemonic or memory trick")
        result["checks"]["has_mnemonic"] = r

    # ── 6. TTS latency test ──
    tts_text = parsed.get("tts_reading") or parsed.get("text") or content
    if tts_text:
        t_tts = time.time()
        try:
            tts_resp = urllib.request.urlopen(
                urllib.request.Request(
                    f"{BASE_URL}/api/tts",
                    data=json.dumps({"text": tts_text, "lang": target_lang}).encode(),
                    headers={"Content-Type": "application/json"},
                ),
                timeout=30
            )
            wav_data = tts_resp.read()
            tts_time_ms = (time.time() - t_tts) * 1000
            result["latency"]["tts_ms"] = round(tts_time_ms)
            result["latency"]["tts_size_bytes"] = len(wav_data)
            result["checks"]["tts_success"] = {"pass": len(wav_data) > 100, "issues": []}
            result["checks"]["tts_latency"] = {
                "pass": tts_time_ms < MAX_TTS_LATENCY_MS,
                "issues": [f"TTS took {round(tts_time_ms)}ms (max {MAX_TTS_LATENCY_MS}ms)"]
                if tts_time_ms >= MAX_TTS_LATENCY_MS else []
            }
        except Exception as e:
            result["checks"]["tts_success"] = {"pass": False, "issues": [str(e)]}

    # ── 7. Scoring ──
    total_checks = len(result["checks"])
    passed_checks = sum(1 for c in result["checks"].values() if c["pass"])
    result["quality_score"] = round(passed_checks / total_checks * 10, 1) if total_checks > 0 else 0
    result["passed"] = result["quality_score"] >= min_score

    # Print results
    print(f"\n  Quality Score: {result['quality_score']}/10 "
          f"({'✅ PASS' if result['passed'] else '❌ FAIL'})")
    for name, check in result["checks"].items():
        icon = "✅" if check["pass"] else "❌"
        print(f"    {icon} {name}")
        for issue in check.get("issues", []):
            print(f"       └─ {issue}")
    if result["latency"]:
        print(f"  Latency: LLM={result['latency'].get('llm_total_ms', '?')}ms"
              f" | TTS={result['latency'].get('tts_ms', '?')}ms")

    return result


# ══════════════════════════════════════════════════════════════
#  MEMORY / SYSTEM CHECKS
# ══════════════════════════════════════════════════════════════

def check_system_resources() -> dict:
    """Check VRAM, RAM, cache stats before and after tests."""
    print("\n" + "=" * 60)
    print("  SYSTEM RESOURCE CHECK")
    print("=" * 60)
    try:
        stats = api_get("/api/stats")
        print(f"  GPU:       {stats.get('gpu_percent', '?')}%")
        print(f"  VRAM:      {stats.get('vram_used_mb', 0)/1024:.1f} GB / "
              f"{stats.get('vram_total_mb', 0)/1024:.1f} GB")
        print(f"  RAM:       {stats.get('ram_percent', '?')}%")
        print(f"  LLM:       {'✅ Connected' if stats.get('llama_connected') else '❌ Disconnected'}")
        print(f"  Tok/s:     {stats.get('tokens_per_sec', 0)}")
        return stats
    except Exception as e:
        print(f"  ⚠️ Could not get stats: {e}")
        return {}


# ══════════════════════════════════════════════════════════════
#  CACHE TEST
# ══════════════════════════════════════════════════════════════

def test_cache_effectiveness() -> dict:
    """Test that sending the same prompt twice uses cache."""
    print("\n" + "=" * 60)
    print("  CACHE EFFECTIVENESS TEST")
    print("=" * 60)

    prompt = "Enseñame a decir hola en japonés"
    data = {
        "messages": [{"role": "user", "content": f"{prompt}\n[User language: es]"}],
        "mode": "teacher",
        "target_lang": "ja",
        "stream": False,
    }

    # First call — should be cache miss
    t1 = time.time()
    r1 = api_post("/api/chat", data)
    time1 = (time.time() - t1) * 1000
    cached1 = r1.get("cached", False)

    # Second call — should be cache hit
    t2 = time.time()
    r2 = api_post("/api/chat", data)
    time2 = (time.time() - t2) * 1000
    cached2 = r2.get("cached", False)

    result = {
        "first_call_ms": round(time1),
        "second_call_ms": round(time2),
        "first_cached": cached1,
        "second_cached": cached2,
        "speedup": round(time1 / time2, 1) if time2 > 0 else 0,
        "pass": cached2 and time2 < time1,
    }

    print(f"  First call:  {result['first_call_ms']}ms (cached: {cached1})")
    print(f"  Second call: {result['second_call_ms']}ms (cached: {cached2})")
    print(f"  Speedup:     {result['speedup']}x")
    print(f"  Result:      {'✅ PASS' if result['pass'] else '❌ FAIL'}")

    return result


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   🎓 ALEX VOICE — E2E TEACHER TEST SUITE               ║")
    print("║   v3.3.1 — Exhaustive from ALL 3 source languages      ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # Check server is running
    try:
        api_get("/api/stats")
        print("\n✅ Server is running at", BASE_URL)
    except Exception:
        print(f"\n❌ Server not running at {BASE_URL}")
        print("   Start it first: python3 server.py --port 3000")
        sys.exit(1)

    # System resources before
    stats_before = check_system_resources()

    # Run all test groups
    all_results = []
    for pair_name, tests in TEST_PROMPTS.items():
        for idx, test_data in enumerate(tests, 1):
            result = run_single_test(pair_name, test_data, idx)
            all_results.append(result)

    # Cache effectiveness test
    cache_result = test_cache_effectiveness()

    # System resources after
    stats_after = check_system_resources()

    # ── Summary ──
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " TEACHER E2E — FINAL RESULTS".center(58) + "║")
    print("╠" + "═" * 58 + "╣")

    total = len(all_results)
    passed = sum(1 for r in all_results if r["passed"])
    avg_score = sum(r["quality_score"] for r in all_results) / total if total > 0 else 0

    print(f"║  Tests: {passed}/{total} passed  |  Avg score: {avg_score:.1f}/10".ljust(58) + "║")
    print(f"║  Cache: {'✅ Working' if cache_result['pass'] else '❌ Not working'}".ljust(58) + "║")

    # Per-language breakdown
    pairs = {}
    for r in all_results:
        p = r["pair"]
        if p not in pairs:
            pairs[p] = {"total": 0, "passed": 0, "scores": []}
        pairs[p]["total"] += 1
        if r["passed"]:
            pairs[p]["passed"] += 1
        pairs[p]["scores"].append(r["quality_score"])

    for pair, data in pairs.items():
        avg = sum(data["scores"]) / len(data["scores"])
        icon = "✅" if data["passed"] == data["total"] else "⚠️"
        print(f"║  {icon} {pair}: {data['passed']}/{data['total']} "
              f"(avg {avg:.1f}/10)".ljust(58) + "║")

    # VRAM check
    if stats_before.get("vram_used_mb") and stats_after.get("vram_used_mb"):
        delta = (stats_after["vram_used_mb"] - stats_before["vram_used_mb"]) / 1024
        vram_ok = delta < 0.5  # Should not leak more than 500MB
        print(f"║  VRAM delta: {delta:+.1f} GB {'✅' if vram_ok else '⚠️ LEAK?'}".ljust(58) + "║")

    print("╚" + "═" * 58 + "╝")

    # Write results to JSON
    output_path = Path(__file__).parent / "results_teacher.json"
    with open(output_path, "w") as f:
        json.dump({
            "suite": "teacher",
            "total": total,
            "passed": passed,
            "avg_score": avg_score,
            "cache": cache_result,
            "results": all_results,
            "stats_before": stats_before,
            "stats_after": stats_after,
        }, f, indent=2, default=str)
    print(f"\n📄 Results saved to {output_path}")

    # Exit code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
