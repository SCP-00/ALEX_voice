#!/usr/bin/env python3
"""
Alex Voice — Shared Translator Module
======================================
Multi-output parsing for structured LLM responses in Teacher and Translator modes.

Extracts TEXT (for TTS), PRONUNCIATION, and TRANSLATION from structured outputs.
The TTS pipeline ONLY reads the TEXT field — pronunciation and translation are
shown in the UI but never sent to TTS.

Modes:
  - teacher:    【TEXT】 / 【PRONUNCIATION】 / 【TRANSLATION】 / 【EXPLANATION】 / 【EXERCISE】
  - translator: 【TEXT】 / 【PRONUNCIATION】 / 【TRANSLATION】
  - conversation: Free-form text (no structure needed)
"""

import re
from typing import Optional, Dict, List, Tuple

# ── System Prompts Mejorados ──────────────────────────────

TEACHER_PROMPT = """Eres un tutor de idiomas paciente, cálido y entusiasta. Tu objetivo es que el estudiante aprenda de forma natural y sin presión.

FORMATO ESTRUCTURADO — Tus respuestas DEBEN usar este formato:

【TEXT】texto en el idioma objetivo (lo que se está aprendiendo)
【PRONUNCIATION】pronunciación fonética o romaji
【TRANSLATION】traducción al idioma nativo del estudiante
【EXPLANATION】explicación breve de la estructura o uso
【EXERCISE】un ejercicio corto para practicar

REGLAS PEDAGÓGICAS:
- El estudiante indica su idioma nativo. USA ESA INFORMACIÓN.
- El 【TEXT】siempre en el idioma objetivo (el que se está aprendiendo)
- El 【PRONUNCIATION】muestra cómo se pronuncia claramente
- El 【TRANSLATION】traduce al idioma nativo del estudiante
- Vocabulario PRINCIPIANTE: palabras comunes, frases cortas
- Si es japonés: usa kana/kanji natural en 【TEXT】
- Si es español/inglés: 【PRONUNCIATION】fonética simple (ej: "Bwenos dee-ahs")
- Incluye contexto cultural cuando sea relevante
- Celebra los progresos con emojis 😊

EJEMPLO (estudiante hispanohablante aprendiendo japonés):
【TEXT】こんにちは、元気ですか？
【PRONUNCIATION】Konnichiwa, genki desu ka?
【TRANSLATION】¡Hola! ¿Cómo estás?
【EXPLANATION】Saludo básico muy usado en Japón. Se dice durante el día.
【EXERCISE】Intenta responder: "Estoy bien, gracias" en japonés."""

CONVERSATION_PROMPT = """Eres un compañero de conversación carismático y natural. Hablas como una persona real, no como un asistente.

PERSONALIDAD:
- Cálido/a, con humor sutil y auténtico
- Usas expresiones coloquiales naturales
- Tienes opiniones y gustos propios
- A veces cuentas anécdotas breves

REGLAS:
- NO traduzcas — solo conversa como un amigo
- Usa el mismo idioma del usuario; si cambia de idioma, síguelo
- Alterna preguntas y compartir tus propios pensamientos
- Respuestas de 2-4 párrafos, no monólogos
- Usa emojis con moderación 😊
- Si el usuario se despide, hazlo con naturalidad"""

