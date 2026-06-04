# Alex Voice — Benchmark Completo

**Fecha:** 2026-06-03T17:55:23.396469
**Modelo:** Qwen3.5-2B-Q8 (Qwen3.6-plus-Distilled)
**Hardware:** NVIDIA RTX 3050 6GB Laptop GPU
**Endpoint:** llama-server (localhost:8081)

---

## 📊 1. Velocidad de Inferencia

### Streaming vs No-Streaming

| Métrica | Streaming | No-Streaming |
|:--------|:---------:|:------------:|
| **TTFT (Time to First Token)** | 3.059s | 3.971s |
| **Tiempo Total Promedio** | 14.130s | 13.235s |
| **Tokens Promedio** | 242 | 240 |
| **Velocidad** | 17.1 tok/s | 18.2 tok/s |

### Por Tamaño de Prompt

| Tamaño | Prompt (chars) | TTFT | Total | Tokens/s | Prompt Proc (tok/s) |
|:-------|:--------------:|:----:|:-----:|:--------:|:-------------------:|
| **short (10 palabras)** | 15 | 1.458s | 4.861s | 12.1 | 2.1 |
| **medium (50 palabras)** | 166 | 6.823s | 22.744s | 17.6 | 6.0 |
| **long (200 palabras)** | 669 | 12.535s | 41.783s | 19.1 | 13.3 |

---

## 🌐 2. Calidad Multilingüe

| Idioma | Precisión | Tiempo Promedio | Tokens Promedio |
|:-------|:---------:|:---------------:|:---------------:|
| **ESPANOL** | 3/3 (100%) | 20.65s | 400.0 |
| **ENGLISH** | 3/3 (100%) | 17.38s | 329.3 |
| **JAPANESE** | 3/3 (100%) | 20.54s | 400.0 |

### ESPANOL — Detalle

**Prompt 1:** ¿Cuál es la diferencia entre 'por qué', 'porque', 'porqué' y 'por que'? Explícam

**Respuesta:** <think>
Thinking Process:

1.  **Analyze the Request:**
   - **User:** Asks about the difference between 'por qué', 'porque', 'porqué' and 'por que' i

**Idioma detectado:** es (esperado: es) — ✅

*Tiempo: 21.03s | Tokens: 400 | Caracteres: 1454*

**Prompt 2:** Háblame sobre la influencia de Gabriel García Márquez en la literatura latinoame

**Respuesta:** <think>
Thinking Process:

1.  **Analyze the Request:**
   - **User:** Asks about the influence of Gabriel García Márquez on Latin American literature

**Idioma detectado:** es (esperado: es) — ✅

*Tiempo: 20.48s | Tokens: 400 | Caracteres: 1604*

**Prompt 3:** Explica el concepto de 'bullying' en el ámbito escolar y cómo prevenirlo desde c

**Respuesta:** <think>
Thinking Process:

1.  **Analyze the Request:**
   - **Topic:** 'Bullying' (bullying) in the school setting and how to prevent it at home.
   

**Idioma detectado:** es (esperado: es) — ✅

*Tiempo: 20.45s | Tokens: 400 | Caracteres: 1780*


### ENGLISH — Detalle

**Prompt 1:** Explain the difference between AI, Machine Learning, and Deep Learning in simple

**Respuesta:** <think>
Thinking Process:

1.  **Analyze the Request:**
   - **Topic:** Difference between AI, Machine Learning, and Deep Learning.
   - **Goal:** Exp

**Idioma detectado:** en (esperado: en) — ✅

*Tiempo: 20.72s | Tokens: 400 | Caracteres: 1708*

**Prompt 2:** What are the implications of quantum computing for cybersecurity?

**Respuesta:** <think>
Thinking Process:

1.  **Analyze User Input:**
   - **Question:** "What are the implications of quantum computing for cybersecurity?"
   - **C

**Idioma detectado:** en (esperado: en) — ✅

*Tiempo: 20.55s | Tokens: 400 | Caracteres: 1831*

**Prompt 3:** Describe the process of photosynthesis and why it's crucial for life on Earth.

**Respuesta:** <think>

</think>

Photosynthesis is the process by which green plants, algae, and some bacteria convert light energy into chemical energy, producing 

**Idioma detectado:** en (esperado: en) — ✅

*Tiempo: 10.86s | Tokens: 188 | Caracteres: 1005*


### JAPANESE — Detalle

**Prompt 1:** 人工知能と機械学習の違いについて説明してください。

**Respuesta:** <think>
ユーザーは「人工知能」と「機械学習」の違いについて説明を求めています。この用語はよく混同されがちですが、明確な定義と区別が重要です。まず、AIは「知的な行為」を指し、機械学習はその一部（学習アルゴリズム）です。AIには機械学習だけでなく、ディープラーニング、ナレッジベース、適応型など

**Idioma detectado:** ja (esperado: ja) — ✅

*Tiempo: 20.76s | Tokens: 400 | Caracteres: 728*

**Prompt 2:** 日本の四季の特徴と、それぞれの季節に関連する伝統的な行事について教えてください。

**Respuesta:** <think>
Okay, let's see. The user is asking about the characteristics of Japan's four seasons and traditional events associated with each. First, I ne

**Idioma detectado:** ja (esperado: ja) — ✅

*Tiempo: 20.40s | Tokens: 400 | Caracteres: 1509*

