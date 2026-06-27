#!/usr/bin/env pwsh
<#
.SYNOPSIS
Check port availability and update .ports.json with available ports.
Creates docker-compose.override.yml with actual port mappings.

.EXAMPLE
./check-ports.ps1
#>

$portsFile = ".ports.json"
$overrideFile = "docker-compose.override.yml"

Write-Host "🔍 Checking port availability..." -ForegroundColor Cyan

# Read current port config
$config = Get-Content $portsFile | ConvertFrom-Json

# Check each service port
$netstat = netstat -ano -p tcp | Select-Object -Skip 4
$usedPorts = @()

foreach ($line in $netstat) {
    if ($line -match 'LISTENING.*(\d+)$') {
        $port = [int]($line -split '\s+' | Where-Object {$_ -match '^\d+$'} | Select-Object -Last 1)
        $usedPorts += $port
    }
}

Write-Host "Used ports: $($usedPorts -join ', ')" -ForegroundColor Yellow

# Check each service and find available port if needed
$overrideServices = @{}

foreach ($service in $config.services.PSObject.Properties) {
    $name = $service.Name
    $target = $service.Value.target
    $current = $service.Value.current

    # Start checking from target port
    $port = $target
    $found = $false

    for ($i = 0; $i -lt 100; $i++) {
        if ($usedPorts -notcontains $port) {
            $config.services.$name.current = $port
            $config.services.$name.available = $true
            $found = $true
            Write-Host "✅ $name : port $port (available)" -ForegroundColor Green
            break
        }
        $port++
    }

    if (-not $found) {
        $config.services.$name.available = $false
        Write-Host "❌ $name : NO PORT AVAILABLE (checked ports $target-$($target+99))" -ForegroundColor Red
    }

    # Add to docker-compose override
    $overrideServices[$name] = @{
        ports = @("$($config.services.$name.current):$target")
    }
}

# Update .ports.json
$config.lastUpdated = (Get-Date -AsUTC -Format o)
$config | ConvertTo-Json -Depth 10 | Set-Content $portsFile
Write-Host "✅ Updated $portsFile" -ForegroundColor Green

# Create docker-compose.override.yml
$override = @{
    version = "3.8"
    services = $overrideServices
}

$override | ConvertTo-Json -Depth 10 | Set-Content $overrideFile
Write-Host "✅ Created $overrideFile" -ForegroundColor Green

# Summary
Write-Host "`n📋 Port Summary:" -ForegroundColor Cyan
foreach ($service in $config.services.PSObject.Properties) {
    $name = $service.Name
    $port = $service.Value.current
    $status = if ($service.Value.available) { "✅" } else { "❌" }
    Write-Host "  $status $name : localhost:$port" -ForegroundColor White
}

Write-Host "`n✨ Ready to run: docker-compose up -d" -ForegroundColor Green
