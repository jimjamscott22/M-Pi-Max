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

    # --- Custom Progress Bar Widget ---
    class ProgressBar(tk.Canvas):
        """A custom Canvas-based progress bar with percentage and absolute value."""
        def __init__(self, parent, width=200, height=24, **kwargs):
            super().__init__(parent, width=width, height=height, bg="#3b4252", bd=0, highlightthickness=0, **kwargs)
            self.width = width
            self.height = height
            self.percent = 0
            self.absolute_text = ""
            self.bind("<Configure>", self._on_configure)

        def set_value(self, percent: float, absolute_text: str = ""):
            """Update the progress bar value and optional absolute text."""
            self.percent = min(100, max(0, percent))
            self.absolute_text = absolute_text
            self.draw()

        def _on_configure(self, event):
            """Redraw when widget is resized."""
            self.width = event.width
            self.height = event.height
            self.draw()

        def draw(self):
            """Render the progress bar."""
            self.delete("all")
            
            # Determine color based on percentage
            if self.percent >= 85:
                bar_color = "#bf616a"  # Nord11 red
            elif self.percent >= 70:
                bar_color = "#ebcb8b"  # Nord13 yellow
            else:
                bar_color = "#88c0d0"  # Nord8 blue
            
            # Draw background
            self.create_rectangle(2, 2, self.width - 2, self.height - 2, fill="#2a2a2a", outline="#4c566a", width=1)
            
            # Draw filled bar
            bar_width = (self.percent / 100.0) * (self.width - 4)
            if bar_width > 0:
                self.create_rectangle(2, 2, 2 + bar_width, self.height - 2, fill=bar_color, outline="")
            
            # Draw percentage text (centered)
            percent_text = f"{self.percent:.0f}%"
            self.create_text(
                self.width / 2, self.height / 2,
                text=percent_text,
                font=("TkFixedFont", 9, "bold"),
                fill="#d8dee9",
                anchor="center"
            )
            
            # Draw absolute value text (right-aligned) if provided
            if self.absolute_text:
                self.create_text(
                    self.width - 6, self.height / 2,
                    text=self.absolute_text,
                    font=("TkFixedFont", 7),
                    fill="#93a1a1",
                    anchor="e"
                )

    root = tk.Tk()
    root.title("M-Pi-Max Desktop")
    root.geometry("900x650")
    
    # Apply Nord Theme
    bg_color = "#2e3440"  # Nord0
    card_bg = "#3b4252"   # Nord1
    fg_color = "#d8dee9"  # Nord4
    accent_color = "#88c0d0"  # Nord8
    
    root.configure(bg=bg_color)

    style = ttk.Style()
    style.theme_use('clam')
    style.configure("TFrame", background=bg_color)
    style.configure("TLabel", background=bg_color, foreground=fg_color)
    style.configure("Title.TLabel", font=("TkDefaultFont", 16, "bold"), foreground=accent_color)
    style.configure("CardTitle.TLabel", font=("TkDefaultFont", 11, "bold"), foreground=accent_color)
    style.configure("Header.TLabel", font=("TkDefaultFont", 9), foreground=fg_color)
    style.configure("Value.TLabel", font=("TkFixedFont", 9), foreground="#a3be8c")
    style.configure("Card.TLabelframe", background=card_bg, foreground=fg_color)
    style.configure("Card.TLabelframe.Label", background=card_bg, foreground=accent_color, font=("TkDefaultFont", 10, "bold"))

    # Main scrollable frame
    canvas = tk.Canvas(root, bg=bg_color, bd=0, highlightthickness=0)
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    title = ttk.Label(scrollable_frame, text="M-Pi-Max Desktop Monitor", style="Title.TLabel")
    title.pack(pady=(10, 15), padx=15)

    # --- CPU Card ---
    cpu_card = ttk.LabelFrame(scrollable_frame, text="CPU", style="Card.TLabelframe", padding=10)
    cpu_card.pack(fill="x", padx=15, pady=(0, 10))

    cpu_usage_frame = ttk.Frame(cpu_card)
    cpu_usage_frame.pack(fill="x", pady=5)
    ttk.Label(cpu_usage_frame, text="Usage:", style="Header.TLabel").pack(side="left", padx=(0, 8))
    cpu_bar = ProgressBar(cpu_usage_frame, width=200, height=22)
    cpu_bar.pack(side="left", padx=(0, 10))

    cpu_freq_label = ttk.Label(cpu_card, text="Frequency: --", style="Value.TLabel")
    cpu_freq_label.pack(anchor="w", pady=2)
    cpu_temp_label = ttk.Label(cpu_card, text="Temperature: --", style="Value.TLabel")
    cpu_temp_label.pack(anchor="w", pady=2)
    cpu_throttle_label = ttk.Label(cpu_card, text="Throttle: --", style="Value.TLabel")
    cpu_throttle_label.pack(anchor="w", pady=2)
    cpu_percore_label = ttk.Label(cpu_card, text="Per-Core: --", style="Value.TLabel")
    cpu_percore_label.pack(anchor="w", pady=2)

    # --- Memory Card ---
    mem_card = ttk.LabelFrame(scrollable_frame, text="Memory", style="Card.TLabelframe", padding=10)
    mem_card.pack(fill="x", padx=15, pady=(0, 10))

    ram_frame = ttk.Frame(mem_card)
    ram_frame.pack(fill="x", pady=5)
    ttk.Label(ram_frame, text="RAM:", style="Header.TLabel").pack(side="left", padx=(0, 8))
    ram_bar = ProgressBar(ram_frame, width=200, height=22)
    ram_bar.pack(side="left", padx=(0, 10))

    swap_frame = ttk.Frame(mem_card)
    swap_frame.pack(fill="x", pady=5)
    ttk.Label(swap_frame, text="Swap:", style="Header.TLabel").pack(side="left", padx=(0, 8))
    swap_bar = ProgressBar(swap_frame, width=200, height=22)
    swap_bar.pack(side="left", padx=(0, 10))

    # --- Disk Card ---
    disk_card = ttk.LabelFrame(scrollable_frame, text="Disk & I/O", style="Card.TLabelframe", padding=10)
    disk_card.pack(fill="x", padx=15, pady=(0, 10))

    disk_frame = ttk.Frame(disk_card)
    disk_frame.pack(fill="x", pady=5)
    ttk.Label(disk_frame, text="Usage:", style="Header.TLabel").pack(side="left", padx=(0, 8))
    disk_bar = ProgressBar(disk_frame, width=200, height=22)
    disk_bar.pack(side="left", padx=(0, 10))

    disk_io_label = ttk.Label(disk_card, text="I/O: --", style="Value.TLabel")
    disk_io_label.pack(anchor="w", pady=2)

    # --- Network Card ---
    net_card = ttk.LabelFrame(scrollable_frame, text="Network", style="Card.TLabelframe", padding=10)
    net_card.pack(fill="x", padx=15, pady=(0, 10))

    net_sent_label = ttk.Label(net_card, text="Sent: --", style="Value.TLabel")
    net_sent_label.pack(anchor="w", pady=2)
    net_recv_label = ttk.Label(net_card, text="Received: --", style="Value.TLabel")
    net_recv_label.pack(anchor="w", pady=2)

    # --- System Card ---
    sys_card = ttk.LabelFrame(scrollable_frame, text="System", style="Card.TLabelframe", padding=10)
    sys_card.pack(fill="x", padx=15, pady=(0, 10))

    uptime_label = ttk.Label(sys_card, text="Uptime: --", style="Value.TLabel")
    uptime_label.pack(anchor="w", pady=2)
    load_label = ttk.Label(sys_card, text="Load Avg: --", style="Value.TLabel")
    load_label.pack(anchor="w", pady=2)

    # --- Status Bar ---
    status = ttk.Label(scrollable_frame, text="Refreshing...", foreground="#4c566a")
    status.pack(pady=(15, 10), padx=15)

    def refresh() -> None:
        try:
            stats = collect_stats(cpu_interval=0.2)
            
            # CPU
            cpu_bar.set_value(stats['cpu']['percent'])
            cpu_freq_label.config(text=f"Frequency: {stats['cpu']['freq_mhz']} MHz")
            temp = stats['cpu']['temp_c']
            cpu_temp_label.config(text=f"Temperature: {temp} °C" if temp is not None else "Temperature: unavailable")
            cpu_throttle_label.config(text=f"Throttle: {stats['cpu']['throttled']}")
            per_core = ", ".join(f"{x:.1f}%" for x in stats['cpu']['per_core'])
            cpu_percore_label.config(text=f"Per-Core: {per_core}")
            
            # Memory
            ram_bar.set_value(stats['memory']['percent'], f"{stats['memory']['used_gb']}/{stats['memory']['total_gb']} GB")
            swap_bar.set_value(stats['swap']['percent'], f"{stats['swap']['used_gb']}/{stats['swap']['total_gb']} GB")
            
            # Disk
            disk_bar.set_value(stats['disk']['percent'], f"{stats['disk']['used_gb']}/{stats['disk']['total_gb']} GB")
            disk_io_label.config(text=f"I/O: Read {stats['disk']['read_mb']} MB, Write {stats['disk']['write_mb']} MB")
            
            # Network
            net_sent_label.config(text=f"Sent: {stats['network']['sent_mb']} MB")
            net_recv_label.config(text=f"Received: {stats['network']['recv_mb']} MB")
            
            # System
            uptime_label.config(text=f"Uptime: {stats['system']['uptime']}")
            load_label.config(text=f"Load Avg: {', '.join(str(x) for x in stats['system']['load_avg'])}")
            
            status.config(text=f"Last update: {time.strftime('%H:%M:%S')}", foreground="#a3be8c")
        except Exception as exc:
            status.config(text=f"Update failed: {exc}", foreground="#bf616a")
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
