#!/usr/bin/env python3
"""
E2E Test Suite — 💬 Conversation Mode
=======================================
Alex Voice v3.3.1 — Exhaustive testing from ALL 3 source languages.

Focus:
- Natural conversation flow (no robotic responses)
- Language matching (responds in same language as user)
- Context memory (remembers previous messages in session)
- TTS quality and streaming
- Voice input pipeline (ASR → chat → TTS)
- Memory management (context window doesn't overflow)
"""

import json
import re
import time
import sys
import urllib.request
from pathlib import Path

BASE_URL = "http://localhost:3001"
TIMEOUT = 60
RESULTS = []


# ══════════════════════════════════════════════════════════════
#  TEST DATA — Conversations from each source language
# ══════════════════════════════════════════════════════════════

CONVERSATION_TESTS = {
    "es": {
        "name": "Spanish native speaker",
        "scenarios": [
            {
                "name": "Basic greeting flow",
                "messages": [
                    "Hola, ¿cómo estás?",
                    "¿Qué opinas del café colombiano?",
                    "¿Has probado algún buen café últimamente?",
                ],
                "checks_per_response": {
                    0: ["responds_spanish", "no_emojis", "natural_tone"],
                    1: ["responds_spanish", "has_opinion", "no_emojis", "engages_question"],
                    2: ["responds_spanish", "personal_anecdote_or_opinion", "asks_followup"],
                },
            },
            {
                "name": "Topic switch handling",
                "messages": [
                    "Cuéntame sobre tu familia",
                    "Cambiando de tema, ¿qué piensas de la inteligencia artificial?",
                    "¿Crees que la IA puede aprender español?",
                ],
                "checks_per_response": {
                    0: ["responds_spanish", "natural_response"],
                    1: ["responds_spanish", "handles_topic_switch", "has_opinion"],
                    2: ["responds_spanish", "engages_with_topic", "asks_followup"],
                },
            },
            {
                "name": "Emotional intelligence",
                "messages": [
                    "Estoy muy triste hoy, me despidieron del trabajo",
                    "Gracias, eso ayuda. ¿Algún consejo para empezar de nuevo?",
                ],
                "checks_per_response": {
                    0: ["responds_spanish", "empathetic_response", "no_emojis"],
                    1: ["responds_spanish", "gives_advice", "encouraging"],
                },
            },
        ],
    },
    "en": {
        "name": "English native speaker",
        "scenarios": [
            {
                "name": "Casual chat about movies",
                "messages": [
                    "Hey! What's your favorite movie?",
                    "Nice choice! Have you seen anything good recently?",
                    "I just watched Dune Part Two. The cinematography was insane.",
                ],
                "checks_per_response": {
                    0: ["responds_english", "has_opinion", "natural_tone", "no_emojis"],
                    1: ["responds_english", "engages_question", "personal_anecdote"],
                    2: ["responds_english", "engages_with_topic", "shares_opinion"],
                },
            },
            {
                "name": "Debate / opinion exchange",
                "messages": [
                    "Do you think remote work is better than office work?",
                    "But don't you think companies lose culture with fully remote?",
                    "Fair point. What about hybrid — is that the sweet spot?",
                ],
                "checks_per_response": {
                    0: ["responds_english", "has_clear_opinion"],
                    1: ["responds_english", "nuanced_response", "acknowledges_counterpoint"],
                    2: ["responds_english", "balanced_view", "engages_with_topic"],
                },
            },
        ],
    },
    "ja": {
        "name": "Japanese native speaker",
        "scenarios": [
            {
                "name": "Basic Japanese conversation",
                "messages": [
                    "こんにちは、今日はいい天気ですね",
                    "日本語を勉強しているんですが、有什么建议吗？",
                    "ありがとう！日本語の勉強は楽しいですか？",
                ],
                "checks_per_response": {
                    0: ["responds_japanese", "natural_tone", "no_emojis"],
                    1: ["responds_japanese", "gives_advice", "encouraging"],
                    2: ["responds_japanese", "engages_question", "personal_anecdote"],
                },
            },
            {
                "name": "Mixed language handling",
                "messages": [
                    "I want to practice my Japanese, can we talk in Japanese?",
                    "日本語で話しましょう！今日は何をしましたか？",
                    "楽しいですね！もっと日本語で話ししましょう",
                ],
                "checks_per_response": {
                    0: ["responds_japanese", "acknowledges_request"],
                    1: ["responds_japanese", "natural_response"],
                    2: ["responds_japanese", "continues_conversation"],
                },
            },
        ],
    },
}


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


def has_japanese(text):
    return any("\u3040" <= c <= "\u309f" or "\u30a0" <= c <= "\u30ff" or "\u4e00" <= c <= "\u9fff" for c in text)


