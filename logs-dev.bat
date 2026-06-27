@echo off
REM View QuantAI service logs

color 09
title QuantAI - Service Logs

echo.
echo ============================================================
echo                 QuantAI Service Logs
echo ============================================================
echo.

echo Available services:
echo   1. backend   (FastAPI)
echo   2. frontend  (Next.js)
echo   3. postgres  (Database)
echo   4. redis     (Cache)
echo   5. ollama    (LLM)
echo   6. celery_worker  (Background jobs)
echo   7. celery_beat    (Scheduler)
echo   8. All services (follow all logs)
echo.

set /p choice="Select service to view logs (1-8): "

if "%choice%"=="1" (
    docker-compose logs -f backend
) else if "%choice%"=="2" (
    docker-compose logs -f frontend
) else if "%choice%"=="3" (
    docker-compose logs -f postgres
) else if "%choice%"=="4" (
    docker-compose logs -f redis
) else if "%choice%"=="5" (
    docker-compose logs -f ollama
) else if "%choice%"=="6" (
    docker-compose logs -f celery_worker
) else if "%choice%"=="7" (
    docker-compose logs -f celery_beat
) else if "%choice%"=="8" (
    docker-compose logs -f
) else (
    echo Invalid choice
    pause
    exit /b 1
)
