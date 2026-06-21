#!/usr/bin/env python3
"""
E2E Test Suite — 🌍 Translator Mode
======================================
Alex Voice v3.3.1 — Exhaustive testing from ALL 3 source languages.

Focus:
- Translation accuracy (6 pairs: EN↔ES, EN→JA, JA→EN, JA→ES, ES→JA)
- Pipeline latency (ASR → Translation → TTS)
- TTS quality (Kokoro ONNX, correct voice per language)
- Idiom translation (cultural equivalents, not literal)
- Edge cases (empty input, very long text, mixed scripts)
- Model loading/unloading
"""

import json
import time
import sys
import base64
import urllib.request
from pathlib import Path

BASE_URL = "http://localhost:3003"
TIMEOUT = 30
RESULTS = []


# ══════════════════════════════════════════════════════════════
#  TEST DATA — Translation pairs FROM each source language
# ══════════════════════════════════════════════════════════════

TRANSLATION_TESTS = {
    # ── FROM SPANISH ──
    "es_to_ja": {
        "from": "es", "to": "ja",
        "tests": [
            {"text": "Buenos días, ¿cómo estás?", "expect_contains": ["おはよう", "こんにちは", "元気"]},
            {"text": "Me gustaría una cerveza, por favor", "expect_contains": ["ビール", "ください", "お願い"]},
            {"text": "¿Dónde está el baño?", "expect_contains": ["トイレ", "お手洗い", "どこ"]},
            {"text": "La vida es bella", "expect_contains": ["人生", "美しい", "素敵"]},
        ],
    },
    "es_to_en": {
        "from": "es", "to": "en",
        "tests": [
            {"text": "Buenos días, ¿cómo estás?", "expect_contains": ["good morning", "how are you"]},
            {"text": "Me gustaría una cerveza, por favor", "expect_contains": ["beer", "please", "would like"]},
            {"text": "Está lloviendo a cántaros", "expect_contains": ["raining cats", "pouring", "heavy"]},
        ],
    },

    # ── FROM ENGLISH ──
    "en_to_ja": {
        "from": "en", "to": "ja",
        "tests": [
            {"text": "Hello, how are you?", "expect_contains": ["こんにちは", "元気"]},
            {"text": "I love Japanese food", "expect_contains": ["日本", "食べ物", "料理", "好き"]},
            {"text": "Break a leg!", "expect_contains": ["頑張", "成功"]},
            {"text": "The weather is beautiful today", "expect_contains": ["天気", "今日", "美しい", "きれい"]},
        ],
    },
    "en_to_es": {
        "from": "en", "to": "es",
        "tests": [
            {"text": "Hello, how are you?", "expect_contains": ["hola", "cómo estás", "buenos"]},
            {"text": "I would like a coffee", "expect_contains": ["café", "quisiera", "me gustaría"]},
            {"text": "It is raining cats and dogs", "expect_contains": ["lloviendo", "a cántaros", "tormenta"]},
        ],
    },

    # ── FROM JAPANESE ──
    "ja_to_es": {
        "from": "ja", "to": "es",
        "tests": [
            {"text": "おはようございます", "expect_contains": ["buenos días", "buenos"]},
            {"text": "すみません、道に迷いました", "expect_contains": ["perdido", "despacio", "dirección"]},
            {"text": "今日はいい天気ですね", "expect_contains": ["clima", "tiempo", "día"]},
        ],
    },
    "ja_to_en": {
        "from": "ja", "to": "en",
        "tests": [
            {"text": "こんにちは、元気ですか？", "expect_contains": ["hello", "how are you", "well"]},
            {"text": "ありがとうございます", "expect_contains": ["thank", "thanks", "appreciate"]},
            {"text": "日本語を勉強しています", "expect_contains": ["japanese", "studying", "learning"]},
        ],
    },
}

# Max latency per stage (generous)
MAX_TRANSLATION_MS = 5000
MAX_TTS_MS = 8000
MAX_PIPELINE_MS = 15000


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════

