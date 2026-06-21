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
# Ollama API: prometheus-orchestrator (Qwen3.5 4B Instruct)
OLLAMA_HOST = "http://localhost:11434/v1"
OLLAMA_MODEL = "prometheus-orchestrator"

# ── Procesos activos ──
_running = {}   # nombre -> subprocess.Popen
_lock = Lock()
_current_mode = None

def eprint(msg):
    try: print(msg)
    except: pass

def log(msg):
    eprint(f"[Menu] {msg}")

def check_ollama_alive():
    """Verificar si Ollama API responde."""
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/models")
        with urllib.request.urlopen(req, timeout=3) as r:
            if r.status == 200:
                return True
        return False
    except urllib.error.HTTPError as e:
        # 404 significa que el endpoint /models no existe en algunas versiones de Ollama
        # pero el servidor está vivo
        if e.code == 404:
            return True
        return False
    except Exception:
        return False

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
    # Liberar modelo de Ollama (descargar de VRAM) usando /api/generate
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=json.dumps({"model": OLLAMA_MODEL, "keep_alive": "0m"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3):
            pass
    except Exception:
        pass
    # Matar procesos hij@s (server.py, translator.py)
    try:
        subprocess.run(["pkill", "-f", "python.*server.py"], capture_output=True, timeout=5)
    except:
        pass
    try:
        subprocess.run(["pkill", "-f", "python.*translator.py"], capture_output=True, timeout=5)
    except:
        pass

def start_server(script, name, port, mode):
    global _current_mode
    path = PROJECT_ROOT / script
    if not path.exists():
        log(f"Script no encontrado: {path}")
        return False
    env = os.environ.copy()
    env["PLAN_B_PORT"] = str(port)
    env["OLLAMA_LLAMA_MODEL"] = OLLAMA_MODEL
    env["LLAMA_HOST"] = OLLAMA_HOST
    try:
        _kwargs = {"env": env}
        if sys.platform == "win32":
            _kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        proc = subprocess.Popen(
            [PYTHON, str(path)],
            **_kwargs,
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
                "ollama_alive": check_ollama_alive(),
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
            if not check_ollama_alive():
                self._json({"error": "Ollama no está corriendo. Ejecuta 'ollama serve' primero."})
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

        # Teacher: necesita Ollama con prometheus-orchestrator
        if not check_ollama_alive():
            self._json({"error": "Ollama no está corriendo. Ejecuta 'ollama serve' primero."})
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
