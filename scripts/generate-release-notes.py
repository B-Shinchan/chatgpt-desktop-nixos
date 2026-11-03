#!/usr/bin/env python3
"""Generate structured GitHub Release notes for ChatGPT Desktop on NixOS."""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_FILE = ROOT / "package.nix"


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else ""
    if not PACKAGE_FILE.exists():
        sys.exit(f"Error: {PACKAGE_FILE} not found")

    content = PACKAGE_FILE.read_text()

    # Extract version
    version_match = re.search(r'version = "([^"]+)";', content)
    version = version_match.group(1) if version_match else "unknown"

    # Extract hash
    hash_match = re.search(r'hash = "(sha256-[^"]+)";', content)
    sri_hash = hash_match.group(1) if hash_match else "unknown"

    # Vendor deb URL
    url = f"https://persistent.oaistatic.com/codex-app-prod/linux/deb/pool/main/c/chatgpt/chatgpt_{version}_amd64.deb"

    if not tag:
        tag = f"v{version}"

    # Determine title
    rev_match = re.search(r"-([0-9]+)$", tag)
    if rev_match:
        title = f"ChatGPT Desktop v{version} (Packaging Revision {rev_match.group(1)})"
    else:
        title = f"ChatGPT Desktop v{version} (NixOS Release)"

    body = f"""### OpenAI ChatGPT Desktop `{version}`

Official OpenAI ChatGPT Linux desktop application packaged natively for NixOS.

#### Upstream Artifact Details

| Property | Value |
| :--- | :--- |
| **Application** | ChatGPT Desktop |
| **Upstream Version** | `{version}` |
| **Upstream Source** | [Official OpenAI APT Debian Repository]({url}) |
| **Architecture** | `amd64` (`x86_64-linux`) |
| **Source SRI Hash** | `{sri_hash}` |

#### Automated CI Verification

- **Flake Evaluation**: Verified Flake outputs and Nix formatting (`nix flake check`)
- **Package Build**: Compiled sandboxed FHS derivation with embedded Codex/CUA helper tools (`nix build`)
- **Desktop Integration**: Validated XDG desktop entry (`chatgpt.desktop`) and icon specification
- **Wayland Window Matching**: Verified Wayland app ID, window identity, and Weston compositor compatibility

#### Installation & Pinning

##### Immediate Run
```bash
nix run github:B-Shinchan/chatgpt-desktop-nixos/{tag}
```

##### Flake Input (`flake.nix`)
Pin this specific release in your system flake:
```nix
inputs.chatgpt-desktop.url = "github:B-Shinchan/chatgpt-desktop-nixos/{tag}";
```

##### NixOS Module (`configuration.nix`)
```nix
imports = [ inputs.chatgpt-desktop.nixosModules.default ];
programs.chatgpt-desktop.enable = true;
```

##### Home Manager (`home.nix`)
```nix
home.packages = [
  inputs.chatgpt-desktop.packages.${{pkgs.stdenv.hostPlatform.system}}.default
];
```

---
> [!NOTE]
> **Independent Community Packaging**: This project provides independent Nix expressions packaging OpenAI's official vendor binaries. It is not affiliated with, sponsored by, or endorsed by OpenAI.
"""

    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a") as f:
            f.write(f"title={title}\n")

    print(body.strip())


if __name__ == "__main__":
    main()
