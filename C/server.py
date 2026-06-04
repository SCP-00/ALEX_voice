#!/usr/bin/env python3
"""
Alex Voice — Plan C: Full Speech Pipeline
Servidor independiente. Enfoque en pipeline completo de voz.
Corre en puerto 3002.
"""

import json
import os
import re
import base64
import struct
import time
import threading
import subprocess
import urllib.request
import urllib.error
import numpy as np
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from collections import OrderedDict

# ── Shared translator module ──────────────────────────────
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.translator import parse_multi_output, get_tts_text, get_system_prompt, build_llm_messages, detect_language_simple

# ── LRU Cache ──────────────────────────────────────────────
class ResponseCache:
    """LRU cache thread-safe para respuestas del LLM."""
    def __init__(self, maxsize=100):
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
PORT = int(os.environ.get("PLAN_C_PORT", "3002"))
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
PROJECT_ROOT = Path(__file__).parent.parent

def _safe_print(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            print(msg.encode('ascii', errors='replace').decode('ascii'))
        except Exception:
            pass

# ── Dependencias opcionales ────────────────────────────────
try:
    import psutil
    HAVE_PSUTIL = True
except ImportError:
    HAVE_PSUTIL = False
    _safe_print("[C] [!] psutil no instalado. Stats no disponibles.")

HAVE_NVML = False
try:
    import pynvml
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    name = pynvml.nvmlDeviceGetName(handle)
    if isinstance(name, bytes):
        name = name.decode('utf-8', errors='replace')
    HAVE_NVML = True
    _safe_print(f"[C] [OK] GPU: {str(name).replace(chr(0),'').strip()}")
except Exception:
    HAVE_NVML = False
    _safe_print("[C] [!] pynvml no disponible. Stats GPU no disponibles.")

# ── Kokoro-82M TTS (opcional) ─────────────────────────────
HAVE_KOKORO = False
KOKORO_PIPELINES = {}
KOKORO_LOCK = threading.Lock()

try:
    from kokoro import KPipeline
    HAVE_KOKORO = True
except ImportError:
    _safe_print("[C] [!] kokoro no instalado. Usando Piper.")

KOKORO_CONFIG = {
    'es': {'code': 'e', 'voice': 'ef_dora'},
    'en': {'code': 'a', 'voice': 'af_heart'},
}

def _get_kokoro_pipeline(lang):
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
            pipeline = KPipeline(lang_code=code, repo_id='hexgrad/Kokoro-82M')
            _safe_print(f"[C] [Kokoro] {lang} cargado en {(time.time()-t0)*1000:.0f}ms")
            KOKORO_PIPELINES[code] = pipeline
            return pipeline, voice
        except Exception as e:
            _safe_print(f"[C] [Kokoro] Error {lang}: {e}")
            return None, None

def _kokoro_synthesize_stream(text, lang):
    pipeline, voice = _get_kokoro_pipeline(lang)
    if pipeline is None:
        return
    try:
        generator = pipeline(text, voice=voice, speed=1)
        for gs, ps, audio in generator:
            if audio is None or len(audio) == 0:
                continue
            audio_float32 = np.asarray(audio, dtype=np.float32)
            audio_float32 = np.clip(audio_float32, -1.0, 1.0)
            audio_int16 = (audio_float32 * 32767).astype(np.int16)
            yield (24000, audio_int16.tobytes())
    except Exception as e:
        _safe_print(f"[C] [Kokoro] Stream error: {e}")

# ── Piper TTS Python API ───────────────────────────────────
HAVE_PIPER_PYTHON = False
try:
    from piper import PiperVoice
    HAVE_PIPER_PYTHON = True
except ImportError:
    _safe_print("[C] [!] piper-tts no instalado.")

class PiperTTS:
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
                _safe_print(f"[C] [Piper] ES cargado en {(time.time()-t0)*1000:.0f}ms")
            except Exception as e:
                _safe_print(f"[C] [Piper] Error ES: {e}")
        if self.en_model_path:
            try:
                t0 = time.time()
                self.en_voice = PiperVoice.load(self.en_model_path, use_cuda=False)
                _safe_print(f"[C] [Piper] EN cargado en {(time.time()-t0)*1000:.0f}ms")
            except Exception as e:
                _safe_print(f"[C] [Piper] Error EN: {e}")
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
                _safe_print(f"[C] [Piper] Error: {e}")
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
                _safe_print(f"[C] [Piper] Stream error: {e}")

    def stop(self):
        self.es_voice = None
        self.en_voice = None
        self.available = False

# ── TTS híbrido unificado ──────────────────────────────────
def _run_piper_file(text, model_path, piper_exe):
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
    except Exception:
        return None

# ── ASR (faster-whisper) ───────────────────────────────────
HAVE_FASTER_WHISPER = False
_asr_models = {}
_asr_lock = threading.Lock()

try:
    from faster_whisper import WhisperModel
    HAVE_FASTER_WHISPER = True
except ImportError:
    _safe_print("[C] [!] faster-whisper no instalado.")

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
            model = WhisperModel(model_name, device="cpu", compute_type="int8")
            _safe_print(f"[C] [ASR] faster-whisper {model_name} cargado en {(time.time()-t0)*1000:.0f}ms")
            _asr_models[model_name] = model
            return model
        except Exception as e:
            _safe_print(f"[C] [!] Error cargando {model_name}: {e}")
            return None

def _asr_transcribe(audio_bytes, language="auto", model_name="base"):
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
    if not text.strip():
        return 'en'
    ja_chars = sum(1 for c in text if '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff')
    if ja_chars > 0:
        return 'ja'
    es_word_set = {
        'hola','gracias','como','estas','muy','bien','que','el','la','los','las',
        'por','para','con','sin','es','son','del','mas','todo','casa','agua',
        'vida','mundo','dia','noche','hoy','ayer','manana','adios','luego',
        'entonces','tambien','solo','cada','bienvenido','amigo','hablar','tener',
        'hacer','poder','saber','querer','bueno','grande','mejor','siempre',
        'nunca','donde','cuando','porque','quien','año','semana','mes','saludos',
        'favor','permiso','disculpa','siento','perdon','feliz','contento',
        'nosotros','ellos','este','esta','ese','esa','aquel','pensar','creer',
        'gustar','trabajar','estudiar','aprender','entender','conocer','buscar',
        'encontrar','perder','ganar','pagar','llevar','traer','dejar','entrar',
        'salir','abrir','cerrar','empezar','terminar',
    }
    es_chars = sum(1 for c in text if '\u00e1' <= c <= '\u00fa' or c in 'ñçüöéèêëàâîôùû¿¡')
    words = [w.strip('.,!?;:\'"()[]{}') for w in text.lower().split() if w.strip('.,!?;:\'"()[]{}')]
    if not words:
        return 'en'
    es_count = sum(1 for w in words if w in es_word_set)
    if es_count > 0 or es_chars > 0:
        return 'es'
    return 'en'

# ── Servidor HTTP ───────────────────────────────────────────
_stats_collector = None
_response_cache = ResponseCache(maxsize=100)
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
        elif self.path in ("/", "/index.html"):
            self._serve_file("plan-c/index.html")
        else:
            super().do_GET()

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
        elif self.path == "/api/translate":
            self._handle_translate(body)
        elif self.path == "/api/parse":
            self._handle_parse(body)
        elif self.path == "/api/tts":
            self._handle_tts(body)
        elif self.path == "/api/tts/stream":
            self._handle_tts_stream(body)
        elif self.path == "/api/asr":
            self._handle_asr(body)
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_chat(self, body):
        """Proxy a llama-server con caché LRU y multi-output parsing."""
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
                chat_data = data
            else:
                user_text = data.get('text', '')
                sys_prompt = get_system_prompt(mode)
                messages = [{'role': 'system', 'content': sys_prompt}]
                user_content = user_text
                if target_lang:
                    user_content = f"{user_text}\n[Target language: {target_lang}]"
                messages.append({'role': 'user', 'content': user_content})
                chat_data = {
                    "messages": messages,
                    "n_predict": data.get("n_predict", 1024),
                    "temperature": data.get("temperature", {
                        'teacher': 0.5, 'translator': 0.3, 'conversation': 0.7
                    }.get(mode, 0.7)),
                    "stream": data.get("stream", False),
                }

            if not chat_data.get("stream"):
                cached = _response_cache.get(chat_data.get("messages", []))
                if cached:
                    _safe_print(f"[C] [proxy] Cache HIT! {len(cached)} chars")
                    result = {
                        "choices": [{"message": {"content": cached}}],
                        "usage": {"completion_tokens": 0, "prompt_tokens": 0},
                        "cached": True,
                    }
                    self._json_response(result)
                    return

            target = f"{LLAMA_HOST}/chat/completions"
            req = urllib.request.Request(
                target,
                data=json.dumps(chat_data).encode(),
                headers={"Content-Type": "application/json"},
            )

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
                with urllib.request.urlopen(req, timeout=120) as resp:
                    result = json.loads(resp.read().decode())
                content = ""
                choices = result.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                cleaned = re.sub(r'<think>[\s\S]*?</think>\s*', '', content).strip()
                if not cleaned:
                    cleaned = content
                parsed = parse_multi_output(cleaned) if mode in ('teacher', 'translator') else {}
                if choices:
                    choices[0]["message"]["content"] = cleaned
                if parsed:
                    result['parsed'] = parsed
                result['mode'] = mode
                if cleaned and len(cleaned) > 20:
                    _response_cache.put(chat_data.get("messages", []), cleaned)
                self._json_response(result)

        except urllib.error.HTTPError as e:
            err = e.read().decode(errors='replace')[:500]
            _safe_print(f"[C] [proxy] llama-server HTTP {e.code}")
            self._json_response({"error": f"HTTP {e.code}: {err}"})
        except Exception as e:
            _safe_print(f"[C] [proxy] {type(e).__name__}: {e}")
            self._json_response({"error": str(e)[:300]})

    def _handle_translate(self, body):
        """Endpoint dedicado para traduccion con multi-output parsing."""
        try:
            data = json.loads(body)
            text = data.get('text', '').strip()
            mode = data.get('mode', 'translator')
            target_lang = data.get('target_lang', '')
            if not text:
                self._json_response({'error': 'Texto vacio'})
                return

            sys_prompt = get_system_prompt(mode)
            if not target_lang and mode == 'translator':
                detected = detect_language_simple(text)
                target_lang = 'es' if detected == 'en' else 'en'
            messages = build_llm_messages(sys_prompt, [], text, mode, target_lang)
            chat_data = {"messages": messages, "n_predict": 512,
                        "temperature": 0.3 if mode == 'translator' else 0.5, "stream": False}
            target = f"{LLAMA_HOST}/chat/completions"
            req = urllib.request.Request(target, data=json.dumps(chat_data).encode(),
                                        headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode())
            content = (result.get("choices", [{}])[0].get("message", {})).get("content", "")
            cleaned = re.sub(r'<think>[\s\S]*?</think>\s*', '', content).strip()
            if not cleaned: cleaned = content
            parsed = parse_multi_output(cleaned)
            tts_text = get_tts_text(cleaned, mode)
            self._json_response({'text': cleaned, 'parsed': parsed, 'tts_text': tts_text,
                               'mode': mode, 'target_lang': target_lang})
        except Exception as e:
            _safe_print(f"[C] [translate] Error: {e}")
            self._json_response({'error': str(e)[:300]})

    def _handle_parse(self, body):
        """Parse a raw LLM response into multi-output format."""
        try:
            data = json.loads(body)
            text = data.get('text', '')
            mode = data.get('mode', 'conversation')
            parsed = parse_multi_output(text)
            tts_text = get_tts_text(text, mode)
            self._json_response({'parsed': parsed, 'tts_text': tts_text})
        except Exception as e:
            self._json_response({'error': str(e)[:200]})

    def _handle_tts(self, body):
        """TTS híbrido: Kokoro (primario) → Piper (fallback) → subprocess."""
        global _piper_tts
        t0 = time.time()
        try:
            data = json.loads(body)
            text = data.get("text", "").strip()
            lang = data.get("lang", "auto")
            mode = data.get("mode", "conversation")
            if mode in ('teacher', 'translator'):
                text = get_tts_text(text, mode)
            if not text:
                self._json_response({"error": "texto vacio"})
                return
            if lang not in ('es', 'en'):
                detected = detect_language(text)
                lang = detected if detected in ('es', 'en') else 'es'

            wav_data = None
            method = ""

            # 1. Kokoro
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
                            full_audio = np.clip(np.concatenate(audio_chunks), -1.0, 1.0)
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
                        _safe_print(f"[C] [TTS] Kokoro falló: {e}")

            # 2. Piper Python API
            if wav_data is None or len(wav_data) < 100:
                if _piper_tts and _piper_tts.available:
                    wav_data = _piper_tts.synthesize(text, lang)
                    method = "piper_python_api"

            # 3. Piper subprocess
            if wav_data is None or len(wav_data) < 100:
                piper_exe = PROJECT_ROOT / "bin" / "piper" / "piper.exe"
                es_model = PROJECT_ROOT / "models" / "es_ES-sharvard-medium.onnx"
                en_model = PROJECT_ROOT / "models" / "en_US-lessac-medium.onnx"
                mp = en_model if lang == 'en' and en_model.exists() else es_model
                wav_data = _run_piper_file(text, mp, piper_exe)
                method = "subprocess"

            if not wav_data or len(wav_data) < 100:
                self._json_response({"error": "No se genero audio"})
                return

            dur = round((time.time() - t0) * 1000)
            _safe_print(f"[C] [TTS] {len(wav_data)}B en {dur}ms ({method})")
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(wav_data)))
            self.end_headers()
            self.wfile.write(wav_data)

        except Exception as e:
            _safe_print(f"[C] [TTS] Error: {e}")
            self._json_response({"error": str(e)[:200]})

    def _handle_tts_stream(self, body):
        """Streaming TTS: Kokoro (primario) → Piper (fallback)."""
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
            if lang not in ('es', 'en'):
                detected = detect_language(text)
                lang = detected if detected in ('es', 'en') else 'es'

            total_pcm = 0
            stream = None

            if HAVE_KOKORO:
                pipeline, voice = _get_kokoro_pipeline(lang)
                if pipeline and voice:
                    stream = _kokoro_synthesize_stream(text, lang)
                    engine_used = "kokoro"

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
            _safe_print(f"[C] [TTS-stream] {total_pcm}B en {dur}ms ({engine_used})")
        except Exception as e:
            _safe_print(f"[C] [TTS-stream] Error: {e}")
            if not headers_sent:
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

        if HAVE_FASTER_WHISPER and _get_asr_model("base") is not None:
            initial = "small" if lang == "ja" else "base"
            try:
                text_result, segments_result, error_msg = _asr_transcribe(raw_audio, lang, initial)
            except Exception as e:
                error_msg = str(e)[:200]

            if text_result and lang == "auto":
                has_ja = any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in text_result)
                if has_ja and initial != "small":
                    _safe_print(f"[C] [ASR] JA detectado → small")
                    try:
                        t2, s2, _ = _asr_transcribe(raw_audio, "ja", "small")
                        if t2:
                            text_result, segments_result = t2, s2
                            error_msg = None
                            method_used = "faster-whisper-auto-ja"
                    except Exception:
                        pass

        if not text_result:
            error_msg = error_msg or "ASR no disponible"
            self._json_response({"error": error_msg})
            return

        dur = round((time.time() - t0) * 1000)
        _safe_print(f"[C] [ASR] {len(text_result)} chars en {dur}ms ({method_used})")
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
            _safe_print(f"[C] {msg}")

