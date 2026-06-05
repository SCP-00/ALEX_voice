@echo off
title Alex Voice — Setup
chcp 65001 >nul
setlocal enabledelayedexpansion

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

set "PY=python"
set "LLAMA_URL=https://github.com/ggml-org/llama.cpp/releases/download/b9479/llama-b9479-bin-win-cuda-13.3-x64.zip"
set "MODEL_URL=https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"

:: ── Cabecera ──
cls
echo =============================================
echo    ⚡ Alex Voice — Instalador automatico
echo =============================================
echo.
echo   Este instalador descargara e instalara todo
echo   lo necesario para ejecutar Alex Voice localmente.
echo.
echo   Requisitos:
echo     - Windows 10/11 de 64 bits
echo     - NVIDIA GPU con 6GB+ VRAM (RTX 3050+)
echo     - Python 3.10+ (con "Add to PATH" marcado)
echo     - 10 GB de espacio libre en disco
echo.
echo   Se instalara:
echo     - PyTorch CUDA 12.4
echo     - llama-server (backend LLM)
echo     - Modelo Qwen2.5-1.5B Q4_K_M (~1.1GB)
echo     - Kokoro-82M TTS + Piper TTS
echo     - faster-whisper (ASR)
echo     - Qwen3-TTS + argos-translate (Traductor)
echo.
pause
cls

:: ── 1. Verificar Python ──
echo =============================================
echo   [1/6] Verificando Python...
echo =============================================
%PY% --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python no encontrado.
    echo   Instala Python 3.10+ desde python.org
    echo   y MARCA "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('%PY% --version 2^>^&1') do set "PYVER=%%v"
echo   ✅ Python !PYVER!

%PY% -m pip --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: pip no disponible.
    pause
    exit /b 1
)
echo   ✅ pip listo
echo.

:: ── 2. Dependencias Python ──
echo =============================================
echo   [2/6] Instalando dependencias Python...
echo =============================================
echo.
call :pip_module wheel wheel
call :pip_module numpy numpy
call :pip_module kokoro kokoro
call :pip_module piper piper-tts
call :pip_module faster_whisper faster-whisper
call :pip_module qwen_tts qwen-tts
call :pip_module argostranslate argostranslate
call :pip_module psutil psutil
call :pip_module pynvml pynvml
call :pip_optional xformers xformers

:: ── PyTorch CUDA ──
%PY% -c "import torch; exit(0 if torch.cuda.is_available() else 1)" >nul 2>&1
if errorlevel 1 (
    echo   INSTALL: torch + torchaudio CUDA 12.4 (~2.5GB)
    %PY% -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
    if errorlevel 1 (
        echo   ERROR: No se pudo instalar PyTorch CUDA.
        pause
        exit /b 1
    )
    echo   ✅ PyTorch CUDA instalado
) else (
    for /f "usebackq delims=" %%c in ('%PY% -c "import torch; print(torch.version.cuda)" 2^>nul') do set "TCUDA=%%c"
    echo   ✅ PyTorch CUDA !TCUDA! ya instalado
)
echo.

:: ── 3. llama-server ──
echo =============================================
echo   [3/6] Verificando llama-server...
echo =============================================
if exist "%ROOT%\llama-server-bin\llama-server.exe" (
    echo   ✅ llama-server ya descargado
) else (
    echo   Descargando llama.cpp CUDA 13.3 (~200MB)...
    if not exist "%ROOT%\llama-server-bin" mkdir "%ROOT%\llama-server-bin"
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ErrorActionPreference='Stop'; $root='%ROOT:\=\\%'; $url='%LLAMA_URL%'; $zip=Join-Path $root 'llama.zip'; $tmp=Join-Path $root 'llama-tmp'; $dest=Join-Path $root 'llama-server-bin'; Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue; New-Item -ItemType Directory -Force $dest ^| Out-Null; Write-Host '   Descargando... (puede tomar varios minutos)'; Invoke-WebRequest -Uri $url -OutFile $zip; Write-Host '   Extrayendo...'; Expand-Archive -Path $zip -DestinationPath $tmp -Force; $exe=Get-ChildItem $tmp -Recurse -Filter 'llama-server.exe' ^| Select-Object -First 1; if(-not $exe){throw 'llama-server.exe no encontrado dentro del ZIP'}; Copy-Item (Join-Path $exe.Directory.FullName '*') $dest -Recurse -Force; Remove-Item $zip -Force -ErrorAction SilentlyContinue; Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue; Write-Host '   ✅ llama-server descargado y extraido'"
    if errorlevel 1 echo   ⚠️  No se pudo descargar. Descarga manual: https://github.com/ggml-org/llama.cpp/releases
)
echo.