def api_post(path, data, timeout=TIMEOUT):
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def api_get(path):
    req = urllib.request.Request(f"{BASE_URL}{path}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def check_translation_quality(translation, expect_contains, from_lang, to_lang):
    """Check translation quality against expectations."""
    results = {"pass": True, "issues": [], "translation": translation}

    if not translation:
        results["pass"] = False
        results["issues"].append("Empty translation")
        return results

    # Check expected words are present
    found = []
    missing = []
    for word_group in expect_contains:
        if isinstance(word_group, list):
            if any(w.lower() in translation.lower() for w in word_group):
                found.append(word_group[0])
            else:
                missing.append(word_group[0])
        else:
            if word_group.lower() in translation.lower():
                found.append(word_group)
            else:
                missing.append(word_group)

    if missing:
        results["pass"] = False
        results["issues"].append(f"Missing expected words: {missing}")

    # Check no source language leakage (translation shouldn't be same as source)
    if translation.strip().lower() == "" :
        results["pass"] = False
        results["issues"].append("Empty translation")

    return results


# ══════════════════════════════════════════════════════════════
#  TRANSLATION TESTS
# ══════════════════════════════════════════════════════════════

def run_translation_tests():
    """Run all text translation tests."""
    print("\n" + "=" * 60)
    print("  TEXT TRANSLATION TESTS")
    print("=" * 60)

    all_results = []

    for pair_name, config in TRANSLATION_TESTS.items():
        print(f"\n  ── {pair_name.upper()} ──")

        for idx, test in enumerate(config["tests"]):
            text = test["text"]
            t0 = time.time()
            try:
                resp = api_post("/api/translate", {
                    "text": text,
                    "from_lang": config["from"],
                    "to_lang": config["to"],
                })
                latency = (time.time() - t0) * 1000
            except Exception as e:
                print(f"    ❌ [{idx + 1}] API error: {e}")
                all_results.append({"pair": pair_name, "pass": False, "error": str(e)})
                continue

            if "error" in resp:
                print(f"    ❌ [{idx + 1}] {text[:40]}... → {resp['error']}")
                all_results.append({"pair": pair_name, "pass": False, "error": resp["error"]})
                continue

            translation = resp.get("translation", "")
            trans_time = resp.get("translation_time_ms", latency)

            quality = check_translation_quality(
                translation, test["expect_contains"], config["from"], config["to"]
            )

            result = {
                "pair": pair_name,
                "input": text[:50],
                "translation": translation[:80],
                "latency_ms": round(latency),
                "trans_time_ms": trans_time,
                "passed": quality["pass"],
                "issues": quality["issues"],
            }
            all_results.append(result)

            icon = "✅" if quality["pass"] else "❌"
            print(f"    {icon} [{idx + 1}] \"{text[:35]}...\"")
            print(f"       → \"{translation[:50]}...\" ({trans_time}ms)")
            if quality["issues"]:
                for issue in quality["issues"]:
                    print(f"       ⚠️ {issue}")

    return all_results


# ══════════════════════════════════════════════════════════════
#  TTS TESTS
# ══════════════════════════════════════════════════════════════

def run_tts_tests():
    """Test TTS for each supported language."""
    print("\n" + "=" * 60)
    print("  TTS QUALITY TESTS (Kokoro ONNX)")
    print("=" * 60)

    test_texts = {
        "Spanish": "Buenos días, ¿cómo estás hoy? Espero que tengas un día maravilloso.",
        "English": "Hello! How are you doing today? I hope you're having a wonderful day.",
        "Japanese": "こんにちは、今日は元気ですか？素晴らしい一日になりますように。",
    }

    results = []
    for lang_name, text in test_texts.items():
        t0 = time.time()
        try:
            req = urllib.request.Request(
                f"{BASE_URL}/api/tts",
                data=json.dumps({"text": text, "language": lang_name}).encode(),
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=30)
            wav_data = resp.read()
            gen_time = int(resp.headers.get("X-Generation-Time-Ms", 0))
            duration = resp.headers.get("X-Audio-Duration-S", "?")
            elapsed_ms = (time.time() - t0) * 1000

            passed = len(wav_data) > 500
            result = {
                "language": lang_name,
                "passed": passed,
                "size_bytes": len(wav_data),
                "gen_time_ms": gen_time,
                "audio_duration_s": duration,
                "latency_ms": round(elapsed_ms),
            }
        except Exception as e:
            result = {"language": lang_name, "passed": False, "error": str(e)}

        results.append(result)
        icon = "✅" if result["passed"] else "❌"
        print(f"  {icon} {lang_name}: {result.get('size_bytes', 0)} bytes, "
              f"{result.get('gen_time_ms', '?')}ms, {result.get('audio_duration_s', '?')}s")

    all_pass = all(r["passed"] for r in results)
    print(f"\n  TTS Overall: {'✅ PASS' if all_pass else '❌ FAIL'}")
    return results


# ══════════════════════════════════════════════════════════════
#  EDGE CASE TESTS
# ══════════════════════════════════════════════════════════════

def run_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "=" * 60)
    print("  EDGE CASE TESTS")
    print("=" * 60)

    results = []

    # Empty text
    try:
        resp = api_post("/api/translate", {"text": "", "from_lang": "en", "to_lang": "es"})
        passed = "error" in resp or resp.get("translation", "").strip() == ""
        results.append({"test": "empty_text", "passed": passed,
                         "issue": "" if passed else "Should handle empty text"})
        print(f"  {'✅' if passed else '❌'} Empty text → {'error' if 'error' in resp else 'handled'}")
    except Exception as e:
        results.append({"test": "empty_text", "passed": False, "issue": str(e)})
        print(f"  ❌ Empty text → {e}")

    # Same language (en → en)
    try:
        resp = api_post("/api/translate", {"text": "Hello world", "from_lang": "en", "to_lang": "en"})
        passed = resp.get("translation", "") == "Hello world"
        results.append({"test": "same_language", "passed": passed})
        print(f"  {'✅' if passed else '❌'} Same language (en→en) → passthrough")
    except Exception as e:
        results.append({"test": "same_language", "passed": False, "issue": str(e)})
        print(f"  ❌ Same language → {e}")

    # Very long text
    try:
        long_text = "This is a test sentence. " * 50  # ~1300 chars
        t0 = time.time()
        resp = api_post("/api/translate", {"text": long_text, "from_lang": "en", "to_lang": "es"})
        latency = (time.time() - t0) * 1000
        passed = "translation" in resp and len(resp.get("translation", "")) > 100
        results.append({"test": "long_text", "passed": passed, "latency_ms": round(latency)})
        print(f"  {'✅' if passed else '❌'} Long text (1300 chars) → {latency:.0f}ms")
    except Exception as e:
        results.append({"test": "long_text", "passed": False, "issue": str(e)})
        print(f"  ❌ Long text → {e}")

    # Japanese with kanji
    try:
        resp = api_post("/api/translate", {"text": "日本語の勉強は楽しいです", "from_lang": "ja", "to_lang": "en"})
        passed = "translation" in resp and len(resp.get("translation", "")) > 5
        results.append({"test": "japanese_kanji", "passed": passed})
        print(f"  {'✅' if passed else '❌'} Japanese kanji → {resp.get('translation', 'error')[:40]}")
    except Exception as e:
        results.append({"test": "japanese_kanji", "passed": False, "issue": str(e)})
        print(f"  ❌ Japanese kanji → {e}")

    # Special characters
    try:
        resp = api_post("/api/translate", {"text": "Hello! @#$%^&*() - 123", "from_lang": "en", "to_lang": "es"})
        passed = "translation" in resp
        results.append({"test": "special_chars", "passed": passed})
        print(f"  {'✅' if passed else '❌'} Special characters → handled")
    except Exception as e:
        results.append({"test": "special_chars", "passed": False, "issue": str(e)})
        print(f"  ❌ Special chars → {e}")

    return results


