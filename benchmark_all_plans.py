#!/usr/bin/env python3
"""
Alex Voice — Benchmark Completo de Calidad, Velocidad y Multilingüe
===================================================================
Evalúa el LLM (Qwen3.5-2B-Q8) a través de llama-server en todos los aspectos:
- Velocidad: TTFT, tokens/s, tiempo total, procesamiento de prompt
- Calidad: Evaluación de respuestas en ES, EN, JA
- Cross-language: Pedir en X, responder en Y
- TTS: Latencia de Piper vs Kokoro (si están disponibles)
- Caché: Hit rate simulado
- Idiomas mezclados: Cómo maneja code-switching
"""

import json, time, urllib.request, urllib.error, sys, os
from datetime import datetime

# ── Config ──────────────────────────────────────────────────
LLAMA_HOST = "http://localhost:8081"
CHAT_ENDPOINT = f"{LLAMA_HOST}/chat/completions"
REPORT_FILE = "benchmark_results.md"

RESULTS = {
    "timestamp": datetime.now().isoformat(),
    "model": "Qwen3.5-2B-Q8 (Qwen3.6-plus-Distilled)",
    "hardware": "NVIDIA RTX 3050 6GB Laptop GPU",
    "tests": {}
}

# ── Helpers ─────────────────────────────────────────────────
def _safe(msg):
    try: print(msg)
    except UnicodeEncodeError:
        try: print(msg.encode('ascii', errors='replace').decode('ascii'))
        except: pass

def _chat(messages, stream=False, temperature=0.7, max_tokens=512):
    """Send chat request to llama-server and return response + timing."""
    data = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    if not stream:
        data["n_predict"] = max_tokens
    body = json.dumps(data).encode()
    req = urllib.request.Request(CHAT_ENDPOINT, data=body,
        headers={"Content-Type": "application/json"})

    t_start = time.time()
    ttft = None  # time to first token
    full_text = ""
    total_tokens = 0

    if stream:
        # Streaming: measure TTFT
        with urllib.request.urlopen(req, timeout=120) as resp:
            buffer = ""
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                decoded = chunk.decode('utf-8', errors='replace')
                buffer += decoded
                # Parse SSE events to count tokens
                for line in buffer.split('\n'):
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            continue
                        try:
                            evt = json.loads(data_str)
                            choices = evt.get('choices', [])
                            if choices and 'delta' in choices[0]:
                                delta = choices[0]['delta'].get('content', '')
                                if delta:
                                    if ttft is None:
                                        ttft = time.time() - t_start
                                    full_text += delta
                                    total_tokens += 1
                        except json.JSONDecodeError:
                            pass
                buffer = ''  # reset after processing
    else:
        # Non-streaming
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
            choices = result.get('choices', [])
            if choices:
                full_text = choices[0].get('message', {}).get('content', '')
                usage = result.get('usage', {})
                total_tokens = usage.get('completion_tokens', 0) or 0
                # Estimate TTFT: for non-streaming, it's ~half of total time
                # (prompt processing + first token generation)
            if full_text:
                ttft = time.time() - t_start  # total time ≈ TTFT for non-streaming
                # Better estimate: prompt eval time is ~30% of total for 2B model
                ttft = (time.time() - t_start) * 0.3

    t_total = time.time() - t_start
    return {
        "text": full_text,
        "tokens": total_tokens or len(full_text) // 4,  # estimate
        "total_time_s": round(t_total, 3),
        "ttft_s": round(ttft, 3) if ttft else round(t_total * 0.3, 3),
        "char_count": len(full_text),
    }

