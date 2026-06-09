#!/usr/bin/env python3
"""
Alex Voice — Translator Server (port 3003)
==========================================
Pipeline: Speech → ASR (faster-whisper GPU) → Translation (argos-translate CPU) → TTS (Kokoro-82M CPU)

ESTRATEGIA DE VELOCIDAD:
- Objetivo: < 10s desde que el usuario habla hasta que escucha la traducción
- TTS principal: Kokoro-82M (CPU, ~85ms latencia, calidad alta)
- TTS fallback: Qwen3-TTS 0.6B (GPU) solo para JA y otros no-Latin
- ASR: Whisper large-v3-turbo precargado en GPU
- Sin VRAM swap: Whisper siempre en GPU, Kokoro siempre en CPU

Benchmark esperado por request típica (EN→ES, 20 chars):
  ASR (Whisper) .......... ~3.0s
  Traducción (argos) ...... ~1.5s
  TTS (Kokoro) ........... ~0.5s
  Overhead HTTP ........... ~0.5s
  ─────────────────────────────
  Total ................... ~5.5s ✅ (< 10s target)
"""

import json, os, sys, time, base64, struct, threading, re
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent.resolve()
FRONTEND_DIR = PROJECT_ROOT / "frontend"
PORT = int(os.environ.get("TRANSLATOR_PORT", "3003"))

# ── Logging estructurado ──────────────────────────────────
def log(level, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [Translator] [{level}] {msg}")

def log_ok(msg):   log("OK", msg)
def log_warn(msg): log("WARN", msg)
def log_err(msg):  log("ERROR", msg)
def log_info(msg): log("INFO", msg)
def log_debug(msg):log("DEBUG", msg)

# ── KOKORO-82M TTS (CPU, ultra-rápido) ──
#   Kokoro es el TTS principal del Translator.
#   ~85ms latencia, calidad "alta" (mejor que Piper, cercano a Qwen3).
#   Solo soporta Latin + español — para JA se usa Qwen3-TTS como fallback.
HAVE_KOKORO = False
_kokoro_pipelines = {}  # lang_code -> KPipeline
_kokoro_lock = threading.Lock()

KOKORO_CONFIG = {
    'es': {'code': 'e', 'voice': 'ef_dora'},
    'en': {'code': 'a', 'voice': 'af_heart'},
}

try:
    from kokoro import KPipeline
    HAVE_KOKORO = True
    log_ok("Kokoro-82M disponible (TTS principal)")
except ImportError:
    log_warn("kokoro no instalado — TTS principal no disponible")

def _get_kokoro(lang):
    """Obtiene o carga lazy un pipeline Kokoro para el idioma."""
    if lang not in KOKORO_CONFIG or not HAVE_KOKORO:
        return None, None
    cfg = KOKORO_CONFIG[lang]
    code, voice = cfg['code'], cfg['voice']
    if code in _kokoro_pipelines:
        return _kokoro_pipelines[code], voice
    with _kokoro_lock:
        if code in _kokoro_pipelines:
            return _kokoro_pipelines[code], voice
        try:
            t0 = time.time()
            pipeline = KPipeline(lang_code=code)
            _kokoro_pipelines[code] = pipeline
            log_info(f"Kokoro {lang}: {(time.time()-t0)*1000:.0f}ms")
            return pipeline, voice
        except Exception as e:
            log_err(f"Kokoro {lang}: {e}")
            return None, None

def _kokoro_synthesize(text, lang, speed=1.0):
    """Sintetiza texto completo con Kokoro, retorna WAV bytes.
    
    Args:
        text: Texto a sintetizar
        lang: Código de idioma ('es' o 'en')
        speed: Velocidad de reproducción (0.7=lento, 1.0=natural, 1.3=rápido)
    """
    pipeline, voice = _get_kokoro(lang)
    if not pipeline or not voice:
        return None
    try:
        generator = pipeline(text, voice=voice, speed=speed)
        chunks = []
        for gs, ps, audio in generator:
            if audio is not None and len(audio) > 0:
                chunks.append(np.asarray(audio, dtype=np.float32))
        if not chunks:
            return None
        full = np.clip(np.concatenate(chunks), -1.0, 1.0)
        int16 = (full * 32767).astype(np.int16)
        data_size = len(int16) * 2
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
        buf[44:44+data_size] = int16.tobytes()
        return bytes(buf)
    except Exception as e:
        log_err(f"Kokoro synth: {e}")
        return None

# ── QWEN3-TTS (GPU) — Fallback para JA y no-Latin ──
#   Se carga BAJO DEMANDA solo cuando el texto contiene caracteres no-Latin.
#   Así ahorramos 2GB VRAM y 277s de carga para el caso común EN/ES.
_qwen3_model = None
_attn_mode = "sdpa"

try:
    import flash_attn
    _attn_mode = "flash_attention_2"
except ImportError:
    pass

def _sanitize_tts_text(text):
    """Limpia texto para Kokoro: elimina no-Latin."""
    safe = re.sub(r'[^\x00-\x7F\u00C0-\u024F\u1E00-\u1EFF\u0300-\u036F\s0-9.,!?;:\'"¡¿()\[\]{}\-–—…&@#%*+=/<>~`$€£¥°]', ' ', text)
    return re.sub(r'\s+', ' ', safe).strip()

def _needs_qwen3(text):
    """Determina si el texto necesita Qwen3-TTS (tiene caracteres no-Latin)."""
    sanitized = _sanitize_tts_text(text)
    return len(sanitized) < len(text.strip()) * 0.8  # >20% chars eliminados = necesita Qwen3

def _load_qwen3():
    """Carga Qwen3-TTS bajo demanda solo si es necesario."""
    global _qwen3_model
    if _qwen3_model is not None:
        return True
    try:
        import torch
        from qwen_tts import Qwen3TTSModel
        log_info("Cargando Qwen3-TTS 0.6B (fallback JA)...")
        t0 = time.time()
        _qwen3_model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
            device_map="cuda:0", dtype=torch.bfloat16,
            attn_implementation=_attn_mode,
        )
        log_info(f"Qwen3-TTS: {(time.time()-t0)*1000:.0f}ms, VRAM: {torch.cuda.memory_allocated()/1024**2:.0f}MB")
        return True
    except Exception as e:
        log_err(f"Error Qwen3: {e}")
        return False

