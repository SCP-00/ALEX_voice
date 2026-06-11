#!/usr/bin/env python3
"""
Alex Voice — Teacher + Conversation.
LLM en GPU, TTS híbrido Kokoro/Piper en CPU.
Corre en puerto 3000 por defecto.
"""

import json
import os
import sys
import re
import base64
import struct
import time
import threading
import subprocess
import urllib.request
import urllib.error
import numpy as np
import shutil
import platform
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from collections import OrderedDict

# Regex compilada: caracteres seguros para TTS (Latin + español)
_TTS_SAFE_RE = re.compile(
    r"[^\x00-\x7F\u00C0-\u024F\u1E00-\u1EFF"
    r"\u0300-\u036F\s0-9.,!?;:\'\"¡¿\(\)\[\]\{\}\-–—…&@#%*+=/<>~`$€£¥°]"
)

# ── Shared prompts module ─────────────────────────────────
from prompts import parse_multi_output, get_tts_text, get_system_prompt, build_llm_messages, detect_language_simple

# ── History module ─────────────────────────────────────────
import history as history_mod
# Renamed to avoid conflict with 'history' variable names

# ── LRU Cache ──────────────────────────────────────────────
class ResponseCache:
    """LRU cache thread-safe para respuestas del LLM."""
    def __init__(self, maxsize=50):
        self._cache = OrderedDict()
        self._maxsize = maxsize
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, messages):
        key_parts = []
        for msg in messages[-4:]:
            role = msg.get('role', '')
            content = msg.get('content', '')[:200]
            key_parts.append(f"{role}:{content}")
        return hash('|'.join(key_parts))

    def get(self, messages):
        key = self._make_key(messages)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def put(self, messages, response):
        if not response or len(response) < 20:
            return
        key = self._make_key(messages)
        with self._lock:
            self._cache[key] = response
            self._cache.move_to_end(key)
            if len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

    def invalidate(self):
        with self._lock:
            self._cache.clear()

    def stats(self):
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                "size": len(self._cache),
                "maxsize": self._maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 1),
            }

# ── Config ─────────────────────────────────────────────────
LLAMA_HOST = os.environ.get("LLAMA_HOST", "http://localhost:8081")

# Soporte para --mode y --port desde línea de comandos (teacher/conv wrapper)
SERVER_MODE = os.environ.get("TEACHER_MODE", "") or os.environ.get("CONV_MODE", "")
PORT = int(os.environ.get("PLAN_B_PORT", "3000"))
for i, arg in enumerate(sys.argv):
    if arg == "--port" and i + 1 < len(sys.argv):
        PORT = int(sys.argv[i + 1])
    elif arg == "--mode" and i + 1 < len(sys.argv):
        SERVER_MODE = sys.argv[i + 1]

FRONTEND_DIR = Path(__file__).parent / "frontend"
PROJECT_ROOT = Path(__file__).parent

# ── Structured logging ──────────────────────────────────
def _log(level, msg):
    ts = time.strftime("%H:%M:%S")
    try:
        print(f"[{ts}] [Server] [{level}] {msg}")
    except UnicodeEncodeError:
        try:
            print(f"[{ts}] [Server] [{level}] {msg.encode('ascii', errors='replace').decode('ascii')}")
        except:
            pass

def log_ok(msg):   _log("OK", msg)
def log_warn(msg): _log("WARN", msg)
def log_err(msg):  _log("ERROR", msg)
def log_info(msg): _log("INFO", msg)

# ── Dependencias opcionales ────────────────────────────────
try:
    import psutil
    HAVE_PSUTIL = True
except ImportError:
    HAVE_PSUTIL = False
    log_warn("psutil no instalado. Stats no disponibles.")

IS_LINUX = platform.system() == 'Linux'

HAVE_NVML = False
try:
    import pynvml
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    name = pynvml.nvmlDeviceGetName(handle)
    if isinstance(name, bytes):
        name = name.decode('utf-8', errors='replace')
    HAVE_NVML = True
    log_ok(f"GPU: {str(name).replace(chr(0),'').strip()}")
except Exception:
    HAVE_NVML = False
    log_warn("nvidia-ml-py no disponible. Stats GPU no disponibles.")

# ── Sanitizador de texto para TTS ───────────────────────────
def _sanitize_tts_text(text):
    """Elimina caracteres no pronunciables por Kokoro/Piper.
    
    Kokoro-82M solo soporta Latin + extensiones españolas.
    Caracteres CJK, Árabe, Cirílico, etc. causan "Caracter japones"
    o similar. Esta función los reemplaza con espacios.
    """
    if not text:
        return ""
    safe = _TTS_SAFE_RE.sub(" ", text)
    safe = re.sub(r"\s+", " ", safe).strip()
    return safe


def _parse_conversation_correction(response: str) -> tuple:
    """Parse the 📝 correction section from a conversation response.
    
    The model adds corrections in this format at the end of its response:
    📝 "user's phrase" → "corrected phrase" (brief explanation)
    
    Returns (main_text, correction_text).
    If no correction found, correction_text is empty string.
    """
    if not response or '📝' not in response:
        return response.strip(), ''
    
    # Find the 📝 marker and split
    parts = response.split('📝', 1)
    main_text = parts[0].strip()
    correction_text = '📝' + parts[1].strip() if len(parts) > 1 else ''
    
    return main_text, correction_text


def _validate_teacher_response(parsed: dict) -> list:
    """Verifica que los campos esenciales del Teacher estén presentes.
    
    Campos requeridos: text, tts_reading, pronunciation, translation
    Retorna lista de nombres de campos faltantes (vacía si todo ok).
    """
    required = ['text', 'tts_reading', 'pronunciation', 'translation']
    missing = [f for f in required if not parsed.get(f, '').strip()]
    return missing


