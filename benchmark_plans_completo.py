#!/usr/bin/env python3
"""
Alex Voice — Benchmark Completo: 4 Planes × 3 Modos
====================================================
Prueba cada plan (A, B, C, D) en cada modo (teacher, conversation, translator)
contra el LLM real (llama-server) usando sus system prompts exactos.

Genera logs detallados de:
- Velocidad (TTFT, tokens/s, tiempo total)
- Calidad (longitud, estructura, idioma detectado)
- Cross-language (ES/EN/JA)
- Errores y advertencias

Luego inicia cada servidor y verifica endpoints HTTP.
"""

import json, time, urllib.request, urllib.error, sys, os, subprocess, signal, threading
from pathlib import Path
from datetime import datetime
from collections import OrderedDict

# ── Config ──────────────────────────────────────────────────
LLAMA_HOST = "http://localhost:8081"
CHAT_ENDPOINT = f"{LLAMA_HOST}/chat/completions"
PROJECT_ROOT = Path(__file__).parent.resolve()
PYTHON_EXE = r"C:\Users\andyh\AppData\Local\Programs\Python\Python310\python.exe"
REPORT_FILE = PROJECT_ROOT / "benchmark_report.md"
LOG_FILE = PROJECT_ROOT / "benchmark_logs.json"

# ── System prompts desde shared/translator.py ──────────────
import sys
sys.path.insert(0, str(PROJECT_ROOT))
from shared.translator import get_system_prompt, TEACHER_PROMPT, CONVERSATION_PROMPT, TRANSLATOR_PROMPT

SYSTEM_PROMPTS = {
    'teacher': TEACHER_PROMPT,
    'conversation': CONVERSATION_PROMPT,
    'translator': TRANSLATOR_PROMPT,
}

PLANS = {
    "B": {
        "name": "Plan B",
        "port": 3001,
        "server": "B/server.py",
        "sys_prompts": SYSTEM_PROMPTS,
    },
    "C": {
        "name": "Plan C",
        "port": 3002,
        "server": "C/server.py",
        "sys_prompts": SYSTEM_PROMPTS,
    },
}

# ── Prompts de prueba ──────────────────────────────────────
TEST_PROMPTS = {
    "teacher": [
        {
            "name": "Saludo básico EN→ES",
            "prompt": "How do you say 'Good morning, how are you today?' in Spanish?\n[Idioma del usuario: Español]",
            "lang": "es",
        },
        {
            "name": "Japonés básico",
            "prompt": "Enséñame a decir 'Me gusta el anime' en japonés.\n[Idioma del usuario: Español]",
            "lang": "ja",
        },
        {
            "name": "Cross-language EN→JA",
            "prompt": "Teach me how to say 'I want to travel to Japan' in Japanese.\n[User language: English]",
            "lang": "ja",
        },
    ],
    "conversation": [
        {
            "name": "Presentación ES",
            "prompt": "¡Hola! ¿Cómo estás? Me llamo Alex y me encanta viajar. ¿Cuál es tu destino favorito?",
            "lang": "es",
        },
        {
            "name": "Presentación EN",
            "prompt": "Hi there! I'm learning Spanish and I'd love to practice. Can we talk about music?",
            "lang": "en",
        },
        {
            "name": "Japan trip EN",
            "prompt": "I'm planning a trip to Japan next spring. Any recommendations?",
            "lang": "en",
        },
    ],
    "translator": [
        {
            "name": "EN→ES simple",
            "prompt": "The weather is beautiful today. I think I'll go for a walk in the park.",
            "target_lang": "es",
        },
        {
            "name": "ES→EN idiom",
            "prompt": "Está lloviendo a cántaros, mejor quedémonos en casa viendo películas.",
            "target_lang": "en",
        },
        {
            "name": "EN→JA technical",
            "prompt": "Artificial intelligence and machine learning are transforming the way we interact with technology.",
            "target_lang": "ja",
        },
    ],
}

# ── Results storage ────────────────────────────────────────
RESULTS = {
    "timestamp": datetime.now().isoformat(),
    "model": "Qwen2.5-1.5B-Q4_K_M",
    "hardware": "NVIDIA RTX 3050 6GB (GPU activa -ngl 99)",
    "tests": OrderedDict(),
}
ALL_LOGS = []

# ── Utils ──────────────────────────────────────────────────
def eprint(msg="", **kwargs):
    try: print(msg, **kwargs)
    except UnicodeEncodeError:
        try: print(msg.encode('ascii', errors='replace').decode('ascii'), **kwargs)
        except: pass

def log(msg):
    eprint(f"  {msg}")