:: ── 4. Modelo LLM ──
echo =============================================
echo   [4/6] Descargando modelo LLM...
echo =============================================
if not exist "%ROOT%\models" mkdir "%ROOT%\models"
if exist "%ROOT%\models\qwen2.5-1.5b-q4_k_m.gguf" (
    echo   ✅ Modelo Qwen2.5-1.5B Q4_K_M ya existe
) else (
    echo   Descargando Qwen2.5-1.5B Q4_K_M (~1.1GB)...
    echo   Esto puede tomar varios minutos segun tu conexion.
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ErrorActionPreference='Stop'; $url='%MODEL_URL%'; $out=Join-Path '%ROOT:\=\\%' 'models\qwen2.5-1.5b-q4_k_m.gguf'; Write-Host '   Descargando...'; Invoke-WebRequest -Uri $url -OutFile $out; Write-Host '   ✅ Modelo descargado'"
    if errorlevel 1 echo   ⚠️  No se pudo descargar. Descarga manual desde HuggingFace.
)
echo.

:: ── 5. Piper TTS models ──
echo =============================================
echo   [5/6] Descargando modelos Piper TTS...
echo =============================================
if not exist "%ROOT%\models" mkdir "%ROOT%\models"
if exist "%ROOT%\models\es_ES-sharvard-medium.onnx" (
    echo   ✅ Piper ES ya existe
) else (
    echo   Descargando Piper ES (77MB)...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Invoke-WebRequest -Uri 'https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx' -OutFile '%ROOT%\models\es_ES-sharvard-medium.onnx'"
    if errorlevel 1 echo   ⚠️  No se pudo descargar Piper ES
)
if exist "%ROOT%\models\en_US-lessac-medium.onnx" (
    echo   ✅ Piper EN ya existe
) else (
    echo   Descargando Piper EN (63MB)...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Invoke-WebRequest -Uri 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx' -OutFile '%ROOT%\models\en_US-lessac-medium.onnx'"
    if errorlevel 1 echo   ⚠️  No se pudo descargar Piper EN
)
echo.

:: ── 6. Paquetes argos ──
echo =============================================
echo   [6/6] Instalando paquetes argos EN/ES/JA...
echo =============================================
%PY% -c "
import argostranslate.package as p
p.update_package_index()
avail = p.get_available_packages()
installed = {(x.from_code, x.to_code) for x in p.get_installed_packages()}
pairs = [('en','es'),('es','en'),('en','ja'),('ja','en')]
for fc, tc in pairs:
    if (fc, tc) not in installed:
        pkg = next((x for x in avail if x.from_code == fc and x.to_code == tc), None)
        if pkg:
            path = pkg.download()
            p.install_from_path(path)
            print(f'  ✅ {fc}->{tc} instalado')
        else:
            print(f'  ⚠️  {fc}->{tc} no disponible')
print('  ✅ argos EN/ES/JA listo')
" 2>&1
if errorlevel 1 echo   ⚠️  argos incompleto — se descargara bajo demanda

echo.
echo =============================================
echo    ✅ Instalacion completada
echo =============================================
echo.
echo   Proximo paso: Ejecuta run.bat
echo   o haz doble clic en menu_server.py
echo.
echo   Acceso directo: http://localhost:5000
echo.
pause
exit /b 0

:: ── Funciones auxiliares ──
:pip_module
%PY% -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('%~1') else 1)" >nul 2>&1
if errorlevel 1 (
    echo   INSTALL: %~2
    %PY% -m pip install %~2
    if errorlevel 1 (
        echo   ERROR: No se pudo instalar %~2
        pause
        exit /b 1
    )
) else (
    echo   ✅ %~2
)
exit /b 0

:pip_optional
%PY% -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('%~1') else 1)" >nul 2>&1
if errorlevel 1 (
    echo   OPTIONAL: %~2
    %PY% -m pip install %~2
    if errorlevel 1 echo   ⚠️  %~2 no disponible (opcional, se usara fallback)
) else (
    echo   ✅ %~2
)
exit /b 0