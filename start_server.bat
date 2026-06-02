@echo off
REM ====================================
REM Alex Voice — Start llama-server (Windows)
REM ====================================
echo =========================================
echo   Alex Voice — Iniciando llama-server
echo =========================================

set LLAMA_DIR=C:\Users\andyh\Documents\llama-b9479-bin-win-cuda-13.3-x64
set MODEL_DIR=C:\Users\andyh\.lmstudio\models\khazarai\Qwen3.5-2B-Qwen3.6-plus-Distilled-GGUF
set MODEL=%MODEL_DIR%\Qwen3.5-2B-Qwen3.6-plus-Distilled-q8_0.gguf

echo  Modelo: %MODEL%
echo  Puerto: 8081
echo  GPU:    todas las capas (-ngl 99)
echo =========================================
echo.
echo Abre frontend\index.html en tu navegador
echo.

"%LLAMA_DIR%\llama-server.exe" -m "%MODEL%" -ngl 99 --host 0.0.0.0 --port 8081 -c 4096 --mlock

pause
