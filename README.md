# M-Pi-Max

A simple, readable system monitor for Raspberry Pi 5 and Linux laptops.

Supports two run modes from the same codebase:

- **Web mode** (FastAPI): open from any device on your LAN
- **Desktop mode** (Tkinter): local GUI window on Linux/Windows with a display session

Both modes show real-time CPU usage/temp/frequency, RAM/swap, disk I/O, network throughput, uptime, and load average.

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

# Web mode (LAN dashboard)
uv run python main.py --mode web --host 0.0.0.0 --port 8000

# Desktop mode (Tkinter GUI)
uv run python main.py --mode desktop
```

## Running with pip

```bash
pip install -r requirements.txt

# Web mode (LAN dashboard)
python main.py --mode web --host 0.0.0.0 --port 8000

# Desktop mode (Tkinter GUI)
python main.py --mode desktop
```

## Quick Launcher Menu

Use the launcher to pick a mode from a menu:

```bash
# With uv
uv run python launch.py

# With pip
python launch.py
```

You can also bypass the menu:

```bash
python launch.py --mode web --host 0.0.0.0 --port 8000
python launch.py --mode desktop --refresh-ms 2000
```

## Accessing the Dashboard

Open a browser and navigate to:

```text
http://<pi-ip>:8000
http://raspberrypi.local:8000
```

## Running as a systemd Service

For headless Raspberry Pi, use **web mode** in systemd.

Copy the included service file and enable it:

```bash
sudo cp mpimax.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mpimax
```

## Suggested Setup by Device

- **Ubuntu laptop**: `--mode desktop` for local usage, or `--mode web` when you want browser access from other devices
- **Desktop Raspberry Pi**: either mode works
- **Headless Raspberry Pi**: `--mode web` only (no display server for Tkinter)

## Pi-Specific Stats

Some stats are Raspberry Pi-specific and require `vcgencmd`:

- **CPU temperature** — read from `/sys/class/thermal/thermal_zone0/temp`
- **Throttle status** — `vcgencmd get_throttled` (detects thermal/voltage issues)

These will show as `unavailable` on non-Pi systems.