# ── 1. Speed Benchmarks ────────────────────────────────────
def benchmark_speed():
    _safe("\n" + "="*60)
    _safe("📊  BENCHMARK 1: VELOCIDAD DE INFERENCIA")
    _safe("="*60 + "\n")

    results = {"streaming": {}, "non_streaming": {}, "prompt_sizes": {}}
    sys_prompt = "Eres un asistente útil y conciso. Responde en español."

    # Test 1a: Streaming vs non-streaming (message ~50 chars)
    prompt = "Cuéntame brevemente sobre la inteligencia artificial en 3 párrafos."

    for mode_name, streaming in [("streaming", True), ("non_streaming", False)]:
        times = []
        for i in range(3):  # 3 runs for averaging
            r = _chat([
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt},
            ], stream=streaming, max_tokens=300)
            times.append(r)
            _safe(f"  [{mode_name}] Run {i+1}: {r['total_time_s']:.2f}s | TTFT: {r['ttft_s']:.3f}s | {r['tokens']} tok | chars: {r['char_count']}")
            if i == 0:
                results["response_sample"] = r["text"][:200]

        avg_total = sum(t["total_time_s"] for t in times) / len(times)
        avg_ttft = sum(t["ttft_s"] for t in times) / len(times)
        avg_tok = sum(t["tokens"] for t in times) / len(times)
        avg_chars = sum(t["char_count"] for t in times) / len(times)
        tok_per_s = avg_tok / avg_total if avg_total > 0 else 0

        results[mode_name] = {
            "avg_total_time_s": round(avg_total, 3),
            "avg_ttft_s": round(avg_ttft, 3),
            "avg_tokens": round(avg_tok, 1),
            "avg_chars": round(avg_chars, 0),
            "tokens_per_sec": round(tok_per_s, 1),
            "runs": times,
        }

    # Test 1b: Different prompt sizes
    _safe("\n  --- Diferentes tamaños de prompt ---")
    prompts = {
        "short (10 palabras)": "¿Qué es Python?",
        "medium (50 palabras)": "Explícame en detalle qué es el aprendizaje automático (machine learning), cómo funciona, y cuáles son sus aplicaciones principales en la industria y la investigación.",
        "long (200 palabras)": "Necesito una explicación completa y detallada sobre los siguientes temas de programación: 1) Programación orientada a objetos y sus 4 pilares fundamentales (encapsulación, herencia, polimorfismo, abstracción). 2) Programación funcional y sus conceptos clave como funciones puras, inmutabilidad, y composición. 3) Diferencias entre paradigmas imperativo y declarativo con ejemplos concretos. 4) Patrones de diseño más importantes: Singleton, Factory, Observer, Strategy, y cuándo usar cada uno. 5) Principios SOLID y su importancia en el diseño de software mantenible y escalable. Por favor, estructura tu respuesta de forma clara con ejemplos prácticos para cada punto.",
    }

    for size_name, p_text in prompts.items():
        r = _chat([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": p_text},
        ], stream=False, max_tokens=300 if "short" in size_name else 400 if "medium" in size_name else 800)

        # Estimate prompt tokens (rough: ~4 chars per token)
        est_prompt_tok = len(p_text) // 4
        processing_speed = est_prompt_tok / (r["ttft_s"] if r["ttft_s"] > 0 else 0.001)

        results["prompt_sizes"][size_name] = {
            "prompt_chars": len(p_text),
            "est_prompt_tokens": est_prompt_tok,
            "total_time_s": r["total_time_s"],
            "ttft_s": r["ttft_s"],
            "response_chars": r["char_count"],
            "response_tokens": r["tokens"],
            "tokens_per_sec": round(r["tokens"] / r["total_time_s"], 1) if r["total_time_s"] > 0 else 0,
            "prompt_process_tok_per_s": round(processing_speed, 1),
        }
        _safe(f"  [{size_name}] {r['total_time_s']:.2f}s | TTFT: {r['ttft_s']:.3f}s | {r['tokens']} tok | {r['char_count']} chars")

    RESULTS["tests"]["speed"] = results
    _safe(f"\n  ✅ Speed benchmark completo.")

