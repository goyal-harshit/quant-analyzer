# QuantAI Development Scripts

Quick-launch batch files for managing the local development environment on Windows. See [QUICKSTART.md](QUICKSTART.md) for the short version.

## Scripts overview

### `start-dev.bat`
**Launches the entire QuantAI stack.**

What it does:
- Verifies Docker and Docker Compose are installed
- Runs the port availability check (`check-ports.ps1`, updates `.ports.json`)
- Starts all services with `docker-compose up -d --build`
- Displays service status and opens http://localhost:3000

**Usage:** double-click `start-dev.bat` (or `cmd /c start-dev.bat`).

**Result (default ports):**
```
Frontend   : http://localhost:3000
API        : http://localhost:8000/api/v1
Database   : localhost:5432
Redis      : localhost:6379
Ollama LLM : localhost:11434
```

---

### `stop-dev.bat`
**Shuts down all services.**

- Runs `docker-compose down`: stops containers and removes networks
- Data is preserved (the `postgres_data` and `ollama_data` volumes are kept)

**Usage:** double-click `stop-dev.bat`.

---

### `status-dev.bat`
**Check running services and port configuration.**

- Shows all containers and their status (`docker-compose ps`)
- Displays current port assignments from `.ports.json`

**Usage:** double-click `status-dev.bat`.

**Output example:**
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

### `logs-dev.bat`
**View service logs with interactive selection.**

- Menu-driven: pick a service (1 backend, 2 frontend, 3 postgres, 4 redis, 5 ollama, 6 celery_worker, 7 celery_beat, 8 all services)
- Streams logs in follow mode; press Ctrl+C to exit

**Usage:** double-click `logs-dev.bat`, then select a service number.

---

## Port management

All scripts use the automatic port checker:

**`.ports.json`** — registry of service ports. Auto-updated when ports conflict. **Local to your machine and gitignored** (it reflects whatever ports happen to be free on your system).

**`check-ports.ps1`** — PowerShell script that:
- Detects port conflicts (via `netstat`)
- Finds the next available port when the target is busy
- Writes host-port mappings to `docker-compose.override.yml` (auto-generated, gitignored — do not edit by hand)

Run manually: `pwsh -NoProfile -ExecutionPolicy Bypass -File "check-ports.ps1"`

To change a port: edit the `target` value in `.ports.json`, run `check-ports.ps1`, then restart the stack.

---

## Quick start

1. **First time:** run `start-dev.bat` and wait ~30 seconds for services to initialize
2. **Verify:** `status-dev.bat`
3. **Debug:** `logs-dev.bat`
4. **Done for the day:** `stop-dev.bat`

---

## Troubleshooting

### Port already in use
Run `start-dev.bat` again — it detects the conflict and uses the next available port. Check `status-dev.bat` to see the assignments.

### Services not starting
Run `logs-dev.bat` → select backend (option 1). Common issues:
- `backend/.env` missing — create it with `cp backend/.env.example backend/.env`
- Database not ready yet — wait 30 seconds and check again
- Port conflict — run `check-ports.ps1` again

### Docker not found
- Install Docker Desktop: https://www.docker.com/products/docker-desktop
- Restart your terminal after installation

---

## Manual commands

If you prefer the command line:

```powershell
docker-compose up -d               # start services
docker-compose down                # stop services
docker-compose ps                  # status
docker-compose logs -f <service>   # follow logs

# Health probes
docker exec quantai_postgres pg_isready
docker exec quantai_redis redis-cli ping
```

---

## Tips

- Keep `status-dev.bat` handy while developing to monitor services
- Use `logs-dev.bat` to debug issues without extra terminal juggling
- Port assignments persist across sessions via `.ports.json`, so restarts are consistent