def _call_llama(messages: list, n_predict: int = 512, temperature: float = 0.5) -> str:
    """Simplified call to llama-server, returns content string.
    
    Used for teacher retry loop. Always non-streaming, no tools.
    Returns empty string on failure.
    """
    payload = {
        "messages": messages,
        "n_predict": n_predict,
        "temperature": temperature,
        "stream": False,
    }
    try:
        req = urllib.request.Request(
            f"{LLAMA_HOST}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
        choices = result.get("choices", [])
        if not choices:
            return ''
        return choices[0].get("message", {}).get("content", '')
    except Exception as e:
        log_err(f"Teacher retry LLM call failed: {e}")
        return ''


def _force_latin_text(text: str) -> str:
    """Elimina TODO carácter no-Latin del texto, dejando solo ASCII + español.
    
    Más agresivo que _sanitize_tts_text — garantiza que Kokoro/Piper
    puedan pronunciar el resultado. Elimina CJK, árabe, cirílico, etc.
    """
    if not text:
        return ''
    # Permitir: ASCII imprimible + español extendido + puntuación común
    latin_re = re.compile(
        r'[^\x20-\x7E\u00C0-\u024F\u00D1\u00F1'  # ASCII printable + Latin ext + Ññ
        r'\u00A1\u00BF\u00E1-\u00FA'                 # ¡ ¿ + vocales acentuadas
        r'\u0300-\u036F'                               # combining diacritics
        r'\s.,!?;:\'\"\(\)\[\]\{\}\-–—…&@#%*+=/<>~`$€£¥°]'
    )
    safe = latin_re.sub(' ', text)
    safe = re.sub(r'\s+', ' ', safe).strip()
    return safe

# ── Kokoro-82M TTS ─────────────────────────────────────────
HAVE_KOKORO = False
KOKORO_PIPELINES = {}  # lang_code -> KPipeline instance (lazy-loaded)
KOKORO_LOCK = threading.Lock()

try:
    from kokoro import KPipeline
    HAVE_KOKORO = True
except ImportError:
    log_warn("kokoro no instalado. pip install kokoro")

# Map: B language (es/en) -> Kokoro lang_code + voice
KOKORO_CONFIG = {
    'es': {'code': 'e', 'voice': 'ef_dora'},
    'en': {'code': 'a', 'voice': 'af_heart'},
}


def _get_kokoro_pipeline(lang):
    """Obtiene o carga lazy un pipeline Kokoro por idioma.
    Retorna (pipeline, voice_name) o (None, None).
    """
    global KOKORO_PIPELINES
    if lang not in KOKORO_CONFIG:
        return None, None
    cfg = KOKORO_CONFIG[lang]
    code = cfg['code']
    voice = cfg['voice']
    
    if code in KOKORO_PIPELINES:
        return KOKORO_PIPELINES[code], voice
    
    with KOKORO_LOCK:
        if code in KOKORO_PIPELINES:
            return KOKORO_PIPELINES[code], voice
        try:
            t0 = time.time()
            pipeline = KPipeline(lang_code=code)
            elapsed = (time.time() - t0) * 1000
            log_info(f"Kokoro {lang} pipeline: {elapsed:.0f}ms")
            KOKORO_PIPELINES[code] = pipeline
            return pipeline, voice
        except Exception as e:
            log_err(f"Kokoro {lang}: {e}")
            return None, None


def _kokoro_synthesize_stream(text, lang):
    """Generator: sintetiza texto con Kokoro y produce tuplas (sample_rate, pcm_bytes).
    
    Kokoro genera audio a 24kHz en chunks por segmento de texto.
    Cada chunk se entrega en cuanto está listo (streaming real).
    Retorna (sample_rate, pcm_int16_bytes, is_last=False).
    """
    pipeline, voice = _get_kokoro_pipeline(lang)
    if pipeline is None:
        return
    
    try:
        generator = pipeline(text, voice=voice, speed=1)
        for gs, ps, audio in generator:
            if audio is None or len(audio) == 0:
                continue
            # audio es float32 numpy a 24kHz → convertir a int16
            audio_float32 = np.asarray(audio, dtype=np.float32)
            # Clamp seguro a [-1, 1] antes de convertir
            audio_float32 = np.clip(audio_float32, -1.0, 1.0)
            audio_int16 = (audio_float32 * 32767).astype(np.int16)
            yield (24000, audio_int16.tobytes())
    except Exception as e:
        log_err(f"Kokoro stream: {e}")


# ── Piper TTS Python API ───────────────────────────────────
HAVE_PIPER_PYTHON = False
try:
    from piper import PiperVoice
    HAVE_PIPER_PYTHON = True
except ImportError:
    log_warn("piper-tts no instalado. pip install piper-tts")

class PiperTTS:
    """Modelos Piper cargados en memoria. Latencia ~45-65ms."""
    def __init__(self, es_model_path, en_model_path):
        self.es_voice = None
        self.en_voice = None
        self.es_model_path = str(es_model_path) if es_model_path else None
        self.en_model_path = str(en_model_path) if en_model_path else None
        self.available = False
        self._lock = threading.Lock()
        self._init_voices()

    def _init_voices(self):
        if not HAVE_PIPER_PYTHON:
            return
        if self.es_model_path:
            try:
                t0 = time.time()
                self.es_voice = PiperVoice.load(self.es_model_path, use_cuda=False)
                log_info(f"Piper ES: {(time.time()-t0)*1000:.0f}ms")
            except Exception as e:
                log_err(f"Piper ES: {e}")
        if self.en_model_path:
            try:
                t0 = time.time()
                self.en_voice = PiperVoice.load(self.en_model_path, use_cuda=False)
                log_info(f"Piper EN: {(time.time()-t0)*1000:.0f}ms")
            except Exception as e:
                log_err(f"Piper EN: {e}")
        self.available = (self.es_voice is not None) or (self.en_voice is not None)

    def synthesize(self, text, lang='es'):
        voice = self.es_voice if lang == 'es' else self.en_voice if lang == 'en' else (self.es_voice or self.en_voice)
        if voice is None:
            return None
        with self._lock:
            try:
                chunks = list(voice.synthesize(text))
                if not chunks:
                    return None
                sample_rate = getattr(chunks[0], 'sample_rate', 22050)
                int16_chunks = []
                for c in chunks:
                    if hasattr(c, 'audio_int16_array') and c.audio_int16_array is not None:
                        int16_chunks.append(c.audio_int16_array)
                    elif hasattr(c, 'audio_int16_bytes') and c.audio_int16_bytes is not None:
                        int16_chunks.append(np.frombuffer(c.audio_int16_bytes, dtype=np.int16))
                if not int16_chunks:
                    return None
                pcm = np.concatenate(int16_chunks)
                data_size = len(pcm) * 2
                buf = bytearray(44 + data_size)
                buf[0:4] = b'RIFF'
                struct.pack_into('<I', buf, 4, data_size + 36)
                buf[8:12] = b'WAVE'
                buf[12:16] = b'fmt '
                struct.pack_into('<I', buf, 16, 16)
                struct.pack_into('<H', buf, 20, 1)
                struct.pack_into('<H', buf, 22, 1)
                struct.pack_into('<I', buf, 24, sample_rate)
                struct.pack_into('<I', buf, 28, sample_rate * 2)
                struct.pack_into('<H', buf, 32, 2)
                struct.pack_into('<H', buf, 34, 16)
                buf[36:40] = b'data'
                struct.pack_into('<I', buf, 40, data_size)
                buf[44:44+data_size] = pcm.tobytes()
                return bytes(buf)
            except Exception as e:
                log_err(f"PiperTTS: {e}")
                return None

    def synthesize_stream(self, text, lang='es'):
        voice = self.es_voice if lang == 'es' else self.en_voice if lang == 'en' else (self.es_voice or self.en_voice)
        if voice is None:
            return
        sr = 22050
        with self._lock:
            try:
                for c in voice.synthesize(text):
                    if sr == 22050:
                        sr = getattr(c, 'sample_rate', 22050)
                    if hasattr(c, 'audio_int16_array') and c.audio_int16_array is not None:
                        yield (sr, c.audio_int16_array.tobytes())
                    elif hasattr(c, 'audio_int16_bytes') and c.audio_int16_bytes is not None:
                        yield (sr, c.audio_int16_bytes)
            except Exception as e:
                log_err(f"PiperTTS stream: {e}")

    def stop(self):
        self.es_voice = None
        self.en_voice = None
        self.available = False

# ── Tool Definitions (for Qwen3.5-2B function calling) ──
# Format compatible with OpenAI API / llama-server chat/completions
TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the internet for current information. Use this when you need up-to-date information about recent events, news, weather, or any topic that might be beyond your knowledge cutoff.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query (e.g., 'latest news 2026', 'weather Barcelona')"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

# ── Web Search (DuckDuckGo) ──────────────────────────────
HAVE_WEB = False
_web_search_lock = threading.Lock()
_WEB_CACHE = {}

try:
    from duckduckgo_search import DDGS
    HAVE_WEB = True
    log_ok("DuckDuckGo Search disponible")
except ImportError:
    log_warn("duckduckgo-search no instalado. pip install ddgs")


def web_search(query, max_results=5):
    """Busca en DuckDuckGo y retorna resultados formateados.
    
    Cachea resultados para búsquedas repetidas (misma query, ~5 min).
    Retorna string con los resultados formateados para inyectar en el prompt.
    """
    if not HAVE_WEB or not query:
        return None
    
    cache_key = query.lower().strip()
    with _web_search_lock:
        if cache_key in _WEB_CACHE:
            cached_time, cached_result = _WEB_CACHE[cache_key]
            if time.time() - cached_time < 300:  # 5 min cache
                log_info(f"Web cache HIT: {query[:50]}...")
                return cached_result
    
    try:
        t0 = time.time()
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        elapsed = (time.time() - t0) * 1000
        
        if not results:
            log_info(f"Web search: sin resultados para '{query[:50]}...' ({elapsed:.0f}ms)")
            return None
        
        # Formatear resultados
        formatted = []
        for i, r in enumerate(results[:max_results], 1):
            title = r.get('title', '').strip()
            body = r.get('body', '').strip()
            href = r.get('href', '').strip()
            if title or body:
                formatted.append(f"[{i}] {title}\n   {body}")
        
        if not formatted:
            return None
        
        result_str = "\n\n--- Resultados de búsqueda web ---\n" + "\n".join(formatted) + "\n--- Fin de resultados web ---"
        
        with _web_search_lock:
            _WEB_CACHE[cache_key] = (time.time(), result_str)
        
        log_info(f"Web search: {len(results)} resultados en {elapsed:.0f}ms")
        return result_str
        
    except Exception as e:
        log_err(f"Web search: {e}")
        return None

# ── ASR (faster-whisper) ───────────────────────────────────
HAVE_FASTER_WHISPER = False
_asr_models = {}
_asr_lock = threading.Lock()

try:
    from faster_whisper import WhisperModel
    HAVE_FASTER_WHISPER = True
except ImportError:
    log_warn("faster-whisper no instalado. pip install faster-whisper")

def _find_wav_data_offset(audio_bytes):
    data_pos = audio_bytes.find(b'data', 12)
    return data_pos + 8 if data_pos >= 0 else 44

def _get_asr_model(model_name):
    if model_name in _asr_models:
        return _asr_models[model_name]
    with _asr_lock:
        if model_name in _asr_models:
            return _asr_models[model_name]
        try:
            t0 = time.time()
            model = WhisperModel(model_name, device="cuda", compute_type="int8_float16")
            log_info(f"Whisper {model_name}: {(time.time()-t0)*1000:.0f}ms")
            _asr_models[model_name] = model
            return model
        except Exception as e:
            log_err(f"Whisper {model_name}: {e}")
            return None

def _asr_transcribe(audio_bytes, language="auto", model_name="small"):
    model = _get_asr_model(model_name)
    if model is None:
        return None, None, f"Modelo '{model_name}' no disponible"
    try:
        sr = 16000
        if len(audio_bytes) >= 44:
            sr = struct.unpack_from('<I', audio_bytes, 24)[0]
        offset = _find_wav_data_offset(audio_bytes)
        pcm_data = audio_bytes[offset:] if len(audio_bytes) > offset else audio_bytes[44:]
        pcm_int16 = np.frombuffer(pcm_data, dtype=np.int16)
        if len(pcm_int16) == 0:
            return None, None, "Audio vacío"
        pcm_float32 = pcm_int16.astype(np.float32) / 32768.0
        lang_code = None if language == "auto" else language
        with _asr_lock:
            segments, info = model.transcribe(
                pcm_float32, language=lang_code, beam_size=1,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=200,
                                    threshold=0.5, neg_threshold=0.35, min_speech_duration_ms=200),
            )
        seg_list = []
        full_text = []
        for seg in segments:
            seg_list.append({"text": seg.text.strip(), "start": round(seg.start, 2), "end": round(seg.end, 2)})
            full_text.append(seg.text.strip())
        text = " ".join(full_text).strip()
        return text, seg_list, None
    except Exception as e:
        return None, None, str(e)[:300]

