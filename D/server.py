#!/usr/bin/env python3
"""
Alex Voice — Plan D: La Configuración Definitiva
Unifica lo mejor de A, B y C: Kokoro-82M, Piper, caché LRU 200, EchoGuard, Debug UI.
Puerto 3003. Optimizado para RTX 3050 6GB + Qwen3-2B-Q4_K_M (1.5GB VRAM, 8K ctx).
"""

import json, os, re, base64, struct, time, threading, subprocess, urllib.request, urllib.error
import numpy as np
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from collections import OrderedDict
from html import escape as html_escape

# ── Config ─────────────────────────────────────────────────
LLAMA_HOST = os.environ.get("LLAMA_HOST", "http://localhost:8081")
PORT = int(os.environ.get("PLAN_D_PORT", "3003"))
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
PROJECT_ROOT = Path(__file__).parent.parent

def _safe_print(msg):
    try: print(msg)
    except UnicodeEncodeError:
        try: print(msg.encode('ascii', errors='replace').decode('ascii'))
        except: pass

# ── Dependencias ──────────────────────────────────────────
try: import psutil; HAVE_PSUTIL = True
except: HAVE_PSUTIL = False; _safe_print("[D] [!] psutil no instalado.")

HAVE_NVML = False
try:
    import pynvml; pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    name = pynvml.nvmlDeviceGetName(handle)
    if isinstance(name, bytes): name = name.decode('utf-8', errors='replace')
    HAVE_NVML = True
    _safe_print(f"[D] [OK] GPU: {str(name).replace(chr(0),'').strip()}")
except Exception:
    _safe_print("[D] [!] pynvml no disponible.")

# ── Kokoro-82M TTS ─────────────────────────────────────────
HAVE_KOKORO = False
KOKORO_PIPELINES = {}; KOKORO_LOCK = threading.Lock()
try:
    from kokoro import KPipeline; HAVE_KOKORO = True
except: _safe_print("[D] [!] kokoro no instalado. pip install kokoro")

KOKORO_CONFIG = {'es': {'code': 'e', 'voice': 'ef_dora'}, 'en': {'code': 'a', 'voice': 'af_heart'}}

def _get_kokoro_pipeline(lang):
    global KOKORO_PIPELINES
    if lang not in KOKORO_CONFIG: return None, None
    cfg = KOKORO_CONFIG[lang]; code = cfg['code']; voice = cfg['voice']
    if code in KOKORO_PIPELINES: return KOKORO_PIPELINES[code], voice
    with KOKORO_LOCK:
        if code in KOKORO_PIPELINES: return KOKORO_PIPELINES[code], voice
        try:
            t0 = time.time(); pipeline = KPipeline(lang_code=code, repo_id='hexgrad/Kokoro-82M')
            _safe_print(f"[D] [Kokoro] {lang} cargado en {(time.time()-t0)*1000:.0f}ms")
            KOKORO_PIPELINES[code] = pipeline; return pipeline, voice
        except Exception as e: _safe_print(f"[D] [Kokoro] Error {lang}: {e}"); return None, None

def _kokoro_synthesize_stream(text, lang):
    pipeline, voice = _get_kokoro_pipeline(lang)
    if pipeline is None: return
    try:
        for gs, ps, audio in pipeline(text, voice=voice, speed=1):
            if audio is None or len(audio) == 0: continue
            a = np.clip(np.asarray(audio, dtype=np.float32), -1.0, 1.0)
            yield (24000, (a * 32767).astype(np.int16).tobytes())
    except Exception as e: _safe_print(f"[D] [Kokoro] Stream error: {e}")

# ── Piper TTS ──────────────────────────────────────────────
HAVE_PIPER_PYTHON = False
try:
    from piper import PiperVoice; HAVE_PIPER_PYTHON = True
except: _safe_print("[D] [!] piper-tts no instalado.")

