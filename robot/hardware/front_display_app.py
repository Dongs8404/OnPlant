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


def build_browser_command(browser: str, url: str) -> list[str]:
    name = os.path.basename(browser)
    if "firefox" in name:
        return [browser, "--kiosk", url]
    return [
        browser,
        "--kiosk",
        "--window-position=0,0",
        "--window-size=1024,600",
        "--start-maximized",
        "--start-fullscreen",
        "--force-device-scale-factor=1",
        "--hide-scrollbars",
        "--app=" + url,
        "--noerrdialogs",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-infobars",
        "--disable-session-crashed-bubble",
        "--password-store=basic",
        "--disable-features=PasswordManagerOnboarding",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--user-data-dir=/tmp/onplant-chromium",
        "--check-for-update-interval=31536000",
        "--autoplay-policy=no-user-gesture-required",
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