# ── Stats Collector ────────────────────────────────────────
class StatsCollector:
    def __init__(self):
        self.lock = threading.Lock()
        self.stats = {
            "cpu_percent": 0.0, "ram_used_gb": 0.0, "ram_total_gb": 0.0, "ram_percent": 0.0,
            "vram_used_mb": 0, "vram_total_mb": 0, "vram_percent": 0.0,
            "gpu_percent": 0, "gpu_temp": 0,
            "tokens_per_sec": 0.0, "context_used": 0, "context_max": 4096, "context_percent": 0.0,
            "tokens_generated": 0, "prompt_tokens": 0, "is_processing": False, "n_slots": 0,
            "llama_connected": False, "slots_detail": [],
        }
        self._last_decoded = 0
        self._last_time = time.time()
        self._tok_times = []
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _poll_loop(self):
        while self._running:
            if HAVE_PSUTIL:
                self._collect_system_stats()
            if HAVE_NVML:
                self._collect_gpu_stats()
            self._collect_llama_stats()
            time.sleep(1.8)

    def _collect_system_stats(self):
        try:
            s = {}
            s["cpu_percent"] = round(psutil.cpu_percent(interval=0), 1)
            m = psutil.virtual_memory()
            s["ram_used_gb"] = round(m.used / (1024**3), 1)
            s["ram_total_gb"] = round(m.total / (1024**3), 1)
            s["ram_percent"] = round(m.percent, 1)
            with self.lock:
                self.stats.update(s)
        except Exception:
            pass

    def _collect_gpu_stats(self):
        try:
            s = {}
            h = pynvml.nvmlDeviceGetHandleByIndex(0)
            mi = pynvml.nvmlDeviceGetMemoryInfo(h)
            s["vram_used_mb"] = round(mi.used / (1024**2), 0)
            s["vram_total_mb"] = round(mi.total / (1024**2), 0)
            s["vram_percent"] = round(mi.used / mi.total * 100, 1)
            s["gpu_percent"] = pynvml.nvmlDeviceGetUtilizationRates(h).gpu
            s["gpu_temp"] = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
            with self.lock:
                self.stats.update(s)
        except Exception:
            pass

    def _collect_llama_stats(self):
        try:
            req = urllib.request.Request(f"{LLAMA_HOST}/slots")
            with urllib.request.urlopen(req, timeout=3) as resp:
                slots = json.loads(resp.read().decode())
        except Exception:
            with self.lock:
                self.stats["llama_connected"] = False
            return
        if not isinstance(slots, list):
            with self.lock:
                self.stats["llama_connected"] = True
            return
        with self.lock:
            self.stats["llama_connected"] = True
            self.stats["n_slots"] = len(slots)
            self.stats["slots_detail"] = slots[:4]
            total_decoded = 0
            total_prompt = 0
            max_ctx = 4096
            processing = False
            for s in slots:
                ctx = s.get("n_ctx", 4096)
                max_ctx = max(max_ctx, ctx)
                if s.get("is_processing"):
                    processing = True
                nt = s.get("next_token", {})
                if isinstance(nt, dict):
                    total_decoded += nt.get("n_decoded", 0) or 0
                elif isinstance(nt, list) and len(nt) > 0:
                    total_decoded += nt[0].get("n_decoded", 0) or 0
                total_prompt += s.get("n_prompt_tokens", 0) or 0
            self.stats["is_processing"] = processing
            self.stats["context_max"] = max_ctx
            self.stats["context_used"] = total_decoded
            self.stats["context_percent"] = round((total_decoded / max_ctx * 100) if max_ctx > 0 else 0, 1)
            self.stats["tokens_generated"] = total_decoded
            self.stats["prompt_tokens"] = total_prompt
            now = time.time()
            if total_decoded > self._last_decoded:
                dt = now - self._last_time
                if dt > 0:
                    rate = (total_decoded - self._last_decoded) / dt
                    self._tok_times.append(rate)
                    if len(self._tok_times) > 5:
                        self._tok_times.pop(0)
                    self.stats["tokens_per_sec"] = round(sum(self._tok_times) / len(self._tok_times), 1)
            elif not processing:
                if self._tok_times:
                    if now - self._last_time > 3.0:
                        self._tok_times = []
                        self.stats["tokens_per_sec"] = 0.0
                else:
                    self.stats["tokens_per_sec"] = 0.0
            self._last_decoded = total_decoded
            self._last_time = now

    def get_stats(self):
        with self.lock:
            return dict(self.stats)

    def stop(self):
        self._running = False

