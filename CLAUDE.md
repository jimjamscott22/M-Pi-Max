# M-Pi-Max

A system monitor for Raspberry Pi 5, built to be bundled with Pi-Apps.

## Project Goals
- Display real-time system stats: CPU usage/temp/frequency, RAM/swap, disk I/O, network throughput, GPU stats, uptime, load average, running processes
- Web dashboard served via FastAPI + uvicorn, accessible from any device on the LAN
- Runs persistently as a systemd service on the Pi
- Clean, simple UI using a lightweight frontend (e.g. Chart.js)

## Stack

- **Backend**: Python 3.11+, FastAPI, uvicorn
- **Stats**: `psutil`, `/proc/`, `/sys/`, `vcgencmd`
- **Frontend**: HTML + Chart.js (no heavy frameworks)
- **Service**: systemd
- **Package manager**: `uv` (preferred); `pip` + `requirements.txt` also supported

## Running the App

**With uv (preferred):**
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

**With pip:**
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Access at `http://<pi-ip>:8000` or `http://raspberrypi.local:8000`

## Dependency Management

- `pyproject.toml` is the source of truth for dependencies (uv)
- `requirements.txt` is kept in sync for pip compatibility
- When adding dependencies, update both files

## Pi-Specific Stats
- CPU temp: `/sys/class/thermal/thermal_zone0/temp`
- Throttle status: `vcgencmd get_throttled`
- GPU stats via `vcgencmd`
- Pi-specific stats gracefully return `None`/`"unavailable"` on non-Pi systems

## Pi-Apps Bundling
- Install script should drop a systemd `.service` file and enable it
- App should be self-contained and easy to install/uninstall
- Avoid heavy dependencies

## Code Style
- Keep it simple and readable — this is meant to be approachable
- Prefer flat structure over unnecessary abstraction
- No premature optimization