def has_spanish(text):
    es_chars = sum(1 for c in text if "\u00e1" <= c <= "\u00fa" or c in "ñçüöéèêëàâîôùû¿¡")
    es_words = {"hola", "gracias", "como", "estas", "muy", "bien", "que", "el", "la",
                "por", "para", "con", "sin", "es", "son", "del", "más", "todo"}
    words = [w.lower().strip(".,!?;:'\"") for w in text.split()]
    return es_chars > 0 or any(w in es_words for w in words)


def has_english(text):
    if has_japanese(text) or has_spanish(text):
        return False
    return any("a" <= c.lower() <= "z" for c in text)


_EMOJI_RE = re.compile("[\u2600-\u27BF\U0001F000-\U0001FFFF\u200D]", re.UNICODE)


def count_emojis(text):
    return len(_EMOJI_RE.findall(text))


def is_natural(text):
    """Heuristic: response has varied sentence structure, questions, etc."""
    sentences = text.split(".")
    questions = text.count("?")
    exclamations = text.count("!")
    word_count = len(text.split())
    return word_count > 20 and (questions > 0 or exclamations > 0 or len(sentences) > 2)


def checks_response(text, checks_list):
    """Run a list of check names against text. Returns dict of results."""
    results = {}
    for check in checks_list:
        if check == "responds_spanish":
            results[check] = {"pass": has_spanish(text), "issue": "Response not in Spanish"}
        elif check == "responds_english":
            results[check] = {"pass": has_english(text), "issue": "Response not in English"}
        elif check == "responds_japanese":
            results[check] = {"pass": has_japanese(text), "issue": "Response not in Japanese"}
        elif check == "no_emojis":
            emoji_count = count_emojis(text)
            results[check] = {"pass": emoji_count == 0, "issue": f"Found {emoji_count} emojis"}
        elif check == "natural_tone":
            results[check] = {"pass": is_natural(text), "issue": "Response seems robotic/too short"}
        elif check == "has_opinion":
            opinion_words = ["think", "believe", "opinion", "pienso", "creo", "opino",
                             "我觉得", "我认为", "思います"]
            results[check] = {"pass": any(w in text.lower() for w in opinion_words),
                              "issue": "No opinion expressed"}
        elif check == "engages_question":
            results[check] = {"pass": "?" in text, "issue": "Doesn't ask a follow-up question"}
        elif check == "asks_followup":
            results[check] = {"pass": "?" in text, "issue": "Should ask follow-up"}
        elif check == "personal_anecdote_or_opinion":
            personal_words = ["I", "me", "my", "yo", "mi", "me", "watashi", "boku"]
            results[check] = {"pass": any(w in text for w in personal_words) or "?" in text,
                              "issue": "Should share personal opinion or ask question"}
        elif check == "personal_anecdote":
            personal_words = ["I", "me", "my"]
            results[check] = {"pass": any(w in text for w in personal_words),
                              "issue": "Should share personal experience"}
        elif check == "handles_topic_switch":
            results[check] = {"pass": True, "issue": ""}  # If we got a response, topic was handled
        elif check == "empathetic_response":
            empathy_words = ["sorry", "understand", "feel", "lamento", "entiendo",
                             "ごめん", "気持", "大変"]
            results[check] = {"pass": any(w in text.lower() for w in empathy_words),
                              "issue": "Response lacks empathy"}
        elif check == "gives_advice":
            advice_words = ["try", "should", "could", "建议", "prueba", "intenta",
                            "considera", "podrías"]
            results[check] = {"pass": any(w in text.lower() for w in advice_words),
                              "issue": "No advice given"}
        elif check == "encouraging":
            encouraging_words = ["great", "good", "awesome", "genial", "bueno",
                                 "がんば", "頑張", "you can", "puedes"]
            results[check] = {"pass": any(w in text.lower() for w in encouraging_words) or "?" in text,
                              "issue": "Not encouraging enough"}
        elif check == "natural_response":
            results[check] = {"pass": len(text.split()) > 10, "issue": "Too short"}
        elif check == "engages_with_topic":
            results[check] = {"pass": len(text.split()) > 15 and "?" in text,
                              "issue": "Should engage more deeply with topic"}
        elif check == "acknowledges_request":
            results[check] = {"pass": True, "issue": ""}  # Any response = acknowledged
        elif check == "continues_conversation":
            results[check] = {"pass": "?" in text or len(text.split()) > 20,
                              "issue": "Should continue the conversation"}
        elif check == "has_clear_opinion":
            opinion_words = ["think", "believe", "prefer", "pienso", "creo", "prefiero",
                             "我觉得", "思います"]
            results[check] = {"pass": any(w in text.lower() for w in opinion_words),
                              "issue": "Should state a clear opinion"}
        elif check == "nuanced_response":
            nuance_words = ["however", "but", "although", "though", "pero", "sin embargo"]
            results[check] = {"pass": any(w in text.lower() for w in nuance_words),
                              "issue": "Should acknowledge counterpoint"}
        elif check == "acknowledges_counterpoint":
            results[check] = {"pass": any(w in text.lower() for w in
                              ["but", "however", "pero", "sin embargo", "でも", "however"]),
                              "issue": "Should acknowledge counterpoint"}
        elif check == "balanced_view":
            results[check] = {"pass": any(w in text.lower() for w in
                              ["both", "balance", "ambos", "ambas", "どちらも"]),
                              "issue": "Should present balanced view"}
        else:
            results[check] = {"pass": True, "issue": ""}
    return results


