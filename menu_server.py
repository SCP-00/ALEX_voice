#!/usr/bin/env python3
"""
Alex Voice — Menu Server (port 5000)
====================================
Hub principal: sirve el menú y gestiona el ciclo de vida de los modos.

API:
  GET  /                    → menu.html
  GET  /api/status          → {mode: running | null, servers: [...]}
  POST /api/start/teacher   → Inicia Teacher (llama-server + server.py)
  POST /api/start/conv      → Inicia Conversación (llama-server + server.py)
  POST /api/start/translator→ Inicia Traductor (translator.py)
  POST /api/start/llama     → Inicia llama-server (standalone)
  POST /api/stop            → Mata todos los procesos
"""

import json, os, sys, time, signal, subprocess, urllib.request, urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread, Lock
from urllib.parse import urlparse, parse_qs, unquote

# ── History + Vocabulary engine ──
import history as history_mod

PROJECT_ROOT = Path(__file__).parent.resolve()
FRONTEND_DIR = PROJECT_ROOT / "frontend"
MENU_PORT = 5000
LLAMA_PORT = 8081
LLAMA_HOST = f"http://localhost:{LLAMA_PORT}"

PYTHON = sys.executable
MODEL_DIR = PROJECT_ROOT / "models"

BACKEND_PRIORITY = ["llama-server-cuda", "llama-server-vulkan", "llama-server"]
BACKEND_LABELS = {
    "llama-server-cuda": "🎮 CUDA",
    "llama-server-vulkan": "⚡ Vulkan",
    "llama-server": "🖥️ CPU",
}

def find_best_llama():
    """Busca el mejor backend disponible."""
    llama_bin = PROJECT_ROOT / "llama-server-bin"
    for name in BACKEND_PRIORITY:
        candidate = llama_bin / name
        if candidate.exists():
            return candidate, BACKEND_LABELS.get(name, name)
        win_candidate = llama_bin / f"{name}.exe"
        if win_candidate.exists():
            return win_candidate, BACKEND_LABELS.get(name, name)
    # Fallback: buscar en llama.cpp build dir
    for path in [
        PROJECT_ROOT / "llama.cpp" / "build" / "bin" / "llama-server",
        PROJECT_ROOT / "llama.cpp" / "build-vulkan" / "bin" / "llama-server",
    ]:
        if path.exists():
            return path, "🖥️ CPU"
    return None, "❌ No disponible"

# ── Procesos activos ──
_running = {}   # nombre -> subprocess.Popen
_lock = Lock()
_current_modes = set()  # múltiples modos pueden estar activos

def eprint(msg):
    try: print(msg)
    except: pass

def log(msg):
    eprint(f"[Menu] {msg}")

# ── Buscar modelo GGUF ──
# Prioridad: Qwen3.5-2B (256k contexto, mejor calidad) > Qwen2.5-1.5B (estándar)
def find_model():
    if not MODEL_DIR.exists():
        return None
    # Preferir Qwen3.5-2B (más inteligente, 256k contexto nativo)
    qwen35 = MODEL_DIR / "qwen3.5-2b-q4_k_m.gguf"
    if qwen35.exists():
        return qwen35
    qwen25 = MODEL_DIR / "qwen2.5-1.5b-q4_k_m.gguf"
    if qwen25.exists():
        return qwen25
    models = sorted(MODEL_DIR.glob("*.gguf"))
    return models[0] if models else None

def get_model_context():
    """Retorna el contexto recomendado según el modelo."""
    model = find_model()
    if model and "qwen3.5" in model.name.lower():
        return 131072  # 128k para Qwen3.5-2B (soporta 256k nativo)
    return 131072  # 128k para todos los modelos modernos (~2.4GB VRAM total)

def find_llama():
    exe, label = find_best_llama()
    if exe:
        return exe
    return None

def get_backend_label():
    _, label = find_best_llama()
    return label

def check_llama_alive():
    try:
        req = urllib.request.Request(f"{LLAMA_HOST}/slots")
        with urllib.request.urlopen(req, timeout=2) as r:
            return True
    except:
        return False