**Prompt 3:** 「いただきます」と「ごちそうさま」の意味と文化的な背景を説明してください。

**Respuesta:** <think>

</think>

「いただきます」と「ごちそうさま」は、日本において食事の開始と終盤における重要な挨拶です。

**「いただきます」の意味と背景**
この言葉は、食事を始める際に言われる「食事を始めましょう」という意味ですが、実はより深く、日本文化に根ざした言葉として見えます。


**Idioma detectado:** ja (esperado: ja) — ✅

*Tiempo: 20.44s | Tokens: 400 | Caracteres: 733*

---

## 🔄 3. Cross-Language & Code-Switching

### Cross-Language (pedir en X, responder en Y)

| Prueba | Esperado | Obtenido | Estado | Tiempo |
|:-------|:--------:|:--------:|:------:|:-----:|
| **ES→EN** | en | es | ❌ | 20.92s |
| **EN→ES** | es | es | ✅ | 3.88s |
| **JA→ES** | es | ja | ❌ | 17.23s |
| **ES→JA** | ja | es | ❌ | 21.36s |
| **EN→JA** | ja | ja | ✅ | 21.78s |

### Respuestas Detalladas

**ES→EN** — Prompt: _Responde en inglés: ¿Cuál es la capital de Francia y qué idioma se habla allí?_

Respuesta: <think>
Thinking Process:

1.  **Analyze the Request:**
   - Language of response: English (explicitly stated: "Responde en inglés")
   - Question: "¿Cuál es la capital de Francia y qué idioma se habl

*Estado: ❌ Incorrecto | Tiempo: 20.92s | Tokens: 400*

**EN→ES** — Prompt: _Answer in Spanish: What is the capital of Japan and what language do they speak _

Respuesta: <think>

</think>

La capital de Japón es **Tokio**. La lengua principal que se habla en la ciudad y en toda Japón es el **japonés**.

*Estado: ✅ Correcto | Tiempo: 3.88s | Tokens: 34*

**JA→ES** — Prompt: _スペイン語で答えてください：日本の首都はどこですか？_

Respuesta: <think>
Thinking Process:

1.  **Analyze the Request:**
    *   Language: Spanish (requested in Spanish).
    * Question: "日本の首都はどこですか？" (What is the capital of Japan?)
    * Target: Answer in Spanish

*Estado: ❌ Incorrecto | Tiempo: 17.23s | Tokens: 322*

**ES→JA** — Prompt: _Responde en japonés: ¿Cuál es la comida tradicional más famosa de México?_

Respuesta: <think>
Thinking Process:

1.  **Analyze the Request:**
   - **Language:** Japanese (Responde en japonés)
   - **Question:** "¿Cuál es la comida tradicional más famosa de México?" (What is the most fa

*Estado: ❌ Incorrecto | Tiempo: 21.36s | Tokens: 400*

**EN→JA** — Prompt: _Answer in Japanese: What are the main differences between Western and Eastern ph_

Respuesta: <think>

</think>

西洋哲学と東洋哲学の主な違いは、以下の点で概ね現れています。

1. **目的と視点**
西洋哲学は「真理の探求」「理性の発展」「自由意志の確立」を目的とし、個人や人類の普遍的な真理を追求します。対照的に、東洋哲学（特に中国・日本・インドの伝統）は「道（道徳・真理）の探求」「平和・調和」「人生の質的な満足」を目的とし、個人と自然、あるいは社会全体の調和を重視し

*Estado: ✅ Correcto | Tiempo: 21.78s | Tokens: 400*

### Code-Switching (idiomas mezclados)

**ES+EN mixed** — Prompt: _Hola! I was thinking about viajar a Japón el next year. What's the best época fo_

Respuesta: <think>

</think>

¡Hola! El año próximo es un excelente momento para viajar a Japón, ya que el clima es más cálido y los precios de las entradas (como los trenes y pasajes de avión) suelen ser más ec

*Idioma detectado: es | Tiempo: 25.36s | Tokens: 500*

**EN+JA mixed** — Prompt: _I love アニメ and 漫画. My favorite is One Piece. Can you recommend some other おすすめ a_

Respuesta: <think>
Okay, the user has expressed a strong interest in anime, specifically mentioning One Piece as a favorite, and wants recommendations for other anime, along with learning about Japanese culture.

*Idioma detectado: en | Tiempo: 25.21s | Tokens: 500*

**ES+EN+JA triple** — Prompt: _Quiero aprender 日本語. I've been studying for 3 meses. ¿Puedes recomendarme some g_

Respuesta: <think>
Here's a thinking process:

1.  **Analyze User Request:**
   - **Goal:** Learn Japanese (日本語)
   - **Progress:** Studied for 3 months
   - **Questions:**
     - Recommend good study methods (勉

*Idioma detectado: ja | Tiempo: 25.26s | Tokens: 500*

---

## 🧠 4. Consistencia y Contexto

### Multi-Turn Conversation (5 turns)

| Métrica | Resultado |
|:--------|:---------:|
| **Retención de contexto** | 100% |
| **Recuerda nombre (Turn 2)** | ✅ |
| **Recuerda nombre (Turn 5)** | ✅ |
| **Recuerda tema de aprendizaje** | ✅ |
| **Cambia a español cuando se pide** | ✅ |

---

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
