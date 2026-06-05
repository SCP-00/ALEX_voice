@echo off
title Alex Voice — Run
chcp 65001 >nul

echo =============================================
echo   Alex Voice — Run
echo   Selecciona un modo:
echo =============================================
echo.
echo   [1] 🌍  Traductor (argos + Qwen3-TTS)
echo   [2] 🎓  Teacher + Conversation (LLM + Kokoro)
echo   [3] ⚡  Todo (Teacher + Conversation + Traductor)
echo   [4] ❌  Cerrar todo
echo.
echo   [0] 🚪  Salir
echo.

set /p opcion="Selecciona una opcion (0-4): "

if "%opcion%"=="1" goto translator
if "%opcion%"=="2" goto plan_b
if "%opcion%"=="3" goto all
if "%opcion%"=="4" goto kill_all
if "%opcion%"=="0" goto end
goto end

:translator
echo.
echo =============================================
echo   Iniciando Traductor (puerto 3003)
echo =============================================
echo.
echo   Requiere: Qwen3-TTS en GPU + argos-translate en CPU
echo   Traduccion: argos-translate (EN/ES/JA)
echo   Audio: Qwen3-TTS-CustomVoice (GPU, ~2GB VRAM)
echo.
echo   Abre: http://localhost:3003
echo.
start "Alex Translator" python translator.py
echo   ✅ Servidor iniciado en puerto 3003
echo   Presiona Ctrl+C en la ventana para cerrar
echo.
timeout /t 5 /nobreak >nul
start http://localhost:3003
goto end

:plan_b
echo.
echo =============================================
echo   Iniciando Teacher + Conversation (puerto 3000)
echo =============================================
echo.
echo   Requiere: llama-server con modelo GGUF
echo   Usa: python launcher.py
echo.
start "Alex Voice" python launcher.py --open
echo   ✅ Servidor iniciado en puerto 3000
echo.
goto end

:kill_all
echo.
echo =============================================
echo   Cerrando procesos de Alex Voice...
echo =============================================
taskkill -f -im llama-server.exe >nul 2>&1
:: Mata ventanas especificas de Alex Voice (no todos los Python)
taskkill -f -fi "WINDOWTITLE eq Alex Voice*" >nul 2>&1
taskkill -f -fi "WINDOWTITLE eq Alex Translator*" >nul 2>&1
echo   ✅ Procesos de Alex Voice cerrados
echo.
timeout /t 2 /nobreak >nul
goto end

:all
echo.
echo =============================================
echo   Iniciando TODOS los servidores
echo =============================================
echo.
echo   Teacher+Conversation: puerto 3000
echo   Traductor:            puerto 3003
echo.
start "Alex Voice" python launcher.py --no-browser
timeout /t 5 /nobreak >nul
start "Alex Translator" python translator.py
timeout /t 5 /nobreak >nul
start http://localhost:3000
start http://localhost:3003
echo   ✅ Servidores iniciados
echo.
goto end

:end
echo.
echo   Hecho!
echo.