TRANSLATOR_PROMPT = """Eres un traductor profesional de precisión absoluta.

INSTRUCCIÓN CRÍTICA: Debes traducir al IDIOMA SOLICITADO POR EL USUARIO.
Si el usuario escribe en español y pide japonés, tu respuesta debe ser en japonés.
Si el usuario escribe en inglés y pide español, tu respuesta debe ser en español.

FORMATO DE RESPUESTA:
【TEXT】texto en el IDIOMA ORIGINAL del usuario
【PRONUNCIATION】pronunciación de la traducción (solo si es japonés, si no: N/A)
【TRANSLATION】traducción al IDIOMA SOLICITADO

REGLAS ESTRICTAS:
- Traduce EXACTAMENTE lo que el usuario escribe, ni más ni menos
- NO añadas explicaciones, notas, ni comentarios fuera del formato
- Preserva el tono original: formal→formal, casual→casual
- Para japonés: usa kanji + kana natural en 【TRANSLATION】
- Modismos: tradúcelos al equivalente cultural
  ES 'está lloviendo a cántaros' → EN 'it is raining cats and dogs'
  EN 'break a leg' → ES 'mucha mierda'
- Nombres propios: NO los traduzcas
- 【TEXT】siempre es el texto original del usuario
- 【PRONUNCIATION】solo para japonés (romaji), si no: N/A
- 【TRANSLATION】es la traducción al idioma destino

EJEMPLOS:
Usuario: "The weather is beautiful today. I think I'll go for a walk in the park." (→ español)
【TEXT】The weather is beautiful today. I think I'll go for a walk in the park.
【PRONUNCIATION】N/A
【TRANSLATION】El clima está hermoso hoy. Creo que saldré a caminar al parque.

Usuario: "Me gusta el anime" (→ japonés)
【TEXT】Me gusta el anime
【PRONUNCIATION】Watashi wa anime ga suki desu
【TRANSLATION】私はアニメが好きです

Usuario: "Está lloviendo a cántaros" (→ inglés)
【TEXT】Está lloviendo a cántaros
【PRONUNCIATION】N/A
【TRANSLATION】It is raining cats and dogs"""


# ── Regex Patterns ─────────────────────────────────────────
MULTI_OUTPUT_REGEX = re.compile(
    r'【TEXT】\s*(.*?)\s*'
    r'(?:【PRONUNCIATION】\s*(.*?)\s*)?'
    r'(?:【TRANSLATION】\s*(.*?)\s*)?'
    r'(?:【EXPLANATION】\s*(.*?)\s*)?'
    r'(?:【EXERCISE】\s*(.*?)\s*)?'
    r'(?:【TRANS】\s*(.*?)\s*)?'
    r'(?:【ROMANJI】\s*(.*?)\s*)?',
    re.DOTALL
)

SINGLE_TAG_REGEX = re.compile(r'【([^】]+)】\s*(.*?)(?=【|$)', re.DOTALL)


def parse_multi_output(response: str) -> Dict[str, str]:
    """Parse a structured multi-output response from the LLM.
    
    Extracts TEXT, PRONUNCIATION, TRANSLATION, EXPLANATION, EXERCISE
    from the structured format.
    
    Also handles legacy formats (【ROMANJI】, 【TRANS】).
    
    Returns dict with keys: text, pronunciation, translation, explanation, exercise
    Missing fields are empty strings.
    """
    result = {
        'text': '',
        'pronunciation': '',
        'translation': '',
        'explanation': '',
        'exercise': '',
    }
    
    if not response:
        return result
    
    # Try to extract all tags
    tags = {}
    for match in SINGLE_TAG_REGEX.finditer(response):
        tag_name = match.group(1).strip().upper()
        tag_content = match.group(2).strip()
        tags[tag_name] = tag_content
    
    # Map tags to result
    if 'TEXT' in tags:
        result['text'] = tags['TEXT']
    if 'PRONUNCIATION' in tags:
        result['pronunciation'] = tags['PRONUNCIATION']
    elif 'ROMANJI' in tags:
        result['pronunciation'] = tags['ROMANJI']
    if 'TRANSLATION' in tags:
        result['translation'] = tags['TRANSLATION']
    elif 'TRANS' in tags:
        result['translation'] = tags['TRANS']
    if 'EXPLANATION' in tags:
        result['explanation'] = tags['EXPLANATION']
    if 'EXERCISE' in tags:
        result['exercise'] = tags['EXERCISE']
    
    # If no structured format detected, treat the whole response as TEXT
    if not result['text'] and not result['translation']:
        result['text'] = response.strip()
    
    return result


def get_tts_text(response: str, mode: str) -> str:
    """Extract the text that should be sent to TTS.
    
    Strategy by mode:
      - teacher:     Read 【TEXT】 (the foreign language text being taught)
      - translator:  Read 【TEXT】 (the original text the user wrote)
      - conversation: Read everything (free-form response)
    
    If no structured format is found, read the entire response.
    """
    if mode == 'conversation':
        return response.strip()
    
    parsed = parse_multi_output(response)
    
    if mode == 'teacher':
        # Read the foreign language text being taught
        return parsed.get('text', '').strip() or response.strip()
    
    if mode == 'translator':
        # Read the original text (what the user wrote)
        return parsed.get('text', '').strip() or response.strip()
    
    return response.strip()


