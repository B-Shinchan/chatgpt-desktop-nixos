#!/usr/bin/env python3
"""Update the pinned amd64 release from the vendor's HTTPS APT feed."""

import argparse
import base64
import json
import os
import re
import subprocess
import time
import urllib.request
from functools import cmp_to_key
from pathlib import Path

PACKAGE = "chatgpt"
BASE_URL = "https://persistent.oaistatic.com/codex-app-prod/linux/deb"
INDEX_URL = BASE_URL + "/dists/stable/main/binary-amd64/Packages"
ROOT = Path(__file__).resolve().parents[1]


def compare_versions(left, right):
    for operator, result in (("lt", -1), ("gt", 1)):
        code = subprocess.run(
            ["dpkg", "--compare-versions", left, operator, right], check=False
        ).returncode
        if code == 0:
            return result
        if code != 1:
            raise ValueError("dpkg rejected an upstream version")
    return 0


def select_release(data):
    releases = []
    for block in re.split(r"\n\s*\n", data.strip()):
        fields = dict(
            line.split(": ", 1)
            for line in block.splitlines()
            if ": " in line and not line[0].isspace()
        )
        if fields.get("Package") != PACKAGE or fields.get("Architecture") != "amd64":
            continue
        version = fields.get("Version", "")
        digest = fields.get("SHA256", "")
        if not re.fullmatch(r"[0-9][0-9A-Za-z.+:~_-]*", version):
            raise ValueError("Missing or invalid version in vendor metadata")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise ValueError("Missing or invalid SHA256 in vendor metadata")
        expected = f"pool/main/{PACKAGE[0]}/{PACKAGE}/{PACKAGE}_{version}_amd64.deb"
        if fields.get("Filename") != expected:
            raise ValueError(
                "Vendor download layout changed; review packaging before updating"
            )
        sri = "sha256-" + base64.b64encode(bytes.fromhex(digest)).decode()
        releases.append((version, sri))
    if not releases:
        raise ValueError(f"No amd64 {PACKAGE} releases in vendor metadata")
    latest = max(releases, key=cmp_to_key(lambda a, b: compare_versions(a[0], b[0])))
    if any(ver == latest[0] and sha != latest[1] for ver, sha in releases):
        raise ValueError("Conflicting hashes for the latest version")
    return latest


def validate_release(version, digest):
    if not re.fullmatch(r"[0-9][0-9A-Za-z.+:~_-]*", version):
        raise ValueError("Invalid release version")
    if not re.fullmatch(r"sha256-[A-Za-z0-9+/]{43}=", digest):
        raise ValueError("Invalid release hash")
    decoded = base64.b64decode(digest[7:], validate=True)
    if len(decoded) != 32 or base64.b64encode(decoded).decode() != digest[7:]:
        raise ValueError("Invalid SHA256 length")


def update_content(content, release):
    version, digest = release
    validate_release(version, digest)
    current = re.findall(r'^  version = "([^"]+)";$', content, re.M)
    hashes = re.findall(r'^    hash = "(sha256-[^"]+)";$', content, re.M)
    if len(current) != 1 or len(hashes) != 1:
        raise ValueError("Expected exactly one pinned version and source hash")
    if compare_versions(version, current[0]) < 0:
        raise ValueError(f"Refusing upstream downgrade from {current[0]} to {version}")
    content = re.sub(
        r'^  version = "[^"]+";$', f'  version = "{version}";', content, flags=re.M
    )
    return re.sub(
        r'^    hash = "sha256-[^"]+";$', f'    hash = "{digest}";', content, flags=re.M
    )


def fetch_index():
    request = urllib.request.Request(
        INDEX_URL, headers={"User-Agent": "NixOS-package-updater/1.0"}
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read().decode("utf-8")
        except (OSError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(2**attempt)


def validate_lock(original, candidate):
    """Permit only a forward pin change of the existing official Nixpkgs input."""
    expected = json.loads(json.dumps(original))
    locked = candidate["nodes"]["nixpkgs"]["locked"]
    if set(locked) != {"type", "owner", "repo", "rev", "narHash", "lastModified"}:
        raise ValueError("Unexpected Nixpkgs lock fields")
    if (locked["type"], locked["owner"], locked["repo"]) != (
        "github",
        "NixOS",
        "nixpkgs",
    ):
        raise ValueError("Only the official NixOS/nixpkgs input may be refreshed")
    if not re.fullmatch(r"[0-9a-f]{40}", locked["rev"]):
        raise ValueError("Invalid Nixpkgs revision")
    validate_release("0", locked["narHash"])
    timestamp = locked["lastModified"]
    if (
        type(timestamp) is not int
        or timestamp < original["nodes"]["nixpkgs"]["locked"]["lastModified"]
        or timestamp > time.time() + 86400
    ):
        raise ValueError("Invalid or backwards Nixpkgs timestamp")
    expected["nodes"]["nixpkgs"]["locked"] = locked
    if candidate != expected:
        raise ValueError("Lock update changed inputs or fields outside the Nixpkgs pin")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate",
        type=Path,
        help="Write validated pin metadata for the publish job",
    )
    parser.add_argument(
        "--apply-candidate",
        type=Path,
        help="Apply validated metadata without executing an application",
    )
    parser.add_argument(
        "--include-lock",
        action="store_true",
        help="Include an audited official Nixpkgs lock refresh",
    )
    args = parser.parse_args()
    lock_path = ROOT / "flake.lock"
    lock_update = None
    lock_changed = False
    if args.apply_candidate:
        candidate = json.loads(args.apply_candidate.read_text())
        if (
            not isinstance(candidate, dict)
            or not {"version", "hash"} <= set(candidate)
            or set(candidate) - {"version", "hash", "nixpkgs_lock"}
        ):
            raise ValueError("Unexpected candidate metadata")
        release = candidate["version"], candidate["hash"]
        if "nixpkgs_lock" in candidate:
            original_lock = json.loads(lock_path.read_text())
            lock_update = candidate["nixpkgs_lock"]
            validate_lock(original_lock, lock_update)
            lock_changed = original_lock != lock_update
    else:
        release = select_release(fetch_index())
        if args.include_lock:
            original_lock = json.loads(
                subprocess.check_output(
                    ["git", "show", "HEAD:flake.lock"], cwd=ROOT, text=True
                )
            )
            lock_update = json.loads(lock_path.read_text())
            validate_lock(original_lock, lock_update)
            lock_changed = original_lock != lock_update
    path = ROOT / "package.nix"
    original = path.read_text()
    updated = update_content(original, release)
    changed = original != updated or lock_changed
    if original != updated:
        path.write_text(updated)
    if args.apply_candidate and lock_changed:
        lock_path.write_text(json.dumps(lock_update, indent=2) + "\n")
    if args.candidate:
        candidate = {"version": release[0], "hash": release[1]}
        if lock_changed:
            candidate["nixpkgs_lock"] = lock_update
        args.candidate.write_text(json.dumps(candidate) + "\n")
    print(f"Vendor release: {release[0]}; package changed: {changed}")
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a") as stream:
            stream.write(f"has_update={str(changed).lower()}\nversion={release[0]}\n")


if __name__ == "__main__":
    main()