def _qwen3_synthesize(text, language="Spanish", speaker="Serena"):
    """Genera audio con Qwen3-TTS para textos no-Latin (JA, ZH, etc)."""
    if not _load_qwen3():
        return None
    try:
        import torch
        with torch.inference_mode():
            wavs, sr = _qwen3_model.generate_custom_voice(
                text=text, language=language, speaker=speaker,
                max_new_tokens=2048, temperature=0.7,
            )
        torch.cuda.synchronize()
        if not wavs or len(wavs) == 0:
            return None
        audio = wavs[0]
        if hasattr(audio, 'cpu'):
            audio = audio.cpu()
        audio_np = np.asarray(audio, dtype=np.float32)
        audio_np = np.clip(audio_np, -1.0, 1.0)
        int16 = (audio_np * 32767).astype(np.int16)
        data_size = len(int16) * 2
        buf = bytearray(44 + data_size)
        buf[0:4] = b'RIFF'
        struct.pack_into('<I', buf, 4, data_size + 36)
        buf[8:12] = b'WAVE'
        buf[12:16] = b'fmt '
        struct.pack_into('<I', buf, 16, 16)
        struct.pack_into('<H', buf, 20, 1)
        struct.pack_into('<H', buf, 22, 1)
        struct.pack_into('<I', buf, 24, sr)
        struct.pack_into('<I', buf, 28, sr * 2)
        struct.pack_into('<H', buf, 32, 2)
        struct.pack_into('<H', buf, 34, 16)
        buf[36:40] = b'data'
        struct.pack_into('<I', buf, 40, data_size)
        buf[44:44+data_size] = int16.tobytes()
        return bytes(buf)
    except Exception as e:
        log_err(f"Qwen3 synth: {e}")
        return None

# ── ARGOS TRANSLATE (CPU) ──
HAVE_ARGOS = False
try:
    import argostranslate.package
    import argostranslate.translate
    HAVE_ARGOS = True
except ImportError:
    pass

_argos_lock = threading.RLock()