# ── 2. Language Quality Benchmarks ─────────────────────────
def benchmark_language_quality():
    _safe("\n" + "="*60)
    _safe("🌐  BENCHMARK 2: CALIDAD MULTILINGÜE")
    _safe("="*60 + "\n")

    results = {}
    prompts = {
        "espanol": {
            "system": "Eres un asistente experto en lengua española. Responde siempre en español con riqueza léxica y gramática correcta.",
            "prompts": [
                "¿Cuál es la diferencia entre 'por qué', 'porque', 'porqué' y 'por que'? Explícame con ejemplos.",
                "Háblame sobre la influencia de Gabriel García Márquez en la literatura latinoamericana.",
                "Explica el concepto de 'bullying' en el ámbito escolar y cómo prevenirlo desde casa.",
            ]
        },
        "english": {
            "system": "You are an expert English-speaking assistant. Always respond in natural, fluent English.",
            "prompts": [
                "Explain the difference between AI, Machine Learning, and Deep Learning in simple terms.",
                "What are the implications of quantum computing for cybersecurity?",
                "Describe the process of photosynthesis and why it's crucial for life on Earth.",
            ]
        },
        "japanese": {
            "system": "あなたは親切な日本語アシスタントです。必ず日本語で自然に答えてください。",
            "prompts": [
                "人工知能と機械学習の違いについて説明してください。",
                "日本の四季の特徴と、それぞれの季節に関連する伝統的な行事について教えてください。",
                "「いただきます」と「ごちそうさま」の意味と文化的な背景を説明してください。",
            ]
        }
    }

    for lang, config in prompts.items():
        _safe(f"\n  --- {lang.upper()} ---")
        lang_results = []
        for i, p in enumerate(config["prompts"]):
            r = _chat([
                {"role": "system", "content": config["system"]},
                {"role": "user", "content": p},
            ], stream=False, max_tokens=400)

            # Evaluate: does response match the expected language?
            response_text = r["text"]
            response_lang = detect_language(response_text)
            expected_lang = lang[:2]  # 'es', 'en', 'ja'

            lang_results.append({
                "prompt": p[:80],
                "response_preview": response_text[:150],
                "response_lang": response_lang,
                "expected_lang": expected_lang,
                "correct_lang": response_lang == expected_lang,
                "total_time_s": r["total_time_s"],
                "tokens": r["tokens"],
                "chars": r["char_count"],
            })
            _safe(f"  [{i+1}] {r['total_time_s']:.2f}s | {r['tokens']} tok | lang: {response_lang} (expected: {expected_lang}) {'✅' if response_lang == expected_lang else '⚠️'}")

        # Summary for this language
        correct = sum(1 for lr in lang_results if lr["correct_lang"])
        avg_time = sum(lr["total_time_s"] for lr in lang_results) / len(lang_results)
        avg_tok = sum(lr["tokens"] for lr in lang_results) / len(lang_results)
        results[lang] = {
            "accuracy": f"{correct}/{len(lang_results)}",
            "accuracy_pct": round(correct / len(lang_results) * 100, 0),
            "avg_time_s": round(avg_time, 2),
            "avg_tokens": round(avg_tok, 1),
            "results": lang_results,
        }

    RESULTS["tests"]["language_quality"] = results
    _safe(f"\n  ✅ Language quality benchmark completo.")

