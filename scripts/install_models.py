#!/usr/bin/env python3
"""
Alex Voice — Universal Model Installer
=======================================
Downloads ALL required models automatically with progress bars.
Reusable by setup.sh (Linux), setup_windows.bat (Windows), or standalone.

Model sources:
  - Kokoro ONNX v1.0:  https://github.com/thewh1teagle/kokoro-onnx/releases
  - Piper TTS:         https://huggingface.co/rhasspy/piper-voices
  - MarianMT:          transformers (auto-cached by huggingface_hub)

Usage:
  python3 scripts/install_models.py          # Download all models
  python3 scripts/install_models.py --kokoro  # Only Kokoro
  python3 scripts/install_models.py --piper   # Only Piper
  python3 scripts/install_models.py --trans   # Only translation
"""

import os
import sys
import time
import urllib.request
from pathlib import Path

# Project root (2 levels up from scripts/)
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent

# ── Download targets ───────────────────────────────────────
MODELS_DIR = PROJECT_ROOT / "models"
ONNX_DIR = MODELS_DIR / "onnx"

KOKORO_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

PIPER_MODELS = {
    "es_ES-sharvard-medium.onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx",
    "en_US-lessac-medium.onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
}

TRANSLATION_PAIRS = [
    "Helsinki-NLP/opus-mt-en-es",
    "Helsinki-NLP/opus-mt-es-en",
    "Helsinki-NLP/opus-mt-en-jap",
    "Helsinki-NLP/opus-mt-ja-en",
    "Helsinki-NLP/opus-mt-ja-es",
]


# ── Terminal helpers ───────────────────────────────────────
def green(s): return f"\033[32m{s}\033[0m"
def blue(s): return f"\033[34m{s}\033[0m"
def yellow(s): return f"\033[33m{s}\033[0m"
def red(s): return f"\033[31m{s}\033[0m"
def bold(s): return f"\033[1m{s}\033[0m"


def download_file(url, dest_path, label="", expected_size=None):
    """Download a file with a live progress bar.
    
    Returns True if successful, False otherwise.
    Skips if file already exists and size matches (or is reasonable).
    """
    dest = Path(dest_path)
    
    # Skip if exists and looks valid
    if dest.exists():
        size = dest.stat().st_size
        if expected_size and size >= expected_size * 0.9:
            print(f"  {green('✔')} {label} already exists ({size / 1024 / 1024:.1f} MB)")
            return True
        elif size > 1024:  # At least 1KB = probably valid
            print(f"  {green('✔')} {label} already exists ({size / 1024 / 1024:.1f} MB)")
            return True
    
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"  {blue('↓')} Downloading {label}...")
    
    class ProgressReporter:
        def __init__(self):
            self.last_update = 0
            self.start_time = time.time()
        
        def report(self, block_count, block_size, total_size):
            downloaded = block_count * block_size
            if total_size > 0:
                percent = min(100, downloaded * 100 / total_size)
                elapsed = time.time() - self.start_time
                speed = downloaded / (elapsed * 1024 * 1024) if elapsed > 0 else 0
                # Update every 0.5s max to avoid flickering
                now = time.time()
                if now - self.last_update > 0.5 or percent >= 100:
                    bar_len = 30
                    filled = int(bar_len * percent / 100)
                    bar = '█' * filled + '░' * (bar_len - filled)
                    print(f"\r    [{bar}] {percent:.0f}% ({downloaded/1024/1024:.1f}/{total_size/1024/1024:.1f} MB, {speed:.1f} MB/s)", end='', flush=True)
                    self.last_update = now
    
    reporter = ProgressReporter()
    try:
        urllib.request.urlretrieve(url, str(dest), reporter.report)
        print()
        size = dest.stat().st_size
        print(f"  {green('✔')} {label} — {size / 1024 / 1024:.1f} MB")
        return True
    except Exception as e:
        print(f"\n  {red('✘')} {label} failed: {e}")
        # Clean up partial download
        if dest.exists():
            dest.unlink()
        return False


def download_kokoro():
    """Download Kokoro ONNX model + voices (~338 MB total)."""
    print(f"\n{bold('📢 Kokoro ONNX TTS')}")
    ONNX_DIR.mkdir(parents=True, exist_ok=True)
    
    ok1 = download_file(KOKORO_URL, ONNX_DIR / "kokoro-v1.0.onnx", "Kokoro ONNX model", expected_size=300 * 1024 * 1024)
    ok2 = download_file(VOICES_URL, ONNX_DIR / "voices-v1.0.bin", "Kokoro voices", expected_size=25 * 1024 * 1024)
    
    if ok1 and ok2:
        print(f"  {green('✔')} Kokoro ready: {len(list(ONNX_DIR.glob('*')))} files")
    return ok1 and ok2