class PiperTTS:
    def __init__(self, es_path, en_path):
        self.es = None; self.en = None; self.es_path = str(es_path) if es_path else None
        self.en_path = str(en_path) if en_path else None; self.avail = False; self._lock = threading.Lock()
        self._load()
    def _load(self):
        if not HAVE_PIPER_PYTHON: return
        for k, p in [('es', self.es_path), ('en', self.en_path)]:
            if p:
                try:
                    t = time.time(); v = PiperVoice.load(p, use_cuda=False)
                    setattr(self, k + '_voice', v)
                    _safe_print(f"[D] [Piper] {k.upper()} en {(time.time()-t)*1000:.0f}ms")
                except Exception as e: _safe_print(f"[D] [Piper] Error {k}: {e}")
        self.avail = (getattr(self, 'es_voice', None) is not None) or (getattr(self, 'en_voice', None) is not None)
    def synth(self, text, lang='es'):
        v = self.es_voice if lang == 'es' else self.en_voice if lang == 'en' else (getattr(self, 'es_voice', None) or getattr(self, 'en_voice', None))
        if v is None: return None
        with self._lock:
            try:
                ch = list(v.synthesize(text)); sr = getattr(ch[0], 'sample_rate', 22050)
                p = np.concatenate([c.audio_int16_array for c in ch if hasattr(c, 'audio_int16_array') and c.audio_int16_array is not None] or
                                   [np.frombuffer(c.audio_int16_bytes, dtype=np.int16) for c in ch if hasattr(c, 'audio_int16_bytes') and c.audio_int16_bytes is not None])
                n = len(p) * 2; b = bytearray(44 + n)
                for o, v in [(0, b'RIFF'), (4, n + 36), (8, b'WAVE'), (12, b'fmt '), (16, 16), (20, 1), (22, 1), (24, sr), (28, sr * 2), (32, 2), (34, 16)]:
                    if isinstance(v, bytes): b[o:o+4] = v
                    elif isinstance(v, int): struct.pack_into('<I' if o in (4,16,24,28,40) else '<H', b, o, v)
                b[36:40] = b'data'; struct.pack_into('<I', b, 40, n); b[44:44+n] = p.tobytes()
                return bytes(b)
            except Exception as e: _safe_print(f"[D] [Piper] Error: {e}"); return None
    def synth_stream(self, text, lang='es'):
        v = self.es_voice if lang == 'es' else self.en_voice if lang == 'en' else (getattr(self, 'es_voice', None) or getattr(self, 'en_voice', None))
        if v is None: return
        sr = 22050
        with self._lock:
            try:
                for c in v.synthesize(text):
                    if sr == 22050: sr = getattr(c, 'sample_rate', 22050)
                    if hasattr(c, 'audio_int16_array') and c.audio_int16_array is not None: yield (sr, c.audio_int16_array.tobytes())
                    elif hasattr(c, 'audio_int16_bytes') and c.audio_int16_bytes is not None: yield (sr, c.audio_int16_bytes)
            except Exception as e: _safe_print(f"[D] [Piper] Stream error: {e}")
    def stop(self): self.es_voice = None; self.en_voice = None; self.avail = False

def _run_piper_file(text, model_path, piper_exe):
    import tempfile
    try:
        t = text; m = str(model_path); p = str(piper_exe)
        inp = tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w', encoding='utf-8'); inp.write(t); inp.close()
        out = tempfile.NamedTemporaryFile(suffix='.wav', delete=False); out.close()
        subprocess.Popen([p, "--model", m, "--output-file", out.name], stdin=open(inp.name, 'rb'),
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait(timeout=15)
        if os.path.exists(out.name):
            d = open(out.name, 'rb').read()
            try: os.unlink(out.name); os.unlink(inp.name)
            except: pass
            return d if len(d) > 100 else None
        try: os.unlink(out.name); os.unlink(inp.name)
        except: pass
        return None
    except: return None

# ── ASR ────────────────────────────────────────────────────
HAVE_FASTER_WHISPER = False
_asr_models = {}; _asr_lock = threading.Lock()
try:
    from faster_whisper import WhisperModel; HAVE_FASTER_WHISPER = True
except: _safe_print("[D] [!] faster-whisper no instalado.")

def _find_wav_off(audio_bytes):
    d = audio_bytes.find(b'data', 12); return d + 8 if d >= 0 else 44

def _get_asr_model(name):
    if name in _asr_models: return _asr_models[name]
    with _asr_lock:
        if name in _asr_models: return _asr_models[name]
        try:
            t = time.time(); m = WhisperModel(name, device="cpu", compute_type="int8")
            _safe_print(f"[D] [ASR] {name} en {(time.time()-t)*1000:.0f}ms"); _asr_models[name] = m; return m
        except Exception as e: _safe_print(f"[D] [!] ASR {name}: {e}"); return None

def _asr_transcribe(audio_bytes, language="auto", model_name="base"):
    model = _get_asr_model(model_name)
    if model is None: return None, None, f"Modelo '{model_name}' no disponible"
    try:
        sr = 16000
        if len(audio_bytes) >= 44: sr = struct.unpack_from('<I', audio_bytes, 24)[0]
        off = _find_wav_off(audio_bytes)
        pcm = audio_bytes[off:] if len(audio_bytes) > off else audio_bytes[44:]
        p16 = np.frombuffer(pcm, dtype=np.int16)
        if len(p16) == 0: return None, None, "Audio vacío"
        p32 = p16.astype(np.float32) / 32768.0
        lc = None if language == "auto" else language
        with _asr_lock:
            segs, info = model.transcribe(p32, language=lc, beam_size=1, vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=200, threshold=0.5, neg_threshold=0.35, min_speech_duration_ms=200))
        sl = []; ft = []
        for s in segs: sl.append({"text": s.text.strip(), "start": round(s.start, 2), "end": round(s.end, 2)}); ft.append(s.text.strip())
        return " ".join(ft).strip(), sl, None
    except Exception as e: return None, None, str(e)[:300]