LANG_MAP = {
    'en': 'English', 'es': 'Spanish', 'ja': 'Japanese',
    'fr': 'French', 'ko': 'Korean', 'zh': 'Chinese', 'de': 'German', 'pt': 'Portuguese',
}
ARGOS_CODES = {'en': 'en', 'es': 'es', 'ja': 'ja', 'fr': 'fr', 'ko': 'ko', 'zh': 'zh', 'de': 'de', 'pt': 'pt'}
_argos_pkgs_loaded = False

def _ensure_lang_pair(from_code, to_code):
    if from_code == to_code or not HAVE_ARGOS:
        return from_code == to_code
    installed = argostranslate.package.get_installed_packages()
    if any(p.from_code == from_code and p.to_code == to_code for p in installed):
        return True
    with _argos_lock:
        installed = argostranslate.package.get_installed_packages()
        if any(p.from_code == from_code and p.to_code == to_code for p in installed):
            return True
        try:
            available = argostranslate.package.get_available_packages()
            pkg = next((p for p in available if p.from_code == from_code and p.to_code == to_code), None)
            if pkg:
                path = pkg.download()
                argostranslate.package.install_from_path(path)
                return True
            return False
        except:
            return False

def _install_core_pairs():
    global _argos_pkgs_loaded
    if _argos_pkgs_loaded or not HAVE_ARGOS:
        return _argos_pkgs_loaded
    with _argos_lock:
        if _argos_pkgs_loaded:
            return True
        ok = sum(1 for fc, tc in [('en','es'),('es','en'),('en','ja'),('ja','en')] if _ensure_lang_pair(fc, tc))
        _argos_pkgs_loaded = ok >= 4
        return _argos_pkgs_loaded

def translate(text, from_lang, to_lang):
    if not HAVE_ARGOS:
        return None, "argos no instalado"
    try:
        fc, tc = ARGOS_CODES.get(from_lang, from_lang), ARGOS_CODES.get(to_lang, to_lang)
        if fc == tc:
            return text, None
        if _ensure_lang_pair(fc, tc):
            return argostranslate.translate.translate(text, fc, tc), None
        if _ensure_lang_pair(fc, 'en') and _ensure_lang_pair('en', tc):
            mid = argostranslate.translate.translate(text, fc, 'en')
            if not mid:
                return None, "Pivot EN falló"
            return argostranslate.translate.translate(mid, 'en', tc), None
        return None, f"No hay ruta de {from_lang}→{to_lang}"
    except Exception as e:
        return None, str(e)[:200]

# ── ASR (faster-whisper GPU) ──
HAVE_WHISPER = False
_asr_models = {}
_asr_lock = threading.Lock()

try:
    from faster_whisper import WhisperModel
    HAVE_WHISPER = True
except ImportError:
    pass

def _get_asr(model_name="large-v3-turbo"):
    if model_name in _asr_models:
        return _asr_models[model_name]
    with _asr_lock:
        if model_name in _asr_models:
            return _asr_models[model_name]
        try:
            m = WhisperModel(model_name, device="cuda", compute_type="int8_float16")
            _asr_models[model_name] = m
            return m
        except Exception as e:
            log_err(f"Error ASR {model_name}: {e}")
            return None

def transcribe_audio(audio_b64, language="auto"):
    if not HAVE_WHISPER:
        return None, None, "faster-whisper no instalado"
    try:
        raw_audio = base64.b64decode(audio_b64)
    except:
        return None, None, "Audio inválido"
    if len(raw_audio) < 100:
        return None, None, "Audio muy pequeño"
    model = _get_asr("large-v3-turbo")
    if model is None:
        return None, None, "ASR no disponible"
    try:
        sr = 16000
        if len(raw_audio) >= 44:
            sr = struct.unpack_from('<I', raw_audio, 24)[0]
        offset = raw_audio.find(b'data', 12)
        offset = offset + 8 if offset >= 0 else 44
        pcm = raw_audio[offset:]
        pcm_int16 = np.frombuffer(pcm, dtype=np.int16)
        if len(pcm_int16) == 0:
            return None, None, "Audio vacío"
        pcm_float32 = pcm_int16.astype(np.float32) / 32768.0
        lang = None if language == "auto" else language
        segments, info = model.transcribe(
            pcm_float32, language=lang, beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=200,
                                threshold=0.5, neg_threshold=0.35, min_speech_duration_ms=200),
            condition_on_previous_text=False,
        )
        texts = [seg.text.strip() for seg in segments]
        full_text = " ".join(texts).strip()
        detected_lang = getattr(info, "language", None) or detect_language(full_text)
        return full_text, detected_lang, None
    except Exception as e:
        return None, None, str(e)[:300]

