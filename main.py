import subprocess
import time

import psutil
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="M-Pi-Max")

# Serve everything in the /static folder at the /static URL path
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Helper functions ---

def get_cpu_temp() -> float | None:
    """Read CPU temperature directly from the Pi's thermal sensor."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            # The file gives millidegrees Celsius, so divide by 1000
            return round(int(f.read().strip()) / 1000, 1)
    except FileNotFoundError:
        return None


def get_throttle_status() -> str:
    """
    Ask the Pi's firmware if the CPU has been throttled due to heat or low voltage.
    vcgencmd is a Pi-specific command-line tool for querying the GPU/firmware.
    Returns the raw hex value, e.g. '0x0' means no throttling.
    """
    try:
        result = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True, text=True, timeout=2
        )
        # Output looks like: "throttled=0x0"
        return result.stdout.strip().split("=")[-1]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "unavailable"


def format_uptime(seconds: float) -> str:
    """Convert raw seconds into a human-readable uptime string."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{days}d {hours}h {minutes}m"


# --- Routes ---

@app.get("/")
def index():
    """Serve the dashboard HTML page."""
    return FileResponse("static/index.html")


@app.get("/stats")
def get_stats():
    """
    Return a snapshot of system stats as JSON.
    The frontend will call this endpoint every few seconds to update the dashboard.
    """

    # CPU — interval=0.5 means psutil measures usage over half a second (more accurate)
    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_freq = psutil.cpu_freq()
    cpu_freq_mhz = round(cpu_freq.current) if cpu_freq else None

    # Per-core usage list, e.g. [12.5, 44.0, 8.3, 22.1] for a quad-core Pi
    per_core = psutil.cpu_percent(percpu=True)

    # Memory — psutil returns bytes, so we convert to GB for readability
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # Disk — check the root partition
    disk = psutil.disk_usage("/")
    disk_io = psutil.disk_io_counters()

    # Network — bytes since boot; we convert to MB
    net_io = psutil.net_io_counters()

    # System uptime — boot time is a Unix timestamp, subtract from now
    uptime_seconds = time.time() - psutil.boot_time()

    # Load average — tuple of (1min, 5min, 15min) averages
    load_avg = [round(x, 2) for x in psutil.getloadavg()]

    return {
        "cpu": {
            "percent": cpu_percent,
            "per_core": per_core,
            "freq_mhz": cpu_freq_mhz,
            "temp_c": get_cpu_temp(),
            "throttled": get_throttle_status(),
        },
        "memory": {
            "total_gb": round(mem.total / 1e9, 2),
            "used_gb": round(mem.used / 1e9, 2),
            "percent": mem.percent,
        },
        "swap": {
            "total_gb": round(swap.total / 1e9, 2),
            "used_gb": round(swap.used / 1e9, 2),
            "percent": swap.percent,
        },
        "disk": {
            "total_gb": round(disk.total / 1e9, 1),
            "used_gb": round(disk.used / 1e9, 1),
            "percent": disk.percent,
            "read_mb": round(disk_io.read_bytes / 1e6, 1) if disk_io else None,
            "write_mb": round(disk_io.write_bytes / 1e6, 1) if disk_io else None,
        },
        "network": {
            "sent_mb": round(net_io.bytes_sent / 1e6, 1),
            "recv_mb": round(net_io.bytes_recv / 1e6, 1),
        },
        "system": {
            "uptime": format_uptime(uptime_seconds),
            "load_avg": load_avg,
        },
    }
