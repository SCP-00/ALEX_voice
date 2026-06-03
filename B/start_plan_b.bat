@echo off
title Alex Voice — Plan B (GPU+CPU)
set PYTHON=C:\Users\andyh\AppData\Local\Programs\Python\Python310\python.exe
cd /d "%~dp0"
echo =============================================
echo   Alex Voice — Plan B
echo   LLM en GPU | TTS en CPU | ASR en CPU
echo   Puerto: 3001
echo =============================================
echo.
if not exist "%PYTHON%" (
    echo [!] Python no encontrado en %PYTHON%
    echo     Instala Python 3.10+ desde python.org
    pause
    exit /b 1
)
echo Iniciando servidor Plan B...
echo     Web UI: http://localhost:3001
echo.
"%PYTHON%" server.py
if %errorlevel% neq 0 (
    echo.
    echo [!] Error (codigo: %errorlevel%)
    echo     pip install faster-whisper piper-tts psutil pynvml numpy kokoro
    echo.
    pause
)