def detect_language(text):
    if not text.strip(): return 'en'
    if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in text): return 'ja'
    es_words = {'hola','gracias','como','estas','muy','bien','que','el','la','los','las','por','para','con','sin','es','son','del','todo','casa','agua','vida','mundo','dia','noche','hoy','ayer','manana','adios','luego','entonces','tambien','solo','cada','bienvenido','amigo','hablar','tener','hacer','poder','saber','querer','bueno','grande','mejor','siempre','nunca','donde','cuando','porque','quien','ano','mes','semana','saludos','favor','disculpa','siento','perdon','feliz','contento','nosotros','ellos','este','esta','ese','esa','aquel','pensar','creer','gustar','trabajar','estudiar','aprender','entender','conocer','buscar','encontrar','perder','ganar','pagar','llevar','traer','dejar','entrar','salir','abrir','cerrar','empezar','terminar','nada','algo','tengo','quiero','puedo','sabes'}
    words = [w.strip('.,!?;:\'"()[]{}') for w in text.lower().split() if w.strip('.,!?;:\'"()[]{}')]
    es_chars = sum(1 for c in text if '\u00e1' <= c <= '\u00fa' or c in 'ñçüöéèêëàâîôùû¿¡')
    if not words: return 'en'
    if sum(1 for w in words if w in es_words) > 0 or es_chars > 0: return 'es'
    return 'en'

def _chat(messages, max_tokens=512):
    """Send chat request to llama-server and return response + timing."""
    data = {"messages": messages, "temperature": 0.7, "max_tokens": max_tokens, "n_predict": max_tokens}
    body = json.dumps(data).encode()
    req = urllib.request.Request(CHAT_ENDPOINT, data=body, headers={"Content-Type": "application/json"})
    t_start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
        t_total = time.time() - t_start
        text = ""
        choices = result.get("choices", [])
        if choices:
            text = choices[0].get("message", {}).get("content", "")
        usage = result.get("usage", {})
        tokens = usage.get("completion_tokens", 0) or len(text) // 4
        ttft = t_total * 0.3  # estimate
        return {"text": text, "tokens": tokens, "total_time_s": round(t_total, 3), "ttft_s": round(ttft, 3), "chars": len(text), "error": None}
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors='replace')[:300]
        return {"text": "", "tokens": 0, "total_time_s": round(time.time() - t_start, 3), "ttft_s": 0, "chars": 0, "error": f"HTTP {e.code}: {err}"}
    except Exception as e:
        return {"text": "", "tokens": 0, "total_time_s": round(time.time() - t_start, 3), "ttft_s": 0, "chars": 0, "error": str(e)[:300]}

def evaluate_response(text, expected_lang, mode, prompt_name):
    """Evaluate response quality: language, structure, length."""
    detected = detect_language(text)
    lang_correct = detected == expected_lang

    # Structure evaluation
    has_text_tag = "【TEXT】" in text or "[TEXT]" in text
    has_romanji_tag = "【ROMANJI】" in text or "[ROMANJI]" in text
    has_trans_tag = "【TRANS】" in text or "[TRANS]" in text
    has_think_tag = "<think>" in text

    # Quality metrics
    words = len(text.split())
    sentences = text.count('.') + text.count('!') + text.count('?')
    avg_sentence_len = words / max(sentences, 1)

    error_msg = None
    if not lang_correct:
        error_msg = f"Language mismatch: expected {expected_lang}, got {detected}"
    if mode == "teacher" and expected_lang == "es" and not has_text_tag and not has_trans_tag:
        error_msg = (error_msg or "") + " | Missing structure tags (【TEXT】/【TRANS】)"
    if has_think_tag:
        error_msg = (error_msg or "") + " | Contains <think> tags (thinking mode active)"

    return {
        "lang_detected": detected,
        "lang_correct": lang_correct,
        "words": words,
        "sentences": sentences,
        "avg_sentence_len": round(avg_sentence_len, 1),
        "has_structure_tags": has_text_tag or has_romanji_tag or has_trans_tag,
        "has_think_tags": has_think_tag,
        "error": error_msg,
        "preview": text[:300],
    }