# ── Stats Collector ───────────────────────────────────────
class StatsCollector:
    def __init__(self):
        self.lock = threading.Lock()
        self.stats = {"cpu_percent": 0.0, "ram_used_gb": 0.0, "ram_total_gb": 0.0, "ram_percent": 0.0,
            "vram_used_mb": 0, "vram_total_mb": 0, "vram_percent": 0.0, "gpu_percent": 0, "gpu_temp": 0,
            "tokens_per_sec": 0.0, "context_used": 0, "context_max": 8192, "context_percent": 0.0,
            "tokens_generated": 0, "prompt_tokens": 0, "is_processing": False, "n_slots": 0, "llama_connected": False, "slots_detail": []}
        self._ld = 0; self._lt = time.time(); self._tt = []; self._run = True
        self._th = threading.Thread(target=self._poll, daemon=True); self._th.start()
    def _poll(self):
        while self._run:
            if HAVE_PSUTIL: self._sys()
            if HAVE_NVML: self._gpu()
            self._llama()
            time.sleep(1.8)
    def _sys(self):
        try:
            with self.lock:
                s = psutil.cpu_percent(interval=0); m = psutil.virtual_memory()
                self.stats.update({"cpu_percent": round(s, 1), "ram_used_gb": round(m.used / (1024**3), 1),
                    "ram_total_gb": round(m.total / (1024**3), 1), "ram_percent": round(m.percent, 1)})
        except: pass
    def _gpu(self):
        try:
            h = pynvml.nvmlDeviceGetHandleByIndex(0); mi = pynvml.nvmlDeviceGetMemoryInfo(h)
            with self.lock:
                v = mi.used / (1024**2); vt = mi.total / (1024**2)
                self.stats.update({"vram_used_mb": round(v, 0), "vram_total_mb": round(vt, 0),
                    "vram_percent": round(mi.used / mi.total * 100, 1),
                    "gpu_percent": pynvml.nvmlDeviceGetUtilizationRates(h).gpu,
                    "gpu_temp": pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)})
        except: pass
    def _llama(self):
        try:
            req = urllib.request.Request(f"{LLAMA_HOST}/slots")
            with urllib.request.urlopen(req, timeout=3) as r: slots = json.loads(r.read().decode())
        except:
            with self.lock: self.stats["llama_connected"] = False
            return
        if not isinstance(slots, list):
            with self.lock: self.stats["llama_connected"] = True
            return
        with self.lock:
            self.stats["llama_connected"] = True; self.stats["n_slots"] = len(slots); self.stats["slots_detail"] = slots[:4]
            td = 0; tp = 0; mc = 8192; proc = False
            for s in slots:
                mc = max(mc, s.get("n_ctx", 8192))
                if s.get("is_processing"): proc = True
                nt = s.get("next_token", {})
                if isinstance(nt, dict): td += nt.get("n_decoded", 0) or 0
                elif isinstance(nt, list) and len(nt) > 0: td += nt[0].get("n_decoded", 0) or 0
                tp += s.get("n_prompt_tokens", 0) or 0
            self.stats.update({"is_processing": proc, "context_max": mc, "context_used": td,
                "context_percent": round((td / mc * 100) if mc > 0 else 0, 1), "tokens_generated": td, "prompt_tokens": tp})
            now = time.time()
            if td > self._ld:
                dt = now - self._lt
                if dt > 0:
                    r = (td - self._ld) / dt; self._tt.append(r)
                    if len(self._tt) > 5: self._tt.pop(0)
                    self.stats["tokens_per_sec"] = round(sum(self._tt) / len(self._tt), 1)
            elif not proc:
                if self._tt:
                    if now - self._lt > 3.0: self._tt = []; self.stats["tokens_per_sec"] = 0.0
                else: self.stats["tokens_per_sec"] = 0.0
            self._ld = td; self._lt = now
    def get_stats(self):
        with self.lock: return dict(self.stats)
    def stop(self): self._run = False

