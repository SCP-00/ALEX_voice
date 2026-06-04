#!/usr/bin/env python3
"""
Alex Voice — Translator Server (port 3003)
==========================================
Pipeline: Speech → STT (faster-whisper CPU) → Translation (argos-translate CPU) → TTS (Qwen3-TTS GPU)

Separado del servidor principal para especializacion.
Carga Qwen3-TTS en GPU bajo demanda. Traduccion corre 100% en CPU.
"""

import json, os, sys, time, base64, struct, threading, re, gc
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

import numpy as np
import torch

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent.resolve()
FRONTEND_DIR = PROJECT_ROOT / "frontend" / "translator"
PORT = int(os.environ.get("TRANSLATOR_PORT", "3003"))

# ── ARGOS TRANSLATE (CPU, lightweight) ──
HAVE_ARGOS = False
try:
    import argostranslate.package
    import argostranslate.translate
    HAVE_ARGOS = True
except ImportError:
    pass

_argos_loaded = False
_argos_lock = threading.Lock()

LANG_MAP = {
    'en': 'English',
    'es': 'Spanish',
    'ja': 'Japanese',
    'fr': 'French',
}

ARGOS_CODES = {
    'en': 'en',
    'es': 'es',
    'ja': 'ja',
}

def _ensure_argos():
    """Ensure argos packages are loaded."""
    global _argos_loaded
    if _argos_loaded:
        return True
    with _argos_lock:
        if _argos_loaded:
            return True
        if not HAVE_ARGOS:
            return False
        try:
            installed = argostranslate.package.get_installed_packages()
            needed = [('en','es'), ('es','en'), ('en','ja'), ('ja','en')]
            for fc, tc in needed:
                found = any(p.from_code == fc and p.to_code == tc for p in installed)
                if not found:
                    return False
            _argos_loaded = True
            return True
        except:
            return False

def translate(text, from_lang, to_lang):
    """Translate text using argos-translate (CPU)."""
    if not _ensure_argos():
        return None, "argos packages not installed"
    try:
        fc = ARGOS_CODES.get(from_lang, from_lang)
        tc = ARGOS_CODES.get(to_lang, to_lang)
        result = argostranslate.translate.translate(text, fc, tc)
        return result, None
    except Exception as e:
        return None, str(e)[:200]


# ── QWEN3-TTS (GPU, OPTIMIZADO) ──
HAVE_QWEN3_TTS = False
_qwen3_model = None
_qwen3_lock = threading.Lock()
_qwen3_warmup_done = False

# ── Atención optimizada: flash-attn o SDPA nativo de PyTorch ──
has_flash_attn = False
attn_mode = "sdpa"  # Default: SDPA nativo de PyTorch 2.0+ (CUDA optimizado)
try:
    import flash_attn
    has_flash_attn = True
    attn_mode = "flash_attention_2"
    print(f"[Translator] flash-attn: DISPONIBLE (aceleracion ~2-3x)")
except ImportError:
    print(f"[Translator] flash-attn: NO DISPONIBLE — usando SDPA nativo de PyTorch")
    print(f"[Translator] Para acelerar: pip install xformers  (Windows)")

try:
    import xformers
    print(f"[Translator] xformers: DISPONIBLE (optimizacion Windows)")
except ImportError:
    pass

def _load_qwen3():
    """Lazy-load Qwen3-TTS on GPU con optimizaciones."""
    global _qwen3_model, HAVE_QWEN3_TTS, _qwen3_warmup_done
    if _qwen3_model is not None:
        return True
    with _qwen3_lock:
        if _qwen3_model is not None:
            return True
        try:
            from qwen_tts import Qwen3TTSModel
            
            print(f"[Translator] Cargando Qwen3-TTS-CustomVoice en GPU...")
            print(f"[Translator] Atencion: {attn_mode}")
            t0 = time.time()
            _qwen3_model = Qwen3TTSModel.from_pretrained(
                "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
                device_map="cuda:0",
                dtype=torch.bfloat16,
                attn_implementation=attn_mode,
            )
            
            # OPTIMIZATION 1: torch.compile() para acelerar inferencia
            try:
                _qwen3_model = torch.compile(_qwen3_model, mode="reduce-overhead")
                print(f"[Translator] torch.compile aplicado (reduce-overhead)")
            except Exception as e:
                print(f"[Translator] torch.compile no disponible: {e}")
            
            load_time = time.time() - t0
            vram = torch.cuda.memory_allocated() / 1024**2
            print(f"[Translator] Modelo cargado en {load_time:.1f}s (VRAM: {vram:.0f}MB)")
            
            # OPTIMIZATION 2: Warmup pass para evitar cold-start
            print(f"[Translator] Ejecutando warmup...")
            _run_warmup()
            _qwen3_warmup_done = True
            
            HAVE_QWEN3_TTS = True
            return True
        except Exception as e:
            print(f"[Translator] Error cargando Qwen3-TTS: {e}")
            return False