# ── Language detection ──
def detect_language(text):
    if not text.strip():
        return 'en'
    if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in text):
        return 'ja'
    es_words = {'hola','gracias','como','estas','muy','bien','que','el','la','los','las','por','para','con','sin','es','son','del','todo','casa','agua','vida'}
    words = [w.strip('.,!?;:\'"()[]{}') for w in text.lower().split() if w.strip('.,!?;:\'"()[]{}')]
    es_chars = sum(1 for c in text if '\u00e1' <= c <= '\u00fa' or c in 'ñçüöéèêëàâîôùû¿¡')
    if not words:
        return 'en'
    if sum(1 for w in words if w in es_words) > 0 or es_chars > 0:
        return 'es'
    return 'en'

# ── HTTP Handler ──
class TranslatorHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/status":
            self._json({
                "kokoro_loaded": HAVE_KOKORO,
                "qwen3_loaded": _qwen3_model is not None,
                "argos_loaded": HAVE_ARGOS,
                "whisper_loaded": HAVE_WHISPER,
                "languages": list(LANG_MAP.keys()),
            })
        elif self.path in ("/", "/index.html"):
            self.path = "/translator.html"
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        if self.path == "/api/translate":
            self._handle_translate(body)
        elif self.path == "/api/tts":
            self._handle_tts(body)
        elif self.path == "/api/asr":
            self._handle_asr(body)
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_translate(self, body):
        t_start = time.time()
        try:
            data = json.loads(body)
            text = data.get("text", "").strip()
            from_lang = data.get("from_lang", "auto")
            to_lang = data.get("to_lang", "es")
            if not text:
                self._json({"error": "Texto vacío"})
                return
            if from_lang == "auto":
                from_lang = detect_language(text)
            translation, error = translate(text, from_lang, to_lang)
            if error:
                self._json({"error": error})
                return
            log_info(f"Traducción: {len(text)} chars {from_lang}→{to_lang} en {(time.time()-t_start)*1000:.0f}ms")
            self._json({
                "original": text, "translation": translation,
                "from_lang": from_lang, "to_lang": to_lang,
                "from_lang_name": LANG_MAP.get(from_lang, from_lang),
                "to_lang_name": LANG_MAP.get(to_lang, to_lang),
                "available_languages": list(LANG_MAP.keys()),
                "total_time_ms": int((time.time() - t_start) * 1000),
            })
        except Exception as e:
            log_err(f"Translate: {e}")
            self._json({"error": str(e)[:200]})

    def _handle_tts(self, body):
        """TTS principal: Kokoro-82M (CPU, ~85ms). Fallback: Qwen3-TTS (GPU) para JA.

        Estrategia de velocidad:
        1. Intentar Kokoro primero (ultra-rápido, CPU)
        2. Si el texto tiene caracteres no-Latin (JA, ZH, KO), usar Qwen3-TTS
        3. Si Kokoro no está disponible, usar Qwen3-TTS

        Target: < 2s para TTS (ideal ~0.5s con Kokoro)
        """
        t0 = time.time()
        try:
            data = json.loads(body)
            text = data.get("text", "").strip()
            language = data.get("language", "")
            to_lang = data.get("to_lang", "es")  # idioma destino de la traducción

            if not text:
                self._json({"error": "Texto vacío"})
                return

            # Detectar si el texto necesita Qwen3 (caracteres no-Latin)
            needs_qwen = _needs_qwen3(text)

            wav_data = None
            engine = ""

            if not needs_qwen and HAVE_KOKORO:
                # Usar Kokoro (rápido, CPU) para EN/ES
                lang = 'es' if to_lang in ('es',) else 'en' if to_lang in ('en',) else 'es'
                speed = data.get("speed", 1.0)
                wav_data = _kokoro_synthesize(text, lang, speed)
                engine = "kokoro"

            if wav_data is None and HAVE_KOKORO:
                # Reintentar con Kokoro sanitizado (fallback de idioma)
                speed = data.get("speed", 1.0)
                wav_data = _kokoro_synthesize(_sanitize_tts_text(text), 'es', speed)
                engine = "kokoro_sanitized"

            if wav_data is None:
                # Fallback a Qwen3-TTS (GPU) — lento pero soporta todos los idiomas
                if _load_qwen3():
                    speaker_map = {'es': 'Serena', 'en': 'Aiden', 'ja': 'Ono_Anna'}
                    speaker = speaker_map.get(to_lang, 'Serena')
                    lang_name = LANG_MAP.get(to_lang, 'Spanish')
                    wav_data = _qwen3_synthesize(text, lang_name, speaker)
                    engine = "qwen3"

            if not wav_data or len(wav_data) < 100:
                self._json({"error": "No se generó audio"})
                return

            gen_time = (time.time() - t0) * 1000
            log_info(f"TTS: {len(text)} chars → {engine} en {gen_time:.0f}ms")
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(wav_data)))
            self.send_header("X-Generation-Time-Ms", str(int(gen_time)))
            self.send_header("X-TTS-Engine", engine)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(wav_data)

        except Exception as e:
            log_err(f"TTS: {e}")
            self._json({"error": str(e)[:200]})

    def _handle_asr(self, body):
        t0 = time.time()
        try:
            data = json.loads(body)
            audio_b64 = data.get("audio", "")
            lang = data.get("lang", "auto")
            if not audio_b64:
                self._json({"error": "No audio"})
                return
            text, whisper_lang, error = transcribe_audio(audio_b64, lang)
            if error:
                self._json({"error": error})
                return
            detected_lang = whisper_lang or detect_language(text)
            dur = (time.time() - t0) * 1000
            log_info(f"ASR: {len(text)} chars en {dur:.0f}ms ({detected_lang})")
            self._json({
                "text": text, "detected_lang": detected_lang,
                "detected_lang_name": LANG_MAP.get(detected_lang, detected_lang),
                "time_ms": int(dur),
            })
        except Exception as e:
            log_err(f"ASR: {e}")
            self._json({"error": str(e)[:200]})

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, fmt, *args):
        msg = fmt % args
        if "/api/" in msg:
            log_debug(f"HTTP {msg}")

