@echo off
REM QuantAI Development Environment Launcher
REM Checks ports, starts docker-compose, shows service status

color 0A
title QuantAI Dev Environment

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║          QuantAI Development Environment Launcher          ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo ❌ ERROR: Docker is not installed or not in PATH
    echo.
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo ✅ Docker found
echo.

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo ❌ ERROR: docker-compose not found
    pause
    exit /b 1
)

echo ✅ Docker Compose found
echo.

REM Run port checker
echo 🔍 Checking port availability...
echo.

pwsh -NoProfile -ExecutionPolicy Bypass -File "check-ports.ps1"

if errorlevel 1 (
    color 0C
    echo.
    echo ❌ Port check failed
    pause
    exit /b 1
)

echo.
echo ✨ Port check complete. Starting services...
echo.

REM Start docker-compose in detached mode
docker-compose up -d

if errorlevel 1 (
    color 0C
    echo.
    echo ❌ Docker Compose failed to start
    pause
    exit /b 1
)

REM Wait for services to initialize
timeout /t 3 /nobreak

REM Show status
echo.
echo 📋 Service Status:
echo.

docker-compose ps

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                  Services Running ✅                        ║
echo ╠════════════════════════════════════════════════════════════╣
echo ║  Frontend   : http://localhost:3000                        ║
echo ║  API        : http://localhost:8000/api/v1                 ║
echo ║  Database   : localhost:5432                               ║
echo ║  Redis      : localhost:6379                               ║
echo ║  Ollama LLM : localhost:11434                               ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

pause
