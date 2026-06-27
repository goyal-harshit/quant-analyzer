# QuantAI Development Scripts

Quick-launch batch files for managing the development environment.

## Scripts Overview

### 🚀 `start-dev.bat`
**Launches the entire QuantAI stack**

What it does:
- ✅ Verifies Docker & Docker Compose are installed
- 🔍 Runs port availability check (updates `.ports.json`)
- 🐳 Starts all services with `docker-compose up -d`
- 📊 Displays service status and port mappings

**Usage:**
```
Double-click start-dev.bat
or
cmd /c start-dev.bat
```

**Result:**
```
Frontend   : http://localhost:3000
API        : http://localhost:8000/api/v1
Database   : localhost:5432
Redis      : localhost:6379
Ollama LLM : localhost:11434
```

---

### 🛑 `stop-dev.bat`
**Gracefully shuts down all services**

What it does:
- Stops all running containers
- Preserves data (databases, volumes)
- Cleans up networks

**Usage:**
```
Double-click stop-dev.bat
```

---

### 📊 `status-dev.bat`
**Check running services and port configuration**

What it does:
- Shows all running containers and their status
- Displays port mappings from `.ports.json`
- Helpful for debugging

**Usage:**
```
Double-click status-dev.bat
```

**Output Example:**
```
NAME              STATUS
quantai_backend   Up 5 minutes
quantai_frontend  Up 5 minutes
quantai_postgres  Up 5 minutes (healthy)
quantai_redis     Up 5 minutes (healthy)

Port Configuration:
  backend : 8000
  frontend : 3000
  postgres : 5432
  redis : 6379
  ollama : 11434
```

---

### 📝 `logs-dev.bat`
**View service logs with interactive selection**

What it does:
- Shows menu to select which service's logs to view
- Streams logs in real-time (follow mode)
- Press Ctrl+C to exit

**Usage:**
```
Double-click logs-dev.bat
Select service number when prompted
```

**Examples:**
- View backend API errors: Select `1`
- View frontend build logs: Select `2`
- Stream all logs: Select `8`

---

## Port Management

All scripts use the automatic port checker:

**File: `.ports.json`**
- Persistent registry of service ports
- Auto-updated when ports conflict
- Committed to git for consistency

**File: `check-ports.ps1`**
- PowerShell script that detects port conflicts
- Finds next available port if needed
- Updates `docker-compose.override.yml`
- Run manually: `pwsh ./check-ports.ps1`

---

## Quick Start

1. **First time setup:**
   ```
   start-dev.bat
   ```
   Wait for services to initialize (~30 seconds)

2. **Check services are running:**
   ```
   status-dev.bat
   ```

3. **View logs if needed:**
   ```
   logs-dev.bat
   ```

4. **When done for the day:**
   ```
   stop-dev.bat
   ```

---

## Troubleshooting

### Port already in use
```
start-dev.bat
```
The script automatically detects conflicts and uses the next available port. Check `status-dev.bat` to see assigned ports.

### Services not starting
```
logs-dev.bat → Select backend (option 1)
```
View backend logs to see errors. Common issues:
- Port conflict: Run `check-ports.ps1` again
- Database not ready: Wait 30 seconds, check again

### Docker not found
- Install Docker Desktop: https://www.docker.com/products/docker-desktop
- Restart your terminal after installation

---

## Manual Commands

If you prefer command line:

```powershell
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Check status
docker-compose ps

# View logs
docker-compose logs -f [service-name]

# Check specific service health
docker exec quantai_postgres pg_isready
docker exec quantai_redis redis-cli ping
```

---

## Memory & Configuration

**Saved in project:**
- `.ports.json` — Port registry (git-tracked)
- `docker-compose.override.yml` — Port overrides (auto-generated)
- `check-ports.ps1` — Port checker script

**Saved in memory:**
- `~/.claude/projects/.../memory/port-management.md`
- Future sessions will auto-check ports before launching

---

## Tips

- 💡 Keep `status-dev.bat` window open while developing to monitor services
- 💡 Use `logs-dev.bat` to debug issues without leaving scripts
- 💡 Ports are automatically saved, so you can restart anytime
- 💡 If you want to change a port: Edit `.ports.json`, then run `check-ports.ps1`
