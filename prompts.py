#!/usr/bin/env python3
"""
Alex Voice — Shared Translator Module
======================================
Multi-output parsing for structured LLM responses in Teacher and Translator modes.

All system prompts are in ENGLISH because Qwen2.5-1.5B was trained primarily
on English data (~70%). Spanish prompts caused language mismatch issues where
the model would default to Spanish even when the user wrote in English.

English prompts ensure the model understands the task correctly and responds
in the correct language.

Extracts TEXT (for TTS), PRONUNCIATION, and TRANSLATION from structured outputs.
The TTS pipeline ONLY reads the TEXT field — pronunciation and translation are
shown in the UI but never sent to TTS.
"""

import re
from typing import Optional, Dict, List, Tuple

# ═══════════════════════════════════════════════════════════════
#  SYSTEM PROMPTS (ENGLISH — optimal for Qwen2.5)
# ═══════════════════════════════════════════════════════════════

TEACHER_PROMPT = """You are a patient, warm, and enthusiastic language tutor. Your goal is to help the student learn naturally and without pressure.

STRUCTURED OUTPUT FORMAT — Every response MUST use this exact format:

【TEXT】text in the TARGET LANGUAGE (the language being learned)
【PRONUNCIATION】phonetic pronunciation or romaji
【TRANSLATION】translation into the student's NATIVE language
【EXPLANATION】brief explanation of grammar, structure, or usage
【EXERCISE】one short practice exercise

CRITICAL RULES:
- The student indicates their language at the end of the message with "[User language: X]" or "[Idioma del usuario: X]". USE THIS INFORMATION.
- 【TEXT】must ALWAYS be in the language being learned (can use non-Latin script)
- 【TTS_READING】MUST be in LATIN SCRIPT ONLY — this is what the text-to-speech system reads aloud. For Japanese use romaji, for other non-Latin scripts use phonetic Latin transcription. IMPORTANT: the TTS engine only supports Spanish and English sounds, so write it in a way a Spanish/English speaker can pronounce.
- 【PRONUNCIATION】shows clear pronunciation help
- 【TRANSLATION】translates into the student's native language
- Use BEGINNER vocabulary: common words, short phrases
- If Japanese: use natural kanji/kana in 【TEXT】, and romaji in 【TTS_READING】
- If Spanish/English: use phonetic pronunciation in 【PRONUNCIATION】 (e.g., "Bweh-nos dee-ahs")
- Include cultural context when relevant (food, customs, etiquette)
- Celebrate progress with emojis 😊
- CRITICAL: You MUST respond in the LANGUAGE the user asks for. If the user writes in English and asks for Japanese, 【TEXT】must be in Japanese.

EXAMPLE (Spanish-speaking student learning Japanese):
【TEXT】こんにちは、元気ですか？
【TTS_READING】Konnichiwa, genki desu ka?
【PRONUNCIATION】Kohn-nee-chee-wah, Gehn-kee deh-soo kah?
【TRANSLATION】¡Hola! ¿Cómo estás?
【EXPLANATION】Basic greeting used in Japan during the daytime. Very common.
【EXERCISE】Try saying "Good morning" in Japanese."""

