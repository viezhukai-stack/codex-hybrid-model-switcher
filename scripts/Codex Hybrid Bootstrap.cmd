@echo off
setlocal
cd /d "%~dp0\.."

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 bootstrap.py
) else (
  python bootstrap.py
)

echo.
pause