# ── Detección de idioma ────────────────────────────────────
def detect_language(text):
    """Detecta es/en/ja/zh/ko en un texto.
    
    Diferencia correctamente:
    - JA: tiene hiragana (3040-309F) o katakana (30A0-30FF)
    - ZH: solo kanji/hanzi (4E00-9FFF) sin kana
    - KO: hangul (AC00-D7AF)
    - ES: acentos + palabras comunes
    - EN: todo lo demas
    """
    if not text.strip():
        return 'en'
    
    has_hiragana = any('\u3040' <= c <= '\u309f' for c in text)
    has_katakana = any('\u30a0' <= c <= '\u30ff' for c in text)
    has_kanji = any('\u4e00' <= c <= '\u9fff' for c in text)
    has_hangul = any('\uac00' <= c <= '\ud7af' for c in text)
    
    # Silabarios japoneses → JA (incluso si mezcla con kanji)
    if has_hiragana or has_katakana:
        return 'ja'
    
    # Hangul coreano → KO
    if has_hangul:
        return 'ko'
    
    # Solo kanji/hanzi sin kana → ZH (chino)
    if has_kanji:
        return 'zh'
    
    # Español: acentos + palabras clave
    es_chars = sum(1 for c in text if '\u00e1' <= c <= '\u00fa' or c in 'ñçüöéèêëàâîôùû¿¡')
    es_words = {'hola','gracias','como','estas','muy','bien','que','el','la','los','las','por','para','con','sin','es','son','del','más','todo','casa','agua','vida','mundo','día','noche','hoy','ayer','mañana','adios','luego','entonces','también','solo','cada','bienvenido','amigo','señor','señora','hablar','tener','hacer','poder','saber','querer','bueno','buena','grande','mejor','siempre','nunca','pronto','tarde','donde','cuando','porque','cual','quien','cuanto','año','semana','mes','lunes','martes','miercoles','jueves','viernes','sabado','domingo','saludos','gracias','muchas','favor','permiso','disculpa','siento','perdon','feliz','contento','cansado','bienvenido','nosotros','ellos','este','esta','ese','esa','aquel','leer','escribir','correr','comer','beber','dormir','vivir','morir','nacer','crecer','pensar','creer','recordar','olvidar','gustar','esperar','viajar','jugar','trabajar','estudiar','enseñar','aprender','entender','conocer','buscar','encontrar','perder','ganar','pagar','vender','comprar','llevar','traer','dejar','entrar','salir','subir','bajar','abrir','cerrar','empezar','terminar','cambiar','mejorar','empeorar','arreglar','romper','limpiar','ensuciar','cocinar','cantar','bailar','pintar','escribir','leer','correr','saltar','nadar','volar','caminar','sentar','parar'}
    words = [w.strip('.,!?;:\'"()[]{}') for w in text.lower().split() if w.strip('.,!?;:\'"()[]{}')]
    if not words:
        return 'en'
    es_count = sum(1 for w in words if w in es_words)
    if es_count > 0 or es_chars > 0:
        return 'es'
    
    return 'en'

