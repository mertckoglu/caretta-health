@echo off
setlocal
title Caretta
cd /d "%~dp0"

echo.
echo   Caretta - astronaut health check
echo   --------------------------------
echo.

rem ---- find Python ---------------------------------------------------------
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not exist ".venv\Scripts\python.exe" if not defined PY (
    echo   Python was not found. Install it from https://www.python.org/downloads/
    echo   and tick "Add python.exe to PATH" during setup.
    echo.
    pause
    exit /b 1
)

rem ---- create the virtual environment the first time -----------------------
if not exist ".venv\Scripts\python.exe" (
    echo   First start: setting things up. This takes a minute or two...
    %PY% -m venv .venv || goto :fail
)
set "VPY=.venv\Scripts\python.exe"

rem ---- install / update packages only when needed --------------------------
set "STAMP=.venv\.requirements-installed"
set "NEED=1"
if exist "%STAMP%" fc /b requirements.txt "%STAMP%" >nul 2>nul && set "NEED=0"
if "%NEED%"=="1" (
    echo   Installing packages...
    "%VPY%" -m pip install --disable-pip-version-check -q --upgrade pip
    "%VPY%" -m pip install --disable-pip-version-check -q -r requirements.txt || goto :fail
    copy /y requirements.txt "%STAMP%" >nul
)

rem ---- already running? just open the browser ------------------------------
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://localhost:8501/_stcore/health).StatusCode } catch { 0 }" | findstr /b "200" >nul
if not errorlevel 1 (
    echo   Caretta is already running - opening it in your browser.
    start "" http://localhost:8501
    exit /b 0
)

echo   Starting Caretta... your browser will open at http://localhost:8501
echo   Keep this window open while you use the site. Close it to stop.
echo.
"%VPY%" -m streamlit run app\ui\Home.py --server.port 8501 --server.headless false
goto :eof

:fail
echo.
echo   Something went wrong during setup. Check your internet connection and try again.
echo   If it keeps failing, delete the .venv folder and run start.bat again.
pause
exit /b 1