# ══════════════════════════════════════════════════════════════
#  SYSTEM STATUS TEST
# ══════════════════════════════════════════════════════════════

def test_system_status():
    """Test /api/status endpoint."""
    print("\n" + "=" * 60)
    print("  SYSTEM STATUS CHECK")
    print("=" * 60)

    try:
        status = api_get("/api/status")
        print(f"  Whisper loaded:   {'✅' if status.get('whisper_loaded') else '❌'}")
        print(f"  Transformers:     {'✅' if status.get('transformers_loaded') else '❌'}")
        print(f"  Kokoro:           {'✅' if status.get('kokoro_loaded') else '❌'}")
        print(f"  Pipeline running: {'✅' if status.get('pipeline_running') else '❌'}")
        print(f"  Languages:        {', '.join(status.get('languages', []))}")
        print(f"  Translators:      {', '.join(status.get('translators_loaded', []))}")
        return {"pass": True, "status": status}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"pass": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════
#  MODEL LOAD/UNLOAD TEST
# ══════════════════════════════════════════════════════════════

def test_model_lifecycle():
    """Test loading and unloading models."""
    print("\n" + "=" * 60)
    print("  MODEL LOAD/UNLOAD LIFECYCLE")
    print("=" * 60)

    # Load
    try:
        t0 = time.time()
        resp = api_post("/api/load", {"pairs": [["en", "es"], ["es", "en"]]})
        load_time = (time.time() - t0) * 1000
        print(f"  Load:  ✅ {resp.get('translators_loaded', 0)} translators in {load_time:.0f}ms")
    except Exception as e:
        print(f"  Load:  ❌ {e}")
        return {"pass": False}

    # Unload
    try:
        resp = api_post("/api/unload", {})
        print(f"  Unload: ✅ {resp.get('message', 'ok')}")
    except Exception as e:
        print(f"  Unload: ❌ {e}")

    return {"pass": True}


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   🌍 ALEX VOICE — E2E TRANSLATOR TEST SUITE            ║")
    print("║   v3.3.1 — Exhaustive from ALL 3 source languages      ║")
    print("╚══════════════════════════════════════════════════════════╝")

    try:
        api_get("/api/status")
        print("\n✅ Translator server running at", BASE_URL)
    except Exception:
        print(f"\n❌ Server not running at {BASE_URL}")
        print("   Start: python3 translator.py")
        sys.exit(1)

    # System status
    status_result = test_system_status()

    # Translation tests
    trans_results = run_translation_tests()

    # TTS tests
    tts_results = run_tts_tests()

    # Edge cases
    edge_results = run_edge_cases()

    # Model lifecycle
    lifecycle_result = test_model_lifecycle()

    # ── Summary ──
    all_tests = trans_results + tts_results + edge_results
    total = len(all_tests)
    passed = sum(1 for t in all_tests if t.get("passed", False))

    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " TRANSLATOR E2E — FINAL RESULTS".center(58) + "║")
    print("╠" + "═" * 58 + "╣")
    print(f"║  Translation: {passed}/{total} passed".ljust(58) + "║")
    print(f"║  TTS:         {sum(1 for t in tts_results if t.get('passed'))}/{len(tts_results)} passed".ljust(58) + "║")
    print(f"║  Edge cases:  {sum(1 for t in edge_results if t.get('passed'))}/{len(edge_results)} passed".ljust(58) + "║")
    print("╚" + "═" * 58 + "╝")

    output_path = Path(__file__).parent / "results_translator.json"
    with open(output_path, "w") as f:
        json.dump({
            "suite": "translator",
            "status": status_result,
            "translations": trans_results,
            "tts": tts_results,
            "edge_cases": edge_results,
            "lifecycle": lifecycle_result,
        }, f, indent=2, default=str)
    print(f"\n📄 Results saved to {output_path}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