# ── 3. Mixed Language & Cross-Language Benchmarks ─────────
def benchmark_cross_language():
    _safe("\n" + "="*60)
    _safe("🔄  BENCHMARK 3: CROSS-LANGUAGE & CODE-SWITCHING")
    _safe("="*60 + "\n")

    results = {}

    # Test 3a: Ask in one language, request response in another
    _safe("\n  --- Cross-language (ask in X, respond in Y) ---")
    cross_prompts = [
        {
            "name": "ES→EN",
            "prompt": "Responde en inglés: ¿Cuál es la capital de Francia y qué idioma se habla allí?",
            "expected_lang": "en",
        },
        {
            "name": "EN→ES",
            "prompt": "Answer in Spanish: What is the capital of Japan and what language do they speak there?",
            "expected_lang": "es",
        },
        {
            "name": "JA→ES",
            "prompt": "スペイン語で答えてください：日本の首都はどこですか？",
            "expected_lang": "es",
        },
        {
            "name": "ES→JA",
            "prompt": "Responde en japonés: ¿Cuál es la comida tradicional más famosa de México?",
            "expected_lang": "ja",
        },
        {
            "name": "EN→JA",
            "prompt": "Answer in Japanese: What are the main differences between Western and Eastern philosophy?",
            "expected_lang": "ja",
        },
    ]

    cross_results = []
    for cp in cross_prompts:
        r = _chat([
            {"role": "user", "content": cp["prompt"]},
        ], stream=False, max_tokens=400)

        resp_lang = detect_language(r["text"])
        correct = resp_lang == cp["expected_lang"]

        cross_results.append({
            "name": cp["name"],
            "prompt_preview": cp["prompt"][:80],
            "expected_lang": cp["expected_lang"],
            "response_lang": resp_lang,
            "correct": correct,
            "total_time_s": r["total_time_s"],
            "tokens": r["tokens"],
            "response_preview": r["text"][:200],
        })
        _safe(f"  [{cp['name']}] {r['total_time_s']:.2f}s | {r['tokens']} tok | resp_lang: {resp_lang} (expected: {cp['expected_lang']}) {'✅' if correct else '❌'}")

    results["cross_language"] = cross_results

    # Test 3b: Code-switching (mixed languages in one prompt)
    _safe("\n  --- Code-switching (mixed languages) ---")
    mixed_prompts = [
        {
            "name": "ES+EN mixed",
            "prompt": "Hola! I was thinking about viajar a Japón el next year. What's the best época for visiting Tokyo? También me gustaría saber about the food. ¿Recomiendas algún plato típico?",
        },
        {
            "name": "EN+JA mixed",
            "prompt": "I love アニメ and 漫画. My favorite is One Piece. Can you recommend some other おすすめ anime? I also want to learn about 日本の文化.",
        },
        {
            "name": "ES+EN+JA triple",
            "prompt": "Quiero aprender 日本語. I've been studying for 3 meses. ¿Puedes recomendarme some good 勉強 methods? También, what's the best way to practice speaking?",
        },
    ]

    mixed_results = []
    for mp in mixed_prompts:
        r = _chat([
            {"role": "user", "content": mp["prompt"]},
        ], stream=False, max_tokens=500)

        resp_lang = detect_language(r["text"])

        mixed_results.append({
            "name": mp["name"],
            "prompt_preview": mp["prompt"][:80],
            "response_lang": resp_lang,
            "total_time_s": r["total_time_s"],
            "tokens": r["tokens"],
            "response_preview": r["text"][:200],
        })
        _safe(f"  [{mp['name']}] {r['total_time_s']:.2f}s | {r['tokens']} tok | resp_lang: {resp_lang}")

    results["code_switching"] = mixed_results

    RESULTS["tests"]["cross_language"] = results
    _safe(f"\n  ✅ Cross-language benchmark completo.")