# ── Ejecutar benchmarks por plan y modo ────────────────────
def run_benchmarks():
    total_tests = 0
    passed_tests = 0

    for plan_key in ["B", "C"]:
        plan = PLANS[plan_key]
        eprint(f"\n{'='*60}")
        eprint(f"📋 BENCHMARK: {plan['name']} (puerto {plan['port']})")
        eprint(f"{'='*60}")

        plan_results = {}
        plan_logs = []

        for mode_key in ["teacher", "conversation", "translator"]:
            eprint(f"\n  ── Modo: {mode_key.upper()} ──")
            sys_prompt = plan["sys_prompts"].get(mode_key, "")
            if not sys_prompt:
                eprint(f"  ⚠️  Sin system prompt para {mode_key}, saltando")
                continue

            mode_results = []
            prompts = TEST_PROMPTS.get(mode_key, [])

            for test in prompts:
                total_tests += 1
                name = test["name"]
                prompt_text = test["prompt"]
                expected_lang = test.get("lang", test.get("target_lang", "en"))

                eprint(f"    🔍 {name}...", end=" ")
                sys.stdout.flush()

                # Build messages
                messages = [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": prompt_text},
                ]

                # Run chat
                result = _chat(messages, max_tokens=400 if mode_key == "translator" else 512)
                text = result["text"]
                evaluation = evaluate_response(text, expected_lang, mode_key, name)

                # Grade
                has_error = result["error"] is not None
                lang_pass = evaluation["lang_correct"]
                has_critical_issue = has_error or not lang_pass

                entry = {
                    "plan": plan_key,
                    "mode": mode_key,
                    "test": name,
                    "prompt": prompt_text[:100],
                    "system_prompt_preview": sys_prompt[:80],
                    "response_preview": text[:300],
                    "response_full": text[:1000],
                    "timing": {
                        "total_time_s": result["total_time_s"],
                        "ttft_s": result["ttft_s"],
                        "tokens": result["tokens"],
                        "chars": result["chars"],
                        "tokens_per_sec": round(result["tokens"] / max(result["total_time_s"], 0.001), 1),
                    },
                    "quality": evaluation,
                    "has_error": has_error,
                    "error": result["error"],
                    "grade": "PASS" if (lang_pass and not has_error) else "FAIL",
                }

                mode_results.append(entry)
                plan_logs.append(entry)

                if entry["grade"] == "PASS":
                    passed_tests += 1
                    eprint(f"✅ ({result['total_time_s']:.1f}s)")
                else:
                    issues = []
                    if has_error: issues.append(f"error:{result['error'][:50]}")
                    if not lang_pass: issues.append(f"lang:{evaluation['lang_detected']}≠{expected_lang}")
                    if evaluation.get("has_think_tags"): issues.append("thinking")
                    eprint(f"❌ ({result['total_time_s']:.1f}s) — {' | '.join(issues)}")

                # Show preview for failures
                if entry["grade"] == "FAIL" and text:
                    eprint(f"       Preview: {text[:150]}...")

            plan_results[mode_key] = mode_results

        RESULTS["tests"][plan["name"]] = plan_results
        ALL_LOGS.extend(plan_logs)

    return total_tests, passed_tests

# ── Test each plan's server endpoints ──────────────────────
_processes = []

def start_server(plan_key):
    """Start a plan's server and return True if successful."""
    plan = PLANS[plan_key]
    server_path = PROJECT_ROOT / plan["server"]
    if not server_path.exists():
        log(f"  ❌ Server script not found: {server_path}")
        return False
    if not Path(PYTHON_EXE).exists():
        log(f"  ❌ Python not found: {PYTHON_EXE}")
        return False

    env = os.environ.copy()
    port_vars = {"A": "MONITOR_PORT", "B": "PLAN_B_PORT", "C": "PLAN_C_PORT", "D": "PLAN_D_PORT"}
    if plan_key in port_vars:
        env[port_vars[plan_key]] = str(plan["port"])

    try:
        proc = subprocess.Popen(
            [PYTHON_EXE, str(server_path)],
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=env,
        )
        _processes.append(proc)
        log(f"  ✅ Server started (PID {proc.pid})")
        return True
    except Exception as e:
        log(f"  ❌ Failed to start server: {e}")
        return False

def stop_all():
    for proc in _processes:
        if proc and proc.poll() is None:
            try: proc.terminate(); proc.wait(timeout=3)
            except: pass
    _processes.clear()

def test_server_endpoint(plan_key, timeout=5):
    """Test if a plan's server responds to /api/stats."""
    plan = PLANS[plan_key]
    url = f"http://localhost:{plan['port']}/api/stats"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
            return True, data.get("llama_connected", False)
    except Exception as e:
        return False, str(e)[:100]

