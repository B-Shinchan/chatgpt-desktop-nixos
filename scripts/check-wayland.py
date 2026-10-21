#!/usr/bin/env python3
"""Verify a real Wayland surface and app ID in a private headless compositor."""

import os
import re
import signal
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = "chatgpt"
APP_ID = "chatgpt"


def stop(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
    except ProcessLookupError:
        process.wait()
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def main():
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="wayland-test-", dir=cache) as temporary:
        base = Path(temporary)
        runtime = base / "runtime"
        runtime.mkdir(mode=0o700)
        # Do not inherit account/API credentials or the user's graphical session.
        env = {
            key: value
            for key, value in os.environ.items()
            if key in ("PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "NIX_SSL_CERT_FILE")
        }
        env.update(
            HOME=str(base),
            XDG_RUNTIME_DIR=str(runtime),
            XDG_CONFIG_HOME=str(base / "config"),
            XDG_CACHE_HOME=str(base / "cache"),
            XDG_DATA_HOME=str(base / "data"),
            XDG_SESSION_TYPE="wayland",
            WAYLAND_DISPLAY="wayland-test",
        )
        weston_log = base / "weston.log"
        with weston_log.open("w") as stream:
            weston = subprocess.Popen(
                [
                    "weston",
                    "-B",
                    "headless",
                    "--renderer=pixman",
                    "--socket=wayland-test",
                    "--idle-time=0",
                    "--no-config",
                ],
                env=env,
                stdout=stream,
                stderr=stream,
                start_new_session=True,
            )
            try:
                for _ in range(100):
                    if (runtime / "wayland-test").exists():
                        break
                    if weston.poll() is not None:
                        raise RuntimeError(weston_log.read_text()[-3000:])
                    time.sleep(0.1)
                else:
                    raise RuntimeError(
                        "Headless Wayland compositor did not become ready"
                    )
                app_log = base / "application.log"
                env["WAYLAND_DEBUG"] = "1"
                with app_log.open("w") as output:
                    # The basic password backend is ONLY for this disposable,
                    # unsigned-in test profile. The installed launcher retains
                    # Secret Service storage; no sandbox is disabled here.
                    application = subprocess.Popen(
                        [
                            "dbus-run-session",
                            f"--config-file={ROOT / 'tests/dbus-session.conf'}",
                            "--",
                            str(ROOT / "result/bin" / PROGRAM),
                            "--ozone-platform=wayland",
                            "--disable-gpu",
                            "--password-store=basic",
                            f"--user-data-dir={base / 'profile'}",
                        ],
                        env=env,
                        stdout=output,
                        stderr=output,
                        start_new_session=True,
                    )
                    try:
                        for _ in range(300):
                            log = app_log.read_text(errors="replace")
                            identities = re.findall(r'set_app_id\("([^\"]+)"\)', log)
                            if APP_ID in identities:
                                time.sleep(1)
                                if application.poll() is not None:
                                    raise RuntimeError(
                                        "Application exited after creating its surface"
                                    )
                                print(f"Wayland surface verified; app_id={APP_ID}")
                                return
                            if application.poll() is not None:
                                break
                            time.sleep(0.1)
                        raise RuntimeError(
                            "Expected Wayland application ID was not observed\n"
                            + app_log.read_text(errors="replace")[-3000:]
                        )
                    finally:
                        stop(application)
            finally:
                stop(weston)


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
