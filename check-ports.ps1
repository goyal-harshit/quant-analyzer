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

Write-Host "[INFO] Checking port availability..." -ForegroundColor Cyan

# Read current port config
$config = Get-Content $portsFile | ConvertFrom-Json

# Check each service port. Extract the port from the *local address* column
# (2nd whitespace-separated field), not a blind "last digit group on the
# line" match — that previously grabbed the trailing PID column instead of
# the port, so busy ports were silently reported as available.
$netstat = netstat -ano -p tcp | Select-Object -Skip 4
$usedPorts = @()

foreach ($line in $netstat) {
    if ($line -match 'LISTENING') {
        $tokens = $line.Trim() -split '\s+'
        $localAddress = $tokens[1]
        if ($localAddress -match ':(\d+)$') {
            $usedPorts += [int]$matches[1]
        }
    }
}
$usedPorts = $usedPorts | Sort-Object -Unique

# A port already published by this project's own running containers isn't a
# conflict — `docker-compose up` will just reconnect to it. Without this,
# re-running the launcher against an already-running stack ratchets every
# port upward on each run instead of reusing the live one.
$ownPorts = @()
try {
    $ownContainerPorts = docker ps --filter "name=quantai_" --format "{{.Ports}}" 2>$null
    foreach ($line in $ownContainerPorts) {
        foreach ($m in [regex]::Matches($line, '(?:0\.0\.0\.0|\[::\]):(\d+)->')) {
            $ownPorts += [int]$m.Groups[1].Value
        }
    }
} catch {
    # Docker not available/running — fall back to treating nothing as "ours".
}
if ($ownPorts.Count -gt 0) {
    Write-Host "Already owned by this project's running containers: $(($ownPorts | Sort-Object -Unique) -join ', ')" -ForegroundColor DarkYellow
    $usedPorts = $usedPorts | Where-Object { $ownPorts -notcontains $_ }
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
            Write-Host "[OK] $name : port $port (available)" -ForegroundColor Green
            break
        }
        $port++
    }

    if (-not $found) {
        $config.services.$name.available = $false
        Write-Host "[ERROR] $name : NO PORT AVAILABLE (checked ports $target-$($target+99))" -ForegroundColor Red
    }

    # Add to docker-compose override
    $overrideServices[$name] = @{
        ports = @("$($config.services.$name.current):$target")
    }
}

# Update .ports.json. Written files are only reported [OK] if the write
# actually succeeds — Set-Content errors (e.g. file locked by another
# process) previously printed a non-terminating error but the script kept
# going and claimed success anyway.
$config.lastUpdated = (Get-Date -AsUTC -Format o)
try {
    $config | ConvertTo-Json -Depth 10 | Set-Content $portsFile -ErrorAction Stop
    Write-Host "[OK] Updated $portsFile" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to write $portsFile : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Create docker-compose.override.yml
# (Compose accepts JSON; the top-level "version" attribute is obsolete in
# Compose v2 and triggers a warning, so it is intentionally omitted.)
$override = @{
    services = $overrideServices
}

try {
    $override | ConvertTo-Json -Depth 10 | Set-Content $overrideFile -ErrorAction Stop
    Write-Host "[OK] Created $overrideFile" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to write $overrideFile : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Summary
Write-Host "`n[INFO] Port Summary:" -ForegroundColor Cyan
foreach ($service in $config.services.PSObject.Properties) {
    $name = $service.Name
    $port = $service.Value.current
    $status = if ($service.Value.available) { "[OK]" } else { "[ERROR]" }
    Write-Host "  $status $name : localhost:$port" -ForegroundColor White
}

Write-Host "`n[OK] Ready to run: docker-compose up -d" -ForegroundColor Green