def _run_warmup():
    """Warmup pass: compila kernels CUDA y pre-calcula embeddings."""
    try:
        warmup_text = "Warmup."
        warmup_lang = "English"
        with torch.inference_mode():
            wavs, sr = _qwen3_model.generate_custom_voice(
                text=warmup_text,
                language=warmup_lang,
                speaker="Vivian",
            )
        del wavs
        torch.cuda.synchronize()
        print(f"[Translator] Warmup completo")
    except Exception as e:
        print(f"[Translator] Warmup ignorado: {e}")

def _unload_qwen3():
    """Unload Qwen3-TTS from GPU to free VRAM."""
    global _qwen3_model, HAVE_QWEN3_TTS, _qwen3_warmup_done
    with _qwen3_lock:
        if _qwen3_model is not None:
            del _qwen3_model
            _qwen3_model = None
            _qwen3_warmup_done = False
            HAVE_QWEN3_TTS = False
            gc.collect()
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            print("[Translator] Qwen3-TTS descargado de GPU")

def qwen3_synthesize(text, language, speaker='Serena'):
    """Synthesize speech with Qwen3-TTS (optimizado)."""
    if not _load_qwen3():
        return None, "Qwen3-TTS not available"
    try:
        # OPTIMIZATION 3: inference_mode desactiva gradientes
        with torch.inference_mode():
            wavs, sr = _qwen3_model.generate_custom_voice(
                text=text,
                language=language,
                speaker=speaker,
            )
        if wavs and len(wavs) > 0:
            return (wavs[0], sr), None
        return None, "No audio generated"
    except Exception as e:
        return None, str(e)[:200]


# ── ASR (faster-whisper, CPU) ──
HAVE_WHISPER = False
_asr_models = {}
_asr_lock = threading.Lock()

try:
    from faster_whisper import WhisperModel
    HAVE_WHISPER = True
except ImportError:
    pass

def _get_asr(model_name="base"):
    if model_name in _asr_models:
        return _asr_models[model_name]
    with _asr_lock:
        if model_name in _asr_models:
            return _asr_models[model_name]
        try:
            m = WhisperModel(model_name, device="cpu", compute_type="int8")
            _asr_models[model_name] = m
            return m
        except Exception as e:
            print(f"[Translator] Error ASR: {e}")
            return None

def transcribe_audio(audio_b64, language="auto"):
    """Transcribe audio with faster-whisper."""
    
    if not HAVE_WHISPER:
        return None, "faster-whisper not installed"
    
    try:
        raw_audio = base64.b64decode(audio_b64)
    except:
        return None, "Invalid audio data"
    
    if len(raw_audio) < 100:
        return None, "Audio too small"
    
    model = _get_asr("base")
    if model is None:
        return None, "ASR model not available"
    
    try:
        # Parse WAV
        sr = 16000
        if len(raw_audio) >= 44:
            sr = struct.unpack_from('<I', raw_audio, 24)[0]
        offset = raw_audio.find(b'data', 12)
        offset = offset + 8 if offset >= 0 else 44
        pcm = raw_audio[offset:]
        pcm_int16 = np.frombuffer(pcm, dtype=np.int16)
        if len(pcm_int16) == 0:
            return None, "Empty audio"
        pcm_float32 = pcm_int16.astype(np.float32) / 32768.0
        lang = None if language == "auto" else language
        
        segments, info = model.transcribe(
            pcm_float32, language=lang, beam_size=1,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=200,
                                threshold=0.5, neg_threshold=0.35, min_speech_duration_ms=200),
        )
        texts = [seg.text.strip() for seg in segments]
        full_text = " ".join(texts).strip()
        return full_text, None
    except Exception as e:
        return None, str(e)[:300]


# ── LANGUAGE DETECTION ──
def detect_language(text):
    """Detect es/en/ja."""
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


