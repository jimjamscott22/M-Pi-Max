# M-Pi-Max

A simple, readable system monitor web dashboard for Raspberry Pi 5.

Displays real-time CPU usage/temp/frequency, RAM/swap, disk I/O, network throughput, uptime, and load average — served over your LAN via FastAPI.

## Requirements

- Raspberry Pi 5 (or any Linux system; Pi-specific stats require `vcgencmd`)
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Running with uv (recommended)

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repo
git clone https://github.com/youruser/M-Pi-Max.git
cd M-Pi-Max

# Run directly — uv handles the venv and dependencies automatically
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

## Running with pip

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Accessing the Dashboard

Open a browser and navigate to:

```text
http://<pi-ip>:8000
http://raspberrypi.local:8000
```

## Running as a systemd Service

Copy the included service file and enable it:

```bash
sudo cp mpimax.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mpimax
```

## Pi-Specific Stats

Some stats are Raspberry Pi-specific and require `vcgencmd`:

- **CPU temperature** — read from `/sys/class/thermal/thermal_zone0/temp`
- **Throttle status** — `vcgencmd get_throttled` (detects thermal/voltage issues)

These will show as `unavailable` on non-Pi systems.