def download_piper():
    """Download Piper TTS models ES + EN (~50 MB each)."""
    print(f"\n{bold('📢 Piper TTS')}")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    results = []
    for filename, url in PIPER_MODELS.items():
        ok = download_file(url, MODELS_DIR / filename, filename, expected_size=40 * 1024 * 1024)
        results.append(ok)
    
    all_ok = all(results)
    if all_ok:
        print(f"  {green('✔')} Piper ready: {len(PIPER_MODELS)} models")
    return all_ok


def download_translation():
    """Pre-download MarianMT translation models via transformers."""
    print(f"\n{bold('📢 Translation Models (MarianMT)')}")
    
    try:
        from transformers import MarianMTModel, MarianTokenizer
    except ImportError:
        print(f"  {yellow('⚠')} transformers not installed. Skipping translation models.")
        print(f"     Install with: pip install transformers sentencepiece")
        return False
    
    success = 0
    for model_name in TRANSLATION_PAIRS:
        try:
            t0 = time.time()
            print(f"  {blue('↓')} Loading {model_name}...", end='', flush=True)
            tokenizer = MarianTokenizer.from_pretrained(model_name)
            model = MarianMTModel.from_pretrained(model_name)
            elapsed = time.time() - t0
            print(f"\r  {green('✔')} {model_name} ({elapsed:.1f}s)")
            success += 1
        except Exception as e:
            print(f"\r  {red('✘')} {model_name}: {e}")
    
    print(f"  {green('✔')} Translation models: {success}/{len(TRANSLATION_PAIRS)} loaded")
    return success == len(TRANSLATION_PAIRS)


def verify():
    """Verify all model files exist."""
    print(f"\n{bold('🔍 Verification')}")
    errors = []
    
    # Kokoro
    kokoro_ok = (ONNX_DIR / "kokoro-v1.0.onnx").exists() and (ONNX_DIR / "voices-v1.0.bin").exists()
    if kokoro_ok:
        print(f"  {green('✔')} Kokoro ONNX")
    else:
        print(f"  {red('✘')} Kokoro ONNX — missing files in {ONNX_DIR}")
        errors.append("Kokoro")
    
    # Piper
    piper_ok = all((MODELS_DIR / f).exists() for f in PIPER_MODELS)
    if piper_ok:
        print(f"  {green('✔')} Piper TTS ({len(PIPER_MODELS)} models)")
    else:
        print(f"  {red('✘')} Piper TTS — missing models")
        errors.append("Piper")
    
    # Translation (check cache via transformers)
    try:
        from transformers import MarianMTModel
        trans_ok = True
        for model_name in TRANSLATION_PAIRS:
            try:
                MarianMTModel.from_pretrained(model_name, local_files_only=True)
            except Exception:
                trans_ok = False
                break
        if trans_ok:
            print(f"  {green('✔')} Translation ({len(TRANSLATION_PAIRS)} models cached)")
        else:
            print(f"  {yellow('⚠')} Translation — some models not cached (will download on first use)")
    except ImportError:
        print(f"  {yellow('⚠')} Translation — transformers not installed")
    
    if errors:
        print(f"\n  {yellow('⚠')} {len(errors)} component(s) with issues: {', '.join(errors)}")
        return False
    
    print(f"\n  {green('✔')} All models verified!")
    return True


def main():
    print(f"{bold('══════════════════════════════════════')}")
    print(f"{bold('  Alex Voice — Model Installer')}")
    print(f"{bold('══════════════════════════════════════')}")
    print(f"  Project: {PROJECT_ROOT}")
    print(f"  Models:  {MODELS_DIR}")
    print()
    
    # Parse CLI args
    args = set(sys.argv[1:])
    do_all = not any(a in args for a in ['--kokoro', '--piper', '--trans'])
    
    t0 = time.time()
    
    if do_all or '--kokoro' in args:
        download_kokoro()
    if do_all or '--piper' in args:
        download_piper()
    if do_all or '--trans' in args:
        download_translation()
    
    elapsed = time.time() - t0
    print(f"\n  {bold(f'⏱️  Total: {elapsed:.0f}s')}")
    
    verify()
    
    print(f"\n  {green(bold('✅ Ready! Run ./alex_voice_app.sh to start.'))}")


if __name__ == "__main__":
    main()