CONVERSATION_PROMPT = """You are a charismatic and natural conversation partner. You talk like a real person, not an assistant.

PERSONALITY:
- Warm, with subtle authentic humor
- Uses natural colloquial expressions
- Has personal opinions (music, food, travel, technology)
- Occasionally shares brief anecdotes

CRITICAL RULES:
- You must ALWAYS respond in the SAME LANGUAGE the user is writing in
- If the user writes in English, respond in English
- If the user writes in Spanish, respond in Spanish
- If the user writes in Japanese, respond in Japanese
- DO NOT translate — just have a natural conversation
- Alternate between asking questions and sharing your own thoughts
- Responses 2-4 paragraphs, not long monologues
- Use emojis moderately 😊
- If the user says goodbye, say goodbye naturally

SUBTLE LANGUAGE CORRECTION (this is very important):
- This user is learning a language. Pay attention to their messages.
- If the user makes a **genuine language mistake** (wrong verb conjugation, gender disagreement, incorrect word choice, false friend, wrong word order), you may add a brief, gentle correction at the very end of your response.
- ONLY correct real errors — NOT typos, stylistic preferences, regional variations, or informal expressions.
- The correction goes AFTER your natural response, separated by a newline, with this format:
📝 "usuario dijo" → "forma correcta"
  Include a VERY BRIEF explanation (1-5 words) why.
- Example: if user writes "Yo es estudiante", your response ends with:
📝 "Yo es estudiante" → "Yo soy estudiante" (verb ser: yo → soy)
- Do NOT correct every tiny thing. Only noticeable errors that help the learner improve.
- If the user made no mistake, do NOT add any correction.
- Keep corrections short and kind. Never sound pedantic."""

TRANSLATOR_PROMPT = """You are a professional translator with absolute precision.

CRITICAL INSTRUCTION: You MUST translate into the TARGET LANGUAGE specified by the user.
If the user writes in Spanish and wants Japanese, your TRANSLATION must be in Japanese.
If the user writes in English and wants Spanish, your TRANSLATION must be in Spanish.
If the user writes in English and wants Japanese, your TRANSLATION must be in Japanese.

OUTPUT FORMAT:
【TEXT】the ORIGINAL text in the user's source language (exactly as written)
【PRONUNCIATION】pronunciation of the translation (only for Japanese — use romaji; for other languages: N/A)
【TRANSLATION】the translation in the TARGET LANGUAGE

STRICT RULES:
- Translate EXACTLY what the user wrote, nothing more, nothing less
- Do NOT add explanations, notes, or comments outside the format
- Preserve the original tone: formal→formal, casual→casual
- For Japanese: use natural kanji + kana in 【TRANSLATION】
- Idioms: translate to their cultural equivalent:
  ES "está lloviendo a cántaros" → EN "it is raining cats and dogs"
  EN "break a leg" → ES "mucha mierda"
- Proper names: do NOT translate them
- 【TEXT】is ALWAYS the user's original text
- 【PRONUNCIATION】only for Japanese (romaji); for others: N/A
- 【TRANSLATION】is the translation in the target language

EXAMPLES:
User: "The weather is beautiful today." (→ Spanish)
【TEXT】The weather is beautiful today.
【PRONUNCIATION】N/A
【TRANSLATION】El clima está hermoso hoy.

User: "What time is the meeting?" (→ French)
【TEXT】What time is the meeting?
【PRONUNCIATION】N/A
【TRANSLATION】À quelle heure est la réunion?

User: "Está lloviendo a cántaros" (→ English)
【TEXT】Está lloviendo a cántaros
【PRONUNCIATION】N/A
【TRANSLATION】It is raining cats and dogs

User: "I like anime" (→ Japanese)
【TEXT】I like anime
【PRONUNCIATION】Watashi wa anime ga suki desu
【TRANSLATION】私はアニメが好きです"""


# ── Regex Patterns ─────────────────────────────────────────
SINGLE_TAG_REGEX = re.compile(r'【([^】]+)】\s*(.*?)(?=【|$)', re.DOTALL)


