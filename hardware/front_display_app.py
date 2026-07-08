from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


def wait_for_server(base_url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    health_url = f"{base_url.rstrip('/')}/api/health"
    while time.monotonic() < deadline:
        try:
            with urlopen(health_url, timeout=3) as response:
                if response.status == 200:
                    return
        except (OSError, URLError):
            time.sleep(1)
    raise RuntimeError(f"server is not reachable: {health_url}")


def find_browser() -> str:
    candidates = [
        "chromium-browser",
        "chromium",
        "google-chrome",
        "firefox",
    ]
    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
    raise RuntimeError("no browser found. Install chromium-browser on Raspberry Pi.")


def detect_screen_size() -> tuple[int, int]:
    env_size = os.getenv("ONPLANT_DISPLAY_SIZE", "").strip().lower()
    if "x" in env_size:
        width, height = env_size.split("x", 1)
        if width.isdigit() and height.isdigit():
            return int(width), int(height)

    commands = [
        ["xrandr", "--current"],
        ["wlr-randr"],
        ["xdpyinfo"],
    ]
    for command in commands:
        if not shutil.which(command[0]):
            continue
        try:
            output = subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL, timeout=2)
        except (OSError, subprocess.SubprocessError):
            continue
        for line in output.splitlines():
            if "*" in line and "x" in line:
                token = line.strip().split()[0]
                if "x" in token:
                    width, height = token.split("x", 1)
                    if width.isdigit() and height.isdigit():
                        return int(width), int(height)
            if "dimensions:" in line and "x" in line:
                token = line.split("dimensions:", 1)[1].strip().split()[0]
                width, height = token.split("x", 1)
                if width.isdigit() and height.isdigit():
                    return int(width), int(height)
    return 1024, 600


def build_browser_command(browser: str, url: str) -> list[str]:
    name = os.path.basename(browser)
    if "firefox" in name:
        return [browser, "--kiosk", url]
    width, height = detect_screen_size()
    return [
        browser,
        "--kiosk",
        "--app=" + url,
        "--window-position=0,0",
        f"--window-size={width},{height}",
        "--start-maximized",
        "--force-device-scale-factor=1",
        "--noerrdialogs",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-infobars",
        "--disable-session-crashed-bubble",
        "--hide-scrollbars",
        "--password-store=basic",
        "--disable-features=PasswordManagerOnboarding",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--user-data-dir=/tmp/onplant-chromium",
        "--check-for-update-interval=31536000",
        "--autoplay-policy=no-user-gesture-required",
        "--start-fullscreen",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Open OnPlant 5-inch display UI in kiosk mode.")
    parser.add_argument("--server", default=os.getenv("ONPLANT_SERVER", "http://192.168.100.198:5050"))
    parser.add_argument("--robot-id", default=os.getenv("ONPLANT_ROBOT_ID", "raspbot-a"))
    parser.add_argument("--wait", type=float, default=30.0)
    parser.add_argument("--no-wait", action="store_true")
    args = parser.parse_args()

    base_url = args.server.rstrip("/")
    display_url = f"{base_url}/display?robot_id={args.robot_id}"

    if not args.no_wait:
        wait_for_server(base_url, args.wait)

    browser = find_browser()
    command = build_browser_command(browser, display_url)
    print("opening display:", display_url)
    return subprocess.call(command)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"front display failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
