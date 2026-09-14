@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul
title NPEE Math Paper Library

where python >nul 2>nul
if errorlevel 1 (
  echo [NPEE ERROR] Python was not found on PATH.
  echo Install Python 3.10+ from https://www.python.org/downloads/
  pause
  exit /b 1
)

python -u -m npee_math_papers %*
set "NPEE_EXIT_CODE=%ERRORLEVEL%"

if not "%NPEE_EXIT_CODE%"=="0" (
  echo.
  echo [NPEE ERROR] Service stopped with exit code %NPEE_EXIT_CODE%.
  pause
)

exit /b %NPEE_EXIT_CODE%