def _run_piper_file(text, model_path, piper_exe):
    """Fallback TTS usando archivos temporales."""
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w', encoding='utf-8') as f:
            f.write(text)
            inp = f.name
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            out = f.name
        proc = subprocess.Popen(
            [str(piper_exe), "--model", str(model_path), "--output-file", out],
            stdin=open(inp, 'rb'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        proc.wait(timeout=15)
        if proc.returncode == 0 and os.path.exists(out):
            data = open(out, 'rb').read()
            try: os.unlink(out); os.unlink(inp)
            except: pass
            return data if len(data) > 100 else None
        try: os.unlink(out); os.unlink(inp)
        except: pass
        return None
    except Exception as e:
        log_err(f"Piper subprocess: {e}")
        return None

# ── Servidor HTTP ───────────────────────────────────────────
_stats_collector = None
_response_cache = ResponseCache(maxsize=50)
_piper_tts = None

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/api/stats":
            self._json_response(_stats_collector.get_stats())
        elif self.path == "/api/cache/stats":
            self._json_response(_response_cache.stats())
        elif self.path == "/api/cache/clear":
            _response_cache.invalidate()
            self._json_response({"ok": True})
        elif self.path == "/api/history/list":
            limit = int(self._get_qs_param('limit', '50'))
            self._json_response({'conversations': history_mod.list_conversations(limit)})
        elif self.path.startswith("/api/history/get"):
            conv_id = self._get_qs_param('id', '')
            if not conv_id:
                self._json_response({'error': 'Missing id param'})
                return
            conv = history_mod.load_conversation(conv_id)
            if conv:
                self._json_response(conv)
            else:
                self._json_response({'error': 'Not found'})
        elif self.path == "/api/vocabulary":
            self._json_response(history_mod.get_all_vocabulary())
        elif self.path == "/api/vocabulary/stats":
            self._json_response(history_mod.get_vocabulary_stats())
        elif self.path == "/api/vocabulary/due":
            limit = int(self._get_qs_param('limit', '20'))
            self._json_response({'words': history_mod.get_due_vocabulary(limit)})
        elif self.path in ("/", "/index.html"):
            self._serve_file("index.html")
        else:
            super().do_GET()

    def _get_qs_param(self, name, default=''):
        """Extract a query string parameter from self.path."""
        if '?' not in self.path:
            return default
        qs = self.path.split('?', 1)[1]
        for part in qs.split('&'):
            if '=' in part:
                k, v = part.split('=', 1)
                if k == name:
                    from urllib.parse import unquote
                    return unquote(v)
        return default

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        if self.path == "/api/chat":
            self._handle_chat(body)
        elif self.path == "/api/tts":
            self._handle_tts(body)
        elif self.path == "/api/tts/stream":
            self._handle_tts_stream(body)
        elif self.path == "/api/asr":
            self._handle_asr(body)
        elif self.path == "/api/web_search":
            self._handle_web_search(body)
        elif self.path == "/api/history/delete":
            data = json.loads(body) if length > 0 else {}
            ok = history_mod.delete_conversation(data.get('id', ''))
            self._json_response({'ok': ok})
        elif self.path == "/api/history/clear":
            count = history_mod.clear_all_history()
            self._json_response({'ok': True, 'deleted': count})
        elif self.path == "/api/vocabulary/delete":
            data = json.loads(body) if length > 0 else {}
            ok = history_mod.delete_vocabulary_word(data.get('word', ''), data.get('language', ''))
            self._json_response({'ok': ok})
        elif self.path == "/api/vocabulary/clear":
            count = history_mod.clear_all_vocabulary()
            self._json_response({'ok': True, 'deleted': count})
        elif self.path == "/api/vocabulary/review":
            data = json.loads(body) if length > 0 else {}
            entry = history_mod.review_word(data.get('word', ''), data.get('language', ''), data.get('quality', 3))
            self._json_response(entry)
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_chat(self, body):
        """Proxy a llama-server con caché LRU y multi-output parsing.
        
        Acepta un campo 'mode' (teacher/conversation) para usar
        system prompts optimizados con formato multi-output (【TEXT】/【PRONUNCIATION】/【TRANSLATION】).
        """
        try:
            data = json.loads(body)
            mode = data.get('mode', 'conversation')
            target_lang = data.get('target_lang', '')
            
            if "messages" not in data and "prompt" in data:
                prompt = data["prompt"]
                parts = re.split(r'<\|im_start\|>(\w+)\n', prompt)
                messages = []
                for i in range(1, len(parts)-1, 2):
                    role = parts[i]
                    content = parts[i+1].replace('<|im_end|>', '').strip()
                    if role == 'system':
                        messages.insert(0, {"role": "system", "content": content})
                    elif role in ('user', 'assistant'):
                        messages.append({"role": role, "content": content})
                chat_data = {
                    "messages": messages,
                    "n_predict": data.get("n_predict", 512),
                    "temperature": data.get("temperature", 0.7),
                    "stream": data.get("stream", False),
                }
            elif "messages" in data:
                messages = list(data.get("messages") or [])
                has_system = bool(messages and messages[0].get("role") == "system")
                if not has_system:
                    messages.insert(0, {"role": "system", "content": get_system_prompt(mode)})
                if target_lang:
                    for msg in reversed(messages):
                        if msg.get("role") == "user":
                            msg["content"] = f"{msg.get('content', '')}\n[Target language: {target_lang}]"
                            break
                
                # ── Tool Calling: web_search via Qwen3.5 function calling ──
                use_tools = data.get("web_search") and mode == 'conversation' and HAVE_WEB
                if use_tools:
                    # Añadir definiciones de herramientas a la request
                    chat_data = {
                        "messages": messages,
                        "n_predict": data.get("n_predict", 512),
                        "temperature": data.get("temperature", {
                            'teacher': 0.5, 'conversation': 0.7
                        }.get(mode, 0.7)),
                        "stream": data.get("stream", False),
                        "tools": TOOLS_DEFINITIONS,
                    }
                else:
                    chat_data = {
                        "messages": messages,
                        "n_predict": data.get("n_predict", 512),
                        "temperature": data.get("temperature", {
                            'teacher': 0.5, 'conversation': 0.7
                        }.get(mode, 0.7)),
                        "stream": data.get("stream", False),
                    }
                
            else:
                # Build messages with proper system prompt from translator module
                user_text = data.get('text', '')
                sys_prompt = get_system_prompt(mode)
                messages = [{'role': 'system', 'content': sys_prompt}]
                # Add target language instruction for translator mode
                user_content = user_text
                if target_lang:
                    user_content = f"{user_text}\n[Target language: {target_lang}]"
                messages.append({'role': 'user', 'content': user_content})
                chat_data = {
                    "messages": messages,
                    "n_predict": data.get("n_predict", 1024),
                    "temperature": data.get("temperature", {
                        'teacher': 0.5, 'conversation': 0.7
                    }.get(mode, 0.7)),
                    "stream": data.get("stream", False),
                }

            # Cache check (skip when tools active — tool results differ per request)
            if not chat_data.get("stream") and not chat_data.get("tools"):
                cached = _response_cache.get(chat_data.get("messages", []))
                if cached:
                    log_info(f"Cache HIT! {len(cached)} chars")
                    # Parse correction section if conversation mode
                    cached_main = cached
                    cached_correction = ''
                    if mode == 'conversation':
                        cached_main, cached_correction = _parse_conversation_correction(cached)
                    result = {
                        "choices": [{"message": {"content": cached_main}}],
                        "usage": {"completion_tokens": 0, "prompt_tokens": 0},
                        "cached": True,
                    }
                    if cached_correction:
                        result['correction'] = cached_correction
                    self._json_response(result)
                    return

            target = f"{LLAMA_HOST}/chat/completions"
            req = urllib.request.Request(
                target,
                data=json.dumps(chat_data).encode(),
                headers={"Content-Type": "application/json"},
            )

            # Force non-streaming when tools active (tool calls need multi-round handshake)
            if chat_data.get("tools"):
                chat_data["stream"] = False

            if chat_data.get("stream"):
                with urllib.request.urlopen(req, timeout=120) as resp:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("X-Mode", mode)
                    self.end_headers()
                    buf = b''
                    while True:
                        chunk = resp.read(4096)
                        if not chunk:
                            break
                        buf += chunk
                        lines = buf.split(b'\n')
                        buf = lines.pop()
                        for line in lines:
                            if line.startswith(b'data: '):
                                try:
                                    data_str = line[6:].decode('utf-8', errors='replace').strip()
                                    if data_str and data_str != '[DONE]':
                                        parsed = json.loads(data_str)
                                        choices = parsed.get('choices', [])
                                        if choices and 'delta' in choices[0]:
                                            delta = choices[0]['delta']
                                            if 'content' in delta and delta['content']:
                                                delta['content'] = re.sub(r'<think>[\s\S]*?</think>\s*', '', delta['content']).strip()
                                        line = b'data: ' + json.dumps(parsed).encode()
                                except Exception:
                                    pass
                            try:
                                self.wfile.write(line + b'\n')
                                self.wfile.flush()
                            except Exception:
                                    break
            else:
                # ── Tool Calling Loop ──
                # If tools were provided, check if the model wants to call a tool.
                # If so, execute it and send the result back to get the final response.
                max_tool_rounds = 3  # Safety limit to prevent infinite loops
                tool_round = 0
                current_messages = list(chat_data.get("messages", []))
                current_tools = chat_data.get("tools")
                
                while tool_round < max_tool_rounds:
                    # Build the request
                    # Tool response rounds need more tokens to synthesize search results
                    current_n_predict = max(data.get("n_predict", 1024), 1024) if tool_round > 0 else max(data.get("n_predict", 512), 1024)
                    payload = {
                        "messages": current_messages,
                        "n_predict": current_n_predict,
                        "temperature": chat_data.get("temperature", 0.7),
                        "stream": False,
                    }
                    if current_tools:
                        payload["tools"] = current_tools
                    
                    req = urllib.request.Request(
                        f"{LLAMA_HOST}/chat/completions",
                        data=json.dumps(payload).encode(),
                        headers={"Content-Type": "application/json"},
                    )
                    
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        result = json.loads(resp.read().decode())
                    
                    choices = result.get("choices", [])
                    if not choices:
                        break
                    
                    message = choices[0].get("message", {})
                    finish_reason = choices[0].get("finish_reason", "")
                    tool_calls = message.get("tool_calls", [])
                    
                    # If no tool calls, we're done
                    if not tool_calls or finish_reason != "tool_calls":
                        break
                    
                    # Add the assistant's tool-call message to history
                    current_messages.append({
                        "role": "assistant",
                        "content": message.get("content", ""),
                        "tool_calls": tool_calls,
                    })
                    
                    # Execute each tool call
                    tool_round += 1
                    for tc in tool_calls:
                        func_name = tc.get("function", {}).get("name", "")
                        func_args_str = tc.get("function", {}).get("arguments", "{}")
                        tool_call_id = tc.get("id", f"call_{tool_round}_{int(time.time())}")
                        
                        if func_name == "web_search":
                            try:
                                func_args = json.loads(func_args_str)
                                query = func_args.get("query", "")
                                log_info(f"🔍 Tool call: web_search(query={query[:80]}...)")
                                search_results = web_search(query)
                                tool_result = search_results if search_results else "No se encontraron resultados para esa búsqueda."
                                log_info(f"📦 Tool result: {len(tool_result)} chars")
                            except Exception as e:
                                tool_result = f"Error executing web_search: {e}"
                                log_err(f"Tool exec error: {e}")
                        else:
                            tool_result = f"Unknown function: {func_name}"
                            log_warn(f"Unknown tool: {func_name}")
                        
                        # Add tool result to messages
                        current_messages.append({
                            "role": "tool",
                            "content": tool_result,
                            "tool_call_id": tool_call_id,
                        })
                    
                    # Remove tools after first round to get a text response
                    current_tools = None
                
                # If we did tool rounds, use the result from the last iteration
                if tool_round > 0:
                    # Use the result from the final non-tool response
                    content = message.get("content", "") if choices else ""
                else:
                    content = choices[0].get("message", {}).get("content", "") if choices else ""
                
                # Strip thinking tags
                cleaned = re.sub(r'<think>[\s\S]*?</think>\s*', '', content).strip()
                if not cleaned:
                    cleaned = content
                # Parse multi-output for teacher mode
                parsed = parse_multi_output(cleaned) if mode == 'teacher' else {}
                # Parse correction section for conversation mode
                correction = ''
                if mode == 'conversation':
                    cleaned, correction = _parse_conversation_correction(cleaned)
                
                # ── Teacher retry loop: validate required fields ──
                teacher_retries = 0
                if mode == 'teacher':
                    while teacher_retries < 2:
                        parsed = parse_multi_output(cleaned)
                        missing = _validate_teacher_response(parsed)
                        if not missing:
                            break
                        teacher_retries += 1
                        log_warn(f"Teacher retry {teacher_retries}: missing fields {missing}")
                        # Append retry instruction to messages
                        retry_text = (
                            f"Your previous response was missing these required fields: {', '.join(missing)}.\n"
                            f"Please respond again using ALL required fields.\n"
                            f"Format:\n"
                            f"【TEXT】...\n"
                            f"【TTS_READING】... (LATIN SCRIPT ONLY!)\n"
                            f"【PRONUNCIATION】...\n"
                            f"【TRANSLATION】...\n"
                            f"【EXPLANATION】...\n"
                            f"【EXERCISE】..."
                        )
                        # The last user message is the original request
                        retry_messages = list(chat_data.get("messages", []))
                        # Add the model's incomplete response for context
                        retry_messages.append({"role": "assistant", "content": cleaned})
                        retry_messages.append({"role": "user", "content": retry_text})
                        
                        new_content = _call_llama(retry_messages, n_predict=512, temperature=0.6)
                        if not new_content:
                            log_err("Teacher retry: LLM returned empty, using original response")
                            break
                        cleaned = re.sub(r'<think>[\s\S]*?</think>\s*', '', new_content).strip()
                        if not cleaned:
                            cleaned = new_content
                    
                    # After retries, re-parse one final time
                    parsed = parse_multi_output(cleaned)
                    # Log result
                    if teacher_retries > 0:
                        log_info(f"Teacher: {teacher_retries} retries used, fields: {list(parsed.keys())}")
                
                # Build final result
                final_result = {
                    "choices": [{"message": {"content": cleaned}}],
                    "usage": result.get("usage", {}),
                    "mode": mode,
                    "tool_calls_used": tool_round,
                    "retries": teacher_retries if mode == 'teacher' else 0,
                }
                if parsed:
                    final_result['parsed'] = parsed
                if correction:
                    final_result['correction'] = correction

                # ── Auto-save to history ──
                conv_id = data.get('conv_id', '')
                user_text = data.get('text', '')
                # Find the last user message from messages
                if not user_text and 'messages' in data:
                    for msg in reversed(data['messages']):
                        if msg.get('role') == 'user':
                            user_text = msg.get('content', '')
                            break
                if user_text and cleaned and len(cleaned) > 10:
                    try:
                        new_id = history_mod.auto_save_exchange(
                            conv_id=conv_id,
                            mode=mode,
                            user_message=user_text,
                            assistant_message=cleaned,
                            parsed=parsed if mode == 'teacher' else None,
                        )
                        if new_id:
                            final_result['conv_id'] = new_id
                    except Exception as e:
                        log_err(f"History save failed: {e}")

                # Cache: conversation mode preserves 📝 section for re-parsing
                #         teacher mode uses post-retry cleaned response
                if mode == 'conversation':
                    cache_content = content.strip()  # Preserve 📝 for re-parse on cache hit
                else:
                    cache_content = cleaned.strip()  # Use post-retry version
                if cache_content and len(cache_content) > 20:
                    _response_cache.put(chat_data.get("messages", []), cache_content)
                self._json_response(final_result)

        except urllib.error.HTTPError as e:
            err = e.read().decode(errors='replace')[:500]
            log_err(f"llama-server HTTP {e.code}: {err[:100]}")
            self._json_response({"error": f"HTTP {e.code}: {err}"})
        except Exception as e:
            log_err(f"{type(e).__name__}: {e}")
            self._json_response({"error": str(e)[:300]})

    def _handle_tts(self, body):
        """TTS híbrido: Kokoro-82M (primario, streaming real) → Piper (fallback).
        
        Estrategia:
        1. Kokoro: mejor calidad, streaming real (~2.5x EN, 1.0x ES)
        2. Piper: ~45ms, siempre disponible como respaldo
        3. subprocess Piper: último recurso
        
        Siempre aplica _force_latin_text() para garantizar que Kokoro/Piper
        reciban solo caracteres pronunciables. Si tras sanitizar no queda
        texto útil, retorna silenciosamente en vez de error.
        """
        global _piper_tts
        t0 = time.time()
        try:
            data = json.loads(body)
            text = data.get("text", "").strip()
            lang = data.get("lang", "auto")
            mode = data.get("mode", "conversation")
            
            # If mode is teacher, extract only the TTS-relevant text
            if mode == 'teacher':
                text = get_tts_text(text, mode)
            if not text:
                self._json_response({"error": "texto vacio"})
                return

            # Forzar Latin: eliminar CJK, árabe, cirílico, etc.
            text = _force_latin_text(text)
            if not text or len(text) < 2:
                log_warn(f"TTS: texto sin caracteres Latin tras sanitizar, saltando")
                self._json_response({"ok": False, "reason": "latin_empty", "error": "Texto sin caracteres Latin pronunciables"})
                return

            # Determinar idioma
            if lang not in ('es', 'en'):
                detected = detect_language(text)
                lang = detected if detected in ('es', 'en') else 'es'

            wav_data = None
            method = "kokoro"
            
            # ── 1. Kokoro-82M (primario) ──
            if HAVE_KOKORO:
                pipeline, voice = _get_kokoro_pipeline(lang)
                if pipeline and voice:
                    try:
                        generator = pipeline(text, voice=voice, speed=1)
                        audio_chunks = []
                        for gs, ps, audio in generator:
                            if audio is not None and len(audio) > 0:
                                audio_chunks.append(np.asarray(audio, dtype=np.float32))
                        
                        if audio_chunks:
                            full_audio = np.concatenate(audio_chunks)
                            full_audio = np.clip(full_audio, -1.0, 1.0)
                            full_int16 = (full_audio * 32767).astype(np.int16)
                            
                            data_size = len(full_int16) * 2
                            buf = bytearray(44 + data_size)
                            buf[0:4] = b'RIFF'
                            struct.pack_into('<I', buf, 4, data_size + 36)
                            buf[8:12] = b'WAVE'
                            buf[12:16] = b'fmt '
                            struct.pack_into('<I', buf, 16, 16)
                            struct.pack_into('<H', buf, 20, 1)
                            struct.pack_into('<H', buf, 22, 1)
                            struct.pack_into('<I', buf, 24, 24000)
                            struct.pack_into('<I', buf, 28, 48000)
                            struct.pack_into('<H', buf, 32, 2)
                            struct.pack_into('<H', buf, 34, 16)
                            buf[36:40] = b'data'
                            struct.pack_into('<I', buf, 40, data_size)
                            buf[44:44+data_size] = full_int16.tobytes()
                            wav_data = bytes(buf)
                            method = "kokoro"
                    except Exception as e:
                        log_err(f"Kokoro falló: {e}")
                        method = "kokoro_fallback"
            
            # ── 2. Piper Python API (fallback) ──
            if wav_data is None or len(wav_data) < 100:
                if _piper_tts and _piper_tts.available:
                    wav_data = _piper_tts.synthesize(text, lang)
                    method = "piper_python_api"
            
            # ── 3. Piper subprocess (último recurso) — Linux/Win compatible ──
            if wav_data is None or len(wav_data) < 100:
                if IS_LINUX:
                    piper_exe = shutil.which("piper") or PROJECT_ROOT / "bin" / "piper" / "piper"
                else:
                    piper_exe = PROJECT_ROOT / "bin" / "piper" / "piper.exe"
                es_model = PROJECT_ROOT / "models" / "es_ES-sharvard-medium.onnx"
                en_model = PROJECT_ROOT / "models" / "en_US-lessac-medium.onnx"
                mp = en_model if lang == 'en' and en_model.exists() else es_model
                if piper_exe.exists():
                    wav_data = _run_piper_file(text, mp, piper_exe)
                    method = "subprocess_fallback"

            if not wav_data or len(wav_data) < 100:
                self._json_response({"error": "No se genero audio"})
                return

            dur = round((time.time() - t0) * 1000)
            log_info(f"TTS: {len(wav_data)}B en {dur}ms ({method})")
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(wav_data)))
            self.end_headers()
            self.wfile.write(wav_data)

        except Exception as e:
            log_err(f"TTS: {e}")
            self._json_response({"error": str(e)[:200]})

    def _handle_tts_stream(self, body):
        """Streaming TTS híbrido: Kokoro-82M (primario) → Piper (fallback).
        
        Kokoro genera audio chunk por chunk (cada segmento de texto).
        Cada chunk se envía al cliente en cuanto está listo.
        Si Kokoro no está disponible, cae en Piper streaming.
        
        Siempre aplica _force_latin_text() para garantizar que Kokoro/Piper
        reciban solo caracteres pronunciables.
        """
        global _piper_tts
        t0 = time.time()
        headers_sent = False
        engine_used = ""
        try:
            data = json.loads(body)
            text = data.get("text", "").strip()
            lang = data.get("lang", "auto")
            if not text:
                self._json_response({"error": "texto vacio"})
                return
            # Forzar Latin: eliminar CJK, árabe, cirílico, etc.
            text = _force_latin_text(text)
            if not text or len(text) < 2:
                log_warn(f"TTS-stream: texto sin caracteres Latin tras sanitizar, saltando")
                self._json_response({"ok": False, "reason": "latin_empty", "error": "Texto sin caracteres Latin pronunciables"})
                return

            if lang not in ('es', 'en'):
                detected = detect_language(text)
                lang = detected if detected in ('es', 'en') else 'es'

            total_pcm = 0
            stream = None
            
            # ── 1. Kokoro streaming ──
            if HAVE_KOKORO:
                pipeline, voice = _get_kokoro_pipeline(lang)
                if pipeline and voice:
                    stream = _kokoro_synthesize_stream(text, lang)
                    engine_used = "kokoro"
            
            # ── 2. Piper streaming (fallback si Kokoro no disponible) ──
            if stream is None:
                if _piper_tts and _piper_tts.available:
                    stream = _piper_tts.synthesize_stream(text, lang)
                    engine_used = "piper"
                else:
                    self._json_response({"error": "TTS no disponible"})
                    return

            for sr, pcm in stream:
                if not headers_sent:
                    self.send_response(200)
                    self.send_header("Content-Type", "audio/L16")
                    self.send_header("X-Sample-Rate", str(sr))
                    self.send_header("X-Channels", "1")
                    self.send_header("X-Bits-Per-Sample", "16")
                    self.send_header("X-TTS-Engine", engine_used)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    headers_sent = True
                self.wfile.write(pcm)
                self.wfile.flush()
                total_pcm += len(pcm)
            dur = round((time.time() - t0) * 1000)
            log_info(f"TTS-stream: {total_pcm}B en {dur}ms ({engine_used})")
        except Exception as e:
            log_err(f"TTS-stream: {e}")
            if not headers_sent:
                self._json_response({"error": str(e)[:200]})

    def _handle_web_search(self, body):
        """Endpoint de búsqueda web DuckDuckGo. 
        
        Acepta: {"query": "texto de búsqueda", "max": 5}
        Retorna: {"results": [...], "count": N} o {"error": "..."}
        """
        try:
            data = json.loads(body)
            query = data.get("query", "").strip()
            max_results = min(data.get("max", 5), 10)
            if not query:
                self._json_response({"error": "query vacía"})
                return
            result_str = web_search(query, max_results)
            if result_str:
                self._json_response({
                    "ok": True,
                    "results": result_str,
                    "count": result_str.count("["),
                })
            else:
                self._json_response({"ok": False, "results": "", "count": 0})
        except Exception as e:
            self._json_response({"error": str(e)[:200]})

    def _handle_asr(self, body):
        """ASR con faster-whisper. Auto-switch: base (ES/EN), small (JA)."""
        t0 = time.time()
        lang = "auto"
        try:
            data = json.loads(body)
            audio_b64 = data.get("audio", "")
            lang = data.get("lang", "auto")
            if not audio_b64:
                self._json_response({"error": "No audio"})
                return
            raw_audio = base64.b64decode(audio_b64)
        except Exception as e:
            self._json_response({"error": f"Error: {str(e)[:100]}"})
            return

        if len(raw_audio) < 100:
            self._json_response({"error": "Audio demasiado pequeño"})
            return

        text_result = None
        segments_result = None
        error_msg = None
        method_used = "faster-whisper"

        if HAVE_FASTER_WHISPER and _get_asr_model("small") is not None:
            try:
                text_result, segments_result, error_msg = _asr_transcribe(raw_audio, lang)
            except Exception as e:
                error_msg = str(e)[:200]

        if not text_result:
            error_msg = error_msg or "ASR no disponible"
            self._json_response({"error": error_msg})
            return

        dur = round((time.time() - t0) * 1000)
        log_info(f"ASR: {len(text_result)} chars en {dur}ms ({method_used})")
        self._json_response({
            "text": text_result,
            "segments": segments_result or [],
            "language": lang,
            "duration_ms": dur,
        })

    def _json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _serve_file(self, rel_path):
        fp = FRONTEND_DIR / rel_path
        if fp.exists():
            self.path = f"/{rel_path}"
            super().do_GET()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")

    def log_message(self, fmt, *args):
        msg = fmt % args
        if "/api/stats" not in msg:
            _log("DEBUG", f"HTTP {msg}")

