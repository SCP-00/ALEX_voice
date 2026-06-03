@echo off
title Alex Voice — Plan B (GPU+CPU)
cd /d "%~dp0"
echo =============================================
echo   Alex Voice — Plan B
echo   LLM en GPU ^| TTS en CPU ^| ASR en CPU
echo   Puerto: 3001
echo =============================================
echo.
echo [1/2] Iniciando servidor Plan B...
echo     Web UI: http://localhost:3001
echo.
python server.py
if %errorlevel% neq 0 (
    echo.
    echo [!] Error al iniciar servidor.
    echo     Asegurate de tener Python y las dependencias instaladas:
    echo     pip install faster-whisper piper-tts psutil pynvml numpy
    echo.
    pause
)
