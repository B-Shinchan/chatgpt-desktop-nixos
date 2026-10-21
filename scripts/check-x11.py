#!/usr/bin/env python3
"""Check the running X11 window class inside a private Xvfb/DBus session."""

import os
import re
import signal
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = "chatgpt"
WINDOW_CLASS = "Chatgpt"


def main():
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="x11-test-", dir=cache) as temporary:
        home = Path(temporary)
        env = {
            key: value
            for key, value in os.environ.items()
            if key
            in ("PATH", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "LANG", "XAUTHORITY")
        }
        env.update(
            HOME=str(home),
            XDG_CONFIG_HOME=str(home / "config"),
            XDG_CACHE_HOME=str(home / "cache"),
            XDG_DATA_HOME=str(home / "data"),
        )
        path = home / "application.log"
        with path.open("w") as log:
            # This password backend is only for an empty unsigned-in test
            # profile, never the installed launcher or the user's profile.
            application = subprocess.Popen(
                [
                    str(ROOT / "result/bin" / PROGRAM),
                    "--ozone-platform=x11",
                    "--disable-gpu",
                    "--password-store=basic",
                    f"--user-data-dir={home / 'profile'}",
                ],
                env=env,
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
            try:
                for _ in range(300):
                    tree = subprocess.check_output(
                        ["xwininfo", "-root", "-tree"], env=env, text=True
                    )
                    for window in re.findall(r"^\s+(0x[0-9a-f]+) ", tree, re.MULTILINE):
                        info = subprocess.run(
                            ["xprop", "-id", window, "WM_CLASS"],
                            env=env,
                            text=True,
                            capture_output=True,
                            check=False,
                        )
                        if WINDOW_CLASS in re.findall(r'"([^"]+)"', info.stdout):
                            time.sleep(1)
                            if application.poll() is not None:
                                raise RuntimeError(
                                    "Application exited after creating its X11 window"
                                )
                            print(f"X11 window verified; WM_CLASS={WINDOW_CLASS}")
                            return
                    if application.poll() is not None:
                        break
                    time.sleep(0.1)
                raise RuntimeError(
                    "Expected X11 window class was not observed\n"
                    + path.read_text(errors="replace")[-3000:]
                )
            finally:
                try:
                    os.killpg(application.pid, signal.SIGTERM)
                    application.wait(timeout=5)
                except ProcessLookupError:
                    application.wait()
                except subprocess.TimeoutExpired:
                    os.killpg(application.pid, signal.SIGKILL)
                    application.wait()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            message = str(error)[-4000:]
            message = (
                message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            )
            print(f"::error::{message}", flush=True)
        raise
