#!/usr/bin/env python3
"""
Alex Voice — Universal Launcher
================================
Inicia de forma confiable: llama-server + servidor del plan + navegador.
Soporta Windows y Linux.

Uso:
    python launcher.py

Windows (doble clic):
    python launcher.py
Linux:
    source venv/bin/activate && python launcher.py
"""

import json, os, sys, time, signal, subprocess, urllib.request, urllib.error, threading, webbrowser
from pathlib import Path
from datetime import datetime
import platform

IS_WINDOWS = platform.system() == "Windows"

# ── Config ──────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()

# Windows-specific paths (only used on Windows)
if IS_WINDOWS:
    DOCUMENTS_LLAMA_DIR = Path.home() / "Documents" / "llama-b9479-bin-win-cuda-13.3-x64"
    MODEL_DIR_Q8 = Path(r"C:\Users\andyh\.lmstudio\models\khazarai\Qwen3.5-2B-Qwen3.6-plus-Distilled-GGUF")
    MODEL_DIR_Q4 = Path(r"C:\Users\andyh\.lmstudio\models\Qwen\Qwen2.5-1.5B-Instruct-GGUF")
    PYTHON_EXE = Path(sys.executable)  # Use current Python
else:
    DOCUMENTS_LLAMA_DIR = None
    MODEL_DIR_Q8 = None
    MODEL_DIR_Q4 = None
    PYTHON_EXE = Path(sys.executable)

LLAMA_PORT = 8081
LLAMA_HOST = f"http://localhost:{LLAMA_PORT}"

# ── Procesos manejados ───────────────────────────────────────
_processes = []  # lista de subprocess.Popen
_cleanup_done = False

# ── Utils ────────────────────────────────────────────────────
def eprint(msg=""):
    try: print(msg)
    except UnicodeEncodeError:
        try: print(msg.encode('ascii', errors='replace').decode('ascii'))
        except: pass

def now_str():
    return datetime.now().strftime("%H:%M:%S")

def log(msg):
    eprint(f"[{now_str()}] {msg}")

def find_model(force_q8=False):
    """Elige el mejor modelo disponible. Prioridad: models/ local > LM Studio (Windows)."""
    env_model = os.environ.get("ALEX_MODEL")
    if env_model:
        p = Path(env_model)
        if p.exists():
            return p, f"Modelo env ({p.name})", 8192

    local_models = [
        (PROJECT_ROOT / "models" / "qwen2.5-1.5b-q4_k_m.gguf", "Qwen2.5-1.5B-Q4_K_M", 8192),
        (PROJECT_ROOT / "models" / "qwen2.5-1.5b-instruct-q4_k_m.gguf", "Qwen2.5-1.5B-Q4_K_M", 8192),
    ]
    
    # Windows-only LM Studio paths
    if IS_WINDOWS and MODEL_DIR_Q4:
        q4_path = MODEL_DIR_Q4 / "qwen2.5-1.5b-instruct-q4_k_m.gguf"
    else:
        q4_path = None
    if IS_WINDOWS and MODEL_DIR_Q8:
        q8_path = MODEL_DIR_Q8 / "Qwen3.5-2B-Qwen3.6-plus-Distilled-q8_0.gguf"
    else:
        q8_path = None

    for path, label, ctx in local_models:
        if path.exists() and not force_q8:
            return path, label, ctx

    local_alternatives = list((PROJECT_ROOT / "models").glob("*.gguf")) if (PROJECT_ROOT / "models").exists() else []
    q4_alternatives = list(MODEL_DIR_Q4.glob("*.gguf")) if IS_WINDOWS and MODEL_DIR_Q4 and MODEL_DIR_Q4.exists() else []
    q8_alternatives = list(MODEL_DIR_Q8.glob("*.gguf")) if IS_WINDOWS and MODEL_DIR_Q8 and MODEL_DIR_Q8.exists() else []

    if force_q8 and q8_path and q8_path.exists():
        return q8_path, "Qwen3.5-2B-Q8", 4096
    if force_q8 and q8_alternatives:
        return q8_alternatives[0], f"Qwen3.5 (Q8, {q8_alternatives[0].name})", 4096
    if q4_path and q4_path.exists() and not force_q8:
        return q4_path, "Qwen2.5-1.5B-Q4_K_M", 8192
    if q4_alternatives and not force_q8:
        return q4_alternatives[0], f"Qwen2.5 (Q4, {q4_alternatives[0].name})", 8192
    if local_alternatives and not force_q8:
        return local_alternatives[0], f"Modelo local ({local_alternatives[0].name})", 8192
    if q8_path and q8_path.exists():
        return q8_path, "Qwen3.5-2B-Q8", 4096
    if q8_alternatives:
        return q8_alternatives[0], f"Qwen3.5 (Q8, {q8_alternatives[0].name})", 4096
    return None, None, 0

