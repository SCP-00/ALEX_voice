@echo off
REM ===============================================
REM Alex Voice — Inicio Completo (Windows)
REM ===============================================
REM 1. llama-server (Qwen3.5-2B, puerto 8081)
REM 2. Monitor server  (python server.py, puerto 3000)
REM ===============================================

set PYTHON=C:\Users\andyh\AppData\Local\Programs\Python\Python310\python.exe
set LLAMA_DIR=C:\Users\andyh\Documents\llama-b9479-bin-win-cuda-13.3-x64
set MODEL_DIR=C:\Users\andyh\.lmstudio\models\khazarai\Qwen3.5-2B-Qwen3.6-plus-Distilled-GGUF
set MODEL=%MODEL_DIR%\Qwen3.5-2B-Qwen3.6-plus-Distilled-q8_0.gguf

if not exist "%MODEL%" (
    echo.
    echo  =============================================
    echo    ERROR: Modelo no encontrado
    echo  =============================================
    echo    %MODEL%
    echo.
    echo    Descargalo desde:
    echo    https://huggingface.co/khazarai/Qwen3.5-2B-Qwen3.6-plus-Distilled-GGUF
    echo.
    pause
    exit /b 1
)

echo.
echo =============================================
echo   Alex Voice — Inicio Completo
echo =============================================
echo.
echo  [1/2] Iniciando llama-server (puerto 8081)...
start "llama-server" "%LLAMA_DIR%\llama-server.exe" -m "%MODEL%" -ngl 99 --host 0.0.0.0 --port 8081 -c 4096 --mlock

echo  [2/2] Iniciando Monitor server (puerto 3000)...
start "monitor-server" cmd /c "\"%PYTHON%\" server.py"

echo.
echo  =============================================
echo   Alex Voice esta corriendo
echo  =============================================
echo.
echo  LLM:     http://localhost:8081
echo  Monitor: http://localhost:3000
echo  Debug:   http://localhost:3000/debug
echo.
echo  Abre frontend/plan-a/index.html en tu navegador
echo.
echo  Presiona cualquier tecla para cerrar TODO...
pause >nul

REM Cleanup al cerrar
echo Cerrando servidores...
taskkill -f -im llama-server.exe >nul 2>&1
taskkill -f -im python.exe >nul 2>&1
echo Listo.