# ── HTTP HANDLER ──
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
                "qwen3_loaded": _qwen3_model is not None,
                "argos_loaded": _argos_loaded,
                "whisper_loaded": HAVE_WHISPER,
                "languages": ["en", "es", "ja"],
            })
        elif self.path in ("/", "/index.html"):
            self.path = "/index.html"
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
        elif self.path == "/api/load":
            self._handle_load(body)
        elif self.path == "/api/unload":
            self._handle_unload()
        else:
            self.send_response(404)
            self.end_headers()
    
    def _handle_load(self, body):
        """Load Qwen3-TTS on demand (can be called before translate for faster first request)."""
        t0 = time.time()
        ok = _load_qwen3()
        self._json({
            "ok": ok,
            "time_ms": int((time.time() - t0) * 1000),
            "message": "Qwen3-TTS loaded on GPU" if ok else "Failed to load",
        })
    
    def _handle_unload(self):
        """Unload Qwen3-TTS to free VRAM."""
        _unload_qwen3()
        self._json({"ok": True, "message": "Qwen3-TTS unloaded"})
    
    def _handle_translate(self, body):
        """Main endpoint: detect language, translate, return results."""
        t_start = time.time()
        try:
            data = json.loads(body)
            text = data.get("text", "").strip()
            from_lang = data.get("from_lang", "auto")
            to_lang = data.get("to_lang", "es")
            
            if not text:
                self._json({"error": "Empty text"})
                return
            
            # Detect language if auto
            if from_lang == "auto":
                from_lang = detect_language(text)
            
            # Translate
            t_trans_start = time.time()
            translation, error = translate(text, from_lang, to_lang)
            trans_time = int((time.time() - t_trans_start) * 1000)
            
            if error:
                self._json({"error": error})
                return
            
            total_time = int((time.time() - t_start) * 1000)
            
            self._json({
                "original": text,
                "translation": translation,
                "from_lang": from_lang,
                "to_lang": to_lang,
                "from_lang_name": LANG_MAP.get(from_lang, from_lang),
                "to_lang_name": LANG_MAP.get(to_lang, to_lang),
                "translation_time_ms": trans_time,
                "total_time_ms": total_time,
            })
        except Exception as e:
            self._json({"error": str(e)[:200]})
    
    def _handle_tts(self, body):
        """Generate audio with Qwen3-TTS."""
        t0 = time.time()
        try:
            data = json.loads(body)
            text = data.get("text", "").strip()
            language = data.get("language", "Spanish")
            speaker = data.get("speaker", "Serena")
            
            if not text:
                self._json({"error": "Empty text"})
                return
            
            (audio, sr), error = qwen3_synthesize(text, language, speaker)
            if error:
                self._json({"error": error})
                return
            
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
            
            gen_time = int((time.time() - t0) * 1000)
            audio_secs = len(int16) / sr
            
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(buf)))
            self.send_header("X-Generation-Time-Ms", str(gen_time))
            self.send_header("X-Audio-Duration-S", f"{audio_secs:.1f}")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(bytes(buf))
            
        except Exception as e:
            self._json({"error": str(e)[:200]})
    
    def _handle_asr(self, body):
        """Speech recognition with faster-whisper."""
        t0 = time.time()
        try:
            data = json.loads(body)
            audio_b64 = data.get("audio", "")
            lang = data.get("lang", "auto")
            
            if not audio_b64:
                self._json({"error": "No audio"})
                return
            
            text, error = transcribe_audio(audio_b64, lang)
            if error:
                self._json({"error": error})
                return
            
            detected_lang = detect_language(text)
            self._json({
                "text": text,
                "detected_lang": detected_lang,
                "detected_lang_name": LANG_MAP.get(detected_lang, detected_lang),
                "time_ms": int((time.time() - t0) * 1000),
            })
        except Exception as e:
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
            print(f"[Translator] {msg}")


# ── MAIN ──
def main():
    print(f"\n{'='*50}")
    print(f"  >> Alex Voice — Translator Server")
    print(f"  >> Port: {PORT}")
    print(f"  >> STT:   faster-whisper (CPU)")
    print(f"  >> TRANS: argos-translate (CPU)")
    print(f"  >> TTS:   Qwen3-TTS-CustomVoice (GPU)")
    print(f"{'='*50}\n")
    
    # Pre-load faster-whisper
    if HAVE_WHISPER:
        t0 = time.time()
        _get_asr("base")
        print(f"[Translator] faster-whisper base cargado en {time.time()-t0:.1f}s")
    
    # Pre-load argos
    if _ensure_argos():
        print(f"[Translator] argos-translate listo (EN/ES/JA)")
    
    # Pre-load Qwen3 (will be slow but first request will be fast)
    print(f"[Translator] Qwen3-TTS se cargara bajo demanda")
    
    # Create frontend dir
    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
    
    httpd = HTTPServer(("0.0.0.0", PORT), TranslatorHandler)
    print(f"[Translator] Servidor listo en http://localhost:{PORT}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Translator] Cerrando...")
    finally:
        _unload_qwen3()
        httpd.server_close()
        print("[Translator] Detenido.")


if __name__ == "__main__":
    main()