def find_llama_exe():
    """Busca llama-server en Linux o Windows."""
    env_exe = os.environ.get("LLAMA_EXE")
    if env_exe and Path(env_exe).exists():
        return Path(env_exe)

    env_dir = os.environ.get("LLAMA_DIR")
    candidates = []
    if env_dir:
        candidates.append(Path(env_dir) / ("llama-server.exe" if IS_WINDOWS else "llama-server"))
    
    # Common paths
    llama_bin = PROJECT_ROOT / "llama-server-bin"
    if IS_WINDOWS:
        candidates.extend([
            llama_bin / "llama-server.exe",
            PROJECT_ROOT / "llama.cpp" / "llama-server.exe",
            DOCUMENTS_LLAMA_DIR / "llama-server.exe",
        ] if DOCUMENTS_LLAMA_DIR else [
            llama_bin / "llama-server.exe",
            PROJECT_ROOT / "llama.cpp" / "llama-server.exe",
        ])
    else:
        candidates.extend([
            llama_bin / "llama-server",
            PROJECT_ROOT / "llama.cpp" / "build" / "bin" / "llama-server",
        ])

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None

def check_slots(host, port, timeout=2):
    """Verifica si llama-server responde. Retorna (True, n_slots) o (False, 0)."""
    try:
        req = urllib.request.Request(f"http://{host}:{port}/slots")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
            n = len(data) if isinstance(data, list) else 0
            return True, n
    except Exception:
        return False, 0

def start_process(args, name="proceso", hidden=True, env=None):
    """Inicia un proceso de forma confiable (Windows y Linux).
    Retorna el objeto Popen o None si falla."""
    kwargs = {}
    if IS_WINDOWS and hidden:
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW  # 0x08000000
    else:
        kwargs['stdout'] = subprocess.DEVNULL if hidden else None
        kwargs['stderr'] = subprocess.DEVNULL if hidden else None

    try:
        proc = subprocess.Popen(args, env=env, **kwargs)
        log(f"  ✅ {name} iniciado (PID {proc.pid})")
        _processes.append(proc)
        return proc
    except Exception as e:
        log(f"  ❌ Error fatal iniciando {name}: {e}")
        return None

def cleanup():
    """Limpia todos los procesos al salir (Linux y Windows)."""
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True
    log("\n  🛑 Limpiando procesos...")
    for proc in reversed(_processes):
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)
                log(f"  ✅ Proceso PID {proc.pid} terminado")
            except Exception as e:
                log(f"  ⚠️  Error terminando PID {proc.pid}: {e}")
    # Forzar kill de cualquier llama-server restante
    if IS_WINDOWS:
        try:
            subprocess.run(["taskkill", "-f", "-im", "llama-server.exe"],
                           capture_output=True, timeout=5)
        except:
            pass
    else:
        try:
            subprocess.run(["pkill", "-x", "llama-server"],
                           capture_output=True, timeout=5)
        except:
            pass
    log("  ✅ Limpieza completa\n")

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