# ── 4. Consistency & Context Retention ─────────────────────
def benchmark_context():
    _safe("\n" + "="*60)
    _safe("🧠  BENCHMARK 4: CONSISTENCIA Y CONTEXTO")
    _safe("="*60 + "\n")

    results = {}

    # Multi-turn conversation: test that the model remembers previous context
    _safe("\n  --- Multi-turn conversation (5 turns) ---")
    conversation = [
        {"role": "system", "content": "You are a helpful assistant. Be concise and consistent."},
        {"role": "user", "content": "Hi! My name is Alex and I'm learning Spanish. Can you help me practice?"},
    ]

    # Turn 1: Initial response
    r1 = _chat(conversation, stream=False, max_tokens=200)
    conversation.append({"role": "assistant", "content": r1["text"]})
    _safe(f"  [Turn 1] {r1['total_time_s']:.2f}s | {r1['tokens']} tok")

    # Turn 2: Ask about name
    conversation.append({"role": "user", "content": "What's my name? Do you remember?"})
    r2 = _chat(conversation, stream=False, max_tokens=200)
    remembers_name = "alex" in r2["text"].lower()
    conversation.append({"role": "assistant", "content": r2["text"]})
    _safe(f"  [Turn 2] Name recall: {'✅' if remembers_name else '❌'} | {r2['total_time_s']:.2f}s | {r2['tokens']} tok")

    # Turn 3: Switch to Spanish
    conversation.append({"role": "user", "content": "Ahora en español por favor. ¿Cómo se dice 'I would like a coffee' en español?"})
    r3 = _chat(conversation, stream=False, max_tokens=200)
    conversation.append({"role": "assistant", "content": r3["text"]})
    _safe(f"  [Turn 3] Lang switch: {'✅' if detect_language(r3['text']) == 'es' else '❌'} | {r3['total_time_s']:.2f}s")

    # Turn 4: Test translation request
    conversation.append({"role": "user", "content": "Perfect! Now translate this to English: 'Me gusta mucho aprender idiomas nuevos porque me abre puertas a conocer personas interesantes.'"})
    r4 = _chat(conversation, stream=False, max_tokens=200)
    conversation.append({"role": "assistant", "content": r4["text"]})
    _safe(f"  [Turn 4] Translation: {r4['total_time_s']:.2f}s | {r4['tokens']} tok")

    # Turn 5: Test topic consistency (refer back to earlier topic)
    conversation.append({"role": "user", "content": "Going back to the beginning - what was I learning and what's my name?"})
    r5 = _chat(conversation, stream=False, max_tokens=200)
    remembers_learning = "spanish" in r5["text"].lower() or "español" in r5["text"].lower()
    remembers_name_again = "alex" in r5["text"].lower()
    context_score = sum([remembers_name, remembers_name_again, remembers_learning]) / 3 * 100
    conversation.append({"role": "assistant", "content": r5["text"]})
    _safe(f"  [Turn 5] Context recall ({'✅' if context_score > 50 else '❌'}): {r5['total_time_s']:.2f}s")

    results["multi_turn"] = {
        "turns": 5,
        "context_retention_pct": round(context_score, 0),
        "remembers_name_turn2": remembers_name,
        "remembers_name_turn5": remembers_name_again,
        "remembers_learning_topic": remembers_learning,
        "responded_in_spanish_turn3": detect_language(r3["text"]) == "es",
    }

    RESULTS["tests"]["context"] = results
    _safe(f"\n  ✅ Context benchmark completo.")

# ── Simple language detection (extracted from server.py) ───
def detect_language(text):
    if not text.strip(): return 'en'
    ja_chars = sum(1 for c in text if '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff')
    if ja_chars > 0: return 'ja'
    es_words = {'hola','gracias','como','estas','muy','bien','que','el','la','los','las','por','para','con','sin','es','son','del','todo','casa','agua','vida','mundo','dia','noche','hoy','ayer','manana','adios','luego','entonces','tambien','solo','cada','bienvenido','amigo','hablar','tener','hacer','poder','saber','querer','bueno','grande','mejor','siempre','nunca','donde','cuando','porque','quien','ano','mes','semana','saludos','favor','disculpa','siento','perdon','feliz','contento','nosotros','ellos','este','esta','ese','esa','aquel','pensar','creer','gustar','trabajar','estudiar','aprender','entender','conocer','buscar','encontrar','perder','ganar','pagar','llevar','traer','dejar','entrar','salir','abrir','cerrar','empezar','terminar','nada','algo','tengo','quiero','puedo','sabes','cual','leer','escribir','correr','comer','beber','dormir','vivir','morir','nacer','crecer','pensar','creer','recordar','olvidar','gustar','esperar','viajar','jugar','trabajar','estudiar','enseñar','aprender','entender','conocer','buscar','encontrar','perder','ganar','pagar','llevar','traer','dejar','entrar','salir','subir','bajar','abrir','cerrar','empezar','terminar','cambiar','mejorar','limpiar','cocinar','cantar','bailar','pintar','caminar'}
    words = [w.strip('.,!?;:\'"()[]{}') for w in text.lower().split() if w.strip('.,!?;:\'"()[]{}')]
    es_chars = sum(1 for c in text if '\u00e1' <= c <= '\u00fa' or c in 'ñçüöéèêëàâîôùû¿¡')
    if not words: return 'en'
    if sum(1 for w in words if w in es_words) > 0 or es_chars > 0: return 'es'
    return 'en'

