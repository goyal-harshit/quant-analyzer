# QuantAI — Quick Start Guide

**System fully running with automatic port management and batch file launchers.**

## ⚡ Get Started (30 seconds)

### First Time Setup
```
Double-click: start-dev.bat
```

That's it! The script will:
1. ✅ Check if Docker is installed
2. 🔍 Scan for port conflicts
3. 🚀 Launch all services
4. 📊 Show status with port assignments

### Result (in ~30 seconds)
```
✅ Frontend   : http://localhost:3000
✅ API        : http://localhost:8000/api/v1
✅ Database   : localhost:5432
✅ Cache      : localhost:6379
✅ LLM        : localhost:11434
```

---

## 🎯 Available Commands

### Launcher Scripts (Just Double-Click)

| Script | Purpose |
|--------|---------|
| `start-dev.bat` | 🚀 Launch entire stack |
| `stop-dev.bat` | 🛑 Stop all services |
| `status-dev.bat` | 📊 Check what's running |
| `logs-dev.bat` | 📝 View service logs |

---

## 📋 What's Running

When `start-dev.bat` completes, you have:

| Service | Port | Purpose |
|---------|------|---------|
| **Frontend** | 3000 | Next.js UI (http://localhost:3000) |
| **Backend API** | 8000 | FastAPI REST endpoints |
| **PostgreSQL** | 5432 | Primary database (TimescaleDB) |
| **Redis** | 6379 | In-memory cache |
| **Ollama** | 11434 | Local LLM inference |
| **Celery** | — | Background job processing |

---

## 🔌 Smart Port Management

**Problem Fixed:** Ports were conflicting with existing services.

**Solution Implemented:**
- `start-dev.bat` automatically runs port checker
- If a port is busy → finds next available port
- Saves configuration to `.ports.json`
- Same ports used every session (consistent)

**Example:**
```
Port 3000 busy? → Uses 3001
Port 8000 busy? → Uses 8001
Saved for next time!
```

Check current ports:
```
Double-click: status-dev.bat
```

---

## 🐛 Troubleshooting

### Services won't start
```
Double-click: logs-dev.bat
Select: 1 (backend) or 2 (frontend)
```
View errors and fix

### Port already in use
```
Double-click: start-dev.bat
```
Automatically detects and uses next available port

### Need to stop services
```
Double-click: stop-dev.bat
```
Gracefully shuts down everything

### Want to change a port manually
Edit `.ports.json`, then:
```
pwsh -NoProfile -ExecutionPolicy Bypass -File "check-ports.ps1"
```

---

## 💻 For Command-Line Folks

If you prefer terminal commands:

```powershell
# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────┐
│           QuantAI Application               │
├─────────────────────────────────────────────┤
│                                             │
│  Frontend              Backend              │
│  ┌──────────────┐    ┌──────────────┐     │
│  │  Next.js     │───→│   FastAPI    │     │
│  │  localhost   │    │   localhost  │     │
│  │  :3000       │    │   :8000      │     │
│  └──────┬───────┘    └──────┬───────┘     │
│         │                   │              │
│         └───────┬───────────┘              │
│                 ↓                          │
│        ┌─────────────────────┐            │
│        │   PostgreSQL        │            │
│        │   Redis Cache       │            │
│        │   Ollama LLM        │            │
│        │   Celery Workers    │            │
│        └─────────────────────┘            │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
project/
├── start-dev.bat              ← Double-click to launch
├── stop-dev.bat               ← Shutdown services
├── status-dev.bat             ← Check running services
├── logs-dev.bat               ← View service logs
├── check-ports.ps1            ← Port availability checker
├── .ports.json                ← Port registry (auto-updated)
├── docker-compose.yml         ← Service definitions
├── docker-compose.override.yml ← Port overrides (auto-generated)
│
├── backend/                   ← FastAPI application
│   ├── main.py
│   ├── models/
│   ├── modules/
│   └── services/
│
└── frontend/                  ← Next.js application
    ├── app/
    ├── components/
    └── out/                   ← Static build
```

---

## 🚀 Daily Workflow

**Morning — Start Development:**
```
Double-click: start-dev.bat
```

**During Day — Monitor Services:**
```
Double-click: status-dev.bat        (check health)
Double-click: logs-dev.bat          (debug issues)
```

**Evening — Stop Everything:**
```
Double-click: stop-dev.bat
```

---

## 🛠️ Configuration Files

### `.ports.json` (Auto-managed)
Tracks which port each service uses:
```json
{
  "services": {
    "frontend": { "target": 3000, "current": 3000 },
    "backend": { "target": 8000, "current": 8000 },
    ...
  }
}
```
- ✅ Automatically updated
- ✅ Git-tracked for consistency
- ✅ Never edit manually (use `check-ports.ps1`)

### `docker-compose.override.yml` (Auto-generated)
Port overrides for docker-compose:
```yaml
services:
  frontend:
    ports: ["3000:3000"]
  backend:
    ports: ["8000:8000"]
  ...
```
- ✅ Auto-created by `check-ports.ps1`
- ✅ Applied automatically
- ✅ Don't edit directly

---

## 📚 Documentation

- **`DEV_SCRIPTS.md`** — Full launcher script documentation
- **`docker-compose.yml`** — Service configuration
- **`.github/workflows/`** — CI/CD pipelines

---

## ✨ Key Features

✅ **Zero-Friction Startup** — Double-click, wait 30 seconds  
✅ **Automatic Port Management** — No conflicts, always available  
✅ **Persistent Configuration** — Same ports every session  
✅ **Easy Debugging** — Interactive log viewer  
✅ **Git-Tracked Settings** — Consistent across team  
✅ **Docker Containerized** — Works on any machine  

---

## 🤔 FAQ

**Q: What if I need to use different ports?**  
A: Edit `.ports.json` with desired ports, then run `check-ports.ps1`

**Q: How do I see what's happening?**  
A: `status-dev.bat` shows all running services. `logs-dev.bat` shows real-time logs.

**Q: Can I run this from command line?**  
A: Yes, use `docker-compose up -d` (but you lose automatic port checking)

**Q: Do I need to restart to apply port changes?**  
A: Yes, stop services (`stop-dev.bat`), update ports, then start (`start-dev.bat`)

**Q: What if Docker isn't installed?**  
A: `start-dev.bat` will tell you where to install it

---

## 🎓 Next Steps

1. ✅ Double-click `start-dev.bat` to launch
2. ✅ Open http://localhost:3000 in browser
3. ✅ Read `DEV_SCRIPTS.md` for advanced usage
4. ✅ Check `.ports.json` to see current configuration

---

**Questions?** Check `DEV_SCRIPTS.md` or read `.github/TROUBLESHOOTING.md`

**Ready?** → **Double-click `start-dev.bat` now!** 🚀