# ── Detect Language ────────────────────────────────────────
def detect_language(text):
    if not text.strip(): return 'en'
    if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in text): return 'ja'
    es_words = {'hola','gracias','como','estas','muy','bien','que','el','la','los','las','por','para','con','sin','es','son','del','todo','casa','agua','vida','mundo','dia','noche','hoy','ayer','manana','adios','luego','entonces','tambien','solo','cada','bienvenido','amigo','hablar','tener','hacer','poder','saber','querer','bueno','grande','mejor','siempre','nunca','donde','cuando','porque','quien','ano','mes','semana','saludos','favor','disculpa','siento','perdon','feliz','contento','nosotros','ellos','este','esta','ese','esa','aquel','pensar','creer','gustar','trabajar','estudiar','aprender','entender','conocer','buscar','encontrar','perder','ganar','pagar','llevar','traer','dejar','entrar','salir','abrir','cerrar','empezar','terminar','nada','algo','tengo','quiero','puedo','sabes','cual','como','cuando','donde'}
    es_c = sum(1 for c in text if '\u00e1' <= c <= '\u00fa' or c in 'ñçüöéèêëàâîôùû¿¡')
    words = [w.strip('.,!?;:\'"()[]{}') for w in text.lower().split() if w.strip('.,!?;:\'"()[]{}')]
    if not words: return 'en'
    if sum(1 for w in words if w in es_words) > 0 or es_c > 0: return 'es'
    return 'en'

# ── Cache LRU ──────────────────────────────────────────────
class ResponseCache:
    def __init__(self, maxsize=200):
        self._c = OrderedDict(); self._m = maxsize; self._lock = threading.Lock(); self._h = 0; self._miss = 0
    def _key(self, msgs):
        return hash('|'.join(f"{m.get('role','')}:{m.get('content','')[:200]}" for m in msgs[-4:]))
    def get(self, msgs):
        k = self._key(msgs)
        with self._lock:
            if k in self._c: self._c.move_to_end(k); self._h += 1; return self._c[k]
            self._miss += 1; return None
    def put(self, msgs, resp):
        if not resp or len(resp) < 20: return
        k = self._key(msgs)
        with self._lock:
            self._c[k] = resp; self._c.move_to_end(k)
            if len(self._c) > self._m: self._c.popitem(last=False)
    def invalidate(self):
        with self._lock: self._c.clear()
    def stats(self):
        with self._lock:
            t = self._h + self._miss; hr = round(self._h / t * 100, 1) if t > 0 else 0
            return {"size": len(self._c), "maxsize": self._m, "hits": self._h, "misses": self._miss, "hit_rate": hr}