# ── Entry point ────────────────────────────────────────────
def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    global _stats_collector
    _stats_collector = StatsCollector()
    httpd = HTTPServer(("0.0.0.0", PORT), Handler)

    mode_name = SERVER_MODE if SERVER_MODE else "teacher"
    mode_label = {'teacher': '🎓 Teacher', 'conversation': '💬 Conversación'}.get(mode_name, mode_name)
    log_info(f"{'='*50}")
    log_info(f"  Alex Voice — {mode_label} (GPU+CPU)")
    log_info(f"{'='*50}")
    log_info(f"  Mode:         {mode_label}")
    log_info(f"  Web UI:       http://localhost:{PORT}")
    log_info(f"  Stats API:    http://localhost:{PORT}/api/stats")
    log_info(f"  llama-server: {LLAMA_HOST}")
    log_info(f"  Cache:        LRU {_response_cache._maxsize} entradas")
    tts_str = "Kokoro-82M (principal)" if HAVE_KOKORO else "Piper"
    log_info(f"  TTS:          {tts_str}")
    log_info(f"  ASR:          Whisper small (GPU, ~1.5 GB VRAM)")
    web_str = "✅ DuckDuckGo" if HAVE_WEB else "❌ No disponible"
    log_info(f"  Web Search:   {web_str}")
    tool_str = "✅ Qwen3.5-2B (web_search)" if HAVE_WEB else "❌ No disponible"
    log_info(f"  Tool Calling: {tool_str}")
    log_info(f"{'='*50}\n")

    if HAVE_FASTER_WHISPER:
        log_info("Cargando Whisper small...")
        _get_asr_model("small")

    # Cargar Piper TTS
    global _piper_tts
    es_model = PROJECT_ROOT / "models" / "es_ES-sharvard-medium.onnx"
    en_model = PROJECT_ROOT / "models" / "en_US-lessac-medium.onnx"
    if es_model.exists() or en_model.exists():
        _piper_tts = PiperTTS(
            es_model_path=es_model if es_model.exists() else None,
            en_model_path=en_model if en_model.exists() else None,
        )
        if _piper_tts and _piper_tts.available:
            log_ok("Piper listo")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log_info("Deteniendo...")
    finally:
        _stats_collector.stop()
        if _piper_tts:
            _piper_tts.stop()
        httpd.server_close()
        if HAVE_NVML:
            try: pynvml.nvmlShutdown()
            except: pass
        log_info("Detenido.")

if __name__ == "__main__":
    main()
