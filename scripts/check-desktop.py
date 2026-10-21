#!/usr/bin/env python3
"""Check installed desktop entries and icon assets without a graphical session."""

import configparser
import shlex
import struct
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
entry_name = "chatgpt.desktop"
application_name = "ChatGPT"
launcher = root / "bin/chatgpt"
entries = sorted((root / "share/applications").glob("*.desktop"))
assert [p.name for p in entries] == [entry_name], (
    "Missing or duplicate application launcher"
)
entry = entries[0]
subprocess.run(["desktop-file-validate", str(entry)], check=True)
config = configparser.ConfigParser(interpolation=None, strict=True)
config.optionxform = str
config.read(entry)
main = config["Desktop Entry"]
assert main["StartupWMClass"] == "Chatgpt"
assert main["Name"] == application_name
assert main["Type"] == "Application"
assert main["Categories"] == "Utility;", "Use one main application-menu category"
assert "%U" in shlex.split(main["Exec"]), (
    "URI/file arguments must reach the application"
)
assert launcher.is_file() and launcher.stat().st_mode & 0o111, (
    "Launcher is not executable"
)
for section in config.sections():
    if "Exec" in config[section]:
        assert shlex.split(config[section]["Exec"])[0] == str(launcher), (
            "Desktop action bypasses packaged launcher"
        )
mimes = main.get("MimeType", "").split(";")
assert "x-scheme-handler/chatgpt" in mimes
assert "x-scheme-handler/http" not in mimes and "x-scheme-handler/https" not in mimes
icon = main["Icon"]
assert "/" not in icon, "Prefer a theme icon name"
icons = [
    p for p in (root / "share").rglob("*") if p.name in (icon + ".png", icon + ".svg")
]
assert icons, f"Missing icon: {icon}"
for path in icons:
    assert path.is_file(), f"Broken icon: {path}"
    if path.suffix == ".png" and "x" in path.parent.parent.name:
        dimensions = path.parent.parent.name.split("x")
        if all(d.isdigit() for d in dimensions):
            with path.open("rb") as stream:
                header = stream.read(24)
            assert header[:8] == b"\x89PNG\r\n\x1a\n"
            assert struct.unpack(">II", header[16:24]) == tuple(map(int, dimensions)), (
                f"Wrong icon dimensions: {path}"
            )
for path in (root / "share").rglob("*"):
    assert not path.is_symlink() or path.exists(), (
        f"Broken desktop asset symlink: {path}"
    )
print(
    f"Validated {application_name} launcher, desktop actions, URI schemes, and icon assets"
)