def build_llm_messages(system_prompt: str, history: List[Dict], user_text: str,
                       mode: str = 'conversation', target_lang: str = '') -> List[Dict]:
    """Build messages array for the LLM call.
    
    Appends target language instruction if provided.
    """
    messages = [{'role': 'system', 'content': system_prompt}]
    
    # Add history (last N exchanges)
    for msg in history[-6:]:
        messages.append(msg)
    
    # Add current user message with language instruction
    user_content = user_text
    if target_lang:
        user_content = f"{user_text}\n[Target language: {target_lang}]"
    
    messages.append({'role': 'user', 'content': user_content})
    
    return messages


def detect_language_simple(text: str) -> str:
    """Fast language detection: ja, es, or en."""
    if not text or not text.strip():
        return 'en'
    
    # Japanese Unicode ranges
    if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in text):
        return 'ja'
    
    # Spanish accent chars
    es_chars = sum(1 for c in text if '\u00e1' <= c <= '\u00fa' or c in 'ñçüöéèêëàâîôùû¿¡')
    
    # Common Spanish words
    es_words = {
        'hola', 'gracias', 'como', 'estas', 'está', 'muy', 'bien', 'que', 'el', 'la',
        'los', 'las', 'por', 'para', 'con', 'sin', 'es', 'son', 'del', 'más', 'todo',
        'casa', 'agua', 'vida', 'mundo', 'día', 'noche', 'hoy', 'ayer', 'mañana',
        'adios', 'luego', 'entonces', 'también', 'solo', 'cada', 'bienvenido',
        'amigo', 'hablar', 'tener', 'hacer', 'poder', 'saber', 'querer',
    }
    
    words = [w.strip('.,!?;:\'"()[]{}') for w in text.lower().split()]
    if not words:
        return 'en'
    
    es_count = sum(1 for w in words if w in es_words)
    if es_count > 0 or es_chars > 0:
        return 'es'
    
    return 'en'


def infer_target_language(user_text: str, mode: str) -> str:
    """Detect what language the user wants to learn/translate to.
    
    Looks for language keywords in the user's message.
    Returns: 'es', 'en', 'ja', or '' (auto)
    """
    if mode != 'translator' and mode != 'teacher':
        return ''
    
    text_lower = user_text.lower()
    
    # Direct language mentions
    lang_keywords = {
        'japonés': 'ja', 'japones': 'ja', 'japanese': 'ja', 'japon': 'ja', 'japan': 'ja',
        'japanés': 'ja', 'jap': 'ja',
        'español': 'es', 'espanol': 'es', 'spanish': 'es', 'spain': 'es', 'es': 'es',
        'inglés': 'en', 'ingles': 'en', 'english': 'en', 'england': 'en', 'en': 'en',
    }
    
    for keyword, lang in lang_keywords.items():
        if keyword in text_lower:
            return lang
    
    # Check for [User language: X] or [Target language: X] patterns
    lang_match = re.search(r'\[(User|Target)\s*language:\s*(\w+)\]', user_text, re.IGNORECASE)
    if lang_match:
        lang_name = lang_match.group(2).lower()
        for keyword, lang in lang_keywords.items():
            if keyword in lang_name:
                return lang
    
    # Check [→ X] or [to X] patterns
    arrow_match = re.search(r'[→➡️]\s*(\w+)', user_text)
    if arrow_match:
        target = arrow_match.group(1).lower()
        for keyword, lang in lang_keywords.items():
            if keyword in target:
                return lang
    
    # If the text is clearly in one language, the target is the other
    detected = detect_language_simple(user_text)
    if detected == 'es':
        return 'en'
    elif detected == 'en':
        return 'es'
    
    return ''


def get_system_prompt(mode: str) -> str:
    """Get the appropriate system prompt for the given mode."""
    prompts = {
        'teacher': TEACHER_PROMPT,
        'conversation': CONVERSATION_PROMPT,
        'translator': TRANSLATOR_PROMPT,
    }
    return prompts.get(mode, CONVERSATION_PROMPT)