# ── MAIN ──
def main():
    log_info(f"{'='*50}")
    log_info(f"  Alex Voice — Translator Server (objetivo <10s)")
    log_info(f"{'='*50}")
    log_info(f"  Puerto: {PORT}")
    log_info(f"  ASR:    faster-whisper large-v3-turbo (GPU, ~3.0 GB)")
    log_info(f"  TRANS:  argos-translate EN↔ES↔JA (CPU, ~1-2s)")
    log_info(f"  TTS:    Kokoro-82M (CPU, ~85ms) + Qwen3 fallback (GPU)")
    log_info(f"{'='*50}")

    # 1. Cargar Whisper large-v3-turbo en GPU (siempre)
    t0 = time.time()
    log_info("Cargando Whisper large-v3-turbo...")
    if HAVE_WHISPER:
        _get_asr("large-v3-turbo")
        log_ok(f"Whisper: {time.time()-t0:.1f}s")

    # 2. Cargar argos
    if _install_core_pairs():
        log_ok("argos EN↔ES↔JA listo")
    else:
        log_warn("argos incompleto — carga bajo demanda")

    # 3. Qwen3-TTS NO se precarga — se carga bajo demanda solo para JA.
    log_info("Qwen3-TTS: carga bajo demanda (solo para JA/no-Latin)")

    # 4. Kokoro se carga bajo demanda (lazy-load en primera request)

    # Iniciar servidor
    httpd = HTTPServer(("0.0.0.0", PORT), TranslatorHandler)
    log_ok(f"Servidor en http://localhost:{PORT}")
    log_info("Pipeline esperado ~5.5s para EN↔ES, ~13s para JA (incluye Qwen3)")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log_info("Cerrando...")
    finally:
        global _qwen3_model
        if _qwen3_model is not None:
            del _qwen3_model
            _qwen3_model = None
            import torch
            torch.cuda.empty_cache()
        httpd.server_close()
        log_info("Detenido.")

if __name__ == "__main__":
    main()