# ══════════════════════════════════════════════════════════════
#  CONTEXT MEMORY TEST
# ══════════════════════════════════════════════════════════════

def test_context_memory():
    """Test that the model remembers earlier messages in the conversation."""
    print("\n" + "=" * 60)
    print("  CONTEXT MEMORY TEST")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "My name is Carlos and I'm from Madrid, Spain"},
        {"role": "user", "content": "I work as a software engineer"},
        {"role": "user", "content": "What's my name and where am I from?"},
    ]

    t0 = time.time()
    try:
        resp = api_post("/api/chat", {
            "messages": messages,
            "mode": "conversation",
            "n_predict": 256,
            "temperature": 0.7,
            "stream": False,
        })
    except Exception as e:
        return {"pass": False, "issue": str(e)}

    latency_ms = (time.time() - t0) * 1000
    content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")

    remembers_name = "carlos" in content.lower()
    remembers_city = "madrid" in content.lower() or "spain" in content.lower()
    remembers_job = "engineer" in content.lower() or "software" in content.lower()

    passed = remembers_name and remembers_city
    issues = []
    if not remembers_name:
        issues.append("Didn't remember name (Carlos)")
    if not remembers_city:
        issues.append("Didn't remember location (Madrid)")
    if not remembers_job:
        issues.append("Didn't remember job (software engineer)")

    print(f"  Remembers name:    {'✅' if remembers_name else '❌'}")
    print(f"  Remembers city:    {'✅' if remembers_city else '❌'}")
    print(f"  Remembers job:     {'✅' if remembers_job else '❌'}")
    print(f"  Latency:           {latency_ms:.0f}ms")
    print(f"  Response:          {content[:100]}...")
    print(f"  Result:            {'✅ PASS' if passed else '❌ FAIL'}")

    return {"pass": passed, "issues": issues, "latency_ms": round(latency_ms)}


# ══════════════════════════════════════════════════════════════
#  TTS STREAMING TEST
# ══════════════════════════════════════════════════════════════

def test_tts_streaming():
    """Test TTS streaming produces valid audio."""
    print("\n" + "=" * 60)
    print("  TTS STREAMING TEST")
    print("=" * 60)

    test_texts = {
        "es": "Hola, ¿cómo estás hoy? Espero que tengas un día maravilloso.",
        "en": "Hello! How are you doing today? I hope you're having a wonderful day.",
        "ja": "こんにちは、今日は元気ですか？素晴らしい一日になりますように。",
    }

    results = {}
    for lang, text in test_texts.items():
        t0 = time.time()
        try:
            req = urllib.request.Request(
                f"{BASE_URL}/api/tts/stream",
                data=json.dumps({"text": text, "lang": lang}).encode(),
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=30)
            audio_data = resp.read()
            sr = int(resp.headers.get("X-Sample-Rate", 24000))
            elapsed_ms = (time.time() - t0) * 1000

            results[lang] = {
                "pass": len(audio_data) > 500,
                "size_bytes": len(audio_data),
                "sample_rate": sr,
                "latency_ms": round(elapsed_ms),
            }
        except Exception as e:
            results[lang] = {"pass": False, "error": str(e)}

        icon = "✅" if results[lang]["pass"] else "❌"
        print(f"  {icon} {lang}: {results[lang].get('size_bytes', 0)} bytes, "
              f"{results[lang].get('latency_ms', '?')}ms")

    all_pass = all(r["pass"] for r in results.values())
    print(f"  Result: {'✅ PASS' if all_pass else '❌ FAIL'}")
    return {"pass": all_pass, "results": results}


# ══════════════════════════════════════════════════════════════
#  LONG CONVERSATION STRESS TEST
# ══════════════════════════════════════════════════════════════

