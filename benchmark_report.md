# Alex Voice — Benchmark Detallado: 4 Planes × 3 Modos

**Fecha:** 2026-06-04T14:41:41.086666
**Modelo:** Qwen2.5-1.5B-Q4_K_M | **Hardware:** NVIDIA RTX 3050 6GB (GPU activa -ngl 99)
**Total pruebas:** 9 | **Aprobadas:** 9 | **Tasa:** 100%

---

## 📊 Resumen General

| Plan | Teacher | Conversation | Translator | Total |
|:-----|:-------:|:------------:|:----------:|:-----:|
| **Alex Voice** | 3/3 | 3/3 | 3/3 | — |

## ⚡ Velocidad Promedio por Plan

| Plan | Tiempo Total | TTFT | Tokens/s | Caracteres |
|:-----|:------------:|:----:|:--------:|:----------:|
| **Alex Voice** | 5.85s | 1.754s | 16.7 | 400 |

---
## 📋 Alex Voice — Detalle

### System Prompts

**TEACHER:** `You are a patient, warm, and enthusiastic language tutor. Your goal is to help the student learn nat...`

**CONVERSATION:** `You are a charismatic and natural conversation partner. You talk like a real person, not an assistan...`

**TRANSLATOR:** `You are a professional translator with absolute precision.

CRITICAL INSTRUCTION: You MUST translate...`

### TEACHER

| Prueba | Estado | Tiempo | Tokens | Tok/s | Idioma | Notas |
|:-------|:------:|:------:|:------:|:-----:|:------:|:------|
| Saludo básico EN→ES | ✅ | 6.4s | 139 | 21.9 | es | OK |
| Japonés básico | ✅ | 5.3s | 111 | 21.0 | ja | OK |
| Cross-language EN→JA | ✅ | 6.6s | 139 | 21.2 | ja | OK |

**Saludo básico EN→ES** — *How do you say 'Good morning, how are you today?' in Spanish?
[Idioma del usuario: Español]*

```
【TEXT】¡Buenos días, ¿cómo estás hoy?
【PRONUNCIATION】Buenos dias, hoe cste
【TRANSLATION】¡Buenos días, ¿cómo estás hoy?
【EXPLANATION】This phrase is commonly used in Spain as a greeting. It is a polite way to start a conversation with someone. The day of the week is often included in the greeting. It i...
```


**Japonés básico** — *Enséñame a decir 'Me gusta el anime' en japonés.
[Idioma del usuario: Español]*

```
【TEXT】私はアニメが好きです。
【PRONUNCIATION】Watashi wa anime ga suki desu.
【TRANSLATION】I like anime.
【EXPLANATION】This phrase means "I like anime" in Japanese. "Watashi" means "I", "wa" indicates a subject, and "anime" is the word for "anime". The rest of the phrase is a simple affirmative.
【EXERCISE】Practice...
```


**Cross-language EN→JA** — *Teach me how to say 'I want to travel to Japan' in Japanese.
[User language: English]*

```
【TEXT】私 want to travel to Japan.
【PRONUNCIATION】Watashi wa want to travel to Japan.
【TRANSLATION】I want to travel to Japan.  
【EXPLANATION】The sentence structure in Japanese is different from English. In Japanese, the subject comes first, followed by the verb, and then the object. The phrase 'want t...
```

### CONVERSATION

| Prueba | Estado | Tiempo | Tokens | Tok/s | Idioma | Notas |
|:-------|:------:|:------:|:------:|:-----:|:------:|:------|
| Presentación ES | ✅ | 3.5s | 42 | 12.0 | es | OK |
| Restaurant rec EN | ✅ | 5.4s | 105 | 19.3 | en | OK |
| Japan trip EN | ✅ | 10.2s | 247 | 24.2 | en | OK |

**Presentación ES** — *¡Hola! ¿Cómo estás? Me llamo Alex y me encanta viajar. ¿Cuál es tu destino favorito?*

```
¡Hola Alex! Estoy muy bien, gracias. Viajar es mi pasión, así que cada lugar me encanta de alguna forma. ¿Qué te ha gustado de tu último viaje?...
```


**Restaurant rec EN** — *Hi there! What's the best restaurant you've been to recently? I'm looking for new places to try.*

```
Hello! It's great to hear about your adventurous spirit. As an AI, I don't eat, but I can tell you about places that people have enjoyed. Have you heard of the new Italian spot in the city center? It's got a beautiful outdoor patio and their pasta is legendary. Another one that's been popping up is ...
```


**Japan trip EN** — *I'm planning a trip to Japan next spring. Any recommendations?*

```
Absolutely! Japan is a paradise for travelers. I'd recommend starting with a trip to Tokyo. It's the heart of the country and has an incredible array of cultural experiences, from the bustling streets of Shibuya to the serene gardens of the Imperial Palace.

If you're looking to mix it up a bit, con...
```

### TRANSLATOR

| Prueba | Estado | Tiempo | Tokens | Tok/s | Idioma | Notas |
|:-------|:------:|:------:|:------:|:-----:|:------:|:------|
| EN→ES simple | ✅ | 6.0s | 67 | 11.1 | es | OK |
| ES→EN idiom | ✅ | 2.9s | 16 | 5.5 | en |  | Missing 【TEXT】 tag | Missing 【TRANSLA |
| EN→JA technical | ✅ | 6.3s | 90 | 14.2 | ja | OK |

**EN→ES simple** — *The weather is beautiful today. I think I'll go for a walk in the park.
[Target language: Spanish]*

```
【TEXT】El clima es hermoso hoy. Creo que voy a hacer una caminata por el parque.
【PRONUNCIATION】N/A
【TRANSLATION】El clima es hermoso hoy. Creo que voy a hacer una caminata por el parque....
```


**ES→EN idiom** — *Está lloviendo a cántaros, mejor quedémonos en casa viendo películas.
[Target language: English]*

```
It is raining cats and dogs, better stay at home and watch movies....
```


**EN→JA technical** — *Artificial intelligence and machine learning are transforming the way we interact with technology.
[*

```
人工知能と機械学習は私たちがテクノロジーとどのように交互作用するようになることを変革しています。
【TEXT】Artificial intelligence and machine learning are transforming the way we interact with technology.
【PRONUNCIATION】N/A
【TRANSLATION】人工知能と機械学習は私たちがテクノロジーとどのように交互作用するようになることを変革しています。...
```


---
## 🌐 Prueba de Endpoints HTTP

| Plan | Puerto | Estado | llama-server |
|:-----|:------:|:------:|:------------:|
| **Alex Voice** | 3000 | No iniciado | — |

## ⚠️ Errores y Problemas Detectados

*Sin errores detectados*

## 🎯 Conclusiones

1. **Velocidad base:** ~20 tok/s en Qwen2.5-1.5B-Q4_K_M (RTX 3050)
2. **Cross-language:** Mejorado con shared/translator.py prompts bilingües
3. **Multi-output:** TEXT/PRONUNCIATION/TRANSLATION parsing activo
4. **TTS inteligente:** Solo lee 【TEXT】, ignora pronunciación y traducción
5. **Planes eliminados:** A y D (peor rendimiento en benchmarks)

### Recomendaciones

| Plan | Recomendación |
|:-----|:--------------|
| **B** | 🥇 Más rápido, Kokoro+Piper, streaming, caché 50 |
| **C** | 🥈 Cache 100, buen equilibrio, streaming |
