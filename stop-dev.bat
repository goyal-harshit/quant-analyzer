@echo off
REM Stop all QuantAI services

color 0E
title QuantAI - Stopping Services

echo.
echo ============================================================
echo              Stopping QuantAI Services
echo ============================================================
echo.

docker-compose down

echo.
echo [OK] All services stopped
echo.

pause
