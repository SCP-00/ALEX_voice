@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
cd /d "%PROJECT_ROOT%"

set "PY=python"
set "LLAMA_URL=https://github.com/ggml-org/llama.cpp/releases/download/b9479/llama-b9479-bin-win-cuda-13.3-x64.zip"
set "MODEL_URL=https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"

title Alex Voice - Setup

echo =============================================
echo   Alex Voice - Setup idempotente
echo   Proyecto: %PROJECT_ROOT%
echo =============================================
echo.

echo [1/6] Verificando Python...
%PY% --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python no esta en PATH.
    echo   Instala Python 3.10+ y marca "Add Python to PATH".
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('%PY% --version 2^>^&1') do set "PYVER=%%v"
echo   OK: Python %PYVER%
%PY% -m pip --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: pip no esta disponible para este Python.
    pause
    exit /b 1
)

echo.
echo [2/6] Verificando GPU NVIDIA...
where nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo   AVISO: nvidia-smi no esta en PATH. El setup continua y PyTorch verificara CUDA.
) else (
    for /f "usebackq delims=" %%g in (`nvidia-smi --query-gpu^=name --format^=csv^,noheader 2^>nul`) do (
        if not defined GPUNAME set "GPUNAME=%%g"
    )
    if defined GPUNAME (
        echo   OK: GPU detectada: !GPUNAME!
    ) else (
        echo   AVISO: nvidia-smi existe, pero no devolvio una GPU.
    )
)

echo.
echo [3/6] Instalando dependencias Python solo si faltan...
call :ensure_module wheel wheel
call :ensure_module ninja ninja
call :ensure_torch_cuda
call :ensure_module argostranslate argostranslate
call :ensure_module qwen_tts qwen-tts
call :ensure_module faster_whisper faster-whisper
call :ensure_module kokoro kokoro
call :ensure_module piper piper-tts
call :ensure_module psutil psutil
call :ensure_module pynvml pynvml
call :ensure_module numpy numpy
call :ensure_optional_module xformers xformers

call :ensure_cuda_env

if /i "%ALEX_INSTALL_FLASH_ATTN%"=="1" (
    call :ensure_optional_module flash_attn flash-attn --no-build-isolation
) else (
    echo   SKIP: flash-attn es opcional. Para intentar instalarlo:
    echo        set ALEX_INSTALL_FLASH_ATTN=1
    echo        Y asegurar CUDA_PATH+ CUDA_HOME configurados (setup los configura)
)

echo.
echo [4/6] Instalando paquetes argos core si faltan...
%PY% -c "import argostranslate.package as p; p.update_package_index(); avail=p.get_available_packages(); installed={(x.from_code,x.to_code) for x in p.get_installed_packages()}; pairs=[('en','es'),('es','en'),('en','ja'),('ja','en')]; [p.install_from_path(pkg.download()) for fc,tc in pairs if (fc,tc) not in installed for pkg in avail if pkg.from_code==fc and pkg.to_code==tc]; print('  OK: argos EN/ES/JA listo')"
if errorlevel 1 (
    echo   AVISO: no se pudieron instalar todos los paquetes argos. Se intentaran bajo demanda.
)

echo.
echo [5/6] Verificando llama-server local...
if exist "%PROJECT_ROOT%\llama-server-bin\llama-server.exe" (
    echo   OK: llama-server-bin\llama-server.exe ya existe
) else (
    echo   Descargando llama.cpp b9479 CUDA 13.3...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $root=$env:PROJECT_ROOT; $zip=Join-Path $root 'llama-server.zip'; $tmp=Join-Path $root 'llama-server-tmp'; $dest=Join-Path $root 'llama-server-bin'; Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue; New-Item -ItemType Directory -Force $dest | Out-Null; Invoke-WebRequest -Uri $env:LLAMA_URL -OutFile $zip; Expand-Archive -Path $zip -DestinationPath $tmp -Force; $exe=Get-ChildItem $tmp -Recurse -Filter 'llama-server.exe' | Select-Object -First 1; if(-not $exe){ throw 'llama-server.exe no encontrado dentro del ZIP' }; Copy-Item (Join-Path $exe.Directory.FullName '*') $dest -Recurse -Force; Remove-Item $zip -Force -ErrorAction SilentlyContinue; Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue"
    if errorlevel 1 (
        echo   ERROR: no se pudo descargar o extraer llama-server.
        echo   Descarga manual: https://github.com/ggml-org/llama.cpp/releases
    ) else (
        echo   OK: llama-server descargado
    )
)