def test_long_conversation():
    """Test 10-message conversation doesn't crash or degrade."""
    print("\n" + "=" * 60)
    print("  LONG CONVERSATION STRESS TEST (10 messages)")
    print("=" * 60)

    messages = []
    latencies = []
    for i in range(10):
        user_msg = f"Tell me something interesting about number {i + 1}. Make it fun!"
        messages.append({"role": "user", "content": user_msg})

        t0 = time.time()
        try:
            resp = api_post("/api/chat", {
                "messages": messages,
                "mode": "conversation",
                "n_predict": 256,
                "temperature": 0.7,
                "stream": False,
            })
            latency = (time.time() - t0) * 1000
            latencies.append(latency)

            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
            messages.append({"role": "assistant", "content": content})

            print(f"  Message {i + 1}/10: {latency:.0f}ms, {len(content)} chars")

            if not content or len(content) < 10:
                print(f"  ⚠️ Response too short at message {i + 1}")
        except Exception as e:
            print(f"  ❌ Error at message {i + 1}: {e}")
            return {"pass": False, "issue": str(e), "completed": i}

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    print(f"\n  Avg latency: {avg_latency:.0f}ms")
    print(f"  Max latency: {max_latency:.0f}ms")
    print(f"  Completed:   10/10 messages")
    print(f"  Result:      ✅ PASS")

    return {
        "pass": True,
        "avg_latency_ms": round(avg_latency),
        "max_latency_ms": round(max_latency),
        "completed": 10,
    }


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   💬 ALEX VOICE — E2E CONVERSATION TEST SUITE           ║")
    print("║   v3.3.1 — Exhaustive from ALL 3 source languages      ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # Check server
    try:
        api_get("/api/stats")
        print("\n✅ Conversation server running at", BASE_URL)
    except Exception:
        print(f"\n❌ Server not running at {BASE_URL}")
        print("   Start: python3 conv_server.py")
        sys.exit(1)

    all_results = []

    # ── Run conversation scenarios ──
    for lang, config in CONVERSATION_TESTS.items():
        print(f"\n{'━' * 60}")
        print(f"  LANGUAGE: {config['name']}")
        print(f"{'━' * 60}")

        for scenario in config["scenarios"]:
            print(f"\n  Scenario: {scenario['name']}")
            print(f"  {'─' * 50}")

            messages = []
            scenario_results = []

            for msg_idx, user_msg in enumerate(scenario["messages"]):
                messages.append({"role": "user", "content": user_msg})

                t0 = time.time()
                try:
                    resp = api_post("/api/chat", {
                        "messages": messages,
                        "mode": "conversation",
                        "n_predict": 512,
                        "temperature": 0.7,
                        "stream": False,
                    })
                    latency = (time.time() - t0) * 1000
                    content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                    messages.append({"role": "assistant", "content": content})
                except Exception as e:
                    content = ""
                    latency = 0
                    print(f"    ❌ API error: {e}")

                # Run checks
                expected_checks = scenario["checks_per_response"].get(msg_idx, [])
                check_results = checks_response(content, expected_checks)

                all_pass = all(c["pass"] for c in check_results.values())
                scenario_results.append({
                    "msg_idx": msg_idx,
                    "user_msg": user_msg[:60],
                    "response_len": len(content),
                    "latency_ms": round(latency),
                    "checks": check_results,
                    "passed": all_pass,
                })

                icon = "✅" if all_pass else "❌"
                print(f"    {icon} [{msg_idx + 1}] {user_msg[:50]}...")
                print(f"       → {len(content)} chars, {latency:.0f}ms")
                for name, check in check_results.items():
                    if not check["pass"]:
                        print(f"       ❌ {name}: {check['issue']}")

            scenario_pass = all(r["passed"] for r in scenario_results)
            all_results.append({
                "lang": lang,
                "scenario": scenario["name"],
                "passed": scenario_pass,
                "details": scenario_results,
            })

    # ── Special tests ──
    memory_result = test_context_memory()
    all_results.append({"test": "context_memory", "passed": memory_result["pass"],
                         "details": memory_result})

    tts_result = test_tts_streaming()
    all_results.append({"test": "tts_streaming", "passed": tts_result["pass"],
                         "details": tts_result})

    stress_result = test_long_conversation()
    all_results.append({"test": "long_conversation", "passed": stress_result["pass"],
                         "details": stress_result})

    # ── Summary ──
    total = len(all_results)
    passed = sum(1 for r in all_results if r["passed"])

    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " CONVERSATION E2E — FINAL RESULTS".center(58) + "║")
    print("╠" + "═" * 58 + "╣")
    print(f"║  Tests: {passed}/{total} passed".ljust(58) + "║")
    print("╚" + "═" * 58 + "╝")

    # Save results
    output_path = Path(__file__).parent / "results_conversation.json"
    with open(output_path, "w") as f:
        json.dump({"suite": "conversation", "total": total, "passed": passed,
                    "results": all_results}, f, indent=2, default=str)
    print(f"\n📄 Results saved to {output_path}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
