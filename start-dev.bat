@echo off
REM QuantAI Development Environment Launcher
REM Checks ports, starts docker-compose, shows service status

color 0A
title QuantAI Dev Environment

echo.
echo ============================================================
echo          QuantAI Development Environment Launcher
echo ============================================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo [ERROR] Docker is not installed or not in PATH
    echo.
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo [OK] Docker found
echo.

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo [ERROR] docker-compose not found
    pause
    exit /b 1
)

echo [OK] Docker Compose found
echo.

REM Run port checker
echo [INFO] Checking port availability...
echo.

pwsh -NoProfile -ExecutionPolicy Bypass -File "check-ports.ps1"

if errorlevel 1 (
    color 0C
    echo.
    echo [ERROR] Port check failed
    pause
    exit /b 1
)

echo.
echo [INFO] Port check complete. Starting services...
echo.

REM Start docker-compose in detached mode and rebuild local images so frontend
REM static exports pick up recent code changes.
docker-compose up -d --build

if errorlevel 1 (
    color 0C
    echo.
    echo [ERROR] Docker Compose failed to start
    pause
    exit /b 1
)

REM Wait for services to initialize
timeout /t 3 /nobreak

REM Show status
echo.
echo Service Status:
echo.

docker-compose ps

REM Read the actual assigned ports from .ports.json (check-ports.ps1 bumps
REM them when a target port is genuinely taken by something else), so the
REM banner and the auto-opened browser tab always point at the real URLs
REM instead of hardcoded defaults that can silently go stale.
for /f "delims=" %%A in ('pwsh -NoProfile -ExecutionPolicy Bypass -Command "(Get-Content .ports.json | ConvertFrom-Json).services.frontend.current"') do set FRONTEND_PORT=%%A
for /f "delims=" %%A in ('pwsh -NoProfile -ExecutionPolicy Bypass -Command "(Get-Content .ports.json | ConvertFrom-Json).services.backend.current"') do set BACKEND_PORT=%%A
for /f "delims=" %%A in ('pwsh -NoProfile -ExecutionPolicy Bypass -Command "(Get-Content .ports.json | ConvertFrom-Json).services.postgres.current"') do set POSTGRES_PORT=%%A
for /f "delims=" %%A in ('pwsh -NoProfile -ExecutionPolicy Bypass -Command "(Get-Content .ports.json | ConvertFrom-Json).services.redis.current"') do set REDIS_PORT=%%A
for /f "delims=" %%A in ('pwsh -NoProfile -ExecutionPolicy Bypass -Command "(Get-Content .ports.json | ConvertFrom-Json).services.ollama.current"') do set OLLAMA_PORT=%%A

echo.
echo ============================================================
echo                  Services Running [OK]
echo ============================================================
echo  Frontend   : http://localhost:%FRONTEND_PORT%
echo  API        : http://localhost:%BACKEND_PORT%/api/v1
echo  Database   : localhost:%POSTGRES_PORT%
echo  Redis      : localhost:%REDIS_PORT%
echo  Ollama LLM : localhost:%OLLAMA_PORT%
echo ============================================================
echo.

echo.
echo [INFO] Waiting for services to fully initialize...
timeout /t 5 /nobreak

echo [INFO] Opening http://localhost:%FRONTEND_PORT% in your browser...
echo.

REM Try to open browser with PowerShell (more reliable)
pwsh -NoProfile -ExecutionPolicy Bypass -Command "Start-Process 'http://localhost:%FRONTEND_PORT%'"

if errorlevel 1 (
    REM Fallback to cmd start command
    start http://localhost:%FRONTEND_PORT%
)

echo.
echo [OK] Browser should open in a few seconds
echo.
echo If browser doesn't open, manually visit: http://localhost:3000
echo.
echo Press any key to close this window...
pause
