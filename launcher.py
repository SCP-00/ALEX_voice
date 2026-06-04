#!/usr/bin/env python3
"""
Alex Voice — Universal Launcher
================================
Inicia de forma confiable: llama-server + servidor del plan + navegador.
Unificado para todos los planes (A, B, C, D).

Uso desde .bat:
    python launcher.py --plan A --port 3000 --server server.py --open
    python launcher.py --plan B --port 3001 --server B/server.py --open
    python launcher.py --plan D --port 3003 --server D/server.py --model q4 --open

Uso directo (doble clic):
    python launcher.py  # por defecto Plan D
"""

import json, os, sys, time, signal, subprocess, urllib.request, urllib.error, threading, webbrowser
from pathlib import Path
from datetime import datetime

# ── Config ──────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
LLAMA_DIR = Path(r"C:\Users\andyh\Documents\llama-b9479-bin-win-cuda-13.3-x64")
MODEL_DIR_Q8 = Path(r"C:\Users\andyh\.lmstudio\models\khazarai\Qwen3.5-2B-Qwen3.6-plus-Distilled-GGUF")
MODEL_DIR_Q4 = Path(r"C:\Users\andyh\.lmstudio\models\Qwen\Qwen2.5-1.5B-Instruct-GGUF")
PYTHON_EXE = Path(r"C:\Users\andyh\AppData\Local\Programs\Python\Python310\python.exe")
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

def find_model():
    """Elige el mejor modelo disponible. Prioridad: Q4_K_M > Q8."""
    q4_path = MODEL_DIR_Q4 / "qwen2.5-1.5b-instruct-q4_k_m.gguf"
    q8_path = MODEL_DIR_Q8 / "Qwen3.5-2B-Qwen3.6-plus-Distilled-q8_0.gguf"

    # Buscar recursivamente archivos .gguf en los directorios
    q4_alternatives = list(MODEL_DIR_Q4.glob("*.gguf")) if MODEL_DIR_Q4.exists() else []
    q8_alternatives = list(MODEL_DIR_Q8.glob("*.gguf")) if MODEL_DIR_Q8.exists() else []

    if q4_path.exists():
        return q4_path, "Qwen2.5-1.5B-Q4_K_M", 8192
    if q4_alternatives:
        return q4_alternatives[0], f"Qwen2.5 (Q4, {q4_alternatives[0].name})", 8192
    if q8_path.exists():
        return q8_path, "Qwen3.5-2B-Q8", 4096
    if q8_alternatives:
        return q8_alternatives[0], f"Qwen3.5 (Q8, {q8_alternatives[0].name})", 4096
    return None, None, 0

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

def start_process(args, name="proceso", hidden=True):
    """Inicia un proceso de forma confiable en Windows.
    Retorna el objeto Popen o None si falla."""
    creation_flags = 0
    if hidden:
        creation_flags = subprocess.CREATE_NO_WINDOW  # 0x08000000

    try:
        # Intentar con CREATE_NO_WINDOW
        proc = subprocess.Popen(
            args,
            creationflags=creation_flags,
            stdout=subprocess.DEVNULL if hidden else None,
            stderr=subprocess.DEVNULL if hidden else None,
        )
        log(f"  ✅ {name} iniciado (PID {proc.pid})")
        _processes.append(proc)
        return proc
    except Exception as e:
        log(f"  ⚠️  Error iniciando {name} con ventana oculta: {e}")
        try:
            # Fallback: sin flags, mostrará ventana
            proc = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            log(f"  ✅ {name} iniciado (PID {proc.pid}, visible)")
            _processes.append(proc)
            return proc
        except Exception as e2:
            log(f"  ❌ Error fatal iniciando {name}: {e2}")
            return None

def cleanup():
    """Limpia todos los procesos al salir."""
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
    try:
        subprocess.run(["taskkill", "-f", "-im", "llama-server.exe"],
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

    llama_exe = LLAMA_DIR / "llama-server.exe"
    if not llama_exe.exists():
        log(f"  ❌ llama-server.exe no encontrado en {llama_exe}")
        return False
    if not model_path.exists():
        log(f"  ❌ Modelo no encontrado: {model_path}")
        return False

    # Flags para desactivar thinking y optimizar velocidad:
    # - `--no-warmup` evita el pre-cálculo (reduce tiempo de inicio ~50%)
    # - `--slot-save-file` no usar (es lento)
    # - Sin `--mlock` (no es necesario, puede causar problemas en 6GB)
    args = [
        str(llama_exe),
        "-m", str(model_path),
        "--host", "0.0.0.0",
        "--port", str(LLAMA_PORT),
        "-ngl", "99",
        "-c", str(ctx_size),
        "--chat-template", "chatml",
        "--no-warmup",
    ]
    log(f"  🚀 Iniciando llama-server...")
    log(f"     Modelo: {model_path.name}")
    log(f"     Contexto: {ctx_size} tokens")
    log(f"     GPU: -ngl 99 (todas las capas)")
    log(f"     Thinking: desactivado (chatml template)")

    proc = start_process(args, "llama-server")
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
    port_vars = {
        "A": "MONITOR_PORT",
        "B": "PLAN_B_PORT",
        "C": "PLAN_C_PORT",
        "D": "PLAN_D_PORT",
    }
    if plan_name in port_vars:
        env[port_vars[plan_name]] = str(port)

    proc = start_process(
        [str(PYTHON_EXE), str(server_path)],
        f"{plan_name} (:{port})",
        hidden=True,
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
    if plan_name == "Plan D":
        eprint(f"  Debug:       http://localhost:{port}/debug")
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
    "A": {
        "name": "Plan A",
        "port": 3000,
        "server": "server.py",
        "info": "LLM en GPU | TTS+ASR en CPU",
    },
    "B": {
        "name": "Plan B",
        "port": 3001,
        "server": "B/server.py",
        "info": "Kokoro-82M + Piper TTS | Caché 50",
    },
    "C": {
        "name": "Plan C",
        "port": 3002,
        "server": "C/server.py",
        "info": "Pipeline Completo: ASR | LLM | TTS",
    },
    "D": {
        "name": "Plan D",
        "port": 3003,
        "server": "D/server.py",
        "info": "Definitivo: Kokoro+Piper | Caché 200 | Debug UI",
    },
}

# ── Main ─────────────────────────────────────────────────────
def main():
    # Parsear args modo CLI
    plan_name = "D"  # default
    port = 3003
    server_script = "D/server.py"
    plan_info = "La Configuración Definitiva"
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
    model_path, model_label, ctx_size = find_model()
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
        log(f'     "{LLAMA_DIR / "llama-server.exe"}" -m "{model_path}" -ngl 99 --port {LLAMA_PORT}')
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
