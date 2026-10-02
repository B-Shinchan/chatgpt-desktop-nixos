# ChatGPT Desktop on NixOS

[![Nix Flake](https://img.shields.io/badge/Nix_Flake-blue?logo=nixos&logoColor=white)](https://nixos.org)
[![Platform](https://img.shields.io/badge/Platform-x86__64--linux-lightgrey?logo=linux&logoColor=white)](https://nixos.org)
[![Wayland Ready](https://img.shields.io/badge/Wayland-Ready-green?logo=wayland&logoColor=white)](https://wayland.freedesktop.org/)
[![Packaging License: MIT](https://img.shields.io/badge/Packaging_License-MIT-yellow.svg)](./LICENSE)

Repackaging of OpenAI's official ChatGPT Linux desktop (`.deb`) application for NixOS, featuring out-of-the-box native Wayland rendering, GNOME Keyring Secret Service persistence across Wayland compositors (Niri, Hyprland, Sway), sanitized MIME protocol associations, and uncorrupted static-PIE execution for the bundled Codex backend daemon.

---

## Architecture: Problems & Solutions

OpenAI distributes the official ChatGPT desktop Linux application as an `x86_64` Debian archive tailored for standard FHS distributions (Ubuntu/Debian). On NixOS, several critical architectural issues arise:

### 1. Static-PIE ELF Corruption by `autoPatchelfHook`
- **Problem**: Upstream bundles static-PIE binaries under `usr/lib/chatgpt/resources/`:
  - `codex` (the core Codex daemon and CLI)
  - `codex-code-mode-host` (code execution helper host)
  - `rg` (bundled Ripgrep binary)
  - `tectonic/tectonic` (bundled LaTeX compiler)
  - `cua_node/bin/node_repl` (the Code Mode REPL MCP stdio server used when editing local files and running code)
  Because static-PIE executables do not contain an ELF interpreter (`.interp`) but have ELF type `ET_DYN`, standard `autoPatchelfHook` treats them as shared libraries. It alters their program headers, inserts a broken `PT_DYNAMIC` segment, and invalidates memory segment offsets. This causes immediate **SIGSEGV (exit code 139)** whenever the Electron app invokes `codex` or `node_repl`, manifesting as the **"Organization Settings"** startup crash or silent crashes during file editing.
- **Solution**: The derivation caches the uncorrupted static-PIE binaries during `installPhase` and registers a hook into `postFixupHooks` via `preFixup`. This hook executes strictly *after* `autoPatchelfPostFixup`, restoring the original, untouched static binaries. The derivation also runs an `installCheckPhase` during build time to guarantee `codex`, `rg`, `tectonic`, `node`, and `node_repl` execute cleanly without crashes.

### 2. File Chooser & GSettings Schema Safety
- **Problem**: Opening a directory or workspace folder prompts GTK's native file chooser dialog. On standalone Wayland compositors (Niri, Hyprland, Sway), missing GSettings schema directories in `XDG_DATA_DIRS` causes GLib to abort (`GLib-GIO-ERROR: No GSettings schemas are installed on the system`).
- **Solution**: Injects `gsettings-desktop-schemas` and `gtk3` schemas directly into `XDG_DATA_DIRS`, ensuring file and folder selection dialogs open reliably without crashing.

### 3. Workspace Git & File Management Integration
- **Problem**: When attaching local folders or projects to ChatGPT/Codex, the backend relies on `git` and `diff` to discover repository structure, track modifications, and compute unified diffs.
- **Solution**: The wrapper pre-populates `git` and `diffutils` in runtime `PATH`, ensuring flawless local file editing, Git status tracking, and workspace operations.

### 4. Rogue Browser Protocol Hijacking
- **Problem**: The upstream `chatgpt.desktop` entry includes `x-scheme-handler/http;` and `x-scheme-handler/https;` in its `MimeType` definition. On many Linux desktop environments, installing the package can hijack the user's default web browser, causing external HTTP/HTTPS links to open inside ChatGPT instead of the browser.
- **Solution**: The derivation sanitizes the desktop entry by stripping out HTTP and HTTPS scheme handlers, retaining only `x-scheme-handler/chatgpt;` and `x-scheme-handler/codex;`.

### 5. Keyring Failures on Non-GNOME Wayland Compositors
- **Problem**: On standalone Wayland compositors (Niri, Hyprland, Sway), Electron often fails to discover a Secret Service provider, falling back to an ephemeral memory store and losing user authentication upon closing the app.
- **Solution**: Enforced `--password-store=gnome-libsecret` via binary wrapper flags, ensuring reliable credential storage backed by standard FreeDesktop Secret Service implementations (`gnome-keyring` or KeePassXC).

### 6. Root TLS / SSL Certificate Trust
- **Problem**: The bundled `codex` agent server and Electron background services communicate with OpenAI authentication endpoints (`auth.openai.com`) and WebSockets (`chatgpt.com`). On NixOS, standard `/etc/ssl/certs` paths may not exist if not explicitly configured.
- **Solution**: The wrapper explicitly injects `SSL_CERT_FILE` and `NIX_SSL_CERT_FILE` pointing to `cacert` (`/etc/ssl/certs/ca-bundle.crt`).

### 7. Native Wayland & Hardware Acceleration
- **Problem**: Default Electron flags launch under XWayland with blurred window scaling and lack of client-side decorations.
- **Solution**: Pre-configured flags `--ozone-platform-hint=auto --enable-features=WaylandWindowDecorations` ensure crisp native Wayland surfaces, and `addDriverRunpath` injects dynamic OpenGL/Vulkan driver paths (`libglvnd`, `mesa`).

---

## Feature Matrix

| Feature | Status | Implementation Details |
| :--- | :---: | :--- |
| **Core Desktop Chat** | **Supported** | Full Electron runtime parity with the official `.deb` release. |
| **Codex Daemon (`app-server`)** | **Supported** | Pristine static-PIE execution; avoids patchelf memory layout corruption. |
| **Code Mode REPL (`node_repl`)** | **Supported** | Bundled MCP stdio server preserved intact for code execution and file editing. |
| **Folder & File Pickers** | **Supported** | Hardened with `gsettings-desktop-schemas` and `gtk3` in `XDG_DATA_DIRS`. |
| **Workspace Git Integration** | **Supported** | `git` and `diffutils` bundled in runtime `PATH` for project tracking. |
| **LaTeX Compilation (`tectonic`)** | **Supported** | Bundled static Tectonic compiler verified and functional. |
| **Native Wayland & DMA-BUF** | **Supported** | Configured with `--ozone-platform-hint=auto --enable-features=WaylandWindowDecorations`. |
| **OAuth `chatgpt://` Callbacks** | **Supported** | Registered via desktop integration; `xdg-utils` injected into runtime `PATH`. |
| **Secret Storage Persistence** | **Supported** | FreeDesktop Secret Service integration via `--password-store=gnome-libsecret`. |
| **Browser Security (No Hijack)** | **Supported** | Stripped rogue `http`/`https` scheme handlers; default web browser remains intact. |
| **TLS/SSL Certificate Trust** | **Supported** | Root certificates provisioned via Nixpkgs `cacert` (`SSL_CERT_FILE`). |
| **Hardware Video & Graphics** | **Supported** | Driver runpaths injected via `addDriverRunpath` (`libglvnd`, `mesa`). |

---

## Quickstart / Ad-hoc Usage

Execute directly without modifying your system configuration:

```bash
nix run github:B-Shinchan/chatgpt-desktop-nixos
```

Or test in a temporary shell:

```bash
nix shell github:B-Shinchan/chatgpt-desktop-nixos -c chatgpt
```

---

## Declarative NixOS Integration

### 1. Flake Inputs
Add `chatgpt-desktop-nixos` to your system `flake.nix`:

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    chatgpt-desktop.url = "github:B-Shinchan/chatgpt-desktop-nixos";
    # Ensure inputs.chatgpt-desktop.inputs.nixpkgs follows your system nixpkgs if desired:
    # chatgpt-desktop.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, chatgpt-desktop, ... }: {
    # System configuration...
  };
}
```

### 2. NixOS Configuration (`configuration.nix`)

Because ChatGPT Desktop contains proprietary binaries from OpenAI, ensure unfree packages are allowed:

```nix
{ pkgs, inputs, ... }:

{
  nixpkgs.config.allowUnfree = true;

  environment.systemPackages = [
    inputs.chatgpt-desktop.packages.${pkgs.stdenv.hostPlatform.system}.default
  ];

  # Required for credential persistence on standalone Wayland compositors:
  services.gnome.gnome-keyring.enable = true;
  security.pam.services.login.enableGnomeKeyring = true;
}
```

> **Note on Desktop Integration & MIME Callbacks:**  
> When installed via `environment.systemPackages`, NixOS automatically links the `.desktop` file and registers the `x-scheme-handler/chatgpt` and `x-scheme-handler/codex` MIME associations system-wide.

### 3. Home Manager (`home.nix`)

```nix
{ pkgs, inputs, ... }:

{
  home.packages = [
    inputs.chatgpt-desktop.packages.${pkgs.stdenv.hostPlatform.system}.default
  ];
}
```

---

## Troubleshooting & Gotchas

### 1. OAuth Sign-In Not Redirecting
If clicking "Sign In" in your browser fails to redirect back into the ChatGPT app:
1. Verify the MIME registration:
   ```bash
   xdg-mime query default x-scheme-handler/chatgpt
   ```
   *Expected output*: `chatgpt.desktop`
2. If unset, manually set the default scheme handler:
   ```bash
   xdg-mime default chatgpt.desktop x-scheme-handler/chatgpt
   xdg-mime default chatgpt.desktop x-scheme-handler/codex
   ```

### 2. Session Lost on App Restart
If you find yourself logged out every time the application is closed:
- Ensure a Secret Service provider (`gnome-keyring` or KeePassXC with Freedesktop Secret Service enabled) is running in your session.
- Under standalone Wayland compositors (Niri, Hyprland, Sway), ensure the keyring daemon is initialized in your startup config:
  ```bash
  dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP
  gnome-keyring-daemon --start --components=secrets
  ```

---

## Legal & Disclaimers

- **Packaging Code**: Licensed under the [MIT License](./LICENSE).
- **Trademarks & Binaries**: **OpenAI**, **ChatGPT**, and **Codex** are trademarks or registered trademarks of **OpenAI, Inc.**
- This repository is an independent community packaging effort and is neither affiliated with nor endorsed by OpenAI.