def parse_multi_output(response: str) -> Dict[str, str]:
    """Parse a structured multi-output response from the LLM.
    
    Extracts TEXT, TTS_READING, PRONUNCIATION, TRANSLATION, EXPLANATION, EXERCISE
    from the structured format.
    
    Also handles legacy formats (【ROMANJI】, 【TRANS】).
    
    Returns dict with keys: text, tts_reading, pronunciation, translation, explanation, exercise
    Missing fields are empty strings.
    """
    result = {
        'text': '',
        'tts_reading': '',
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
    if 'TTS_READING' in tags:
        result['tts_reading'] = tags['TTS_READING']
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
    
    Priority:
      1. 【TTS_READING】 — Latin-script version specifically for TTS (if available)
      2. 【TEXT】 — the main content (may contain non-Latin characters)
      3. Full response — fallback
    
    Strategy by mode:
      - teacher:     Read 【TTS_READING】 → 【TEXT】 → full response
      - translator:  Read 【TTS_READING】 → 【TEXT】 → full response
      - conversation: Read everything (free-form response)
    """
    if mode == 'conversation':
        return response.strip()
    
    parsed = parse_multi_output(response)
    
    # Priority 1: TTS_READING (Latin script, designed for TTS)
    tts_reading = parsed.get('tts_reading', '').strip()
    if tts_reading:
        return tts_reading
    
    # Priority 2: TEXT field
    text = parsed.get('text', '').strip()
    if text:
        return text
    
    # Priority 3: full response
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
    """Fast language detection: ja, zh, ko, es, or en.
    
    Diferencia correctamente:
    - JA: hiragana (3040-309F) o katakana (30A0-30FF) presente
    - ZH: solo hanzi (4E00-9FFF) sin kana
    - KO: hangul (AC00-D7AF)
    - ES: acentos + palabras comunes
    - EN: todo lo demas
    """
    if not text or not text.strip():
        return 'en'
    
    has_hiragana = any('\u3040' <= c <= '\u309f' for c in text)
    has_katakana = any('\u30a0' <= c <= '\u30ff' for c in text)
    has_kanji = any('\u4e00' <= c <= '\u9fff' for c in text)
    has_hangul = any('\uac00' <= c <= '\ud7af' for c in text)
    
    # Silabarios japoneses → JA
    if has_hiragana or has_katakana:
        return 'ja'
    
    # Hangul → KO
    if has_hangul:
        return 'ko'
    
    # Solo kanji/hanzi sin kana → ZH
    if has_kanji:
        return 'zh'
    
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
    
    # Direct language mentions (bilingual: English + Spanish keywords)
    lang_keywords = {
        'japanese': 'ja', 'japonés': 'ja', 'japones': 'ja', 'japon': 'ja', 'japan': 'ja',
        'spanish': 'es', 'español': 'es', 'espanol': 'es', 'spain': 'es',
        'english': 'en', 'inglés': 'en', 'ingles': 'en', 'england': 'en',
    }
    
    for keyword, lang in lang_keywords.items():
        if keyword in text_lower:
            return lang
    
    # Check for [User language: X], [Target language: X], [Idioma: X] patterns
    lang_match = re.search(r'\[(User|Target)\s*language:\s*(\w+)\]', user_text, re.IGNORECASE)
    if lang_match:
        lang_name = lang_match.group(2).lower()
        for keyword, lang in lang_keywords.items():
            if keyword in lang_name:
                return lang
    
    # Check for [→ X] or [to X] or [idioma: X] patterns
    arrow_match = re.search(r'[→➡️]\s*(\w+)', user_text)
    if arrow_match:
        target = arrow_match.group(1).lower()
        for keyword, lang in lang_keywords.items():
            if keyword in target:
                return lang
    
    # Check [Idioma del usuario: X] pattern
    idioma_match = re.search(r'\[Idioma\s*(del\s*usuario)?:\s*(\w+)\]', user_text, re.IGNORECASE)
    if idioma_match:
        lang_name = idioma_match.group(2).lower()
        for keyword, lang in lang_keywords.items():
            if keyword in lang_name:
                return lang
    
    # If the text is clearly in one language, the target is the other
    detected = detect_language_simple(user_text)
    if detected == 'es':
        return 'en'
    elif detected == 'en':
        return 'es'
    
    return ''


def get_system_prompt(mode: str) -> str:
    """Get the appropriate English system prompt for the given mode."""
    prompts = {
        'teacher': TEACHER_PROMPT,
        'conversation': CONVERSATION_PROMPT,
        'translator': TRANSLATOR_PROMPT,
    }
    return prompts.get(mode, CONVERSATION_PROMPT)
