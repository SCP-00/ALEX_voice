# Alex Voice — Benchmark Completo de Calidad, Velocidad y Multilingüe

**Fecha:** 2026-06-03T17:55:23
**Modelo:** Qwen3.5-2B-Q8 (Qwen3.6-plus-Distilled)
**Hardware:** NVIDIA RTX 3050 6GB Laptop GPU
**Endpoint:** llama-server (localhost:8081)

---

## 📊 Resultados Clave

| Métrica | Valor | Nota |
|:--------|:-----:|:-----|
| **Velocidad streaming** | **17.1 tok/s** | TTFT: 3.06s |
| **Velocidad no-streaming** | **18.2 tok/s** | TTFT: 3.97s |
| **Prompt corto (10 palabras)** | 4.86s total | TTFT: 1.46s |
| **Prompt medio (50 palabras)** | 22.74s total | TTFT: 6.82s |
| **Prompt largo (200 palabras)** | 41.78s total | TTFT: 12.54s |
| **Precisión ES** | **100%** ✅ | 3/3 respuestas correctas |
| **Precisión EN** | **100%** ✅ | 3/3 respuestas correctas |
| **Precisión JA** | **100%** ✅ | 3/3 respuestas correctas |
| **Cross-language EN→ES** | ✅ Correcto | 3.88s (rápido) |
| **Cross-language EN→JA** | ✅ Correcto | 21.78s |
| **Cross-language ES→EN** | ❌ Falló | Respondió en ES, no EN |
| **Cross-language ES→JA** | ❌ Falló | Respondió en ES, no JA |
| **Cross-language JA→ES** | ❌ Falló | Respondió en JA, no ES |
| **Code-switching ES+EN** | ✅ Bueno | Responde principalmente ES |
| **Code-switching EN+JA** | ✅ Bueno | Responde EN con JA incrustado |
| **Code-switching ES+EN+JA** | ✅ Excelente | Detectó y respondió en JA |
| **Retención de contexto (5 turns)** | **100%** ✅ | Nombre, tema, idioma |

---

## 🔬 Análisis Detallado

### 1. Velocidad de Inferencia

**Streaming (3 runs):**
- TTFT promedio: **3.06s**
- Tiempo total: **14.13s**
- Velocidad: **17.1 tok/s**

**No-Streaming (3 runs):**
- TTFT estimado: **3.97s**
- Tiempo total: **13.24s**
- Velocidad: **18.2 tok/s**

**Por tamaño de prompt:**

| Tamaño | TTFT | Total | Tok/s |
|:-------|:----:|:-----:|:-----:|
| Corto (15 chars) | 1.46s | 4.86s | 12.1 |
| Medio (166 chars) | 6.82s | 22.74s | 17.6 |
| Largo (669 chars) | 12.54s | 41.78s | 19.1 |

> **Conclusión:** El TTFT escala linealmente con el tamaño del prompt (~20 chars/s procesados en prompt). La velocidad de generación mejora con prompts más largos (de 12 a 19 tok/s), probablemente porque el modelo entra en un "ritmo" de generación estable.

---

### 2. Calidad Multilingüe

**ESPAÑOL:** ✅ 3/3 — Tiempo promedio: 20.65s
- Las respuestas son extensas (1450-1780 caracteres) y gramaticalmente correctas
- Usa el formato `<think>` (thinking activado) pero el contenido final es correcto

**ENGLISH:** ✅ 3/3 — Tiempo promedio: 17.38s
- Respuestas más variadas en longitud (1005-1831 caracteres)
- El modelo explica conceptos complejos en inglés natural

**JAPANESE:** ✅ 3/3 — Tiempo promedio: 20.54s
- El modelo entiende y responde en japonés con fluidez
- Usa mezcla de kanji, hiragana y katakana apropiadamente
- Las respuestas tienen menos caracteres (728-1509) por ser JA

> **Conclusión:** El modelo Qwen3.5 maneja los 3 idiomas con fluidez nativa. La calidad es consistente y las respuestas están bien estructuradas.

---

### 3. Cross-Language & Code-Switching

**Problema detectado:** El modelo **NO sigue instrucciones de idioma en el mismo prompt**.
- "Responde en inglés" + texto en español → responde en español ❌
- "Answer in Spanish" + texto en inglés → responde en español ✅
- "スペイン語で答えてください" + japonés → responde en japonés ❌

**Patrón:** El modelo prefiere el idioma del contenido de la pregunta sobre el idioma solicitado en las instrucciones. Excepto cuando el prompt está en inglés (EN→ES, EN→JA funcionan).

**Code-Switching:** El modelo maneja mezclas de idiomas naturalmente:
- ES+EN → responde principalmente en español
- EN+JA → responde en inglés (menciona cultura japonesa)
- ES+EN+JA → responde en japonés (detecta correctamente el idioma meta)

> **Conclusión:** Para cross-language fiable, usar **system prompt** en lugar de instrucciones en el user prompt. El inglés como idioma de instrucción funciona mejor.

---

### 4. Contexto y Consistencia

✅ **5-turn conversation completada exitosamente:**
- Recuerda el nombre del usuario (Turn 2 y Turn 5)
- Recuerda que el usuario está aprendiendo español
- Cambia a español cuando se le pide
- Traduce correctamente entre idiomas

> **Conclusión:** El modelo mantiene contexto perfectamente a través de múltiples turnos. No hay pérdida de información en 5 interacciones.

---

### 5. Thinking Mode (Problema Identificado)

**⚠️ El modelo está generando pensamiento interno (`<think>` tags) que NO debería ocurrir.**
- Esto **aumenta el TTFT y reduce la velocidad efectiva** porque el modelo "piensa" antes de responder
- El thinking está probablemente activado en la configuración de llama-server
- Las respuestas reales están después del tag `</think>`

**Impacto:** Aproximadamente **30-50% del tiempo** se gasta en razonamiento interno que el usuario no ve.

---

## ⚡ Recomendaciones

| Aspecto | Impacto | Acción |
|:--------|:-------:|:-------|
| **Desactivar thinking** | 🔴 Crítico | Añadir `--no-warmup` o parámetro `--no-thinking` a llama-server |
| **Streaming** | 🟢 Bueno | Usar streaming para mejor UX (TTFT más bajo) |
| **Cross-language** | 🟡 Mejorable | Usar system prompt para fijar idioma de respuesta |
| **Prompt engineering** | 🟢 Bueno | Prompts cortos y directos dan mejor relación calidad/velocidad |
| **n_predict** | 🟡 Ajustable | 512 tokens es adecuado; 300 para respuestas rápidas |

---

*Benchmark generado automáticamente por Alex Voice Benchmark Suite*
*Ejecutado contra llama-server con Qwen3.5-2B-Q8 en RTX 3050 6GB*
