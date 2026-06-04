@echo off
title Alex Voice — Setup
chcp 65001 >nul
setlocal enabledelayedexpansion

echo =============================================
echo   Alex Voice — Setup Automatico
echo   Asistente Local con IA Multilingue
echo =============================================
echo.

:: ── Check NVIDIA GPU ──
echo [1/7] Verificando GPU NVIDIA...
nvidia-smi >nul 2>&1
if %errorlevel% neq 0 (
    echo   ❌ No se detecto GPU NVIDIA.
    echo   Este proyecto requiere CUDA y una GPU NVIDIA compatible.
    echo   Si tienes una GPU NVIDIA, instala los drivers desde:
    echo   https://www.nvidia.com/Download/index.aspx
    pause
    exit /b 1
)
for /f "tokens=2 delims=: " %%g in ('nvidia-smi --query-gpu=name --format=csv,noheader 2^>^&1') do set gpuname=%%g
echo   GPU detectada: %gpuname%

:: ── Check Python ──
echo.
echo [2/7] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   Python no encontrado. Descargando Python 3.10...
    echo   Abriendo pagina de descarga...
    start https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe
    echo.
    echo   ⚠️  Instala Python 3.10 MANUALMENTE.
    echo   MARCA "Add Python to PATH" durante la instalacion.
    echo   Despues de instalar, ejecuta este script NUEVAMENTE.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set pyver=%%v
echo   Python %pyver% — OK

:: ── Git (for cloning models) ──
echo.
echo [3/7] Verificando Git...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   Git no encontrado (opcional, se usara pip para todo)
) else (
    for /f %%v in ('git --version') do echo   %%v — OK
)

:: ── CUDA torch ──
echo.
echo [4/7] Instalando PyTorch CUDA...
echo   (puede tomar 2-5 minutos, ~3GB de descarga)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124 2>&1 | findstr /i "successfully" >nul
if %errorlevel% neq 0 (
    echo   ⚠️  Error instalando torch CUDA. Intentando CPU version...
    pip install torch torchaudio
)
python -c "import torch; print('  OK: CUDA', torch.version.cuda if torch.cuda.is_available() else 'NO CUDA')" 2>&1

:: ── Python dependencies ──
echo.
echo [5/7] Instalando dependencias Python...
pip install argostranslate 2>&1 | findstr /i "successfully"
pip install qwen-tts 2>&1 | findstr /i "successfully"
pip install faster-whisper 2>&1 | findstr /i "successfully"
pip install kokoro psutil pynvml 2>&1 | findstr /i "successfully"

:: Install argos language packages
echo.
echo   Instalando paquetes de idioma argos...
python -c "
import argostranslate.package
argostranslate.package.update_package_index()
available = argostranslate.package.get_available_packages()
for fc, tc in [('en','es'),('es','en'),('en','ja'),('ja','en')]:
    pkg = next((p for p in available if p.from_code==fc and p.to_code==tc), None)
    if pkg:
        path = pkg.download()
        argostranslate.package.install_from_path(path)
        print(f'  OK: {fc}->{tc}')
"

echo.
echo [6/7] Descargando llama-server...
if not exist "llama-server-bin\" (
    mkdir llama-server-bin
    echo   Descargando llama-b9479 (CUDA 13.3)...
    curl -L -o llama-server.zip "https://github.com/ggml-org/llama.cpp/releases/download/b9479/llama-b9479-bin-win-cuda-13.3-x64.zip"
    tar -xf llama-server.zip -C llama-server-bin --strip-components=1 2>nul
    :: Fallback si tar no existe (Windows 10 version < 17063)
    if not exist "llama-server-bin\llama-server.exe" (
        echo   Usando PowerShell para extraer...
        powershell -Command "Expand-Archive -Path llama-server.zip -DestinationPath llama-server-bin-tmp; if(test-path 'llama-server-bin-tmp\*\llama-server.exe'){move 'llama-server-bin-tmp\*\*' 'llama-server-bin\' -Force} else {move 'llama-server-bin-tmp\*' 'llama-server-bin\' -Force}; remove-item -Recurse -Force llama-server-bin-tmp -ErrorAction SilentlyContinue" >nul 2>&1
    )
    del llama-server.zip 2>nul
    echo   OK: llama-server descargado
) else (
    echo   OK: ya existe
)

:: ── Download GGUF model ──
echo.
echo [7/7] Descargando modelo LLM...
echo   Recomendado: Qwen2.5-1.5B-Q4_K_M (~1.1GB)
echo.

if not exist "models\qwen2.5-1.5b-q4_k_m.gguf" (
    mkdir models 2>nul
    echo   Descargando modelo (esto puede tomar varios minutos)...
    echo   URL: huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF
    echo.
    echo   ⚠️  Descarga MANUAL recomendada (el archivo es grande):
    echo   1. Abre: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF
    echo   2. Descarga: qwen2.5-1.5b-instruct-q4_k_m.gguf
    echo   3. Muevelo a: models\qwen2.5-1.5b-q4_k_m.gguf
    echo.
    echo   O ejecuta el comando (puede fallar si no tienes huggingface-cli):
    pip install huggingface-hub
    huggingface-cli download Qwen/Qwen2.5-1.5B-Instruct-GGUF qwen2.5-1.5b-instruct-q4_k_m.gguf --local-dir models
) else (
    echo   OK: modelo ya existe
)

echo.
echo =============================================
echo   ✅ Setup completado!
echo.
echo   Para iniciar, ejecuta:  run.bat
echo =============================================
echo.
pause
