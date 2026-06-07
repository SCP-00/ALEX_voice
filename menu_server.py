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
  POST /api/start/all       → Inicia todo
  POST /api/stop            → Mata todos los procesos
"""

import json, os, sys, time, signal, subprocess, urllib.request, urllib.error, webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread, Lock

PROJECT_ROOT = Path(__file__).parent.resolve()
FRONTEND_DIR = PROJECT_ROOT / "frontend"
MENU_PORT = 5000
LLAMA_PORT = 8081
LLAMA_HOST = f"http://localhost:{LLAMA_PORT}"

PYTHON = sys.executable
LLAMA_EXE = PROJECT_ROOT / "llama-server-bin" / "llama-server"
LLAMA_EXE_WIN = PROJECT_ROOT / "llama-server-bin" / "llama-server.exe"
MODEL_DIR = PROJECT_ROOT / "models"

# ── Procesos activos ──
_running = {}   # nombre -> subprocess.Popen
_lock = Lock()
_current_mode = None

def eprint(msg):
    try: print(msg)
    except: pass

def log(msg):
    eprint(f"[Menu] {msg}")

# ── Buscar modelo GGUF ──
def find_model():
    if not MODEL_DIR.exists():
        return None
    models = sorted(MODEL_DIR.glob("*.gguf"))
    return models[0] if models else None

def find_llama():
    if LLAMA_EXE.exists():
        return LLAMA_EXE
    if LLAMA_EXE_WIN.exists():
        return LLAMA_EXE_WIN
    # Fallback: solo revisar paths conocidos
    for path in [
        PROJECT_ROOT / "llama.cpp" / "llama-server",
        PROJECT_ROOT / "llama.cpp" / "build" / "bin" / "llama-server",
    ]:
        if path.exists():
            return path
    return None

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
    global _current_mode
    with _lock:
        proc = _running.pop(name, None)
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                try: proc.kill()
                except: pass
        if not _running:
            _current_mode = None

def kill_all():
    global _current_mode
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
        _current_mode = None
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
    args = [
        str(exe), "-m", str(model_path),
        "--host", "0.0.0.0", "--port", str(LLAMA_PORT),
        "-ngl", "99", "-c", "8192",
        "--chat-template", "chatml", "--no-warmup",
    ]
    # Set LD_LIBRARY_PATH for llama-server to find libllama.so
    llama_env = os.environ.copy()
    llama_bin_dir = str(PROJECT_ROOT / "llama-server-bin")
    llama_env["LD_LIBRARY_PATH"] = f"{llama_bin_dir}:" + llama_env.get("LD_LIBRARY_PATH", "")
    try:
        proc = subprocess.Popen(args, env=llama_env)
        with _lock:
            _running["llama-server"] = proc
        log("llama-server iniciado, esperando carga del modelo...")
        if wait_for_llama():
            log("llama-server listo")
            return True
        log("Tiempo de espera agotado")
        return False
    except Exception as e:
        log(f"Error iniciando llama-server: {e}")
        return False

def start_server(script, name, port, mode):
    global _current_mode
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
            _current_mode = mode
        time.sleep(2)
        return True
    except Exception as e:
        log(f"Error iniciando {name}: {e}")
        return False

def open_browser(url):
    try:
        webbrowser.open(url)
    except:
        pass

# ── HTTP Handler ──
class MenuHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/":
            self._serve("menu.html")
        elif self.path == "/api/status":
            self._json({
                "mode": _current_mode,
                "servers": list(_running.keys()),
                "llama_alive": check_llama_alive(),
            })
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
        else:
            self._json({"error": "ruta no valida"})

    def _start_mode(self, name, port, mode_name):
        if _current_mode:
            self._json({
                "error": f"Ya hay un modo activo: {_current_mode}. Detenlo antes de iniciar otro.",
                "current_mode": _current_mode,
            })
            return

        if name == "translator":
            ok = start_server("translator.py", "translator", 3003, "translator")
            if ok:
                t = Thread(target=lambda: (time.sleep(3), open_browser("http://localhost:3003")))
                t.daemon = True
                t.start()
                self._json({"ok": True, "url": "http://localhost:3003", "mode": "translator"})
            else:
                self._json({"error": "No se pudo iniciar el Traductor"})
            return

        if name == "conv":
            model = find_model()
            if not model:
                self._json({"error": "No se encontró modelo GGUF. Ejecuta setup.bat primero."})
                return
            llama_ok = start_llama(model)
            if not llama_ok:
                self._json({"error": "llama-server no pudo cargar el modelo en GPU"})
                return
            ok = start_server("conv_server.py", "conv", 3001, "conversation")
            if ok:
                t = Thread(target=lambda: (time.sleep(2), open_browser("http://localhost:3001")))
                t.daemon = True
                t.start()
                self._json({"ok": True, "url": "http://localhost:3001", "mode": "conversation"})
            else:
                self._json({"error": "No se pudo iniciar Conversación"})
            return

        # Teacher: necesita llama-server
        model = find_model()
        if not model:
            self._json({"error": "No se encontró modelo GGUF. Ejecuta setup.bat primero."})
            return

        # Iniciar llama-server (blocking — espera hasta que el modelo cargue en GPU)
        llama_ok = start_llama(model)
        if not llama_ok:
            self._json({"error": "llama-server no pudo cargar el modelo en GPU"})
            return

        # Iniciar server.py
        ok = start_server("server.py", name, port, mode_name)
        if ok:
            t = Thread(target=lambda: (time.sleep(2), open_browser(f"http://localhost:{port}")))
            t.daemon = True
            t.start()
            self._json({"ok": True, "url": f"http://localhost:{port}", "mode": mode_name})
        else:
            self._json({"error": "No se pudo iniciar el servidor"})



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
