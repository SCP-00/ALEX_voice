@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ── Auto-detect project root (donde se ejecuta setup.bat) ──
set "PROJECT_ROOT=%~dp0"
:: Remove trailing backslash
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
cd /d "%PROJECT_ROOT%"

title Alex Voice — Setup

echo =============================================
echo   Alex Voice — Setup Automatico
echo   Asistente Local con IA Multilingue
echo   Proyecto: %PROJECT_ROOT%
echo =============================================
echo.

:: ── Check NVIDIA GPU ──
set STEP=1
echo [%STEP%/7] Verificando GPU NVIDIA...
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
echo   ✅ GPU detectada: %gpuname%

:: ── Check Python ──
echo.
set /a STEP+=1
echo [%STEP%/7] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   ❌ Python no encontrado. Descarga Python 3.10:
    echo   https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe
    echo   MARCA "Add Python to PATH" durante la instalacion.
    start https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set pyver=%%v
echo   ✅ Python %pyver%

:: ── pip dependencies ──
echo.
set /a STEP+=1
echo [%STEP%/7] Instalando dependencias base (wheel, ninja)...
pip install wheel ninja 2>&1 | findstr /i "successfully" >nul
echo   ✅ Wheel + Ninja

:: ── CUDA torch ──
echo.
set /a STEP+=1
echo [%STEP%/7] Instalando PyTorch CUDA...
echo   (puede tomar 2-5 minutos, ~3GB de descarga)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124 2>&1 | findstr /i "successfully" >nul
if %errorlevel% neq 0 (
    echo   ⚠️  Error instalando torch CUDA. Intentando CPU version...
    pip install torch torchaudio
)
python -c "import torch; print('  ✅ CUDA', torch.version.cuda if torch.cuda.is_available() else 'NO CUDA')" 2>&1

:: ── Python dependencies ──
echo.
set /a STEP+=1
echo [%STEP%/7] Instalando dependencias Python...

echo   Instalando argostranslate...
pip install argostranslate -q 2>&1 | findstr /i "successfully" >nul
echo   ✅ argostranslate

echo   Instalando qwen-tts...
pip install qwen-tts -q 2>&1 | findstr /i "successfully" >nul
echo   ✅ qwen-tts

echo   Instalando faster-whisper...
pip install faster-whisper -q 2>&1 | findstr /i "successfully" >nul
echo   ✅ faster-whisper

echo   Instalando kokoro + utilidades...
pip install kokoro psutil pynvml -q 2>&1 | findstr /i "successfully" >nul
echo   ✅ kokoro, psutil, pynvml

echo   Instalando flash-attn (opcional, acelera Qwen3-TTS)...
pip install flash-attn --no-build-isolation -q 2>&1 | findstr /i "successfully" >nul
if %errorlevel% equ 0 (
    echo   ✅ flash-attn (Qwen3-TTS acelerado ~2x)
) else (
    echo   ⚠️  flash-attn no disponible (sin CUDA toolkit)
    echo   Para instalarlo manualmente, ejecuta este PowerShell como Admin:
    echo   ^> $env:CUDA_PATH="C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4"
    echo   ^> pip install flash-attn --no-build-isolation
)

:: Install argos language packages
echo.
echo   Instalando paquetes de idioma argos (EN/ES/JA)...
python -c "
import argostranslate.package
argostranslate.package.update_package_index()
available = argostranslate.package.get_available_packages()
for fc, tc in [('en','es'),('es','en'),('en','ja'),('ja','en'),('ja','es'),('es','ja')]:
    pkg = next((p for p in available if p.from_code==fc and p.to_code==tc), None)
    if pkg:
        path = pkg.download()
        argostranslate.package.install_from_path(path)
        print(f'  OK: {fc}->{tc}')
" 2>&1
echo   ✅ Paquetes de idioma

:: ── llama-server ──
echo.
set /a STEP+=1
echo [%STEP%/7] Descargando llama-server...

if not exist "%PROJECT_ROOT%\llama-server-bin" mkdir "%PROJECT_ROOT%\llama-server-bin" 2>nul

