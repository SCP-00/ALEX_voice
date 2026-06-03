#!/usr/bin/env python3
"""
Alex Voice — Monitor Server
Provee monitoreo en tiempo real de hardware y LLM via API REST.
Sirve las interfaces HTML y expone /api/stats con datos actualizados.
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

# ── Módulos propios ────────────────────────────────────────────
from logger import add_log, get_logs, get_log_stats, clear_logs

# ── Configuración ──────────────────────────────────────────────
LLAMA_HOST = os.environ.get("LLAMA_HOST", "http://localhost:8081")
PORT = int(os.environ.get("MONITOR_PORT", "3000"))
FRONTEND_DIR = Path(__file__).parent / "frontend"
POLL_INTERVAL = 1.8  # segundos entre actualizaciones

def _safe_print(msg):
    """Print that handles UnicodeEncodeError on Windows consoles."""
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            print(msg.encode('ascii', errors='replace').decode('ascii'))
        except Exception:
            pass

# ── Dependencias opcionales ────────────────────────────────────
try:
    import psutil
    HAVE_PSUTIL = True
except ImportError:
    HAVE_PSUTIL = False
    _safe_print("[!] psutil no instalado. Stats de CPU/RAM no disponibles.")
    _safe_print("    pip install psutil")

HAVE_NVML = False
try:
    import pynvml
    pynvml.nvmlInit()
    gpu_name = pynvml.nvmlDeviceGetName(pynvml.nvmlDeviceGetHandleByIndex(0))
    if isinstance(gpu_name, bytes):
        gpu_name = gpu_name.decode('utf-8', errors='replace')
    elif isinstance(gpu_name, str):
        pass  # already string in newer pynvml
    else:
        gpu_name = str(gpu_name)
    gpu_name = gpu_name.replace('\x00', '').strip()
    HAVE_NVML = True
    _safe_print(f"[OK] pynvml init OK - GPU: {gpu_name}")
except Exception as e:
    error_str = str(e).encode('ascii', errors='replace').decode()
    HAVE_NVML = False
    _safe_print(f"[!] pynvml no disponible ({error_str}). Stats de GPU no disponibles.")
    _safe_print("    pip install pynvml")


# ── Colector de Stats (hilo background) ────────────────────────
class StatsCollector:
    def __init__(self):
        self.lock = threading.Lock()
        self.stats = {
            "cpu_percent": 0.0,
            "ram_used_gb": 0.0,
            "ram_total_gb": 0.0,
            "ram_percent": 0.0,
            "vram_used_mb": 0,
            "vram_total_mb": 0,
            "vram_percent": 0.0,
            "gpu_percent": 0,
            "gpu_temp": 0,
            "tokens_per_sec": 0.0,
            "context_used": 0,
            "context_max": 4096,
            "context_percent": 0.0,
            "tokens_generated": 0,
            "prompt_tokens": 0,
            "is_processing": False,
            "n_slots": 0,
            "llama_connected": False,
            "slots_detail": [],
        }
        self._last_decoded = 0
        self._last_time = time.time()
        self._tok_times = []  # sliding window for tokens/s
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
            time.sleep(POLL_INTERVAL)

    def _collect_system_stats(self):
        try:
            stats = {}
            stats["cpu_percent"] = round(psutil.cpu_percent(interval=0), 1)
            mem = psutil.virtual_memory()
            stats["ram_used_gb"] = round(mem.used / (1024 ** 3), 1)
            stats["ram_total_gb"] = round(mem.total / (1024 ** 3), 1)
            stats["ram_percent"] = round(mem.percent, 1)
            with self.lock:
                self.stats.update(stats)
        except Exception:
            pass

    def _collect_gpu_stats(self):
        try:
            stats = {}
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            vram_used = mem_info.used / (1024 ** 2)
            vram_total = mem_info.total / (1024 ** 2)
            stats["vram_used_mb"] = round(vram_used, 0)
            stats["vram_total_mb"] = round(vram_total, 0)
            stats["vram_percent"] = round((vram_used / vram_total) * 100, 1)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            stats["gpu_percent"] = util.gpu
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            stats["gpu_temp"] = temp
            with self.lock:
                self.stats.update(stats)
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
            self.stats["slots_detail"] = slots[:4]  # keep last 4 for detail view

            # Aggregate across all slots
            total_decoded = 0
            total_prompt = 0
            max_ctx = 4096
            processing = False
            active_slot = None

            for s in slots:
                ctx = s.get("n_ctx", 4096)
                max_ctx = max(max_ctx, ctx)

                if s.get("is_processing"):
                    processing = True
                    active_slot = s

                # Next token info
                nt = s.get("next_token", {})
                if isinstance(nt, dict):
                    total_decoded += nt.get("n_decoded", 0) or 0
                elif isinstance(nt, list) and len(nt) > 0:
                    total_decoded += nt[0].get("n_decoded", 0) or 0

                total_prompt += s.get("n_prompt_tokens", 0) or 0

            self.stats["is_processing"] = processing
            self.stats["context_max"] = max_ctx
            self.stats["context_used"] = total_decoded
            self.stats["context_percent"] = round(
                (total_decoded / max_ctx * 100) if max_ctx > 0 else 0, 1
            )
            self.stats["tokens_generated"] = total_decoded
            self.stats["prompt_tokens"] = total_prompt

            # Tokens/s from sliding window
            now = time.time()
            if total_decoded > self._last_decoded:
                dt = now - self._last_time
                if dt > 0:
                    tok_rate = (total_decoded - self._last_decoded) / dt
                    self._tok_times.append(tok_rate)
                    # Keep last 5 readings for smoothing
                    if len(self._tok_times) > 5:
                        self._tok_times.pop(0)
                    avg_rate = sum(self._tok_times) / len(self._tok_times)
                    self.stats["tokens_per_sec"] = round(avg_rate, 1)
            elif not processing:
                # Keep last rate for 3s before decaying (so user can see it)
                if self._tok_times:
                    now2 = time.time()
                    if now2 - self._last_time > 3.0:
                        self._tok_times = []
                        self.stats["tokens_per_sec"] = 0.0
                    # else: keep the last reading visible
                else:
                    self.stats["tokens_per_sec"] = 0.0

            self._last_decoded = total_decoded
            self._last_time = now

    def get_stats(self):
        with self.lock:
            return dict(self.stats)

    def get_hardware_detail(self):
        """Devuelve info detallada de hardware como LM Studio."""
        detail = {
            "gpu": {
                "name": 'N/A',
                "driver_version": 'N/A',
                "compute_capability": 'N/A',
                "temperature": 0,
                "power_draw_w": 0,
                "utilization_gpu": 0,
                "utilization_memory": 0,
            },
            "vram": {
                "total_mb": 0,
                "used_mb": 0,
                "free_mb": 0,
                "percent": 0.0,
            },
            "ram": {
                "total_gb": 0.0,
                "used_gb": 0.0,
                "percent": 0.0,
            },
            "cpu": {
                "name": 'N/A',
                "percent": 0.0,
                "cores_physical": 0,
                "cores_logical": 0,
            },
            "llama": {
                "connected": False,
                "model": 'N/A',
                "context_size": 4096,
                "slots": 0,
                "is_processing": False,
            },
        }
        if HAVE_NVML:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode('utf-8', errors='replace')
                detail["gpu"]["name"] = str(name).replace('\x00', '').strip()
                try:
                    ver = pynvml.nvmlSystemGetDriverVersion()
                    if isinstance(ver, bytes):
                        ver = ver.decode('utf-8', errors='replace')
                    detail["gpu"]["driver_version"] = str(ver).replace('\x00', '').strip()
                except Exception:
                    pass
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                detail["vram"]["total_mb"] = round(mem.total / (1024**2))
                detail["vram"]["used_mb"] = round(mem.used / (1024**2))
                detail["vram"]["free_mb"] = round(mem.free / (1024**2))
                detail["vram"]["percent"] = round(mem.used / mem.total * 100, 1)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                detail["gpu"]["utilization_gpu"] = util.gpu
                detail["gpu"]["utilization_memory"] = util.memory
                detail["gpu"]["temperature"] = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                try:
                    detail["gpu"]["power_draw_w"] = round(pynvml.nvmlDeviceGetPowerUsage(handle) / 1000, 1)
                except Exception:
                    pass
            except Exception:
                pass
        if HAVE_PSUTIL:
            try:
                detail["cpu"]["percent"] = psutil.cpu_percent(interval=0)
                detail["cpu"]["cores_physical"] = psutil.cpu_count(logical=False) or 0
                detail["cpu"]["cores_logical"] = psutil.cpu_count(logical=True) or 0
                import platform
                detail["cpu"]["name"] = platform.processor() or 'N/A'
                mem = psutil.virtual_memory()
                detail["ram"]["total_gb"] = round(mem.total / (1024**3), 1)
                detail["ram"]["used_gb"] = round(mem.used / (1024**3), 1)
                detail["ram"]["percent"] = mem.percent
            except Exception:
                pass
        # LLM info from stats
        with self.lock:
            detail["llama"]["connected"] = self.stats.get("llama_connected", False)
            detail["llama"]["is_processing"] = self.stats.get("is_processing", False)
            detail["llama"]["slots"] = self.stats.get("n_slots", 0)
            detail["llama"]["context_size"] = self.stats.get("context_max", 4096)
        return detail

    def stop(self):
        self._running = False



# ── Detección de idioma ────────────────────────────────────────
def detect_language(text):
    """Detecta si el texto es japonés, español o inglés.
    
    Mejorado: deteccion robusta incluso para textos cortos.
    """
    if not text.strip():
        return 'en'
    
    # JA detection por caracteres Unicode
    ja_chars = sum(1 for c in text if '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff')
    if ja_chars > 0:
        return 'ja'
    
    # ES detection: caracteres acentuados + palabras comunes
    es_chars = sum(1 for c in text if '\u00e1' <= c <= '\u00fa' or c in 'ñçüöéèêëàâîôùû¿¡')
    
    # Common Spanish words (incluso sin acentos)
    es_words = {'hola','gracias','como','estas','está','muy','bien','que','el','la',
                'los','las','un','una','por','para','con','sin','es','son',
                'eres','soy','esta','está','estoy','del','se','no','sí','pero',
                'más','menos','todo','nada','algo','casa','libro','agua',
                'sol','mar','vida','mundo','tiempo','día','noche',
                'semana','mes','año','hoy','ayer','mañana','adios','chao',
                'luego','entonces','también','solo','cada','bienvenido','amigo',
                'gente','señor','señora','usted','nosotros','ellos','este','esta',
                'ese','esa','aquel','hablar','decir','tener','hacer','poder','saber',
                'querer','venir','poner','dar','ver','comer','beber','dormir','vivir',
                'bueno','buena','buenos','buenas','malo','mala','malos','malas',
                'grande','grandes','pequeño','pequeña','nuevo','nueva','nuevos','nuevas',
                'viejo','vieja','viejos','viejas','alto','alta','altos','altas',
                'bajo','baja','bajos','bajas','bonito','bonita','feo','fea',
                'facil','facil','dificil','dificil','caro','cara','caros','caras',
                'barato','barata','baratos','baratas','caliente','calientes',
                'frio','fria','frios','frias',
                'abierto','abierta','cerrado','cerrada','listo','lista',
                'ocupado','ocupada','contento','contenta','triste','tristes',
                'primero','primera','primeros','primeras','ultimo','ultima',
                'mejor','mejores','peor','peores',
                'siempre','nunca','jamas','pronto','tarde','temprano',
                'cerca','lejos','encima','debajo','dentro','fuera','arriba','abajo',
                'donde','cuando','porque','cual','cuales','quien','quienes',
                'cuanto','cuanta','cuantos','cuantas',
                'dias','dia','día','días','semana','semanas','mes','meses',
                'ano','año','años','hoy','ayer','manana','mañana',
                'noche','noches','tarde','tardes','madrugada',
                'semana','semanas','finde','findes',
                'lunes','martes','miercoles','jueves','viernes','sabado','domingo',
                'enero','febrero','marzo','abril','mayo','junio',
                'julio','agosto','septiembre','octubre','noviembre','diciembre',
                'primavera','verano','otonio','invierno',
                'ahi','alli','aqui','alla','aca','acá','allá',
                'detras','detrás','adelante','atras','atrás','alrededor',
                'junto','junta','juntos','juntas','separado','separada',
                'mucho','mucha','muchos','muchas','poco','poca','pocos','pocas',
                'demasiado','bastante','suficiente','escaso','abundante',
                'tuyo','tuya','tuyos','tuyas','mio','mia','mios','mias',
                'suyo','suya','suyos','suyas','nuestro','nuestra','nuestros','nuestras',
                'vuestro','vuestra','vuestros','vuestras',
                'aquel','aquella','aquellos','aquellas',
                'algun','alguna','algunos','algunas','ningun','ninguna',
                'cualquier','cualquiera','varios','varias',
                'ambos','ambas','demas','demás','propio','propia','ajeno','ajena',
                'mismo','misma','mismos','mismas','otro','otra','otros','otras',
                'tal','tales','cierto','cierta','ciertos','ciertas',
                'saludos','recuerdos','besos','abrazos','feliz','felices',
                'contento','contenta','enojado','enojada','cansado','cansada',
                'enfermo','enferma','sano','sana','vivo','viva','muerto','muerta',
                'felicitaciones','enhorabuena','bienvenido','bienvenida',
                'bienvenidos','bienvenidas','gracias','muchas','muchisimas',
                'de','nada','por','favor','permiso','disculpa','disculpe',
                'lo','siento','perdon','perdona','perdone','oye','oiga',
                'mira','mire','escucha','escuche','atiende','atienda'}
    
    # English keywords expandido
    en_keywords = {
        'the','is','are','was','were','and','this','that','with','have','has','had',
        'not','but','for','you','all','can','our','its','what','will','been','from',
        'they','would','about','there','their','your','which','when','make','like',
        'just','over','also','than','then','some','them','into','could','other',
        'more','these','many','each','here','very','only','hello','hi','hey','how',
        'why','where','who','thanks','thank','please','yes','no','good','well',
        'great','fine','okay','sure','right','wrong','love','like','want','need',
        'know','think','feel','see','go','come','get','give','take','use','find',
        'tell','ask','work','help','show','try','keep','let','start','done',
        'would','could','should','might','must','shall','may','can','will',
        'being','having','doing','saying','going','getting','making','looking',
        'seems','means','takes','gives','puts','sets','brings','calls'
    }
    
    words = [w.strip('.,!?;:\'"()[]{}') for w in text.lower().split() if w.strip('.,!?;:\'"()[]{}')]
    
    if not words:
        # Si solo hay signos o caracteres especiales
        single = text.strip('.,!?;:\'"()[]{} \t\n\r')
        if single and '\u4e00' <= single[0] <= '\u9fff':
            return 'ja'
        return 'en'
    
    # 1. JA override (if any Japanese chars, it's Japanese)
    # Already handled above
    
    # 2. Check Spanish words and accented chars FIRST
    es_count = sum(1 for w in words if w in es_words)
    if es_count > 0 or es_chars > 0:
        return 'es'
    
    # 3. English keyword detection
    en_count = sum(1 for w in words if w in en_keywords)
    if en_count / max(len(words), 1) >= 0.2:  # 20% threshold para textos cortos
        return 'en'
    
    # 4. Fallback: count English vs Spanish-like patterns
    # If no strong signal, prefer English (more common for code/mixed content)
    return 'en'


def split_by_language(text):
    """Divide texto en segmentos por idioma (es/en/ja).
    
    Retorna lista de (texto, idioma) manteniendo el orden original.
    Los segmentos consecutivos del mismo idioma se fusionan.
    
    La estrategia es:
    1. Dividir por saltos de linea (boundaries fuertes)
    2. Dentro de cada linea, dividir por puntuacion final
    3. Para lineas con guiones mixtos (e.g. "Hello こんにちは"),
       dividir en el punto de transicion de script.
    """
    if not text.strip():
        return []
    
    # Paso 1: dividir por saltos de linea
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    raw_segments = []
    for line in lines:
        # Paso 2: dentro de cada linea, dividir por puntuacion final
        sentences = re.split(r'(?<=[.!?¡!¿?])\s+', line)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            sentences = [line]
        
        for s in sentences:
            # Paso 3: check for mixed scripts within sentence
            # Use script distribution to find transition points
            mixed_segs = _split_mixed_script(s)
            raw_segments.extend(mixed_segs)
    
    # Paso 4: fusionar segmentos consecutivos del mismo idioma
    segments = []
    for s in raw_segments:
        if not s:
            continue
        if segments and segments[-1][1] == s[1]:
            segments[-1] = (segments[-1][0] + ' ' + s[0], s[1])
        else:
            segments.append(s)
    
    return segments if segments else [(text, detect_language(text))]


def _split_mixed_script(text):
    """Divide una oracion que contiene scripts mixtos (e.g. "Hello こんにちは").
    Retorna lista de (texto, idioma).
    """
    if not text:
        return []
    
    # Check if mixed
    has_ja = any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in text)
    
    if not has_ja:
        # Single language -> detect and return
        return [(text, detect_language(text))]
    
    # Split at boundaries: Latin vs Japanese
    result = []
    current = ''
    current_type = None
    
    for c in text:
        is_ja = '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff'
        is_latin = ('a' <= c <= 'z' or 'A' <= c <= 'Z' or c in ' .!?,;:\'"-' or c.isdigit())
        is_es = '\u00e1' <= c <= '\u00fa' or c in '\u00f1\u00e7\u00fc\u00f6'
        is_space = c == ' ' and not current_type  # skip leading spaces
        
        char_type = 'ja' if is_ja else ('latin' if (is_latin or is_es) else 'other')
        
        if char_type == 'other' and not current:
            continue  # skip leading non-script chars
        
        if current_type is None:
            current = c
            current_type = char_type
        elif char_type == current_type or (char_type == 'other' and not is_ja):
            current += c
        else:
            # Transition detected
            if current.strip():
                result.append((current.strip(), 'ja' if current_type == 'ja' else detect_language(current)))
            current = c
            current_type = char_type
    
    # Last segment
    if current and current.strip():
        result.append((current.strip(), 'ja' if current_type == 'ja' else detect_language(current)))
    
    return result if result else [(text, detect_language(text))]


# ── Piper TTS Python API ────────────────────────────────────────
# Usa las Python bindings de piper-tts para mantener los modelos
# cargados en memoria. Latencia: ~45ms (vs ~2400ms con subprocess).

HAVE_PIPER_PYTHON = False
try:
    from piper import PiperVoice
    HAVE_PIPER_PYTHON = True
except ImportError:
    HAVE_PIPER_PYTHON = False
    _safe_print("[!] piper-tts no instalado. Usando subprocess Piper (lento).")
    _safe_print("    pip install piper-tts")


class PiperTTS:
    """Mantiene modelos Piper cargados en memoria via Python API.
    
    Latencia: ~45-65ms por sintesis (vs ~2400ms con subprocess).
    Los modelos se cargan una vez al iniciar el servidor.
    Thread-safe mediante threading.Lock.
    """
    
    def __init__(self, es_model_path, en_model_path, piper_exe_path=None):
        self.es_voice = None
        self.en_voice = None
        self.es_model_path = str(es_model_path) if es_model_path else None
        self.en_model_path = str(en_model_path) if en_model_path else None
        self.piper_exe_path = str(piper_exe_path) if piper_exe_path else None
        self.available = False
        self._lock = threading.Lock()  # thread safety for synthesize
        self._init_voices()
    
    def _init_voices(self):
        """Carga ambos modelos en memoria."""
        if not HAVE_PIPER_PYTHON:
            _safe_print("[PiperTTS] piper-tts no disponible, usando fallback")
            return
        
        if self.es_model_path:
            try:
                t0 = time.time()
                self.es_voice = PiperVoice.load(self.es_model_path, use_cuda=False)
                _safe_print(f"[PiperTTS] ES cargado en {(time.time()-t0)*1000:.0f}ms")
            except Exception as e:
                _safe_print(f"[PiperTTS] Error cargando ES: {e}")
                self.es_voice = None
        
        if self.en_model_path:
            try:
                t0 = time.time()
                self.en_voice = PiperVoice.load(self.en_model_path, use_cuda=False)
                _safe_print(f"[PiperTTS] EN cargado en {(time.time()-t0)*1000:.0f}ms")
            except Exception as e:
                _safe_print(f"[PiperTTS] Error cargando EN: {e}")
                self.en_voice = None
        
        self.available = (self.es_voice is not None) or (self.en_voice is not None)
        if self.available:
            _safe_print(f"[PiperTTS] Listo! Latencia ~45-65ms por sintesis")

    def synthesize(self, text, lang='es'):
        """Sintetiza texto usando el modelo precargado.
        Retorna bytes WAV o None si falla.
        
        Los chunks de PiperVoice.synthesize() son AudioChunk con:
          - audio_int16_array: numpy.ndarray (int16) 
          - audio_int16_bytes: bytes PCM raw
          - sample_rate: int
        """
        voice = self.es_voice if lang == 'es' else self.en_voice if lang == 'en' else \
                (self.es_voice or self.en_voice)
        
        if voice is None:
            return None
        
        with self._lock:
            try:
                # Consumir el generador para obtener chunks de audio
                chunks = list(voice.synthesize(text))
                if not chunks:
                    return None
                
                # Obtener sample rate del primer chunk
                sample_rate = getattr(chunks[0], 'sample_rate', 22050)
                
                # AudioChunk tiene audio_int16_array (numpy int16) o audio_int16_bytes
                int16_chunks = []
                for c in chunks:
                    if hasattr(c, 'audio_int16_array') and c.audio_int16_array is not None:
                        int16_chunks.append(c.audio_int16_array)
                    elif hasattr(c, 'audio_int16_bytes') and c.audio_int16_bytes is not None:
                        int16_chunks.append(np.frombuffer(c.audio_int16_bytes, dtype=np.int16))
                
                if not int16_chunks:
                    return None
                
                pcm_int16 = np.concatenate(int16_chunks)
                
                # Crear WAV
                data_size = len(pcm_int16) * 2  # 16-bit
                buffer_size = 44 + data_size
                
                wav = bytearray(buffer_size)
                wav[0:4] = b'RIFF'
                struct.pack_into('<I', wav, 4, buffer_size - 8)
                wav[8:12] = b'WAVE'
                wav[12:16] = b'fmt '
                struct.pack_into('<I', wav, 16, 16)
                struct.pack_into('<H', wav, 20, 1)  # PCM
                struct.pack_into('<H', wav, 22, 1)  # mono
                struct.pack_into('<I', wav, 24, sample_rate)
                struct.pack_into('<I', wav, 28, sample_rate * 2)  # byte_rate
                struct.pack_into('<H', wav, 32, 2)  # block_align
                struct.pack_into('<H', wav, 34, 16)  # bits_per_sample
                wav[36:40] = b'data'
                struct.pack_into('<I', wav, 40, data_size)
                wav[44:44+data_size] = pcm_int16.tobytes()
                
                return bytes(wav)
                
            except Exception as e:
                _safe_print(f"[PiperTTS] Error sintesis: {e}")
                return None
    
    def stop(self):
        """Libera los modelos."""
        self.es_voice = None
        self.en_voice = None
        self.available = False
        _safe_print("[PiperTTS] Modelos liberados")


# ── ASR (Speech-to-Text) con faster-whisper ─────────────────────
# Usa faster-whisper (Whisper via CTranslate2) para transcripción
# de audio. Modelo tiny (~75 MB RAM, muy rápido en CPU).

HAVE_FASTER_WHISPER = False
_asr_model = None
_asr_lock = threading.Lock()


def _find_wav_data_offset(audio_bytes):
    """Encuentra el offset de los datos PCM en un WAV buscando 'data' chunk.
    
    La mayoría de WAVs tienen header de 44 bytes, pero algunos incluyen
    chunks adicionales (fact, list, etc.). Esta función es más robusta.
    """
    data_pos = audio_bytes.find(b'data', 12)  # buscar después de "WAVE" header
    if data_pos >= 0:
        return data_pos + 8  # 4 bytes 'data' + 4 bytes size
    return 44  # fallback: header estándar de 44 bytes
try:
    from faster_whisper import WhisperModel
    HAVE_FASTER_WHISPER = True
except ImportError:
    HAVE_FASTER_WHISPER = False
    _safe_print("[!] faster-whisper no instalado. Usando whisper.cpp.")
    _safe_print("    pip install faster-whisper")


def _asr_transcribe(audio_bytes, language="auto"):
    """Transcribe audio WAV usando faster-whisper.
    Retorna (texto, segmentos, error_msg).
    Los primeros 44 bytes son el header WAV, el resto es PCM.
    """
    global _asr_model
    if _asr_model is None:
        return None, None, "ASR model no cargado"
    try:
        # Parse WAV header para obtener sample_rate
        sample_rate = 16000  # default
        if len(audio_bytes) >= 44:
            # Sample rate está en bytes 24-27 del WAV
            sample_rate = struct.unpack_from('<I', audio_bytes, 24)[0]
        
        # Extraer PCM data (búsqueda robusta de 'data' chunk)
        pcm_offset = _find_wav_data_offset(audio_bytes)
        pcm_data = audio_bytes[pcm_offset:] if len(audio_bytes) > pcm_offset else audio_bytes[44:]
        
        # Convertir bytes PCM a float32 numpy array (normalizado a [-1, 1])
        pcm_int16 = np.frombuffer(pcm_data, dtype=np.int16)
        if len(pcm_int16) == 0:
            return None, None, "Audio vacío"
        pcm_float32 = pcm_int16.astype(np.float32) / 32768.0
        
        # Transcribir (thread-safe)
        lang_code = None if language == "auto" else language
        with _asr_lock:
            segments, info = _asr_model.transcribe(
                pcm_float32,
                language=lang_code,
                beam_size=1,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300),
            )
        
        detected_lang = info.language if info else language
        
        seg_list = []
        full_text = []
        for seg in segments:
            seg_list.append({
                "text": seg.text.strip(),
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
            })
            full_text.append(seg.text.strip())
        
        text = " ".join(full_text).strip()
        return text, seg_list, None
    except Exception as e:
        return None, None, str(e)[:300]


# ── Piper Persistent Server (Fallback) ──────────────────────────
# Mantiene dos procesos Piper persistentes (ES y EN) para evitar
# el overhead de ~2.4s de cargar el modelo en cada request.
# NOTA: Este enfoque no reduce significativamente la latencia
# porque Piper.exe carga el modelo cada vez igual. Se mantiene
# como fallback si piper-tts Python bindings no estan disponibles.

class PiperPersistentProcess:
    """Mantiene un proceso Piper vivo con stdin/stdout pipes persistentes.
    
    En lugar de ejecutar piper.exe cada vez (que tarda ~2.4s en cargar
    el modelo), mantenemos el proceso abierto y escribimos/leemos por
    las pipes. La latencia baja a ~200-400ms.
    """
    
    def __init__(self, piper_exe, model_path, name="piper"):
        self.piper_exe = str(piper_exe)
        self.model_path = str(model_path)
        self.name = name
        self.proc = None
        self.lock = threading.Lock()
        self.available = False
        self._start()
    
    def _start(self):
        """Inicia el proceso Piper persistente."""
        try:
            self.proc = subprocess.Popen(
                [self.piper_exe, "--model", self.model_path, "--output_raw"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,  # unbuffered
            )
            self.available = True
            _safe_print(f"[PiperServer] {self.name} iniciado (PID {self.proc.pid})")
        except Exception as e:
            _safe_print(f"[PiperServer] Error iniciando {self.name}: {e}")
            self.available = False
    
    def synthesize(self, text):
        """Sintetiza texto usando el proceso persistente.
        Retorna bytes WAV o None si falla.
        """
        if not self.available or not self.proc:
            return None
        
        with self.lock:
            try:
                # Escribir texto + newline (Piper lee hasta EOF o newline)
                self.proc.stdin.write(text.encode('utf-8'))
                self.proc.stdin.write(b'\n')
                self.proc.stdin.flush()
                
                # Leer raw audio de stdout
                # Piper escribe raw PCM (16-bit mono, 22050Hz) y luego cierra
                # Leemos en chunks hasta detectar fin
                chunks = []
                while True:
                    chunk = self.proc.stdout.read(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    # Si recibimos menos de 4096, probablemente terminó
                    if len(chunk) < 4096:
                        break
                
                raw_audio = b''.join(chunks)
                
                if len(raw_audio) < 100:
                    # Proceso murió o no generó audio -> reiniciar
                    self._restart()
                    return None
                
                # Convertir raw PCM a WAV
                return self._raw_to_wav(raw_audio)
                
            except Exception as e:
                _safe_print(f"[PiperServer] Error en {self.name}: {e}")
                self._restart()
                return None
    
    def _raw_to_wav(self, raw_audio):
        """Convierte raw PCM (16-bit mono, 22050Hz) a WAV."""
        sample_rate = 22050
        bits_per_sample = 16
        num_channels = 1
        
        data_size = len(raw_audio)
        buffer_size = 44 + data_size
        
        wav = bytearray(buffer_size)
        wav[0:4] = b'RIFF'
        struct.pack_into('<I', wav, 4, buffer_size - 8)
        wav[8:12] = b'WAVE'
        wav[12:16] = b'fmt '
        struct.pack_into('<I', wav, 16, 16)
        struct.pack_into('<H', wav, 20, 1)  # PCM
        struct.pack_into('<H', wav, 22, num_channels)
        struct.pack_into('<I', wav, 24, sample_rate)
        struct.pack_into('<I', wav, 28, sample_rate * num_channels * bits_per_sample // 8)
        struct.pack_into('<H', wav, 32, num_channels * bits_per_sample // 8)
        struct.pack_into('<H', wav, 34, bits_per_sample)
        wav[36:40] = b'data'
        struct.pack_into('<I', wav, 40, data_size)
        wav[44:44+data_size] = raw_audio
        
        return bytes(wav)
    
    def _restart(self):
        """Reinicia el proceso Piper."""
        try:
            if self.proc:
                self.proc.kill()
                self.proc.wait(timeout=3)
        except:
            pass
        self.available = False
        self._start()
    
    def stop(self):
        """Detiene el proceso Piper."""
        self.available = False
        try:
            if self.proc:
                self.proc.kill()
                self.proc.wait(timeout=3)
        except:
            pass
        self.proc = None
        _safe_print(f"[PiperServer] {self.name} detenido")


def _run_piper_stdin(text, model_path, piper_exe):
    """Ejecuta Piper usando stdin/stdout (sin archivos temporales).
    Retorna bytes WAV o None si falla.
    
    Metodo legacy: ya no se usa directamente si hay PiperServer disponible.
    """
    try:
        proc = subprocess.Popen(
            [str(piper_exe), "--model", str(model_path), "--output_raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        raw_audio, _ = proc.communicate(input=text.encode('utf-8'), timeout=15)
        
        if proc.returncode != 0 or len(raw_audio) < 100:
            return None
            
        # Convertir raw PCM (16-bit mono, 22050Hz) a WAV con header
        sample_rate = 22050
        bits_per_sample = 16
        num_channels = 1
        
        data_size = len(raw_audio)
        buffer_size = 44 + data_size
        
        wav = bytearray(buffer_size)
        wav[0:4] = b'RIFF'
        struct.pack_into('<I', wav, 4, buffer_size - 8)
        wav[8:12] = b'WAVE'
        wav[12:16] = b'fmt '
        struct.pack_into('<I', wav, 16, 16)
        struct.pack_into('<H', wav, 20, 1)
        struct.pack_into('<H', wav, 22, num_channels)
        struct.pack_into('<I', wav, 24, sample_rate)
        struct.pack_into('<I', wav, 28, sample_rate * num_channels * bits_per_sample // 8)
        struct.pack_into('<H', wav, 32, num_channels * bits_per_sample // 8)
        struct.pack_into('<H', wav, 34, bits_per_sample)
        wav[36:40] = b'data'
        struct.pack_into('<I', wav, 40, data_size)
        wav[44:44+data_size] = raw_audio
        
        return bytes(wav)
    except Exception as e:
        _safe_print(f"[TTS-piper] error: {e}")
        return None


def _run_piper_file(text, model_path, piper_exe):
    """Ejecuta Piper con archivo temporal (fallback).
    Se usa solo si PiperServer y _run_piper_stdin fallan.
    """
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w', encoding='utf-8') as f:
            f.write(text)
            input_path = f.name
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            output_path = f.name
        
        proc = subprocess.Popen(
            [str(piper_exe), "--model", str(model_path),
             "--output-file", output_path],
            stdin=open(input_path, 'rb'),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait(timeout=15)
        
        if proc.returncode == 0 and os.path.exists(output_path):
            with open(output_path, 'rb') as f:
                wav_data = f.read()
            try:
                os.unlink(output_path)
                os.unlink(input_path)
            except:
                pass
            return wav_data if len(wav_data) > 100 else None
        
        if os.path.exists(output_path): os.unlink(output_path)
        if os.path.exists(input_path): os.unlink(input_path)
        return None
    except Exception as e:
        _safe_print(f"[TTS-file] error: {e}")
        return None


# ── Servidor HTTP ──────────────────────────────────────────────
_stats_collector = None
_piper_tts = None  # PiperTTS con modelos precargados en memoria
_piper_es = None   # Fallback: proceso persistente ES
_piper_en = None   # Fallback: proceso persistente EN
_piper_exe_path = None  # Cache de ruta


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            directory=str(FRONTEND_DIR),
            **kwargs,
        )

    def do_GET(self):
        if self.path == "/api/stats":
            self._json_response(_stats_collector.get_stats())
        elif self.path == "/api/logs":
            self._json_response(get_logs())
        elif self.path == "/api/logs/stats":
            self._json_response(get_log_stats())
        elif self.path == "/api/logs/clear":
            clear_logs()
            self._json_response({"ok": True})
        elif self.path == "/api/logs/export":
            self._handle_log_export()
        elif self.path == "/api/hardware":
            self._json_response(_stats_collector.get_hardware_detail())
        elif self.path in ("/", "/index.html"):
            self._serve_file("plan-a/index.html")
        elif self.path in ("/debug", "/debug.html"):
            self._serve_file("debug.html")
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

        if self.path == "/tts":
            self._handle_tts(body)
        elif self.path == "/api/tts-gpu":
            self._handle_tts_gpu(body)
        elif self.path == "/api/asr":
            self._handle_asr(body)
        elif self.path == "/api/log":
            self._handle_log(body)
        elif self.path == "/api/chat":
            self._handle_chat(body)
        elif self.path == "/api/tts-piper":
            self._handle_tts_piper(body)
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_chat(self, body):
        """Proxy: reenvía la request al endpoint /chat/completions de llama-server.
        
        Usa /chat/completions (OpenAI-compatible) para que el chat template
        de Qwen3.5 procese correctamente los mensajes y desactive el thinking.
        """
        try:
            data = json.loads(body)
            # Si el frontend envía messages array, lo pasamos directamente
            # Si envía prompt raw (compatibilidad), lo convertimos
            if "messages" not in data and "prompt" in data:
                # Legacy mode: raw prompt → convert to chat format
                messages = []
                prompt = data.get("prompt", "")
                # Parse im_start tags into messages
                parts = re.split(r'<\|im_start\|>(\w+)\n', prompt)
                for i in range(1, len(parts)-1, 2):
                    role = parts[i]
                    content = parts[i+1].replace('<|im_end|>', '').strip()
                    if role == 'system':
                        messages.insert(0, {"role": "system", "content": content})
                    elif role in ('user', 'assistant'):
                        messages.append({"role": role, "content": content})
                
                # Remove stop parameter (chat template handles it)
                chat_data = {
                    "messages": messages,
                    "n_predict": data.get("n_predict", 512),
                    "temperature": data.get("temperature", 0.7),
                    "stream": data.get("stream", False),
                }
            else:
                chat_data = data

            target = f"{LLAMA_HOST}/chat/completions"
            req = urllib.request.Request(
                target,
                data=json.dumps(chat_data).encode(),
                headers={"Content-Type": "application/json"},
            )
            
            if chat_data.get("stream"):
                # Streaming: relay SSE response
                with urllib.request.urlopen(req, timeout=120) as resp:
                    # Relay the streaming response headers
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    
                    # Stream chunks directly to client
                    while True:
                        chunk = resp.read(4096)
                        if not chunk:
                            break
                        try:
                            self.wfile.write(chunk)
                            self.wfile.flush()
                        except Exception:
                            break
            else:
                # Non-streaming: relay JSON response
                with urllib.request.urlopen(req, timeout=120) as resp:
                    result = json.loads(resp.read().decode())
                
                # Extract content and tokens for rich logging
                content = ""
                choices = result.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                usage = result.get("usage", {})
                token_count = usage.get("completion_tokens", 0)
                prompt_tokens = usage.get("prompt_tokens", 0)
                lang_detected = detect_language(content) if content else ""
                add_log("output", content[:500], mode="plan-a", language=lang_detected,
                        token_count=token_count, char_count=len(content),
                        extra={"prompt_tokens": prompt_tokens})
                self._json_response(result)

        except urllib.error.HTTPError as e:
            error_body = e.read().decode(errors='replace')[:500]
            _safe_print(f"[proxy] llama-server HTTP {e.code}")
            self._json_response({"error": f"llama-server HTTP {e.code}: {error_body}"})
        except Exception as e:
            _safe_print(f"[proxy] {type(e).__name__}: {e}")
            self._json_response({"error": str(e)[:300]})

    def _handle_tts_piper(self, body):
        """Endpoint para TTS con modelos precargados en memoria.
        
        Usa piper-tts Python API (PiperTTS) que mantiene los modelos
        cargados en memoria. Latencia: ~45-65ms.
        Fallback: subprocess Piper (~2400ms) si la API no esta disponible.
        
        Input: {"text": "...", "lang": "es"|en"}
        Output: WAV audio (raw)
        """
        global _piper_tts, _piper_es, _piper_en, _piper_exe_path
        t0 = time.time()
        method_used = "python_api"
        model_used = ""
        char_count = 0
        lang = ""
        try:
            data = json.loads(body)
            text = data.get("text", "").strip()
            lang = data.get("lang", "auto")
            char_count = len(text)
            
            if not text:
                self._json_response({"error": "texto vacio"})
                return
            
            # --- PRIMARY: Usar PiperTTS (modelos en memoria) ---
            wav_data = None
            if _piper_tts and _piper_tts.available:
                # Determinar que modelo usar
                if lang == 'en':
                    model_used = "en_US-lessac-medium"
                    wav_data = _piper_tts.synthesize(text, 'en')
                    method_used = "python_api"
                elif lang == 'es':
                    model_used = "es_ES-sharvard-medium"
                    wav_data = _piper_tts.synthesize(text, 'es')
                    method_used = "python_api"
                else:
                    # Auto-detect
                    detected = detect_language(text)
                    if detected == 'en':
                        model_used = "en_US-lessac-medium"
                        wav_data = _piper_tts.synthesize(text, 'en')
                    else:
                        model_used = "es_ES-sharvard-medium"
                        wav_data = _piper_tts.synthesize(text, 'es')
                    method_used = "python_api"
            
            # --- FALLBACK 1: PiperPersistentProcess (pipe) ---
            if wav_data is None:
                piper_proc = None
                if lang == 'en' and _piper_en and _piper_en.available:
                    piper_proc = _piper_en
                    model_used = "en_US-lessac-medium"
                elif lang == 'es' and _piper_es and _piper_es.available:
                    piper_proc = _piper_es
                    model_used = "es_ES-sharvard-medium"
                else:
                    detected = detect_language(text)
                    if detected == 'en' and _piper_en and _piper_en.available:
                        piper_proc = _piper_en
                        model_used = "en_US-lessac-medium"
                    elif _piper_es and _piper_es.available:
                        piper_proc = _piper_es
                        model_used = "es_ES-sharvard-medium"
                
                if piper_proc:
                    wav_data = piper_proc.synthesize(text)
                    method_used = "persistent_pipe"
            
            # --- FALLBACK 2: Subprocess stdin ---
            if wav_data is None:
                project_root = Path(__file__).parent
                piper_exe = project_root / "bin" / "piper" / "piper.exe"
                es_model = project_root / "models" / "es_ES-sharvard-medium.onnx"
                en_model = project_root / "models" / "en_US-lessac-medium.onnx"
                model_path = en_model if 'en' in model_used else es_model
                
                wav_data = _run_piper_stdin(text, model_path, piper_exe)
                method_used = "fallback_stdin"
                
                if wav_data is None:
                    wav_data = _run_piper_file(text, model_path, piper_exe)
                    method_used = "fallback_file"
            
            if wav_data is None or len(wav_data) < 100:
                add_log("tts_error", "No se genero audio", voice_model=model_used,
                        method=method_used, duration_ms=round((time.time()-t0)*1000),
                        char_count=char_count, language=lang)
                self._json_response({"error": "No se genero audio"})
                return
            
            duration_ms = round((time.time() - t0) * 1000)
            add_log("tts", f"{len(wav_data)}B en {duration_ms}ms",
                    voice_model=model_used, method=method_used,
                    duration_ms=duration_ms, char_count=char_count, language=lang)
            
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(wav_data)))
            self.end_headers()
            self.wfile.write(wav_data)
            
        except Exception as e:
            duration_ms = round((time.time() - t0) * 1000)
            _safe_print(f"[TTS-piper] Error: {e}")
            add_log("tts_error", str(e)[:200], method=method_used,
                    duration_ms=duration_ms, char_count=char_count,
                    error_detail=str(e)[:500], language=lang or '')
            self._json_response({"error": str(e)[:200]})



    def _handle_log(self, body):
        try:
            data = json.loads(body)
            add_log(
                entry_type=data.get("type", "info"),
                data=data.get("data", ""),
                mode=data.get("mode", ""),
                language=data.get("language", ""),
                voice_model=data.get("voice_model", ""),
                duration_ms=data.get("duration_ms"),
                token_count=data.get("token_count"),
                char_count=data.get("char_count"),
                method=data.get("method"),
                segment_info=data.get("segment_info"),
                error_detail=data.get("error_detail"),
            )
            self._json_response({"ok": True})
        except Exception as e:
            self._json_response({"error": str(e)[:200]})

    def _handle_log_export(self):
        """Exporta todos los logs como descarga JSON."""
        logs = get_logs()
        json_str = json.dumps(logs, ensure_ascii=False, indent=2)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Disposition", f'attachment; filename="alex_voice_logs_{time.strftime("%Y%m%d_%H%M%S")}.json"')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(json_str)))
        self.end_headers()
        self.wfile.write(json_str.encode('utf-8'))

    def _json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _serve_file(self, rel_path):
        file_path = FRONTEND_DIR / rel_path
        if file_path.exists():
            self.path = f"/{rel_path}"
            super().do_GET()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")

    def _handle_tts_gpu(self, body):
        """Ejecuta OuteTTS (llama-tts) en GPU y devuelve el WAV."""
        try:
            data = json.loads(body)
            text = data.get("text", "")
            if not text.strip():
                self._json_response({"error": "texto vacío"})
                return

            project_root = Path(__file__).parent
            llama_tts = Path(r"C:\Users\andyh\Documents\llama-b9479-bin-win-cuda-13.3-x64\llama-tts.exe")
            model_path = Path(r"C:\Users\andyh\Documents\llama-models\OuteTTS-0.2-500M-Q4_K_M.gguf")

            if not llama_tts.exists():
                self._json_response({"error": "llama-tts.exe no encontrado"})
                return
            if not model_path.exists():
                self._json_response({"error": "Modelo OuteTTS no encontrado"})
                return

            request_id = str(int(time.time() * 1000))
            project_root = Path(__file__).parent
            output_file = project_root / "tmp" / f"outetts_{request_id}.wav"
            (project_root / "tmp").mkdir(exist_ok=True)

            _safe_print(f"[TTS-GPU] {len(text)} chars - generando...")

            proc = subprocess.Popen(
                [str(llama_tts), "-m", str(model_path), "--tts-oute-default",
                 "-p", text, "-o", str(output_file), "-ngl", "99"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
                add_log("tts_error", "OuteTTS timed out (>30s)", voice_model="outetts")
                self._json_response({"error": "OuteTTS timed out"})
                return

            if proc.returncode != 0:
                add_log("tts_error", f"OuteTTS falló (código {proc.returncode})", voice_model="outetts")
                self._json_response({"error": f"OuteTTS falló (código {proc.returncode})"})
                return

            if not output_file.exists():
                add_log("tts_error", "No se generó archivo WAV", voice_model="outetts")
                self._json_response({"error": "No se generó archivo WAV"})
                return

            wav_data = output_file.read_bytes()

            try:
                output_file.unlink(missing_ok=True)
            except Exception:
                pass

            add_log("tts", f"{len(wav_data)}B (GPU)", voice_model="outetts")

            _safe_print(f"[TTS-GPU] {len(wav_data)} bytes generados")

            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(wav_data)))
            self.end_headers()
            self.wfile.write(wav_data)

        except Exception as e:
            add_log("tts_error", f"GPU TTS error: {str(e)[:100]}", voice_model="outetts")
            self._json_response({"error": str(e)[:200]})

    def _handle_asr(self, body):
        """Recibe audio WAV, transcribe con faster-whisper y devuelve texto.
        
        Usa faster-whisper (Python API, modelo tiny en CPU) como método
        primario. Caída a whisper-cli.exe si faster-whisper no está disponible.
        
        Input:  {"audio": "base64_wav", "lang": "es|en|ja|auto"}  o raw WAV
        Output: {"text": "...", "segments": [...], "language": "..."}
        """
        global _asr_model
        project_root = Path(__file__).parent
        whisper_exe = project_root / "bin" / "whisper" / "Release" / "whisper-cli.exe"
        whisper_model_path = project_root / "models" / "ggml-tiny.bin"
        t0 = time.time()
        lang = "auto"
        
        # ── Parse input: JSON or raw WAV ──
        is_json = False
        data = None
        raw_audio = body
        if len(body) > 4 and body[0:1] in (b'{', b'['):
            try:
                data = json.loads(body)
                is_json = True
            except Exception:
                is_json = False
        
        if is_json and data:
            # JSON mode: check for echo test
            text = data.get("text", "")
            lang = data.get("lang", "auto")
            if text:
                # Text echo mode (testing)
                self._json_response({"text": text, "segments": [{"text": text}]})
                return
            
            # Base64 audio
            audio_b64 = data.get("audio", "")
            if not audio_b64:
                self._json_response({"error": "No se recibió audio"})
                return
            try:
                raw_audio = base64.b64decode(audio_b64)
            except Exception as e:
                self._json_response({"error": f"Error decodificando: {str(e)[:100]}"})
                return
        
        if len(raw_audio) < 100:
            self._json_response({"error": "Audio demasiado pequeño"})
            return
        
        file_size = len(raw_audio)
        _safe_print(f"[ASR] {file_size} bytes - transcribiendo...")
        
        # ── PRIMARY: faster-whisper (Python API) ──
        text_result = None
        segments_result = None
        error_msg = None
        method_used = "faster-whisper"
        
        if HAVE_FASTER_WHISPER and _asr_model is not None:
            try:
                text_result, segments_result, error_msg = _asr_transcribe(raw_audio, lang)
            except Exception as e:
                error_msg = str(e)[:200]
            
            if text_result:
                _safe_print(f"[ASR] faster-whisper: {len(text_result)} chars en {(time.time()-t0)*1000:.0f}ms")
        
        # ── FALLBACK: whisper-cli.exe ──
        if not text_result and whisper_exe.exists() and whisper_model_path.exists():
            method_used = "whisper-cli"
            try:
                # Guardar WAV temporal
                request_id = str(int(time.time() * 1000))
                (project_root / "tmp").mkdir(exist_ok=True)
                input_file = project_root / "tmp" / f"asr_{request_id}.wav"
                input_file.write_bytes(raw_audio)
                
                cmd = [
                    str(whisper_exe), "-m", str(whisper_model_path),
                    "-f", str(input_file), "-l", lang,
                    "-np", "-t", "4", "--no-prints",
                ]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    stdout, stderr = proc.communicate(timeout=30)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    error_msg = "whisper.cpp timed out"
                    stdout = b""
                
                try:
                    input_file.unlink(missing_ok=True)
                except Exception:
                    pass
                
                if proc.returncode == 0 and stdout:
                    output_text = stdout.decode('utf-8', errors='replace').strip()
                    segments_result = []
                    full_text = []
                    for line in output_text.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        m = re.match(r'^\[\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}\](.*)', line)
                        if m:
                            seg_text = m.group(1).strip()
                            if seg_text:
                                segments_result.append({"text": seg_text})
                                full_text.append(seg_text)
                        elif not line.startswith('['):
                            segments_result.append({"text": line})
                            full_text.append(line)
                    text_result = " ".join(full_text).strip() or output_text
                    error_msg = None
                else:
                    err_text = stderr.decode('utf-8', errors='replace')[:200]
                    error_msg = f"whisper falló (código {proc.returncode}): {err_text}"
            except Exception as e:
                error_msg = str(e)[:200]
        
        # ── Result ──
        duration_ms = round((time.time() - t0) * 1000)
        if not text_result:
            error_msg = error_msg or "ASR no disponible (ni faster-whisper ni whisper-cli.exe)"
            add_log("asr_error", error_msg, duration_ms=duration_ms, language=lang, method=method_used)
            self._json_response({"error": error_msg})
            return
        
        add_log("asr", f"{len(text_result)} chars en {duration_ms}ms: {text_result[:100]}",
                duration_ms=duration_ms, char_count=len(text_result), language=lang, method=method_used)
        self._json_response({
            "text": text_result,
            "segments": segments_result or [],
            "language": lang,
            "duration_ms": duration_ms,
        })

    def _handle_tts(self, body):
        """Ejecuta Piper TTS con el texto recibido y devuelve el WAV."""
        try:
            data = json.loads(body)
            text = data.get("text", "")
            if not text.strip():
                self._json_response({"error": "texto vacío"})
                return

            # Configuración de rutas
            project_root = Path(__file__).parent
            piper_exe = project_root / "bin" / "piper" / "piper.exe"
            model_path = project_root / "models" / "es_ES-sharvard-medium.onnx"
            # Detectar idioma del texto y elegir modelo de voz
            es_chars = sum(1 for c in text if '\u00e1' <= c <= '\u00fa' or c in 'ñçüöéèêëàâîôùû')
            en_keywords = {'the', 'is', 'are', 'was', 'were', 'and', 'this', 'that', 'with', 'have', 'has', 'had', 'not', 'but', 'for', 'you', 'all', 'can', 'our', 'its', 'what', 'will', 'been', 'from', 'they', 'would', 'about', 'there', 'their', 'your', 'which', 'when', 'make', 'like', 'just', 'over', 'also', 'than', 'then', 'some', 'them', 'into', 'could', 'other', 'than', 'more', 'these', 'many', 'each', 'here', 'very', 'only', 'two', 'way', 'even', 'much', 'new', 'any', 'such', 'long', 'same', 'right', 'high', 'down', 'back', 'good', 'own', 'old', 'great', 'well', 'first', 'last', 'life', 'hand', 'part', 'world', 'state', 'need', 'feel', 'three', 'place', 'help', 'point', 'case', 'week', 'company', 'system', 'program', 'work', 'room', 'area', 'thing', 'fact', 'thing', 'side', 'head', 'night', 'days', 'home', 'water', 'order', 'small', 'found', 'still', 'name', 'line', 'turn', 'set', 'play', 'land', 'sea', 'example', 'end', 'group', 'number', 'ever', 'mean', 'let', 'kind', 'hand', 'men', 'women', 'girl', 'boy', 'world', 'year', 'week', 'month', 'day', 'hour', 'minute', 'second', 'time', 'now', 'today', 'always', 'never', 'sometimes', 'often', 'usually', 'already', 'still', 'yet', 'because', 'before', 'after', 'since', 'until', 'while', 'though', 'although', 'however', 'therefore', 'thus', 'hence', 'furthermore', 'moreover', 'nevertheless', 'nonetheless', 'consequently', 'accordingly', 'additionally', 'meanwhile', 'incidentally', 'likewise', 'namely', 'otherwise', 'still', 'then', 'thereafter', 'thus', 'hence', 'lastly', 'finally', 'further', 'indeed', 'indeed', 'perhaps', 'maybe', 'quite', 'rather', 'hardly', 'barely', 'scarcely', 'nearly', 'almost', 'just', 'only', 'simply', 'merely'}
            words = [w.strip('.,!?;:\'"()[]{}') for w in text.lower().split() if w.strip('.,!?;:\'"()[]{}')]
            total_words = len(words)
            en_count = sum(1 for w in words if w in en_keywords)
            en_ratio = en_count / total_words if total_words > 0 else 0
            # Decidir idioma por proporción de palabras inglesas
            eng_model = project_root / "models" / "en_US-lessac-medium.onnx"
            if en_ratio > 0.3 or (en_count > 2 and es_chars < 3):
                if eng_model.exists():
                    model_path = eng_model
                    _safe_print(f"[TTS] Ingles ({model_path.name}) - ratio={en_ratio:.2f}")
                else:
                    _safe_print("[TTS] No hay modelo ingles, usando espanol")

            # ID único por request para evitar colisiones
            request_id = str(int(time.time() * 1000))
            output_file = project_root / "tmp" / f"tts_{request_id}.wav"
            (project_root / "tmp").mkdir(exist_ok=True)

            _safe_print(f"[TTS] {len(text)} chars - {model_path.name}")

            # Verificar existencia antes de ejecutar
            if not piper_exe.exists():
                add_log("tts_error", f"Piper no encontrado en {piper_exe}", voice_model="error")
                self._json_response({"error": f"Piper no encontrado en {piper_exe}"})
                return
            if not model_path.exists():
                add_log("tts_error", f"Modelo no encontrado: {model_path}", voice_model="error")
                self._json_response({"error": f"Modelo no encontrado: {model_path}"})
                return

            # Escribir texto a archivo temporal (evita problemas de encoding en pipe de Windows)
            input_file = project_root / "tmp" / f"tts_input_{request_id}.txt"
            input_file.write_text(text, encoding="utf-8")

            # Ejecutar Piper usando archivo como input (evita pipe encoding issues)
            proc = subprocess.Popen(
                [str(piper_exe), "--model", str(model_path), "--output-file", str(output_file)],
                stdin=open(str(input_file), "rb"),  # leer archivo como stdin
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            proc.wait(timeout=15)

            # Limpiar archivo de entrada
            try:
                input_file.unlink(missing_ok=True)
            except Exception:
                pass

            if proc.returncode != 0:
                add_log("tts_error", f"Piper falló (código {proc.returncode})", voice_model=model_path.name)
                self._json_response({"error": f"Piper falló (código {proc.returncode})"})
                return

            # Leer el WAV generado
            if not output_file.exists():
                add_log("tts_error", "No se generó el archivo WAV", voice_model=model_path.name)
                self._json_response({"error": "No se generó el archivo WAV"})
                return

            wav_data = output_file.read_bytes()

            # Limpiar archivo temporal
            try:
                output_file.unlink(missing_ok=True)
            except Exception:
                pass

            add_log("tts", f"{len(wav_data)}B", voice_model=model_path.name)

            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(wav_data)))
            self.end_headers()
            self.wfile.write(wav_data)

        except subprocess.TimeoutExpired:
            add_log("tts_error", "Piper timed out (>15s)")
            self._json_response({"error": "Piper timed out (>15s)"})
        except Exception:
            # Si el WAV se generó a pesar del error, devolverlo
            try:
                if output_file.exists():
                    wav_data = output_file.read_bytes()
                    if len(wav_data) > 1000:
                        self.send_response(200)
                        self.send_header("Content-Type", "audio/wav")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.send_header("Content-Length", str(len(wav_data)))
                        self.end_headers()
                        self.wfile.write(wav_data)
                        return
            except Exception:
                pass
            add_log("tts_error", "Error al generar audio")
            self._json_response({"error": "Error al generar audio"})

    def log_message(self, fmt, *args):
        msg = fmt % args
        if "/api/stats" not in msg and "/tts" not in msg:
            _safe_print(f"[monitor] {msg}")


# ── Punto de entrada ───────────────────────────────────────────
def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # Windows UTF-8 fix

    global _stats_collector
    _stats_collector = StatsCollector()

    httpd = HTTPServer(("0.0.0.0", PORT), Handler)

    _safe_print(f"\n{'='*50}")
    _safe_print(f"  >> Alex Voice - Monitor Server")
    _safe_print(f"{'='*50}")
    _safe_print(f"  Web UI:       http://localhost:{PORT}")
    _safe_print(f"  Stats API:    http://localhost:{PORT}/api/stats")
    _safe_print(f"  llama-server: {LLAMA_HOST}")
    _safe_print(f"  Poll rate:    cada {POLL_INTERVAL}s")
    _safe_print(f"{'='*50}")
    _safe_print("  Presiona Ctrl+C para detener\n")

    # Inicializar ASR (faster-whisper modelo tiny en CPU)
    global _asr_model
    if HAVE_FASTER_WHISPER:
        try:
            t0 = time.time()
            _asr_model = WhisperModel("tiny", device="cpu", compute_type="int8")
            _safe_print(f"  [ASR] faster-whisper tiny cargado en {(time.time()-t0)*1000:.0f}ms")
        except Exception as e:
            _safe_print(f"  [!] Error cargando faster-whisper: {e}")
            _asr_model = None
    
    # Inicializar PiperTTS (modelos precargados en memoria via Python API)
    global _piper_tts, _piper_es, _piper_en, _piper_exe_path
    try:
        project_root = Path(__file__).parent
        piper_exe = project_root / "bin" / "piper" / "piper.exe"
        es_model = project_root / "models" / "es_ES-sharvard-medium.onnx"
        en_model = project_root / "models" / "en_US-lessac-medium.onnx"
        
        _piper_exe_path = piper_exe if piper_exe.exists() else None
        
        # PRIMARY: PiperTTS Python API (modelos en memoria, ~45ms)
        if es_model.exists() or en_model.exists():
            _piper_tts = PiperTTS(
                es_model_path=es_model if es_model.exists() else None,
                en_model_path=en_model if en_model.exists() else None,
                piper_exe_path=piper_exe if piper_exe.exists() else None,
            )
            if _piper_tts and _piper_tts.available:
                _safe_print(f"  [PiperTTS] Listo! Latencia ~45ms por sintesis")
        
        # FALLBACK: Procesos Piper persistentes (pipe, ~2100ms)
        if piper_exe.exists():
            if es_model.exists() and (not _piper_tts or not _piper_tts.es_voice):
                _piper_es = PiperPersistentProcess(piper_exe, es_model, "es_ES")
                if _piper_es and _piper_es.available:
                    _safe_print(f"  [Fallback] ES persistente listo")
            if en_model.exists() and (not _piper_tts or not _piper_tts.en_voice):
                _piper_en = PiperPersistentProcess(piper_exe, en_model, "en_US")
                if _piper_en and _piper_en.available:
                    _safe_print(f"  [Fallback] EN persistente listo")
        
        if not _piper_tts and not _piper_es and not _piper_en:
            _safe_print(f"  [!] Piper no disponible")
    except Exception as e:
        _safe_print(f"  [!] Error iniciando Piper: {e}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        _safe_print("\nDeteniendo monitor...")
    finally:
        _stats_collector.stop()
        if _piper_tts:
            _piper_tts.stop()
        if _piper_es:
            _piper_es.stop()
        if _piper_en:
            _piper_en.stop()
        httpd.server_close()
        if HAVE_NVML:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
        _safe_print("Monitor detenido.")


if __name__ == "__main__":
    main()