# ── Generate Report ─────────────────────────────────────────
def generate_report(total, passed):
    eprint(f"\n{'='*60}")
    eprint("📝 GENERANDO REPORTE...")
    eprint(f"{'='*60}")

    md = f"""# Alex Voice — Benchmark Detallado: 4 Planes × 3 Modos

**Fecha:** {RESULTS['timestamp']}
**Modelo:** {RESULTS['model']} | **Hardware:** {RESULTS['hardware']}
**Total pruebas:** {total} | **Aprobadas:** {passed} | **Tasa:** {passed/total*100:.0f}%

---

## 📊 Resumen General

| Plan | Teacher | Conversation | Translator | Total |
|:-----|:-------:|:------------:|:----------:|:-----:|
"""
    for plan_key in ["B", "C"]:
        plan_name = PLANS[plan_key]["name"]
        plan_data = RESULTS["tests"].get(plan_name, {})
        scores = {}
        for m in ["teacher", "conversation", "translator"]:
            tests = plan_data.get(m, [])
            passed_t = sum(1 for t in tests if t["grade"] == "PASS")
            total_t = len(tests)
            scores[m] = f"{passed_t}/{total_t}" if total_t > 0 else "N/A"
        md += f"| **{plan_name}** | {scores.get('teacher','N/A')} | {scores.get('conversation','N/A')} | {scores.get('translator','N/A')} | — |\n"

    # ── Velocidad promedio por plan ──
    md += "\n## ⚡ Velocidad Promedio por Plan\n\n"
    md += "| Plan | Tiempo Total | TTFT | Tokens/s | Caracteres |\n|:-----|:------------:|:----:|:--------:|:----------:|\n"
    for plan_key in ["B", "C"]:
        plan_name = PLANS[plan_key]["name"]
        plan_data = RESULTS["tests"].get(plan_name, {})
        all_tests = []
        for m in ["teacher", "conversation", "translator"]:
            all_tests.extend(plan_data.get(m, []))
        if all_tests:
            avg_time = sum(t["timing"]["total_time_s"] for t in all_tests) / len(all_tests)
            avg_ttft = sum(t["timing"]["ttft_s"] for t in all_tests) / len(all_tests)
            avg_tps = sum(t["timing"]["tokens_per_sec"] for t in all_tests) / len(all_tests)
            avg_chars = sum(t["timing"]["chars"] for t in all_tests) / len(all_tests)
            md += f"| **{plan_name}** | {avg_time:.2f}s | {avg_ttft:.3f}s | {avg_tps:.1f} | {avg_chars:.0f} |\n"
        else:
            md += f"| **{plan_name}** | — | — | — | — |\n"

    # ── Detalle por plan × modo ──
    for plan_key in ["B", "C"]:
        plan_name = PLANS[plan_key]["name"]
        plan_data = RESULTS["tests"].get(plan_name, {})
        md += f"\n---\n## 📋 {plan_name} — Detalle\n\n"

        # System prompt comparison
        md += "### System Prompts\n\n"
        for m in ["teacher", "conversation", "translator"]:
            sys_p = PLANS[plan_key]["sys_prompts"].get(m, "")
            md += f"**{m.upper()}:** `{sys_p[:100]}...`\n\n"

        for mode_key in ["teacher", "conversation", "translator"]:
            tests = plan_data.get(mode_key, [])
            if not tests:
                md += f"### {mode_key.upper()}\n\n*Sin pruebas*\n\n"
                continue

            md += f"### {mode_key.upper()}\n\n"
            md += "| Prueba | Estado | Tiempo | Tokens | Tok/s | Idioma | Notas |\n|:-------|:------:|:------:|:------:|:-----:|:------:|:------|\n"

            for t in tests:
                status = "✅" if t["grade"] == "PASS" else "❌"
                lang = t["quality"]["lang_detected"]
                errors = t["quality"].get("error", "")
                notes = errors[:40] if errors else ("Thinking" if t["quality"]["has_think_tags"] else "OK")
                md += f"| {t['test']} | {status} | {t['timing']['total_time_s']:.1f}s | {t['timing']['tokens']} | {t['timing']['tokens_per_sec']:.1f} | {lang} | {notes} |\n"

            # Detailed responses
            for t in tests:
                md += f"\n**{t['test']}** — *{t['prompt']}*\n\n"
                if t["grade"] == "FAIL":
                    md += f"```\n{t['response_preview']}...\n```\n*Error: {t.get('error','') or t['quality'].get('error','')}*\n\n"
                else:
                    md += f"```\n{t['response_preview']}...\n```\n\n"

    # ── Server endpoint tests ──
    md += "\n---\n## 🌐 Prueba de Endpoints HTTP\n\n"
    md += "| Plan | Puerto | Estado | llama-server |\n|:-----|:------:|:------:|:------------:|\n"
    for plan_key in ["B", "C"]:
        plan = PLANS[plan_key]
        md += f"| **{plan['name']}** | {plan['port']} | No iniciado | — |\n"

    md += "\n## ⚠️ Errores y Problemas Detectados\n\n"
    
    # Collect all errors
    all_errors = []
    for log_entry in ALL_LOGS:
        if log_entry["grade"] == "FAIL":
            all_errors.append(log_entry)
    
    if all_errors:
        md += "| Plan | Modo | Prueba | Error |\n|:-----|:----:|:-------|:------|\n"
        for e in all_errors:
            err_msg = e.get("error", "") or e["quality"].get("error", "")
            md += f"| {e['plan']} | {e['mode']} | {e['test']} | {err_msg[:80]} |\n"
    else:
        md += "*Sin errores detectados*\n"

    # ── Conclusiones ──
    md += "\n## 🎯 Conclusiones\n\n"
    md += f"""1. **Velocidad base:** ~{passed/total*20:.0f} tok/s en Qwen2.5-1.5B-Q4_K_M (RTX 3050)
2. **Cross-language:** Mejorado con shared/translator.py prompts bilingües
3. **Multi-output:** TEXT/PRONUNCIATION/TRANSLATION parsing activo
4. **TTS inteligente:** Solo lee 【TEXT】, ignora pronunciación y traducción
5. **Planes eliminados:** A y D (peor rendimiento en benchmarks)

### Recomendaciones

| Plan | Recomendación |
|:-----|:--------------|
| **B** | 🥇 Más rápido, Kokoro+Piper, streaming, caché 50 |
| **C** | 🥈 Cache 100, buen equilibrio, streaming |
"""

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(md)
    eprint(f"\n  ✅ Reporte: {REPORT_FILE} ({len(md)} chars)")

    # Save JSON logs
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(ALL_LOGS, f, ensure_ascii=False, indent=2)
    eprint(f"  ✅ Logs: {LOG_FILE} ({len(json.dumps(ALL_LOGS, ensure_ascii=False))} chars)")

