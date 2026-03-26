import argparse
import os
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


def collect_stats(cpu_interval: float = 0.5) -> dict:
    """Collect a single snapshot of all metrics used by both UI modes."""
    cpu_percent = psutil.cpu_percent(interval=cpu_interval)
    cpu_freq = psutil.cpu_freq()
    cpu_freq_mhz = round(cpu_freq.current) if cpu_freq else None

    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    disk_io = psutil.disk_io_counters()
    net_io = psutil.net_io_counters()
    uptime_seconds = time.time() - psutil.boot_time()
    load_avg = [round(x, 2) for x in psutil.getloadavg()]

    return {
        "cpu": {
            "percent": cpu_percent,
            "per_core": psutil.cpu_percent(percpu=True),
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


def run_desktop(refresh_ms: int = 2000) -> None:
    """Run a local Tkinter dashboard for desktop Linux/Windows sessions."""
    try:
        import tkinter as tk
        from tkinter import ttk
    except ImportError as exc:
        raise RuntimeError("Tkinter is not available in this Python install.") from exc

    has_display = os.name == "nt" or bool(
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    )
    if not has_display:
        raise RuntimeError(
            "No graphical session detected. Use --mode web on headless devices."
        )

    root = tk.Tk()
    root.title("M-Pi-Max Desktop")
    root.geometry("760x440")

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)

    title = ttk.Label(frame, text="M-Pi-Max Desktop Monitor", font=("TkDefaultFont", 16, "bold"))
    title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

    labels: dict[str, ttk.Label] = {}
    rows = [
        ("CPU Usage", "cpu_percent"),
        ("CPU Frequency", "cpu_freq"),
        ("CPU Temperature", "cpu_temp"),
        ("CPU Throttle", "cpu_throttle"),
        ("Per-Core Usage", "per_core"),
        ("RAM", "ram"),
        ("Swap", "swap"),
        ("Disk", "disk"),
        ("Disk I/O", "disk_io"),
        ("Network", "network"),
        ("Load Avg", "load_avg"),
        ("Uptime", "uptime"),
    ]

    for index, (name, key) in enumerate(rows, start=1):
        label_name = ttk.Label(frame, text=f"{name}:", font=("TkDefaultFont", 10, "bold"))
        label_name.grid(row=index, column=0, sticky="nw", padx=(0, 12), pady=3)
        value_label = ttk.Label(frame, text="--", justify="left", wraplength=520)
        value_label.grid(row=index, column=1, sticky="nw", pady=3)
        labels[key] = value_label

    status = ttk.Label(frame, text="Refreshing...", foreground="#555555")
    status.grid(row=len(rows) + 1, column=0, columnspan=2, sticky="w", pady=(14, 0))

    def refresh() -> None:
        try:
            stats = collect_stats(cpu_interval=0.2)
            labels["cpu_percent"].config(text=f"{stats['cpu']['percent']}%")
            labels["cpu_freq"].config(text=f"{stats['cpu']['freq_mhz']} MHz")

            temp = stats["cpu"]["temp_c"]
            labels["cpu_temp"].config(text=f"{temp} C" if temp is not None else "unavailable")
            labels["cpu_throttle"].config(text=stats["cpu"]["throttled"])

            per_core = ", ".join(f"{x:.1f}%" for x in stats["cpu"]["per_core"])
            labels["per_core"].config(text=per_core)

            labels["ram"].config(
                text=(
                    f"{stats['memory']['used_gb']} / {stats['memory']['total_gb']} GB "
                    f"({stats['memory']['percent']}%)"
                )
            )
            labels["swap"].config(
                text=(
                    f"{stats['swap']['used_gb']} / {stats['swap']['total_gb']} GB "
                    f"({stats['swap']['percent']}%)"
                )
            )
            labels["disk"].config(
                text=(
                    f"{stats['disk']['used_gb']} / {stats['disk']['total_gb']} GB "
                    f"({stats['disk']['percent']}%)"
                )
            )
            labels["disk_io"].config(
                text=(
                    f"Read {stats['disk']['read_mb']} MB, "
                    f"Write {stats['disk']['write_mb']} MB"
                )
            )
            labels["network"].config(
                text=(
                    f"Sent {stats['network']['sent_mb']} MB, "
                    f"Recv {stats['network']['recv_mb']} MB"
                )
            )

            labels["load_avg"].config(text=", ".join(str(x) for x in stats["system"]["load_avg"]))
            labels["uptime"].config(text=stats["system"]["uptime"])
            status.config(text=f"Last update: {time.strftime('%H:%M:%S')}", foreground="#2E7D32")
        except Exception as exc:  # Keep UI alive even if one sample fails.
            status.config(text=f"Update failed: {exc}", foreground="#B00020")
        finally:
            root.after(refresh_ms, refresh)

    refresh()
    root.mainloop()


def run_web(host: str, port: int, reload: bool) -> None:
    """Launch the existing FastAPI dashboard server."""
    import uvicorn

    uvicorn.run("main:app", host=host, port=port, reload=reload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M-Pi-Max system monitor")
    parser.add_argument(
        "--mode",
        choices=["web", "desktop"],
        default="web",
        help="Run as LAN web dashboard or local desktop app.",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host for web mode.")
    parser.add_argument("--port", type=int, default=8000, help="Port for web mode.")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload in web mode during development.",
    )
    parser.add_argument(
        "--refresh-ms",
        type=int,
        default=2000,
        help="Desktop refresh interval in milliseconds.",
    )
    return parser.parse_args()


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

    return collect_stats(cpu_interval=0.5)


if __name__ == "__main__":
    args = parse_args()
    if args.mode == "desktop":
        run_desktop(refresh_ms=args.refresh_ms)
    else:
        run_web(host=args.host, port=args.port, reload=args.reload)