def wait_for_llama(max_wait=90):
    """Espera hasta que llama-server responda. Retorna True si está listo."""
    log("  Esperando a que cargue el modelo en GPU...")
    start = time.time()
    last_msg = time.time()
    dots = 0
    while time.time() - start < max_wait:
        ready, n_slots = check_slots("127.0.0.1", LLAMA_PORT)
        if ready:
            elapsed = time.time() - start
            log(f"  ✅ ¡Listo! {n_slots} slot(s) disponibles en {elapsed:.0f}s")
            return True
        # Animación simple
        now = time.time()
        if now - last_msg >= 5:
            dots = (dots + 1) % 4
            elapsed = int(now - start)
            remaining = max_wait - elapsed
            bar_len = 20
            filled = int((elapsed / max_wait) * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            log(f"     [{bar}] {elapsed}s / {max_wait}s máximo")
            last_msg = now
        time.sleep(1)
    log(f"  ❌ Tiempo agotado ({max_wait}s). Revisa CUDA/GPU.")
    return False

def start_llama_server(model_path, ctx_size):
    """Inicia llama-server si no está corriendo."""
    log("  🔍 Verificando puerto 8081...")
    ready, n = check_slots("127.0.0.1", LLAMA_PORT)
    if ready:
        log(f"  ✅ Ya está corriendo ({n} slots)")
        return True

    llama_exe = find_llama_exe()
    if llama_exe is None:
        log("  ❌ llama-server no encontrado.")
        log(f"     Revisa: {PROJECT_ROOT / 'llama-server-bin'}")
        log("     O configura LLAMA_EXE / LLAMA_DIR.")
        return False
    if not model_path.exists():
        log(f"  ❌ Modelo no encontrado: {model_path}")
        return False

    # Flags optimizados para velocidad (benchmarks TTFT aplicados).
    args = [
        str(llama_exe),
        "-m", str(model_path),
        "--host", "0.0.0.0",
        "--port", str(LLAMA_PORT),
        "-ngl", "99",
        "-c", str(ctx_size),
        "--chat-template", "chatml",
        "--no-warmup",
        "--reasoning-format", "none",
        "--no-ui",
    ]
    log(f"  🚀 Iniciando llama-server...")
    log(f"     Modelo: {model_path.name}")
    log(f"     Contexto: {ctx_size} tokens")
    log(f"     GPU: -ngl 99 (todas las capas)")
    log(f"     Thinking: desactivado (chatml template)")

    # Set LD_LIBRARY_PATH for llama-server to find libllama.so on Linux
    env = os.environ.copy()
    if not IS_WINDOWS:
        llama_bin_dir = str(PROJECT_ROOT / "llama-server-bin")
        env["LD_LIBRARY_PATH"] = f"{llama_bin_dir}:" + env.get("LD_LIBRARY_PATH", "")

    proc = start_process(args, "llama-server", hidden=IS_WINDOWS, env=env)
    if proc is None:
        return False

    return wait_for_llama()

def start_plan_server(plan_name, port, server_script):
    """Inicia el servidor Python del plan."""
    if not PYTHON_EXE.exists():
        log(f"  ❌ Python no encontrado en {PYTHON_EXE}")
        return False
    server_path = PROJECT_ROOT / server_script
    if not server_path.exists():
        log(f"  ❌ Servidor no encontrado: {server_path}")
        return False

    log(f"  🚀 Iniciando {plan_name} (puerto {port})...")
    env = os.environ.copy()
    # Pasar puerto como variable de entorno (lo usan los servers)
    if server_script.replace("\\", "/").endswith("server.py"):
        env["PLAN_B_PORT"] = str(port)

    proc = start_process(
        [str(PYTHON_EXE), str(server_path)],
        f"{plan_name} (:{port})",
        hidden=True,
        env=env,
    )
    return proc is not None

def open_browser(port):
    """Abre el navegador por defecto en la URL del plan."""
    url = f"http://localhost:{port}"
    log(f"  🌐 Abriendo navegador en {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        log(f"  ⚠️  No se pudo abrir navegador: {e}")
        log(f"     Abre manualmente: {url}")

def print_banner(plan_name, port, model_label, ctx_size, plan_info=""):
    """Muestra el banner de inicio."""
    width = 55
    eprint()
    eprint("=" * width)
    eprint(f"  >> Alex Voice — {plan_name}")
    eprint(f"  {plan_info}" if plan_info else "")
    eprint(f"  Web UI:      http://localhost:{port}")

    eprint(f"  llama-server: {LLAMA_HOST}")
    eprint(f"  Modelo:      {model_label} ({ctx_size} ctx)")
    eprint(f"  GPU VRAM:    ~{1.2 if 'Q4' in model_label else 3.0} GB de 5.28 GB")
    eprint(f"  TTS:         Kokoro-82M + Piper (CPU)")
    eprint(f"  ASR:         faster-whisper (CPU)")
    eprint("=" * width)
    eprint()
    log(f"  🟢 {plan_name} ACTIVO — Presiona Ctrl+C para cerrar todo")
    eprint()

# ── Configuraciones de Planes ──────────────────────────────
PLANS = {
    "B": {
        "name": "Alex Voice",
        "port": 3000,
        "server": "server.py",
        "info": "Kokoro-82M + Piper TTS | Traductor multi-output | Streaming",
    },
}

# ── Main ─────────────────────────────────────────────────────
def main():
    # Parsear args modo CLI
    plan_name = "B"  # default
    port = 3000
    server_script = "server.py"
    plan_info = "Kokoro-82M + Piper + Traductor multi-output + Streaming"

    open_browser_flag = True
    force_q8 = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--plan" and i + 1 < len(args):
            plan_name = args[i + 1].upper()
            i += 2
        elif args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        elif args[i] == "--server" and i + 1 < len(args):
            server_script = args[i + 1]
            i += 2
        elif args[i] == "--no-browser":
            open_browser_flag = False
            i += 1
        elif args[i] == "--q8":
            force_q8 = True
            i += 1
        else:
            i += 1

    # Config desde diccionario
    if plan_name in PLANS:
        cfg = PLANS[plan_name]
        plan_name = cfg["name"]
        port = cfg["port"]
        server_script = cfg["server"]
        plan_info = cfg["info"]

    # Registrar signal handlers para cleanup
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    eprint()
    eprint("=" * 55)
    eprint("  🤖  Alex Voice — Universal Launcher")
    eprint("=" * 55)

    # 1. Seleccionar modelo
    model_path, model_label, ctx_size = find_model(force_q8=force_q8)
    if model_path is None:
        log("  ❌ No se encontró ningún modelo GGUF.")
        log("     Descarga uno desde:")
        log("     • Qwen2.5-1.5B Q4_K_M (recomendado, ~1.1GB):")
        log("       https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF")
        eprint()
        input("  Presiona Enter para salir...")
        sys.exit(1)

    log(f"  📦 Modelo: {model_label}")
    log(f"  📐 Contexto: {ctx_size} tokens")
    log(f"  🎯 Plan: {plan_name} (puerto {port})")

    # 2. Iniciar llama-server
    eprint()
    if not start_llama_server(model_path, ctx_size):
        log("  ❌ No se pudo iniciar llama-server.")
        log("     Verifica CUDA, GPU, y drivers.")
        log("     Para iniciar manualmente:")
        llama_exe = find_llama_exe() or Path("llama-server.exe")
        log(f'     "{llama_exe}" -m "{model_path}" -ngl 99 --port {LLAMA_PORT}')
        eprint()
        input("  Presiona Enter para salir...")
        cleanup()
        sys.exit(1)

    # 3. Iniciar servidor del plan
    eprint()
    if not start_plan_server(plan_name, port, server_script):
        log(f"  ❌ No se pudo iniciar {plan_name}.")
        eprint()
        input("  Presiona Enter para salir...")
        cleanup()
        sys.exit(1)

    # Pequeña pausa para que el servidor se estabilice
    time.sleep(2)

    # 4. Abrir navegador
    if open_browser_flag:
        eprint()
        open_browser(port)
        time.sleep(0.5)
    # 5. Mostrar banner final
    print_banner(plan_name, port, model_label, ctx_size, plan_info)

    # 6. Mantener vivo hasta Ctrl+C
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()
