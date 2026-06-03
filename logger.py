#!/usr/bin/env python3
"""
Alex Voice — Logger Module
Sistema de logging enriquecido para eventos de la aplicación.
Extraído de server.py para modularización.
"""

import time
import threading

# ── Configuración ──────────────────────────────────────────────
_event_log = []
_log_lock = threading.Lock()
MAX_LOG_ENTRIES = 2000  # mantiene hasta 2000 entradas en memoria


# ── Funciones públicas ─────────────────────────────────────────
def add_log(entry_type, data, mode="", language="", voice_model="",
            duration_ms=None, token_count=None, char_count=None,
            method=None, segment_info=None, error_detail=None,
            extra=None):
    """Añade una entrada enriquecida al log de eventos.
    
    Args:
        entry_type: tipo de evento (input, output, tts, error, etc.)
        data: texto descriptivo o datos del evento
        mode: modo actual (teacher, conversation, translator)
        language: idioma detectado (es, en, ja)
        voice_model: modelo de voz usado
        duration_ms: latencia en milisegundos
        token_count: cantidad de tokens generados
        char_count: cantidad de caracteres
        method: método usado (piper_stdin, piper_file, outetts, speech)
        segment_info: info de segmentación TTS (json string)
        error_detail: detalle del error (stack trace, etc.)
        extra: dict con campos adicionales
    """
    with _log_lock:
        now = time.time()
        entry = {
            "ts": now,
            "timestamp": time.strftime("%H:%M:%S", time.localtime(now)),
            "timestamp_ms": f"{time.strftime('%H:%M:%S', time.localtime(now))}.{int((now % 1) * 1000):03d}",
            "type": entry_type,
            "data": data[:1000] if isinstance(data, str) else data,
            "mode": mode or "",
            "language": language or "",
            "voice_model": voice_model or "",
            "duration_ms": duration_ms,
            "token_count": token_count,
            "char_count": char_count,
            "method": method or "",
            "segment_info": segment_info,
            "error_detail": error_detail,
            "extra": extra or {},
        }
        _event_log.append(entry)
        if len(_event_log) > MAX_LOG_ENTRIES:
            _event_log.pop(0)


def get_logs():
    """Retorna una copia de todas las entradas del log."""
    with _log_lock:
        return list(_event_log)


def get_log_stats():
    """Retorna estadísticas agregadas de los logs.
    
    Returns:
        dict con: total, by_type, by_language, errors,
                  tts_avg_ms, tts_count, chat_avg_ms, chat_count
    """
    with _log_lock:
        total = len(_event_log)
        if total == 0:
            return {"total": 0, "by_type": {}, "by_language": {}, "errors": 0}

        by_type = {}
        by_language = {}
        errors = 0
        tts_total_ms = 0
        tts_count = 0
        chat_total_ms = 0
        chat_count = 0

        for e in _event_log:
            t = e.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

            lang = e.get("language", "")
            if lang:
                by_language[lang] = by_language.get(lang, 0) + 1

            if "error" in t:
                errors += 1

            if "tts" in t and e.get("duration_ms"):
                tts_total_ms += e["duration_ms"]
                tts_count += 1

            if "chat" in t and e.get("duration_ms"):
                chat_total_ms += e["duration_ms"]
                chat_count += 1

        return {
            "total": total,
            "by_type": by_type,
            "by_language": by_language,
            "errors": errors,
            "tts_avg_ms": round(tts_total_ms / tts_count, 1) if tts_count > 0 else 0,
            "tts_count": tts_count,
            "chat_avg_ms": round(chat_total_ms / chat_count, 1) if chat_count > 0 else 0,
            "chat_count": chat_count,
        }


def clear_logs():
    """Limpia todas las entradas del log."""
    with _log_lock:
        _event_log.clear()
