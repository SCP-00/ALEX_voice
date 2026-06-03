@echo off
title Alex Voice — Plan D (Configuración Definitiva)
setlocal enabledelayedexpansion

:: ── Rutas fijas ──────────────────────────────────────────
set PYTHON=C:\Users\andyh\AppData\Local\Programs\Python\Python310\python.exe
set LLAMA_DIR=C:\Users\andyh\Documents\llama-b9479-bin-win-cuda-13.3-x64

:: Prioridad 1: Qwen3-2B-Q4_K_M (~1.5 GB VRAM, recomendado)
set MODEL_DIR_Q4=C:\Users\andyh\.lmstudio\models\Qwen\Qwen3-2B-Instruct-GGUF
set MODEL_Q4=%MODEL_DIR_Q4%\qwen3-2b-instruct-q4_k_m.gguf

:: Prioridad 2: Qwen3.5-2B-Q8 (~3.0 GB VRAM, fallback si no existe Q4)
set MODEL_DIR_Q8=C:\Users\andyh\.lmstudio\models\khazarai\Qwen3.5-2B-Qwen3.6-plus-Distilled-GGUF
set MODEL_Q8=%MODEL_DIR_Q8%\Qwen3.5-2B-Qwen3.6-plus-Distilled-q8_0.gguf

set PLAN_PORT=3003
set PLAN_NAME=Plan D
set SERVER_SCRIPT=%~dp0server.py

cd /d "%~dp0"

echo =============================================
echo   Alex Voice — %PLAN_NAME%
echo   Configuración Definitiva
echo   LLM GPU (~1.5 GB) ^| Kokoro+Piper TTS ^| Caché 200
echo   Web UI: http://localhost:%PLAN_PORT%
echo =============================================
echo.

:: ── Validar dependencias ────────────────────────────────
if not exist "%PYTHON%" (
    echo [!] Python no encontrado en %PYTHON%
    echo     Instala Python 3.10+ desde python.org
    echo.
    pause
    exit /b 1
)
if not exist "%LLAMA_DIR%\llama-server.exe" (
    echo [!] llama-server.exe no encontrado en %LLAMA_DIR%
    echo.
    pause
    exit /b 1
)

:: ── Elegir modelo: preferir Q4_K_M (1.5GB VRAM, 8K contexto) ──
set MODEL=%MODEL_Q8%
set CTX=4096
set MODEL_LABEL=Qwen3.5-2B-Q8

if exist "%MODEL_Q4%" (
    set MODEL=%MODEL_Q4%
    set CTX=8192
    set MODEL_LABEL=Qwen3-2B-Q4_K_M
    echo       🏆 Modelo optimizado encontrado: %MODEL_LABEL%
    echo       (~1.5 GB VRAM, 8K contexto, sin thinking)
) else (
    echo       ⚠️ Usando modelo existente: %MODEL_LABEL%
    echo       (~3.0 GB VRAM, 4K contexto)
    echo       Para mejor rendimiento, descarga:
    echo       https://huggingface.co/Qwen/Qwen3-2B-Instruct-GGUF
)
echo.

if not exist "%MODEL%" (
    echo [!] Modelo no encontrado:
    echo     %MODEL%
    echo     Descarga Qwen3-2B-Instruct Q4_K_M (~1.5 GB):
    echo     https://huggingface.co/Qwen/Qwen3-2B-Instruct-GGUF
    echo.
    echo     O reinstala Qwen3.5-2B-Q8 desde:
    echo     https://huggingface.co/khazarai/Qwen3.5-2B-Qwen3.6-plus-Distilled-GGUF
    echo.
    pause
    exit /b 1
)

:: ── Verificar / iniciar llama-server ─────────────────────
echo [1/3] Verificando llama-server en puerto 8081...
powershell -Command "& {try{$t=New-Object System.Net.Sockets.TcpClient;$t.Connect('127.0.0.1',8081);$t.Close();exit 0}catch{exit 1}}"
if %errorlevel% equ 0 goto llama_ready

echo       No detectado. Iniciando llama-server con %MODEL_LABEL%...
echo       Contexto: %CTX% tokens
start "llama-server" "%LLAMA_DIR%\llama-server.exe" -m "%MODEL%" -ngl 99 --host 0.0.0.0 --port 8081 -c %CTX% --mlock

echo       Esperando a que arranque (puede tardar ~10s)...
set WAIT_COUNT=0
:wait_llama
set /a WAIT_COUNT+=1
if !WAIT_COUNT! gtr 30 (
    echo [!] llama-server no arranco tras 60s.
    echo     Revisa CUDA/GPU o ejecuta manualmente:
    echo     "%LLAMA_DIR%\llama-server.exe" -m "%MODEL%" -ngl 99 --port 8081
    pause
    exit /b 1
)
timeout /t 2 /nobreak >nul
powershell -Command "& {try{$r=Invoke-WebRequest -Uri 'http://localhost:8081/slots' -TimeoutSec 2 -UseBasicParsing;exit 0}catch{exit 1}}"
if %errorlevel% neq 0 goto wait_llama

:llama_ready
echo       ✅ llama-server listo (%MODEL_LABEL%, %CTX% contexto)

:: ── Iniciar servidor Python ──────────────────────────────
echo [2/3] Iniciando servidor %PLAN_NAME% (puerto %PLAN_PORT%)...
start "%PLAN_NAME%" cmd /c ""%PYTHON%" "%SERVER_SCRIPT%""

:: ── Abrir Chrome ─────────────────────────────────────────
echo [3/3] Abriendo navegador en http://localhost:%PLAN_PORT%...
timeout /t 2 /nobreak >nul
start "" "http://localhost:%PLAN_PORT%"

echo.
echo =============================================
echo   ✅ %PLAN_NAME% ACTIVO
echo   Web UI:      http://localhost:%PLAN_PORT%
echo   Debug:       http://localhost:%PLAN_PORT%/debug
echo   Llama-server: http://localhost:8081
echo   Modelo:      %MODEL_LABEL% (%CTX% contexto)
echo   VRAM LLM:    ~1.5 GB (Q4) / ~3.0 GB (Q8)
echo =============================================
echo.
echo  PRESIONA CUALQUIER TECLA PARA CERRAR TODO
echo  (llama-server + servidor seran detenidos)
echo.
pause >nul

:: ── Cleanup al cerrar ────────────────────────────────────
echo Cerrando servidores...
taskkill -f -im llama-server.exe >nul 2>&1
taskkill -f -im python.exe >nul 2>&1
echo Listo.