if exist "%PROJECT_ROOT%\llama-server-bin\llama-server.exe" (
    echo   ✅ Ya existe
) else (
    echo   Descargando ~100MB...
    curl -L -o "%PROJECT_ROOT%\llama-server.zip" "https://github.com/ggml-org/llama.cpp/releases/download/b9479/llama-b9479-bin-win-cuda-13.3-x64.zip"
    if exist "%PROJECT_ROOT%\llama-server.zip" (
        :: Intentar con tar (Windows 10 17063+)
        tar -xf "%PROJECT_ROOT%\llama-server.zip" -C "%PROJECT_ROOT%\llama-server-bin" --strip-components=1 2>nul
        if not exist "%PROJECT_ROOT%\llama-server-bin\llama-server.exe" (
            echo   Fallback: extrayendo con PowerShell...
            powershell -Command "
                Expand-Archive -Path '%PROJECT_ROOT%\llama-server.zip' -DestinationPath '%PROJECT_ROOT%\llama-server-tmp' -Force;
                $items = Get-ChildItem '%PROJECT_ROOT%\llama-server-tmp';
                if($items.Count -eq 1 -and (Get-Item $items[0]).PSIsContainer) {
                    Move-Item '$($items[0].FullName)\*' '%PROJECT_ROOT%\llama-server-bin\' -Force;
                } else {
                    Move-Item '$($items[0].FullName)\*' '%PROJECT_ROOT%\llama-server-bin\' -Force;
                }
                Remove-Item -Recurse -Force '%PROJECT_ROOT%\llama-server-tmp' -ErrorAction SilentlyContinue;
            " >nul 2>&1
        )
        del "%PROJECT_ROOT%\llama-server.zip" 2>nul
        if exist "%PROJECT_ROOT%\llama-server-bin\llama-server.exe" (
            echo   ✅ llama-server descargado
        ) else (
            echo   ❌ No se pudo extraer llama-server
            echo   Descarga manual: https://github.com/ggml-org/llama.cpp/releases
            echo   Mueve llama-server.exe a: %PROJECT_ROOT%\llama-server-bin\
        )
    ) else (
        echo   ❌ No se pudo descargar llama-server
        echo   Descarga manual: https://github.com/ggml-org/llama.cpp/releases
        echo   Mueve llama-server.exe a: %PROJECT_ROOT%\llama-server-bin\
    )
)

:: ── Download ALL AI models (al final, todo automatico) ──
echo.
set /a STEP+=1
echo [%STEP%/7] Descargando modelos de IA...
echo.

if not exist "%PROJECT_ROOT%\models" mkdir "%PROJECT_ROOT%\models" 2>nul

:: 7a. LLM Model (~1.1GB)
echo   [7a/3] Modelo LLM: Qwen2.5-1.5B-Q4_K_M (~1.1GB)
if exist "%PROJECT_ROOT%\models\qwen2.5-1.5b-q4_k_m.gguf" (
    echo   ✅ Ya descargado
) else (
    echo   Descargando desde HuggingFace...
    python -c "
import os, urllib.request, sys
url = 'https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf'
out = os.path.join(r'%PROJECT_ROOT%\models', 'qwen2.5-1.5b-q4_k_m.gguf')
print('  Descargando (~1.1GB, esto toma varios minutos)...')
sys.stdout.flush()
try:
    urllib.request.urlretrieve(url, out)
    print('  ✅ LLM descargado')
except Exception as e:
    print(f'  ❌ Error: {e}')
    print('  Descarga manual: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF')
" 2>&1
)

:: 7b. Qwen3-TTS model (~2GB, se descarga al primer uso)
echo.
echo   [7b/3] Qwen3-TTS-CustomVoice (~2GB)
echo   Se descargara automaticamente al primer uso del traductor

:: 7c. faster-whisper model (~150MB, se descarga al primer uso)
echo.
echo   [7c/3] faster-whisper base (~150MB)
echo   Se descargara automaticamente al primer uso del traductor

echo.
echo =============================================
echo   ✅ Setup completado!
echo.
echo   Proyecto: %PROJECT_ROOT%
echo   Para iniciar, ejecuta:  run.bat
echo =============================================
echo.
pause
