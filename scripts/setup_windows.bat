@echo off
chcp 65001 >nul
title Alex Voice — Windows Setup (v3.3)
setlocal enabledelayedexpansion

:: ═══════════════════════════════════════════════════════════
::  Alex Voice — Windows Installer (v3.3)
::  Model: prometheus-orchestrator (Qwen3.5 4B Instruct)
::  Context: 64K optimizado
::  Requiere: Windows 10/11, GPU NVIDIA 6GB+ VRAM
:: ═══════════════════════════════════════════════════════════

set ROOT=%~dp0..
cd /d "%ROOT%"

echo.
echo ╔═══════════════════════════════════════════╗
echo ║   🎙️  Alex Voice — Windows Setup           ║
echo ║   v3.3 · 64K optimizado · Ollama API     ║
echo ╚═══════════════════════════════════════════╝
echo.

:: ── 1. Check Python ─────────────────────────────────────
echo [1/5] Checking Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   ! Python not found. Downloading Python 3.10...
    echo   Opening https://www.python.org/downloads/
    start https://www.python.org/downloads/
    echo   Please install Python 3.10+, checking "Add Python to PATH"
    pause
    python --version >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo   ✘ Python still not found. Install manually and re-run.
        pause
        exit /b 1
    )
)
for /f "tokens=2" %%a in ('python --version 2^>^&1') do echo   ✔ Python %%a

:: ── 2. Create venv + install deps ──────────────────────
echo [2/5] Setting up virtual environment...
if not exist "venv\" (
    python -m venv venv
    echo   ✔ Virtual environment created
) else (
    echo   ✔ Virtual environment already exists
)
call venv\Scripts\activate.bat

echo   Installing Python packages (this may take 5-10 minutes)...
pip install --upgrade pip -q

:: Check CUDA
python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   ✔ PyTorch CUDA already installed
) else (
    echo   Installing PyTorch CUDA 12.4...
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
)
pip install faster-whisper onnxruntime silero-vad kokoro-onnx piper-tts cutlet unidic-lite
pip install transformers sentencepiece psutil pynvml numpy
echo   ✔ Python packages installed

:: ── 3. Install Ollama ────────────────────────────────────
echo [3/5] Installing Ollama...
where ollama >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   ✔ Ollama already installed
) else (
    echo   Downloading Ollama for Windows...
    curl -fsSL -o "%TEMP%\OllamaSetup.exe" https://ollama.com/download/OllamaSetup.exe
    if exist "%TEMP%\OllamaSetup.exe" (
        echo   Running Ollama installer...
        "%TEMP%\OllamaSetup.exe" /S
        echo   ✔ Ollama installed
    ) else (
        echo   ! Download failed. Please install manually:
        echo     https://ollama.com/download/windows
    )
)

:: ── 4. Pull LLM model ───────────────────────────────────
echo [4/5] Downloading LLM model (prometheus-orchestrator)...
ollama list | findstr prometheus-orchestrator >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   ✔ prometheus-orchestrator already downloaded
) else (
    echo   Downloading prometheus-orchestrator (Qwen3.5 4B, ~2.9 GB)...
    echo   This may take 10-20 minutes...
    ollama pull prometheus-orchestrator
    echo   ✔ Model downloaded
)

:: ── 5. Download model files ─────────────────────────────
echo [5/5] Downloading model files (Kokoro, Piper, Translation)...
python scripts/install_models.py

:: ── Create Desktop shortcut ─────────────────────────────
echo.
echo Creating desktop shortcut...
set DESKTOP=%USERPROFILE%\Desktop
set SHORTCUT=%DESKTOP%\Alex Voice.lnk
if exist "%SHORTCUT%" (
    echo   ✔ Shortcut already exists
) else (
    powershell -Command "$WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut('%SHORTCUT%'); $SC.TargetPath = '%ROOT%\alex_voice_app.sh'; $SC.WorkingDirectory = '%ROOT%'; $SC.Description = 'Alex Voice — AI Language Learning'; $SC.Save()" >nul 2>&1
    if exist "%SHORTCUT%" (
        echo   ✔ Desktop shortcut created
    ) else (
        echo   ! Could not create shortcut (WSL script)
    )
)

:: ── Done ─────────────────────────────────────────────────
echo.
echo ╔═══════════════════════════════════════════╗
echo ║   ✅ Setup Complete (v3.3)                 ║
echo ╚═══════════════════════════════════════════╝
echo.
echo   Architecture:
echo     • LLM:  Ollama API → prometheus-orchestrator (Qwen3.5 4B, 64K ctx)
echo     • TTS:  Kokoro ONNX (CPU, 54 voices, 5 langs)
echo     • ASR:  faster-whisper small (GPU)
echo     • VAD:  Silero VAD (CPU)
echo.
echo   VRAM Budget:
echo     • Teacher/Conversation: Ollama + Whisper = ~4.0 GB
echo     • Translator:          Whisper + MarianMT = ~1.7 GB
echo.
echo   Next step:
echo     Run: alex_voice_app.sh
echo     Or:  python menu_server.py
echo.
echo   NOTE: alex_voice_app.sh requires WSL or Git Bash.
echo         For direct Windows use: python menu_server.py
echo.
pause
