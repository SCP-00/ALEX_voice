@echo off
title Alex Voice — Run
chcp 65001 >nul

echo =============================================
echo    ⚡ Alex Voice — Inicio rapido
echo =============================================
echo.
echo   Abriendo menu principal...
echo   http://localhost:5000
echo.
echo   Presiona Ctrl+C en esta ventana para cerrar todo.
echo.

:: Iniciar menu server
start "Alex Menu" python menu_server.py

:: Esperar a que arranque
timeout /t 3 /nobreak >nul

:: Abrir navegador
start http://localhost:5000

:: Mantener ventana visible
echo.
echo   ✅ Menu abierto en tu navegador
echo   Cierra esta ventana para detener todo.
echo.
echo   Para cerrar servidores manualmente:
echo     taskkill -f -im python.exe
echo.
pause