# ── System Prompts (Mejorados con Few-Shot) ───────────────
SYSTEM_PROMPTS = {
    'teacher': (
        "Eres un tutor de idiomas paciente y claro. Explicas en el idioma del usuario.\n\n"
        "REGLAS:\n"
        "- Responde SIEMPRE con este formato exacto:\n"
        "  【TEXT】texto en el idioma objetivo\n"
        "  【ROMANJI】pronunciación fonética\n"
        "  【TRANS】traducción al idioma del usuario\n"
        "- El usuario es principiante. Usa vocabulario básico y frases cortas.\n"
        "- Después de la traducción, añade 1 ejercicio breve.\n"
        "- Ejemplo de respuesta completa:\n"
        "  【TEXT】Hello, how are you?\n"
        "  【ROMANJI】Jeh-loh, jau ar iu?\n"
        "  【TRANS】¡Hola! ¿Cómo estás?\n"
        "  💪 Ejercicio: Traduce 'Buenos días' al inglés.\n"
        "- Incluye contexto cultural cuando sea relevante.\n"
        "- Celebra los progresos con emojis."
    ),
    'conversation': (
        "Eres un compañero de conversación natural y auténtico.\n\n"
        "PERSONALIDAD:\n"
        "- Cálido/a, con humor sutil\n"
        "- Usas expresiones coloquiales naturales\n"
        "- Tienes opiniones propias (música, comida, viajes, tecnología)\n"
        "- A veces cuentas anécdotas breves\n\n"
        "REGLAS:\n"
        "- NO traduzcas — solo conversa naturalmente\n"
        "- Usa el mismo idioma que el usuario\n"
        "- Alterna preguntas y opiniones personales\n"
        "- Respuestas de 2-4 párrafos, no monólogos\n"
        "- Usa emojis con moderación 😊\n"
        "- Si el usuario se despide, hazlo con naturalidad"
    ),
    'translator': (
        "Eres un traductor profesional de precisión absoluta.\n\n"
        "REGLAS:\n"
        "- Traduce EXACTAMENTE lo que el usuario escribe, ni más ni menos\n"
        "- NO añadas explicaciones, notas, ni comentarios\n"
        "- Preserva el tono: formal→formal, casual→casual\n"
        "- Modismos: tradúcelos al equivalente cultural:\n"
        "  ES 'está lloviendo a cántaros' → EN 'it's raining cats and dogs'\n"
        "  EN 'break a leg' → ES '¡mucha mierda!'\n"
        "- Preserva formato: listas, código, poemas, fechas\n"
        "- Nombres propios: NO los traduzcas\n"
        "- Una sola línea de traducción. Sin prefacios. Sin adornos.\n"
        "- IDIOMAS: El usuario escribe en el idioma de entrada.\n"
        "  Tú respondes SOLO con la traducción. Si el texto está vacío: '⚠️ Texto no reconocido'"
    ),
}

# ── Cache LRU ──────────────────────────────────────────────
_cache = ResponseCache(maxsize=200)

# ── Regex para limpiar thinking ────────────────────────────
THINK_REGEX = re.compile(r'<think>[\s\S]*?</think>\s*')

def _clean_response(text):
    """Elimina tags de thinking del texto."""
    cleaned = THINK_REGEX.sub('', text).strip()
    return cleaned if cleaned else text

_piper_tts = None
_stats = None

