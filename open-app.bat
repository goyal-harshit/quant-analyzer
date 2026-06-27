@echo off
REM Open QuantAI app in browser (without starting services)

color 0A
title QuantAI - Open App

echo.
echo Opening QuantAI...
echo.

REM Check if services are running
docker-compose ps >nul 2>&1
if errorlevel 1 (
    color 0C
    echo [ERROR] Docker or Docker Compose not running
    echo.
    echo Please start services first using: start-dev.bat
    pause
    exit /b 1
)

REM Check if frontend is running
docker-compose ps | findstr quantai_frontend >nul
if errorlevel 1 (
    color 0C
    echo [ERROR] Frontend service is not running
    echo.
    echo Please start services first using: start-dev.bat
    pause
    exit /b 1
)

REM Check if frontend is responding
curl -s -I http://localhost:3000 >nul 2>&1
if errorlevel 1 (
    color 0E
    echo [WARNING] Frontend may not be ready yet, trying to open anyway...
    echo.
)

echo [INFO] Opening http://localhost:3000 ...
echo.

REM Try PowerShell first (more reliable)
pwsh -NoProfile -ExecutionPolicy Bypass -Command "Start-Process 'http://localhost:3000'" 2>nul

if errorlevel 1 (
    REM Fallback to cmd start
    start http://localhost:3000
)

echo [OK] Browser should open now
echo.
echo Services Status:
docker-compose ps | findstr quantai_
echo.

pause