def wait_for_llama(timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if check_llama_alive():
            return True
        time.sleep(1)
    return False
def kill_process(name):
    global _current_modes
    with _lock:
        proc = _running.pop(name, None)
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                try: proc.kill()
                except: pass
        # Actualizar modos activos
        _current_modes = {m for m in _current_modes if m != name}

def kill_all():
    global _current_modes
    with _lock:
        for name, proc in list(_running.items()):
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except:
                    try: proc.kill()
                    except: pass
        _running.clear()
        _current_modes.clear()
    # Matar llama-server si está vivo (coincidencia exacta)
    try:
        subprocess.run(["pkill", "-x", "llama-server"],
                       capture_output=True, timeout=5)
    except:
        pass

def start_llama(model_path):
    if check_llama_alive():
        log("llama-server ya está corriendo")
        return True
    exe = find_llama()
    if not exe:
        log("llama-server no encontrado")
        return False
    backend_label = get_backend_label()
    args = [
        str(exe), "-m", str(model_path),
        "--host", "0.0.0.0", "--port", str(LLAMA_PORT),
        "-c", str(get_model_context()),
        "--chat-template", "chatml", "--no-warmup",
    ]
    # GPU layers: auto-detect by backend
    if "cpu" in backend_label.lower():
        args.extend(["-ngl", "0"])
    else:
        args.extend(["-ngl", "99"])
    # Set LD_LIBRARY_PATH for llama-server to find libllama.so
    llama_env = os.environ.copy()
    llama_bin_dir = str(PROJECT_ROOT / "llama-server-bin")
    llama_env["LD_LIBRARY_PATH"] = f"{llama_bin_dir}:" + llama_env.get("LD_LIBRARY_PATH", "")
    try:
        proc = subprocess.Popen(args, env=llama_env)
        with _lock:
            _running["llama-server"] = proc
        log(f"llama-server ({backend_label}) iniciado, esperando carga del modelo...")
        if wait_for_llama():
            log(f"llama-server ({backend_label}) listo")
            return True
        log("Tiempo de espera agotado")
        return False
    except Exception as e:
        log(f"Error iniciando llama-server: {e}")
        return False
def start_server(script, name, port, mode):
    global _current_modes
    path = PROJECT_ROOT / script
    if not path.exists():
        log(f"Script no encontrado: {path}")
        return False
    env = os.environ.copy()
    env["PLAN_B_PORT"] = str(port)
    # Set CUDA library path for subprocesses (PyTorch CUDA needs it)
    # Auto-detect Python version for venv path
    py_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    cuda_lib = PROJECT_ROOT / "venv" / "lib" / py_version / "site-packages" / "nvidia" / "cuda_runtime" / "lib"
    if not cuda_lib.exists():
        # Fallback: search for nvidia/cuda_runtime in site-packages
        for sp in [PROJECT_ROOT / "venv" / "lib" / py_version / "site-packages",
                    PROJECT_ROOT / "venv" / "lib64" / py_version / "site-packages"]:
            if sp.exists():
                for cuda_dir in sp.glob("nvidia/cuda_runtime/lib"):
                    if cuda_dir.exists():
                        cuda_lib = cuda_dir
                        break
    if cuda_lib.exists():
        env["LD_LIBRARY_PATH"] = f"{cuda_lib}:" + env.get("LD_LIBRARY_PATH", "")
    try:
        proc = subprocess.Popen(
            [PYTHON, str(path)],
            env=env,
        )
        with _lock:
            _running[name] = proc
            _current_modes.add(name)
        time.sleep(2)
        return True
    except Exception as e:
        log(f"Error iniciando {name}: {e}")
        return False

# ── HTTP Handler ──
class MenuHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/":
            self._serve("menu.html")
        elif self.path == "/api/status":
            self._json({
                "modes": list(_current_modes),
                "servers": list(_running.keys()),
                "llama_alive": check_llama_alive(),
            })
        elif self.path == "/api/history/list":
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            limit = int(qs.get('limit', ['50'])[0])
            self._json({'conversations': history_mod.list_conversations(limit)})
        elif self.path.startswith("/api/history/get"):
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            conv_id = qs.get('id', [''])[0]
            if not conv_id:
                self._json({'error': 'Missing id'})
                return
            conv = history_mod.load_conversation(conv_id)
            if conv:
                self._json(conv)
            else:
                self._json({'error': 'Not found'})
        elif self.path == "/api/vocabulary":
            self._json(history_mod.get_all_vocabulary())
        elif self.path == "/api/vocabulary/stats":
            self._json(history_mod.get_vocabulary_stats())
        elif self.path == "/api/vocabulary/due":
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            limit = int(qs.get('limit', ['20'])[0])
            self._json({'words': history_mod.get_due_vocabulary(limit)})
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/start/teacher":
            self._start_mode("teacher", port=3000, mode_name="teacher")
        elif self.path == "/api/start/conv":
            self._start_mode("conv", port=3001, mode_name="conversation")
        elif self.path == "/api/start/translator":
            self._start_mode("translator", port=3003, mode_name="translator")
        elif self.path == "/api/stop":
            kill_all()
            self._json({"ok": True, "message": "Todos los servidores detenidos"})
        elif self.path == "/api/history/delete":
            data = self._parse_body()
            ok = history_mod.delete_conversation(data.get('id', ''))
            self._json({'ok': ok})
        elif self.path == "/api/history/clear":
            count = history_mod.clear_all_history()
            self._json({'ok': True, 'deleted': count})
        elif self.path == "/api/vocabulary/delete":
            data = self._parse_body()
            ok = history_mod.delete_vocabulary_word(data.get('word', ''), data.get('language', ''))
            self._json({'ok': ok})
        elif self.path == "/api/vocabulary/clear":
            count = history_mod.clear_all_vocabulary()
            self._json({'ok': True, 'deleted': count})
        else:
            self._json({"error": "ruta no valida"})

    def _start_mode(self, name, port, mode_name):
        # Si hay un modo LLM activo, detenerlo primero
        for active in list(_current_modes):
            if active in ("teacher", "conv"):
                log(f"Deteniendo modo activo '{active}' antes de iniciar '{name}'")
                kill_all()
                time.sleep(1)
                break
        
        # Translator puede correr independientemente
        if name == "translator":
            if "translator" in _current_modes:
                self._json({"ok": True, "url": "http://localhost:3003", "mode": "translator", "info": "Ya estaba corriendo"})
                return
            ok = start_server("translator.py", "translator", 3003, "translator")
            if ok:
                self._json({"ok": True, "url": "http://localhost:3003", "mode": "translator"})
            else:
                self._json({"error": "No se pudo iniciar el Traductor"})
            return

        # Teacher o Conversation: necesita llama-server
        model = find_model()
        if not model:
            self._json({"error": "No se encontró modelo GGUF"})
            return

        llama_ok = start_llama(model)
        if not llama_ok:
            self._json({"error": "llama-server no pudo cargar el modelo en GPU"})
            return

        # Elegir script según modo
        if name == "conv":
            script = "conv_server.py"
        else:
            script = "teacher_server.py"

        ok = start_server(script, name, port, mode_name)
        if ok:
            self._json({"ok": True, "url": f"http://localhost:{port}", "mode": mode_name})
        else:
            self._json({"error": "No se pudo iniciar el servidor"})



    def _parse_body(self):
        """Parse JSON body from POST request."""
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length > 0:
                return json.loads(self.rfile.read(length).decode())
        except:
            pass
        return {}

    def _serve(self, filename):
        fp = FRONTEND_DIR / filename
        if fp.exists():
            self.path = f"/{filename}"
            super().do_GET()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt, *args):
        msg = fmt % args
        if "/api/" in msg:
            log(msg)

# ── Main ──
def main():
    signal.signal(signal.SIGINT, lambda s, f: (kill_all(), sys.exit(0)))
    signal.signal(signal.SIGTERM, lambda s, f: (kill_all(), sys.exit(0)))

    httpd = HTTPServer(("0.0.0.0", MENU_PORT), MenuHandler)
    print(f"\n{'='*50}")
    print(f"  >> Alex Voice — Menu Principal")
    print(f"  >> http://localhost:{MENU_PORT}")
    print(f"  >> Presiona Ctrl+C para cerrar")
    print(f"{'='*50}\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Menu] Cerrando...")
    finally:
        kill_all()
        httpd.server_close()
        print("[Menu] Detenido.")

if __name__ == "__main__":
    main()