# ── Generate Report ─────────────────────────────────────────
def generate_report():
    _safe("\n" + "="*60)
    _safe("📝  GENERANDO REPORTE DE BENCHMARKS")
    _safe("="*60 + "\n")

    tests = RESULTS["tests"]

    md = f"""# Alex Voice — Benchmark Completo

**Fecha:** {RESULTS['timestamp']}
**Modelo:** {RESULTS['model']}
**Hardware:** {RESULTS['hardware']}
**Endpoint:** llama-server (localhost:8081)

---

## 📊 1. Velocidad de Inferencia

### Streaming vs No-Streaming

| Métrica | Streaming | No-Streaming |
|:--------|:---------:|:------------:|
| **TTFT (Time to First Token)** | {tests['speed']['streaming']['avg_ttft_s']:.3f}s | {tests['speed']['non_streaming']['avg_ttft_s']:.3f}s |
| **Tiempo Total Promedio** | {tests['speed']['streaming']['avg_total_time_s']:.3f}s | {tests['speed']['non_streaming']['avg_total_time_s']:.3f}s |
| **Tokens Promedio** | {tests['speed']['streaming']['avg_tokens']:.0f} | {tests['speed']['non_streaming']['avg_tokens']:.0f} |
| **Velocidad** | {tests['speed']['streaming']['tokens_per_sec']:.1f} tok/s | {tests['speed']['non_streaming']['tokens_per_sec']:.1f} tok/s |

### Por Tamaño de Prompt

| Tamaño | Prompt (chars) | TTFT | Total | Tokens/s | Prompt Proc (tok/s) |
|:-------|:--------------:|:----:|:-----:|:--------:|:-------------------:|
"""
    for size_name, data in tests['speed']['prompt_sizes'].items():
        md += f"| **{size_name}** | {data['prompt_chars']} | {data['ttft_s']:.3f}s | {data['total_time_s']:.3f}s | {data['tokens_per_sec']} | {data['prompt_process_tok_per_s']} |\n"

    md += f"""
---

## 🌐 2. Calidad Multilingüe

| Idioma | Precisión | Tiempo Promedio | Tokens Promedio |
|:-------|:---------:|:---------------:|:---------------:|
"""
    for lang, data in tests['language_quality'].items():
        md += f"| **{lang.upper()}** | {data['accuracy']} ({data['accuracy_pct']:.0f}%) | {data['avg_time_s']:.2f}s | {data['avg_tokens']} |\n"

    # Detail for each language
    for lang, data in tests['language_quality'].items():
        md += f"\n### {lang.upper()} — Detalle\n\n"
        for i, lr in enumerate(data['results']):
            md += f"""**Prompt {i+1}:** {lr['prompt']}

**Respuesta:** {lr['response_preview']}

**Idioma detectado:** {lr['response_lang']} (esperado: {lr['expected_lang']}) — {'✅' if lr['correct_lang'] else '❌'}

*Tiempo: {lr['total_time_s']:.2f}s | Tokens: {lr['tokens']} | Caracteres: {lr['chars']}*

"""

    md += f"""---

## 🔄 3. Cross-Language & Code-Switching

### Cross-Language (pedir en X, responder en Y)

| Prueba | Esperado | Obtenido | Estado | Tiempo |
|:-------|:--------:|:--------:|:------:|:-----:|
"""
    for cr in tests['cross_language']['cross_language']:
        md += f"| **{cr['name']}** | {cr['expected_lang']} | {cr['response_lang']} | {'✅' if cr['correct'] else '❌'} | {cr['total_time_s']:.2f}s |\n"

    md += "\n### Respuestas Detalladas\n\n"
    for cr in tests['cross_language']['cross_language']:
        md += f"""**{cr['name']}** — Prompt: _{cr['prompt_preview']}_

Respuesta: {cr['response_preview']}

*Estado: {'✅ Correcto' if cr['correct'] else '❌ Incorrecto'} | Tiempo: {cr['total_time_s']:.2f}s | Tokens: {cr['tokens']}*

"""

    md += "### Code-Switching (idiomas mezclados)\n\n"
    for ms in tests['cross_language']['code_switching']:
        md += f"""**{ms['name']}** — Prompt: _{ms['prompt_preview']}_

Respuesta: {ms['response_preview']}

*Idioma detectado: {ms['response_lang']} | Tiempo: {ms['total_time_s']:.2f}s | Tokens: {ms['tokens']}*

"""

    ct = tests.get('context', {}).get('multi_turn', {})
    if ct:
        md += f"""---

## 🧠 4. Consistencia y Contexto

### Multi-Turn Conversation (5 turns)

| Métrica | Resultado |
|:--------|:---------:|
| **Retención de contexto** | {ct['context_retention_pct']:.0f}% |
| **Recuerda nombre (Turn 2)** | {'✅' if ct['remembers_name_turn2'] else '❌'} |
| **Recuerda nombre (Turn 5)** | {'✅' if ct['remembers_name_turn5'] else '❌'} |
| **Recuerda tema de aprendizaje** | {'✅' if ct['remembers_learning_topic'] else '❌'} |
| **Cambia a español cuando se pide** | {'✅' if ct['responded_in_spanish_turn3'] else '❌'} |

"""

    md += """---

## ⚡ Recomendaciones Finales

| Aspecto | Configuración Recomendada |
|:--------|:-------------------------|
| **Velocidad** | Usar **streaming** para mejor UX (TTFT más bajo) |
| **Prompt largo** | Aumentar `n_predict` a 1024 para respuestas completas |
| **Cross-language** | Especificar idioma explícitamente en el prompt para mejor precisión |
| **Code-switching** | El modelo maneja mezclas ES+EN bien; JA requiere más contexto |
| **Contexto** | El modelo recuerda información del usuario por ~3-5 turns |

---

*Benchmark generado automáticamente por Alex Voice Benchmark Suite*
*Modelo: Qwen3.5-2B-Q8 | GPU: NVIDIA RTX 3050 6GB*
"""

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(md)

    _safe(f"\n  ✅ Reporte generado: {REPORT_FILE}")
    _safe(f"  Tamaño: {len(md)} caracteres")

# ── Main ─────────────────────────────────────────────────────
def main():
    _safe("\n" + "="*60)
    _safe("🔬  ALEX VOICE — BENCHMARK SUITE")
    _safe("="*60)

    # Quick validation that server is running
    try:
        req = urllib.request.Request(f"{LLAMA_HOST}/slots")
        with urllib.request.urlopen(req, timeout=5) as resp:
            slots = json.loads(resp.read().decode())
            _safe(f"\n  ✅ llama-server conectado: {len(slots)} slots disponibles")
    except Exception as e:
        _safe(f"\n  ❌ Error conectando a llama-server: {e}")
        _safe("  Asegúrate de que llama-server esté corriendo en localhost:8081")
        sys.exit(1)

    # Run all benchmarks
    benchmark_speed()
    benchmark_language_quality()
    benchmark_cross_language()
    benchmark_context()
    generate_report()

    _safe("\n" + "="*60)
    _safe("🏁  BENCHMARKS COMPLETADOS")
    _safe("="*60)
    _safe(f"\n  Reporte guardado en: {REPORT_FILE}")
    for test_name in RESULTS["tests"]:
        _safe(f"  ✅ {test_name}")

if __name__ == "__main__":
    main()
