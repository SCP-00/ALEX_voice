# 🔬 Plan de Pruebas — ALEX Voice v2.1
## Evaluación de Modelos, TTS, ASR y Fluidez Conversacional

**Fecha:** 2026-06-21
**Hardware:** RTX 3050 6GB | 16GB RAM | i5-13420H | Kali Linux

---

## Modelos a Evaluar

| Modelo | Tamaño | VRAM | Tipo | Thinking Mode |
|--------|--------|------|------|---------------|
| Qwen2.5-3B-Instruct Q4_K_M | 2.0 GB | ~2.0 GB | Non-thinking | ❌ Siempre produce texto directo |
| Qwen3.5-4B-Instruct Q4_K_M | 2.9 GB | ~2.8 GB | Thinking (optional) | ✅ Puede usar `<think>` chains |

**Contexto objetivo:** 32K tokens (suficiente para conversaciones largas)

---

## ETAPA 1: Benchmark de Modelos Solos
> **Objetivo:** Medir velocidad (tok/s), calidad de respuestas, y capacidad multilingüe.

### 1.1 — Velocidad pura (sin sistema)
```
Test: "Write a short paragraph about the weather in Tokyo"
Métricas: time-to-first-token, tokens/sec, tiempo total
Configuración: n_ctx=32768, temperature=0.7, n_predict=256
```

### 1.2 — Calidad EN/ES/JA
```
Tests:
- EN: "Explain what a haiku is in 3 sentences"
- ES: "Explica qué es un haiku en 3 oraciones"
- JA: "俳句について3文で説明してください"
Métricas: Relevancia, gramática correcta, formato limpio
```

### 1.3 — Comparación Thinking vs Non-Thinking
```
Test con Qwen3.5-4B:
- Con thinking: "How do you say 'I love you' in Japanese and explain the grammar?"
- Sin thinking: Mismo prompt con --reasoning-format none
Métricas: Tiempo de respuesta, calidad, si el thinking aporta valor
```

### 1.4 — Memoria conversacional (multi-turn)
```
Test: 5 turnos de conversación, verificar que mantiene contexto
Turno 1: "My name is Carlos"
Turno 2: "I'm learning Japanese"
Turno 3: "What's my name?"
Turno 4: "What language am I learning?"
Turno 5: "Greet me in Japanese using my name"
```

---

## ETAPA 2: Formato Instruct + Multi-Output
> **Objetivo:** Verificar que los modelos siguen el formato 【TEXT】/【TTS_READING】/etc.

### 2.1 — Teacher mode output
```
Prompt: System prompt de teacher + "Teach me to say hello in Japanese"
Verificar: Campos 【TEXT】,【TTS_READING】,【PRONUNCIATION】,【TRANSLATION】,【EXPLANATION】,【EXERCISE】
```

### 2.2 — Conversation mode output
```
Prompt: System prompt de conversation + "Tell me about your favorite food"
Verificar: Respuesta natural, SIN emojis, SIN thinking tags
```

### 2.3 — Emojis en output
```
Verificar: Los prompts nuevos有效地 prohíben emojis
Test: Teacher y Conversation, verificar que NO aparecen emojis en output
```

---

## ETAPA 3: Full Stack (LLM + ASR + TTS)
> **Objetivo:** Medir latencia end-to-end y verificar que TTS no lee basura.

### 3.1 — TTS sanitization
```
Tests:
- Input: "Hola 😊 carita sonriente mundo <think>hmm</think>" → Esperado: "Hola mundo"
- Input: "Love you <think>analysis...</think> ❤️🔥" → Esperado: "Love you"
- Input: "日本語テスト <think>ok</think> Hello" → Esperado: "Hello"
```

### 3.2 — LLM → TTS pipeline
```
1. Iniciar llama-server con Qwen2.5-3B
2. Enviar /api/chat con teacher mode
3. Extraer TTS_READING del response
4. Enviar a /api/tts
5. Verificar: audio generado, sin basura en el texto
```

### 3.3 — ASR → LLM → TTS pipeline
```
1. Enviar audio grabado a /api/asr
2. Tomar texto transcrito → enviar a /api/chat
3. Tomar response → extraer TTS_READING → enviar a /api/tts
4. Medir latencia total de cada etapa
```

---

## ETAPA 4: Browser Test (UI)
> **Objetivo:** Verificar que los rediseños de UI funcionan correctamente.

### 4.1 — Menu UI
```
- Abrir http://localhost:5000
- Verificar: 3 cards visibles, colores correctos, hover effects
- Click en Teacher → verificar carga
- Click en Conversación → verificar cambio de modo
```

### 4.2 — Teacher UI
```
- Abrir http://localhost:3000
- Verificar: Layout card-based, secciones visibles
- Enviar mensaje → verificar respuesta estructurada
- Verificar: phonetics, pronunciation, translation se muestran
```

### 4.3 — Conversation UI
```
- Abrir http://localhost:3001
- Verificar: Voice visualizer, chat bubbles
- Enviar mensaje → verificar respuesta natural
```

---

## ETAPA 5: Comparación de Fluidez
> **Objetivo:** Determinar qué modelo es mejor para conversación fluida.

### 5.1 — Tiempo de primera palabra
```
Medir: Cuánto tiempo hasta que el LLM empieza a generar tokens
Umbral aceptable: < 500ms para conversación fluida
```

### 5.2 — Throughput para conversación
```
Medir: Tokens por segundo para respuestas conversacionales (50-200 tokens)
Umbral aceptable: > 15 tok/s para percepción de fluidez
```

### 5.3 — Thinking mode overhead
```
Con Qwen3.5-4B:
- Medir tiempo con thinking activado vs desactivado
- Evaluar si el thinking agrega valor real o solo retrasa
- Determinar: ¿El thinking es útil para tool calling pero malo para conversación?
```

### 5.4 — Recomendación final
```
Criterios:
- Teacher mode: ¿Necesita thinking? (probablemente no — respuestas predecibles)
- Conversation mode: ¿Necesita thinking? (definitivamente no — fluidez es clave)
- Tool calling: ¿Necesita thinking? (quizás — para planeación de herramientas)
```

---

## Resultados Esperados

| Métrica | Objetivo | Qwen2.5-3B | Qwen3.5-4B |
|---------|----------|------------|------------|
| Tokens/sec (32K ctx) | > 15 tok/s | ? | ? |
| Time to first token | < 500ms | ? | ? |
| Teacher output quality | 6/6 fields | ? | ? |
| Emojis in TTS | 0 | ? | ? |
| Thinking overhead | < 2x slowdown | N/A | ? |
| VRAM usage | < 5.5 GB | ? | ? |

---

## Decisiones Clave

1. **¿Qwen2.5-3B (non-thinking) es suficiente para Teacher?** → Sí si produce respuestas estructuradas correctas
2. **¿Qwen3.5-4B (thinking) aporta algo al Conversation mode?** → Probablemente no — el thinking retrasa la fluidez
3. **¿Cuál modelo para el Professor de japonés?** → Depende de la calidad de tool calling
4. **¿Thinking mode solo para tool calling?** → Posible configuración híbrida
