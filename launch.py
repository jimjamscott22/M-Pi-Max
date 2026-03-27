#!/usr/bin/env python3
"""Small launcher for choosing M-Pi-Max web or desktop mode."""

from __future__ import annotations

import argparse
import subprocess
import sys


def run_main(extra_args: list[str]) -> None:
    """Run main.py with the current Python executable and provided args."""
    command = [sys.executable, "main.py", *extra_args]
    subprocess.run(command, check=True)


def prompt_with_default(label: str, default: str) -> str:
    value = input(f"{label} [{default}]: ").strip()
    return value or default


def run_menu() -> int:
    print("M-Pi-Max Launcher")
    print("1) Web mode (LAN dashboard)")
    print("2) Desktop mode (Tkinter)")
    print("3) Quit")

    choice = input("Choose an option [1-3]: ").strip() or "1"
    if choice == "1":
        host = prompt_with_default("Host", "0.0.0.0")
        port = prompt_with_default("Port", "8000")
        run_main(["--mode", "web", "--host", host, "--port", port])
        return 0

    if choice == "2":
        refresh_ms = prompt_with_default("Refresh interval (ms)", "2000")
        run_main(["--mode", "desktop", "--refresh-ms", refresh_ms])
        return 0

    if choice == "3":
        print("Launcher exited.")
        return 0

    print("Invalid option. Please run launch.py again.")
    return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M-Pi-Max mode launcher")
    parser.add_argument(
        "--mode",
        choices=["menu", "web", "desktop"],
        default="menu",
        help="Run launcher menu or jump directly to a mode.",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host for web mode.")
    parser.add_argument("--port", default="8000", help="Port for web mode.")
    parser.add_argument(
        "--refresh-ms",
        default="2000",
        help="Desktop refresh interval in milliseconds.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload in web mode.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.mode == "menu":
        raise SystemExit(run_menu())

    if args.mode == "web":
        web_args = ["--mode", "web", "--host", args.host, "--port", str(args.port)]
        if args.reload:
            web_args.append("--reload")
        run_main(web_args)
    else:
        run_main(["--mode", "desktop", "--refresh-ms", str(args.refresh_ms)])