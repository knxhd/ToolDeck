@echo off
setlocal

rem ============================================================
rem  build-windows.cmd - cmd wrapper for build-windows.ps1
rem
rem  Use it from cmd.exe or by double-clicking, no PowerShell
rem  window needed first:
rem    build-windows.cmd                          full build (no tray)
rem    build-windows.cmd -Tray                    tray build
rem    build-windows.cmd -Tray -SkipFrontend
rem    build-windows.cmd -Tray -PythonPath "D:\Program\miniconda3\python.exe"
rem
rem  Equivalent to:
rem    powershell -NoProfile -ExecutionPolicy Bypass -File build-windows.ps1 <args>
rem  The real work is still done by the PowerShell process.
rem ============================================================

rem When double-clicked, keep the window open so the result stays visible
set "DOUBLECLICK="
echo %cmdcmdline% | find /i "%~nx0" >nul && set "DOUBLECLICK=1"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-windows.ps1" %*
set "RC=%ERRORLEVEL%"

if defined DOUBLECLICK (
    echo.
    if "%RC%"=="0" (echo [done] output: backend\dist\) else (echo [failed] exit code %RC%)
    echo Press any key to exit...
    pause >nul
)

exit /b %RC%