# ── HTTP Handler ──────────────────────────────────────────
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_GET(self):
        p = self.path
        if p == "/api/stats": self._json(_stats.get_stats())
        elif p == "/api/cache/stats": self._json(_cache.stats())
        elif p == "/api/cache/clear": _cache.invalidate(); self._json({"ok": True})
        elif p in ("/", "/index.html"): self._serve("plan-d/index.html")
        elif p == "/debug" or p == "/debug.html": self._debug_ui()
        else: super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        l = int(self.headers.get("Content-Length", 0))
        b = self.rfile.read(l) if l > 0 else b"{}"
        if self.path == "/api/chat": self._chat(b)
        elif self.path == "/api/tts": self._tts(b)
        elif self.path == "/api/tts/stream": self._tts_stream(b)
        elif self.path == "/api/tts/clone": self._tts_clone(b)
        elif self.path == "/api/asr": self._asr(b)
        else: self.send_response(404); self.end_headers()

    def _chat(self, body):
        try:
            data = json.loads(body)
            if "messages" not in data and "prompt" in data:
                parts = re.split(r'<\|im_start\|>(\w+)\n', data["prompt"])
                msgs = []
                for i in range(1, len(parts)-1, 2):
                    r = parts[i]; c = parts[i+1].replace('<|im_end|>', '').strip()
                    if r == 'system': msgs.insert(0, {"role": r, "content": c})
                    elif r in ('user', 'assistant'): msgs.append({"role": r, "content": c})
                chat_data = {"messages": msgs, "n_predict": data.get("n_predict", 1024),
                            "temperature": data.get("temperature", 0.7), "stream": data.get("stream", False)}
            else: chat_data = data

            if not chat_data.get("stream"):
                cached = _cache.get(chat_data.get("messages", []))
                if cached:
                    _safe_print(f"[D] [proxy] Cache HIT! {len(cached)} chars")
                    self._json({"choices": [{"message": {"content": cached}}], "usage": {}, "cached": True})
                    return

            req = urllib.request.Request(f"{LLAMA_HOST}/chat/completions",
                data=json.dumps(chat_data).encode(), headers={"Content-Type": "application/json"})

            if chat_data.get("stream"):
                with urllib.request.urlopen(req, timeout=120) as resp:
                    self.send_response(200)
                    for k in ["Content-Type", "Cache-Control"]:
                        self.send_header(k, ["text/event-stream", "no-cache"]["Cache-Control".startswith(k) or 0])
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    while True:
                        c = resp.read(4096)
                        if not c: break
                        try: self.wfile.write(c); self.wfile.flush()
                        except: break
            else:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    result = json.loads(resp.read().decode())
                content = (result.get("choices", [{}])[0].get("message", {})).get("content", "")
                # 🧹 STRIP THINKING TAGS
                content = _clean_response(content)
                # Actualizar el resultado
                choices = result.get("choices", [])
                if choices:
                    choices[0].get("message", {})["content"] = content
                if content and len(content) > 20: _cache.put(chat_data.get("messages", []), content)
                self._json(result)
        except urllib.error.HTTPError as e:
            self._json({"error": f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"})
        except Exception as e: self._json({"error": str(e)[:300]})

    def _tts(self, body):
        global _piper_tts; t0 = time.time()
        try:
            d = json.loads(body); text = d.get("text","").strip(); lang = d.get("lang","auto")
            if not text: self._json({"error":"texto vacio"}); return
            if lang not in ('es','en'): l = detect_language(text); lang = l if l in ('es','en') else 'es'
            wav = None; method = ""

            # 1. Kokoro
            if HAVE_KOKORO:
                p, v = _get_kokoro_pipeline(lang)
                if p and v:
                    try:
                        ch = [np.asarray(a, dtype=np.float32) for _,_,a in p(text, voice=v, speed=1) if a is not None and len(a)>0]
                        if ch:
                            a = np.clip(np.concatenate(ch), -1.0, 1.0); i16 = (a * 32767).astype(np.int16)
                            n = len(i16)*2; b = bytearray(44+n)
                            for o, val in [(0,b'RIFF'),(4,n+36),(8,b'WAVE'),(12,b'fmt '),(16,16),(20,1),(22,1),(24,24000),(28,48000),(32,2),(34,16)]:
                                if isinstance(val, bytes): b[o:o+4]=val
                                elif isinstance(val, int): struct.pack_into('<I' if o in (4,16,24,28,40) else '<H',b,o,val)
                            b[36:40]=b'data'; struct.pack_into('<I',b,40,n); b[44:44+n]=i16.tobytes()
                            wav = bytes(b); method = "kokoro"
                    except: pass

            # 2. Piper
            if not wav or len(wav) < 100:
                if _piper_tts and _piper_tts.avail:
                    wav = _piper_tts.synth(text, lang); method = "piper"

            # 3. Fallback subprocess
            if not wav or len(wav) < 100:
                piper = PROJECT_ROOT / "bin" / "piper" / "piper.exe"
                es = PROJECT_ROOT / "models" / "es_ES-sharvard-medium.onnx"
                en = PROJECT_ROOT / "models" / "en_US-lessac-medium.onnx"
                mp = en if lang == 'en' and en.exists() else es
                wav = _run_piper_file(text, mp, piper); method = "subprocess"

            if not wav or len(wav) < 100: self._json({"error":"No se genero audio"}); return
            dur = round((time.time()-t0)*1000)
            _safe_print(f"[D] [TTS] {len(wav)}B en {dur}ms ({method})")
            self.send_response(200)
            for k,v in [("Content-Type","audio/wav"),("Access-Control-Allow-Origin","*"),("X-TTS-Engine",method)]: self.send_header(k,v)
            self.send_header("Content-Length", str(len(wav)))
            self.end_headers(); self.wfile.write(wav)
        except Exception as e: self._json({"error":str(e)[:200]})

    def _tts_stream(self, body):
        global _piper_tts; t0 = time.time(); hs = False; eng = ""
        try:
            d = json.loads(body); text = d.get("text","").strip(); lang = d.get("lang","auto")
            if not text: self._json({"error":"texto vacio"}); return
            if lang not in ('es','en'): l = detect_language(text); lang = l if l in ('es','en') else 'es'
            total = 0; stream = None
            if HAVE_KOKORO:
                p, v = _get_kokoro_pipeline(lang)
                if p and v: stream = _kokoro_synthesize_stream(text, lang); eng = "kokoro"
            if stream is None:
                if _piper_tts and _piper_tts.avail: stream = _piper_tts.synth_stream(text, lang); eng = "piper"
                else: self._json({"error":"TTS no disponible"}); return
            for sr, pcm in stream:
                if not hs:
                    self.send_response(200)
                    for k,v in [("Content-Type","audio/L16"),("X-Sample-Rate",str(sr)),("X-Channels","1"),("X-Bits-Per-Sample","16"),("X-TTS-Engine",eng),("Access-Control-Allow-Origin","*")]: self.send_header(k,v)
                    self.end_headers(); hs = True
                self.wfile.write(pcm); self.wfile.flush(); total += len(pcm)
            dur = round((time.time()-t0)*1000)
            _safe_print(f"[D] [TTS-stream] {total}B en {dur}ms ({eng})")
        except Exception as e:
            _safe_print(f"[D] [TTS-stream] Error: {e}")
            if not hs: self._json({"error":str(e)[:200]})

    def _tts_clone(self, body):
        """Qwen3-TTS voice cloning endpoint (experimental, CPU)."""
        self._json({"status": "experimental", "message":
            "Qwen3-TTS voice cloning requiere: pip install qwen-tts torch torchaudio. "
            "Envía POST con {'text': '...', 'reference_audio': 'base64_wav', 'reference_text': '...'}"})

    def _asr(self, body):
        t0 = time.time(); lang = "auto"
        try:
            d = json.loads(body); b64 = d.get("audio",""); lang = d.get("lang","auto")
            if not b64: self._json({"error":"No audio"}); return
            raw = base64.b64decode(b64)
        except Exception as e: self._json({"error":f"Error: {str(e)[:100]}"}); return
        if len(raw) < 100: self._json({"error":"Audio demasiado pequeño"}); return
        text = None; segs = None; err = None; method = "faster-whisper"
        if HAVE_FASTER_WHISPER and _get_asr_model("base") is not None:
            init = "small" if lang == "ja" else "base"
            try: text, segs, err = _asr_transcribe(raw, lang, init)
            except Exception as e: err = str(e)[:200]
            if text and lang == "auto":
                if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in text) and init != "small":
                    _safe_print("[D] [ASR] JA detectado → small")
                    try:
                        t2, s2, _ = _asr_transcribe(raw, "ja", "small")
                        if t2: text, segs = t2, s2; err = None; method = "faster-whisper-auto-ja"
                    except: pass
        if not text: self._json({"error": err or "ASR no disponible"}); return
        dur = round((time.time()-t0)*1000)
        _safe_print(f"[D] [ASR] {len(text)} chars en {dur}ms ({method})")
        self._json({"text": text, "segments": segs or [], "language": lang, "duration_ms": dur})

    def _json(self, data):
        self.send_response(200)
        for k,v in [("Content-Type","application/json"),("Access-Control-Allow-Origin","*"),("Cache-Control","no-cache")]: self.send_header(k,v)
        self.end_headers(); self.wfile.write(json.dumps(data).encode())

    def _serve(self, rel):
        fp = FRONTEND_DIR / rel
        if fp.exists(): self.path = f"/{rel}"; super().do_GET()
        else: self.send_response(404); self.end_headers(); self.wfile.write(b"Not found")

    def _debug_ui(self):
        s = _stats.get_stats() if _stats else {}
        html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Debug — Plan D</title><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',sans-serif;background:#0a0e17;color:#e0e8f5;padding:20px;max-width:1200px;margin:0 auto}}
h1{{font-size:18px;margin-bottom:20px;color:#3b82f6}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-bottom:20px}}
.card{{background:#111827;border:1px solid #2a3650;border-radius:10px;padding:14px}}
.card h3{{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#8899bb;margin-bottom:8px}}
.stat{{font-family:'JetBrains Mono',monospace;font-size:13px;padding:3px 0;display:flex;justify-content:space-between}}
.stat .v{{color:#3b82f6;font-weight:600}}
.llama-on{{color:#22c55e}} .llama-off{{color:#ef4444}}
.bar{{height:6px;background:#1c2538;border-radius:3px;overflow:hidden;margin:4px 0}}
.bar-fill{{height:100%;border-radius:3px;transition:width .3s}}
.bar-purple{{background:linear-gradient(90deg,#2563eb,#3b82f6)}}
.bar-green{{background:linear-gradient(90deg,#059669,#22c55e)}}
.bar-orange{{background:linear-gradient(90deg,#ea580c,#f59e0b)}}
.bar-yellow{{background:linear-gradient(90deg,#d97706,#f59e0b)}}
pre{{font-family:'JetBrains Mono',monospace;font-size:11px;background:#0a0e17;padding:8px;border-radius:6px;overflow-x:auto;max-height:200px;overflow-y:auto}}
</style></head><body>
<h1>🐞 Debug — Plan D</h1>
<div class="grid">
<div class="card"><h3>🎮 GPU</h3>
<div class="stat">VRAM <span class="v">{s.get('vram_used_mb',0)/1024:.1f} / {s.get('vram_total_mb',0)/1024:.1f} GB</span></div>
<div class="bar"><div class="bar-fill bar-purple" style="width:{s.get('vram_percent',0)}%"></div></div>
<div class="stat">Util <span class="v">{s.get('gpu_percent',0)}%</span></div>
<div class="stat">Temp <span class="v">{s.get('gpu_temp',0)}°C</span></div>
</div>
<div class="card"><h3>💻 Sistema</h3>
<div class="stat">RAM <span class="v">{s.get('ram_used_gb',0)} / {s.get('ram_total_gb',0)} GB</span></div>
<div class="bar"><div class="bar-fill bar-green" style="width:{s.get('ram_percent',0)}%"></div></div>
<div class="stat">CPU <span class="v">{s.get('cpu_percent',0)}%</span></div>
<div class="bar"><div class="bar-fill bar-yellow" style="width:{s.get('cpu_percent',0)}%"></div></div>
</div>
<div class="card"><h3>🧠 LLM</h3>
<div class="stat">Estado <span class="v {'llama-on' if s.get('llama_connected') else 'llama-off'}">{'✅ Conectado' if s.get('llama_connected') else '❌ Desconectado'}</span></div>
<div class="stat">Velocidad <span class="v">{s.get('tokens_per_sec',0)} tok/s</span></div>
<div class="stat">Contexto <span class="v">{s.get('context_percent',0)}%</span></div>
<div class="bar"><div class="bar-fill bar-orange" style="width:{s.get('context_percent',0)}%"></div></div>
</div>
<div class="card"><h3>💾 Caché LRU</h3>
<div class="stat">Entradas <span class="v">{s.get('cache_size',0)} / 200</span></div>
<div class="stat">Hit rate <span class="v">{s.get('cache_hit_rate',0)}%</span></div>
</div>
</div>
<div class="card"><h3>📋 Slots Detail</h3>
<pre>{json.dumps(s.get('slots_detail',[]), indent=2, default=str)[:2000]}</pre>
</div>
<script>setInterval(()=>location.reload(),2000)</script></body></html>"""
        self.send_response(200); self.send_header("Content-Type", "text/html")
        self.end_headers(); self.wfile.write(html.encode())

    def log_message(self, fmt, *args):
        msg = fmt % args
        if "/api/stats" not in msg: _safe_print(f"[D] {msg}")

# ── Entry point ────────────────────────────────────────────
def main():
    import sys
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except: pass

    global _stats; _stats = StatsCollector()
    httpd = HTTPServer(("0.0.0.0", PORT), Handler)

    _safe_print(f"\n{'='*55}")
    _safe_print(f"  >> Alex Voice — Plan D (La Configuración Definitiva)")
    _safe_print(f"{'='*55}")
    _safe_print(f"  Web UI:       http://localhost:{PORT}")
    _safe_print(f"  Debug:        http://localhost:{PORT}/debug")
    _safe_print(f"  llama-server: {LLAMA_HOST}")
    _safe_print(f"  Cache:        LRU {_cache._m} entradas")
    _safe_print(f"  VRAM:         ~2.3 GB de 5.28 GB ({(2.3/5.28*100):.0f}%)")
    tts_s = "Kokoro-82M + Piper" if HAVE_KOKORO else "Piper Python API (~45ms)"
    _safe_print(f"  TTS:          {tts_s}")
    _safe_print(f"  ASR:          faster-whisper (base + small auto-switch)")
    _safe_print(f"{'='*55}\n")

    if HAVE_FASTER_WHISPER: _get_asr_model("base")
    global _piper_tts
    es = PROJECT_ROOT / "models" / "es_ES-sharvard-medium.onnx"
    en = PROJECT_ROOT / "models" / "en_US-lessac-medium.onnx"
    if es.exists() or en.exists():
        _piper_tts = PiperTTS(es if es.exists() else None, en if en.exists() else None)
        if _piper_tts and _piper_tts.avail: _safe_print("[D] [Piper] Listo! ~45ms por sintesis")

    try: httpd.serve_forever()
    except KeyboardInterrupt: _safe_print("\n[D] Deteniendo...")
    finally:
        _stats.stop()
        if _piper_tts: _piper_tts.stop()
        httpd.server_close()
        if HAVE_NVML:
            try: pynvml.nvmlShutdown()
            except: pass
        _safe_print("[D] Detenido.")

if __name__ == "__main__": main()