# ── Entry point ────────────────────────────────────────────
def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    global _stats_collector
    _stats_collector = StatsCollector()
    httpd = HTTPServer(("0.0.0.0", PORT), Handler)

    _safe_print(f"\n{'='*50}")
    _safe_print(f"  >> Alex Voice — Plan C (Full Speech Pipeline)")
    _safe_print(f"{'='*50}")
    _safe_print(f"  Web UI:       http://localhost:{PORT}")
    _safe_print(f"  Stats API:    http://localhost:{PORT}/api/stats")
    _safe_print(f"  llama-server: {LLAMA_HOST}")
    _safe_print(f"  Cache:        LRU {_response_cache._maxsize} entradas")
    tts_str = "Kokoro-82M + Piper" if HAVE_KOKORO else "Piper Python API (~45ms)"
    _safe_print(f"  TTS:          {tts_str}")
    _safe_print(f"  ASR:          faster-whisper (base + small auto-switch)")
    _safe_print(f"{'='*50}\n")

    # Cargar ASR base
    if HAVE_FASTER_WHISPER:
        _get_asr_model("base")

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
            _safe_print(f"[C] [Piper] Listo! Latencia ~45ms por sintesis")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        _safe_print("\n[C] Deteniendo...")
    finally:
        _stats_collector.stop()
        if _piper_tts:
            _piper_tts.stop()
        httpd.server_close()
        if HAVE_NVML:
            try: pynvml.nvmlShutdown()
            except: pass
        _safe_print("[C] Detenido.")

if __name__ == "__main__":
    main()