echo.
echo [6/6] Verificando modelo LLM local...
if not exist "%PROJECT_ROOT%\models" mkdir "%PROJECT_ROOT%\models" >nul 2>&1
if exist "%PROJECT_ROOT%\models\qwen2.5-1.5b-q4_k_m.gguf" (
    echo   OK: modelo Qwen2.5 local ya existe
) else (
    echo   Descargando Qwen2.5-1.5B Q4_K_M (~1.1GB)...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Invoke-WebRequest -Uri $env:MODEL_URL -OutFile (Join-Path $env:PROJECT_ROOT 'models\qwen2.5-1.5b-q4_k_m.gguf')"
    if errorlevel 1 (
        echo   ERROR: no se pudo descargar el modelo.
        echo   Descarga manual: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF
    ) else (
        echo   OK: modelo descargado
    )
)

echo.
echo =============================================
echo   Setup completado.
echo   Siguiente paso: run.bat
echo =============================================
echo.
pause
exit /b 0

:ensure_module
set "IMPORT_NAME=%~1"
set "PIP_SPEC=%~2"
%PY% -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('%IMPORT_NAME%') else 1)" >nul 2>&1
if errorlevel 1 (
    echo   INSTALL: %PIP_SPEC%
    %PY% -m pip install %PIP_SPEC%
    if errorlevel 1 exit /b 1
) else (
    echo   OK: %PIP_SPEC%
)
exit /b 0

:ensure_optional_module
set "IMPORT_NAME=%~1"
set "PIP_SPEC=%~2"
set "EXTRA_ARGS=%~3"
%PY% -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('%IMPORT_NAME%') else 1)" >nul 2>&1
if errorlevel 1 (
    echo   OPTIONAL: %PIP_SPEC%
    %PY% -m pip install %PIP_SPEC% %EXTRA_ARGS%
    if errorlevel 1 (
        echo   AVISO: %PIP_SPEC% no se pudo instalar. Se usara fallback.
        exit /b 0
    )
) else (
    echo   OK: %PIP_SPEC%
)
exit /b 0

:ensure_cuda_env
set "CUDA_BASE=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4"
if exist "%CUDA_BASE%\bin\nvcc.exe" (
    if not defined CUDA_PATH set "CUDA_PATH=%CUDA_BASE%"
    if not defined CUDA_HOME set "CUDA_HOME=%CUDA_BASE%"
    echo "%PATH%" | findstr /i "CUDA" >nul 2>&1
    if errorlevel 1 (
        set "PATH=%CUDA_BASE%\bin;%PATH%"
        echo   OK: CUDA bin agregado al PATH (nvcc accesible)
    ) else (
        echo   OK: CUDA ya en PATH
    )
    echo   OK: CUDA_PATH=%CUDA_PATH%
    echo   OK: CUDA_HOME=%CUDA_HOME%
) else (
    echo   AVISO: nvcc.exe no encontrado en %CUDA_BASE%\bin.
    echo   flash-attn necesita CUDA Toolkit 12.4+ con nvcc.exe.
    echo   Descarga: https://developer.nvidia.com/cuda-downloads
)
exit /b 0

:ensure_torch_cuda
%PY% -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() and torch.version.cuda else 1)" >nul 2>&1
if errorlevel 1 (
    echo   INSTALL: torch + torchaudio CUDA 12.4
    %PY% -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
    if errorlevel 1 exit /b 1
) else (
    for /f "usebackq delims=" %%c in (`%PY% -c "import torch; print(torch.version.cuda)" 2^>nul`) do set "TORCH_CUDA=%%c"
    echo   OK: torch CUDA !TORCH_CUDA!
)
exit /b 0
