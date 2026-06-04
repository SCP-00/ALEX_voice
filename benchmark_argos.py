#!/usr/bin/env python3
"""Benchmark argos-based translator (port 3003) with 8 languages."""

import json, sys, time, urllib.request, urllib.error
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TRANS_HOST = "http://localhost:3003"
RESULTS = []

def log(msg):
    print("  " + msg)

def test_translate(text, from_lang, to_lang):
    """Test argos translation via translator server."""
    t0 = time.time()
    try:
        data = json.dumps({"text": text, "from_lang": from_lang, "to_lang": to_lang}).encode()
        req = urllib.request.Request(TRANS_HOST + "/api/translate", data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read().decode())
        elapsed = time.time() - t0
        if resp.get("error"):
            return {"time": round(elapsed, 3), "error": resp["error"], "status": "ERROR"}
        return {
            "time": round(elapsed, 3),
            "translation_time_ms": resp.get("translation_time_ms", 0),
            "translation": resp.get("translation", ""),
            "status": "OK",
            "from": resp.get("from_lang", from_lang),
            "to": resp.get("to_lang", to_lang),
        }
    except Exception as e:
        return {"time": round(time.time() - t0, 3), "error": str(e)[:100], "status": "ERROR"}

# ── 8-LANGUAGE TRANSLATION MATRIX ──
# Test texts in each language
TEXTS = {
    "en": "Hello, how are you today? I hope you're having a wonderful day.",
    "es": "Hola, como estas hoy? Espero que tengas un dia maravilloso.",
    "ja": "Konnichiwa, genki desu ka? Suteki na ichinichi wo sugoshiteimasu you ni.",
    "fr": "Bonjour, comment allez-vous aujourd'hui? J'espere que vous passez une excellente journee.",
    "ko": "Annyeonghaseyo, oneul eotteoke jinaeseyo? Areumdaun haruga doesigi barabnida.",
    "zh": "Ni hao, jin tian ni hao ma? Xi wang ni you yi ge mei hao de yi tian.",
    "de": "Hallo, wie geht es Ihnen heute? Ich hoffe, Sie haben einen wunderbaren Tag.",
    "pt": "Ola, como voce esta hoje? Espero que voce esteja tendo um dia maravilhoso.",
}

# All pairs to test (from -> to)
ALL_LANGS = ["en", "es", "ja", "fr", "ko", "zh", "de", "pt"]
TEST_PAIRS = []

# Test all combinations of the 3 core languages (EN, ES, JA)
for src in ["en", "es", "ja"]:
    for tgt in ["en", "es", "ja"]:
        if src != tgt:
            TEST_PAIRS.append((src, tgt))

# Test FR with EN, ES, JA
for src in ["en", "es", "ja"]:
    TEST_PAIRS.append((src, "fr"))
    TEST_PAIRS.append(("fr", src))

# Test a few KO, ZH, DE, PT combos
for src in ["en", "es"]:
    for tgt in ["ko", "zh", "de", "pt"]:
        TEST_PAIRS.append((src, tgt))

log("=" * 60)
log("ARGOS TRANSLATOR BENCHMARK — 8 Idiomas")
log("Date: " + datetime.now().isoformat())
log("=" * 60)

# Verify server
try:
    req = urllib.request.Request(TRANS_HOST + "/api/status")
    with urllib.request.urlopen(req, timeout=3) as r:
        status = json.loads(r.read().decode())
        log("Server: OK (Qwen3 loaded: " + str(status.get("qwen3_loaded", False)) + ")")
        log("Langs: " + str(status.get("languages", [])))
except Exception as e:
    log("Server NOT FOUND: " + str(e))
    sys.exit(1)

log("")
log("Testing " + str(len(TEST_PAIRS)) + " translation pairs...")
log("")

for src, tgt in TEST_PAIRS:
    text = TEXTS.get(src, TEXTS["en"])
    name = src.upper() + "->" + tgt.upper()
    log("[" + name + "] " + text[:50] + "...")

    r = test_translate(text, src, tgt)

    if r["status"] == "OK":
        trans_preview = r.get("translation", "")[:60]
        log("  OK: " + str(round(r["time"], 3)) + "s | " + trans_preview)
    else:
        log("  FAIL: " + r.get("error", ""))

    RESULTS.append({
        "pair": name,
        "from": src,
        "to": tgt,
        "time_s": r.get("time", 0),
        "translation_time_ms": r.get("translation_time_ms", 0),
        "translation_preview": (r.get("translation", "") or "")[:80],
        "status": r["status"],
        "pivot": False,
    })

    # Also mark pivot translations (es<->ja)
    if (src == "es" and tgt == "ja") or (src == "ja" and tgt == "es"):
        RESULTS[-1]["pivot"] = True

# ── SUMMARY ──
log("")
log("=" * 60)
log("SUMMARY")
log("=" * 60)

total = len(RESULTS)
ok = sum(1 for r in RESULTS if r["status"] == "OK")
fail = total - ok
avg_time = sum(r["time_s"] for r in RESULTS if r["status"] == "OK") / max(ok, 1)
pivot_tests = [r for r in RESULTS if r.get("pivot")]
pivot_ok = sum(1 for r in pivot_tests if r["status"] == "OK")

log("Total: " + str(total) + " | OK: " + str(ok) + " | Fail: " + str(fail))
log("Avg time: " + str(round(avg_time, 3)) + "s")
log("Pivot (es<->ja): " + str(pivot_ok) + "/" + str(len(pivot_tests)) + " OK")

# Per-language stats
log("")
log("--- By source language ---")
for lang in ALL_LANGS:
    lang_tests = [r for r in RESULTS if r["from"] == lang]
    lang_ok = sum(1 for r in lang_tests if r["status"] == "OK")
    lang_avg = sum(r["time_s"] for r in lang_tests if r["status"] == "OK") / max(lang_ok, 1)
    log("  " + lang.upper() + ": " + str(lang_ok) + "/" + str(len(lang_tests)) +
        " OK, avg " + str(round(lang_avg, 3)) + "s")

# Save
with open("benchmark_results/benchmark_argos_results.json", "w", encoding="utf-8") as f:
    json.dump(RESULTS, f, ensure_ascii=False, indent=2)

log("")
log("Results saved to benchmark_results/benchmark_argos_results.json")