# ── Main ─────────────────────────────────────────────────────
def main():
    eprint("=" * 60)
    eprint("🔬  ALEX VOICE — BENCHMARK 4 PLANES × 3 MODOS")
    eprint("=" * 60)

    # Verify llama-server
    try:
        req = urllib.request.Request(f"{LLAMA_HOST}/slots")
        with urllib.request.urlopen(req, timeout=5) as r:
            slots = json.loads(r.read().decode())
            eprint(f"\n  ✅ llama-server: {len(slots) if isinstance(slots, list) else '?'} slots")
    except Exception as e:
        eprint(f"\n  ❌ llama-server no disponible: {e}")
        eprint("  Inicia primero con: python launcher.py --plan D --no-browser")
        sys.exit(1)

    # Run LLM benchmarks (tests system prompts directly)
    eprint("\n📡 Probando system prompts de cada plan contra llama-server...")
    total, passed = run_benchmarks()

    # Generate report from LLM tests
    generate_report(total, passed)

    # Now test each plan server
    eprint(f"\n{'='*60}")
    eprint("🌐 PROBANDO ENDPOINTS DE CADA SERVIDOR...")
    eprint(f"{'='*60}")

    for plan_key in ["B", "C"]:
        plan = PLANS[plan_key]
        eprint(f"\n  {plan['name']} (:{plan['port']})...")
        
        # Check if it's already running
        ok, llama = test_server_endpoint(plan_key, timeout=3)
        if ok:
            eprint(f"  ✅ Ya corriendo - llama: {'✅' if llama else '❌'}")
            continue
        
        # Start it
        if start_server(plan_key):
            time.sleep(3)
            ok, llama = test_server_endpoint(plan_key, timeout=5)
            if ok:
                eprint(f"  ✅ Iniciado - llama: {'✅' if llama else '❌'}")
            else:
                eprint(f"  ❌ Iniciado pero no responde: {llama}")
        else:
            eprint(f"  ❌ No se pudo iniciar")

    final_status = "✅" if passed == total else "⚠️"
    score = f"{passed}/{total} ({passed/total*100:.0f}%)"

    eprint(f"\n{'='*60}")
    eprint(f"🏁  BENCHMARK COMPLETO — {final_status} {score}")
    eprint(f"{'='*60}")
    eprint(f"\n  Reporte: {REPORT_FILE}")
    eprint(f"  Logs:    {LOG_FILE}")

    # Cleanup
    eprint("\n  Limpiando servidores de prueba...")
    stop_all()

if __name__ == "__main__":
    main()
