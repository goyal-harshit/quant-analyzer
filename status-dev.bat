@echo off
REM Check QuantAI service status

color 0B
title QuantAI - Service Status

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║           QuantAI Service Status                           ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

docker-compose ps

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║              Port Configuration                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Show ports from .ports.json
pwsh -NoProfile -ExecutionPolicy Bypass -Command "Get-Content .ports.json | ConvertFrom-Json | Select-Object -ExpandProperty services | ForEach-Object { $_.PSObject.Properties | ForEach-Object { Write-Host ('  ' + $_.Name + ' : ' + $_.Value.current) } }"

echo.
echo ℹ️  To view detailed logs: docker-compose logs [service-name]
echo ℹ️  Example: docker-compose logs backend
echo.

pause
