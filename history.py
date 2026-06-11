#!/usr/bin/env python3
"""
Alex Voice — History + Vocabulary Engine
=========================================
Guarda conversaciones, extrae vocabulario de respuestas Teacher,
y gestiona un sistema SRS (Spaced Repetition System) simple.

Estructura en disco:
  data/
    history/
      2024-01-01_12-30-00_abc123.json
      2024-01-02_14-00-00_def456.json
      ...
    vocabulary.json
"""

import json
import os
import re
import time
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple

# ── Config ──
PROJECT_ROOT = Path(__file__).parent.resolve()
DATA_DIR = PROJECT_ROOT / "data"
HISTORY_DIR = DATA_DIR / "history"
VOCAB_FILE = DATA_DIR / "vocabulary.json"

# ── Thread safety ──
_history_lock = threading.Lock()
_vocab_lock = threading.Lock()

# ── Ensure directories exist ──
def _ensure_dirs():
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

_ensure_dirs()

# ═══════════════════════════════════════════════════════════════
#  CONVERSATION HISTORY
# ═══════════════════════════════════════════════════════════════

def _generate_id() -> str:
    """Generate a unique, sortable conversation ID."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    # Add a short random suffix for uniqueness
    import random
    suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=4))
    return f"{ts}_{suffix}"

def _conversation_path(conv_id: str) -> Path:
    return HISTORY_DIR / f"{conv_id}.json"

def save_conversation(conv_data: dict) -> str:
    """Save or update a conversation. Returns the conversation ID.

    conv_data should have:
      - id (str): if omitted, auto-generated
      - mode (str): 'teacher', 'conversation', 'translator'
      - messages (list): list of {role, content, parsed?, vocabulary?}
      - title (str, optional): auto-generated from first user message

    Automatically sets/updates timestamps.
    """
    with _history_lock:
        conv_id = conv_data.get('id', '')
        if not conv_id:
            conv_id = _generate_id()
            conv_data['id'] = conv_id

        path = _conversation_path(conv_id)
        existing = {}
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        # Merge: preserve existing title if not changing
        merged = dict(existing)
        merged.update(conv_data)
        merged['id'] = conv_id
        merged['updated_at'] = datetime.now(timezone.utc).isoformat()
        if 'created_at' not in merged:
            merged['created_at'] = datetime.now(timezone.utc).isoformat()

        # Auto-generate title from first user message if not set
        if not merged.get('title'):
            messages = merged.get('messages', [])
            for msg in messages:
                if msg.get('role') == 'user':
                    text = msg.get('content', '').strip()
                    if text:
                        merged['title'] = text[:60] + ('...' if len(text) > 60 else '')
                        break
            if not merged.get('title'):
                merged['title'] = f"{merged.get('mode', 'conversation').capitalize()} — {merged.get('created_at', '')[:10]}"

        merged['message_count'] = len(merged.get('messages', []))

        # Write atomically
        tmp = path.with_suffix('.tmp')
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)
            tmp.replace(path)
        except Exception as e:
            print(f"[History] Error saving {conv_id}: {e}")
            return ''

        return conv_id

def load_conversation(conv_id: str) -> Optional[dict]:
    """Load a conversation by ID. Returns None if not found."""
    path = _conversation_path(conv_id)
    if not path.exists():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[History] Error loading {conv_id}: {e}")
        return None

def list_conversations(limit: int = 50) -> List[dict]:
    """List all conversations, sorted by updated_at descending.

    Returns summaries (no full messages) for performance.
    Each summary: {id, title, mode, created_at, updated_at, message_count}
    """
    convs = []
    try:
        for f in sorted(HISTORY_DIR.glob("*.json"), reverse=True):
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                convs.append({
                    'id': data.get('id', f.stem),
                    'title': data.get('title', 'Sin título'),
                    'mode': data.get('mode', 'conversation'),
                    'created_at': data.get('created_at', ''),
                    'updated_at': data.get('updated_at', ''),
                    'message_count': data.get('message_count', 0),
                })
            except (json.JSONDecodeError, OSError):
                continue
            if len(convs) >= limit:
                break
    except OSError:
        pass
    return convs

def delete_conversation(conv_id: str) -> bool:
    """Delete a conversation by ID."""
    path = _conversation_path(conv_id)
    try:
        if path.exists():
            path.unlink()
            return True
    except OSError:
        pass
    return False

def clear_all_history() -> int:
    """Delete ALL conversations. Returns count deleted."""
    count = 0
    try:
        for f in HISTORY_DIR.glob("*.json"):
            try:
                f.unlink()
                count += 1
            except OSError:
                continue
    except OSError:
        pass
    return count


# ═══════════════════════════════════════════════════════════════
#  VOCABULARY EXTRACTION + SRS
# ═══════════════════════════════════════════════════════════════

def extract_vocabulary_from_parsed(parsed: dict, language: str = '') -> List[dict]:
    """Extract vocabulary words from a parsed Teacher response.

    Looks at 【TEXT】 (main phrase), 【PRONUNCIATION】, 【TRANSLATION】.
    Returns list of dicts: {word, reading, translation, language}
    """
    vocab = []
    text = (parsed.get('text') or '').strip()
    reading = (parsed.get('pronunciation') or parsed.get('tts_reading') or '').strip()
    translation = (parsed.get('translation') or '').strip()

    if not text or not translation:
        return vocab

    # Detect language from character set
    if not language:
        if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in text):
            language = 'ja'
        elif any('\uac00' <= c <= '\ud7af' for c in text):
            language = 'ko'
        elif any('\u4e00' <= c <= '\u9fff' for c in text):
            language = 'zh'
        elif any('\u00c0' <= c <= '\u00ff' or c in 'ñç' for c in text.lower()):
            language = 'es'
        else:
            language = 'en'

    # Split text into phrases (by punctuation or newlines)
    phrases = re.split(r'[。！？\.\!\?\n]+', text)
    for phrase in phrases:
        phrase = phrase.strip()
        if not phrase or len(phrase) < 2:
            continue
        vocab.append({
            'word': phrase,
            'reading': reading if reading else '',
            'translation': translation,
            'language': language,
        })
        # Only extract the first phrase as vocabulary
        break

    return vocab


def _load_vocab() -> dict:
    """Load the full vocabulary file."""
    try:
        if VOCAB_FILE.exists():
            with open(VOCAB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _save_vocab(vocab: dict):
    """Save the full vocabulary file atomically."""
    tmp = VOCAB_FILE.with_suffix('.tmp')
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(vocab, f, ensure_ascii=False, indent=2)
        tmp.replace(VOCAB_FILE)
    except Exception as e:
        print(f"[Vocab] Error saving: {e}")


def add_vocabulary_words(words: List[dict], conv_id: str = ''):
    """Add extracted vocabulary words to the SRS database.

    If a word already exists, updates its SRS metadata.
    """
    if not words:
        return

    with _vocab_lock:
        vocab = _load_vocab()

        for word_entry in words:
            lang = word_entry.get('language', 'unknown')
            word_text = word_entry.get('word', '').strip()
            if not word_text:
                continue

            # Initialize language group if needed
            if lang not in vocab:
                vocab[lang] = {}

            existing = vocab[lang].get(word_text)
            if existing:
                # Update existing entry
                existing['last_seen'] = datetime.now(timezone.utc).isoformat()
                existing['repetitions'] += 1
                if conv_id and conv_id not in existing.get('source_conversations', []):
                    existing.setdefault('source_conversations', []).append(conv_id)
            else:
                # New word
                now = datetime.now(timezone.utc).isoformat()
                vocab[lang][word_text] = {
                    'word': word_text,
                    'reading': word_entry.get('reading', ''),
                    'translation': word_entry.get('translation', ''),
                    'language': lang,
                    'first_seen': now,
                    'last_seen': now,
                    'last_reviewed': '',
                    'next_review': now,  # Due for immediate review
                    'interval_days': 0,
                    'ease_factor': 2.5,
                    'repetitions': 1,
                    'source_conversations': [conv_id] if conv_id else [],
                }

        _save_vocab(vocab)


def review_word(word_text: str, language: str, quality: int) -> dict:
    """Review a word using SM-2 algorithm.

    quality: 0-5 (0 = forgot, 5 = perfect recall)
    Returns the updated word entry.
    """
    quality = max(0, min(5, quality))

    with _vocab_lock:
        vocab = _load_vocab()
        lang_group = vocab.get(language, {})
        entry = lang_group.get(word_text)
        if not entry:
            return {}

        # SM-2 Algorithm
        if quality >= 3:
            if entry['repetitions'] == 0:
                entry['interval_days'] = 1
            elif entry['repetitions'] == 1:
                entry['interval_days'] = 6
            else:
                if entry['interval_days'] == 0:
                    entry['interval_days'] = 1
                else:
                    entry['interval_days'] = round(entry['interval_days'] * entry['ease_factor'])
            entry['repetitions'] += 1
        else:
            entry['repetitions'] = 0
            entry['interval_days'] = 1

        # Update ease factor
        ef = entry['ease_factor'] + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        entry['ease_factor'] = max(1.3, round(ef, 2))

        # Calculate next review date
        entry['last_reviewed'] = datetime.now(timezone.utc).isoformat()
        from datetime import timedelta
        next_date = datetime.now(timezone.utc) + timedelta(days=entry['interval_days'])
        entry['next_review'] = next_date.isoformat()

        _save_vocab(vocab)
        return entry


def get_due_vocabulary(limit: int = 20) -> List[dict]:
    """Get vocabulary words due for review.

    Returns list of {word, reading, translation, language, ...} sorted
    by next_review ascending.
    """
    now = datetime.now(timezone.utc).isoformat()
    due = []
    vocab = _load_vocab()

    for lang, words in vocab.items():
        for word_text, entry in words.items():
            next_review = entry.get('next_review', '')
            if not next_review or next_review <= now:
                entry_copy = dict(entry)
                entry_copy['lang_group'] = lang
                due.append(entry_copy)

    due.sort(key=lambda x: x.get('next_review', ''))
    return due[:limit]


def get_all_vocabulary() -> dict:
    """Get ALL vocabulary, grouped by language."""
    return _load_vocab()


def get_vocabulary_stats() -> dict:
    """Get vocabulary statistics."""
    vocab = _load_vocab()
    total = 0
    by_lang = {}
    due_count = 0
    now = datetime.now(timezone.utc).isoformat()

    for lang, words in vocab.items():
        count = len(words)
        by_lang[lang] = count
        total += count
        for entry in words.values():
            next_review = entry.get('next_review', '')
            if not next_review or next_review <= now:
                due_count += 1

    return {
        'total': total,
        'by_language': by_lang,
        'due_for_review': due_count,
    }


def delete_vocabulary_word(word_text: str, language: str) -> bool:
    """Delete a specific vocabulary word."""
    with _vocab_lock:
        vocab = _load_vocab()
        if language in vocab and word_text in vocab[language]:
            del vocab[language][word_text]
            if not vocab[language]:
                del vocab[language]
            _save_vocab(vocab)
            return True
    return False


def clear_all_vocabulary() -> int:
    """Delete ALL vocabulary. Returns count deleted."""
    with _vocab_lock:
        vocab = _load_vocab()
        count = sum(len(words) for words in vocab.values())
        _save_vocab({})
    return count


# ═══════════════════════════════════════════════════════════════
#  AUTO-SAVE HELPER (for server.py)
# ═══════════════════════════════════════════════════════════════

def auto_save_exchange(conv_id: str, mode: str,
                       user_message: str, assistant_message: str,
                       parsed: dict = None) -> str:
    """Save a single exchange into a conversation.

    If conv_id is empty, starts a new conversation.
    Returns the conversation ID (new or existing).
    """
    # Load existing or create new
    conv_data = None
    if conv_id:
        conv_data = load_conversation(conv_id)

    if conv_data is None:
        conv_data = {
            'mode': mode,
            'messages': [],
        }
        if conv_id:
            conv_data['id'] = conv_id

    # Append messages
    messages = conv_data.get('messages', [])
    messages.append({'role': 'user', 'content': user_message})
    msg_entry = {'role': 'assistant', 'content': assistant_message}
    if parsed:
        msg_entry['parsed'] = parsed
    messages.append(msg_entry)
    conv_data['messages'] = messages
    conv_data['mode'] = mode

    # Extract vocabulary from teacher mode
    if mode == 'teacher' and parsed:
        words = extract_vocabulary_from_parsed(parsed)
        if words:
            existing_vocab = conv_data.get('vocabulary', [])
            existing_words = {v.get('word') for v in existing_vocab}
            for w in words:
                if w['word'] not in existing_words:
                    existing_vocab.append(w)
                    existing_words.add(w['word'])
            conv_data['vocabulary'] = existing_vocab
            add_vocabulary_words(words, conv_id)

    return save_conversation(conv_data)
