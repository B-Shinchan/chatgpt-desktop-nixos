# ChatGPT Desktop for NixOS

[![Build](https://github.com/B-Shinchan/chatgpt-desktop-nixos/actions/workflows/ci.yml/badge.svg)](https://github.com/B-Shinchan/chatgpt-desktop-nixos/actions/workflows/ci.yml)
[![Upstream updates](https://github.com/B-Shinchan/chatgpt-desktop-nixos/actions/workflows/update.yml/badge.svg)](https://github.com/B-Shinchan/chatgpt-desktop-nixos/actions/workflows/update.yml)

Community packaging of **OpenAI's official Linux application** for NixOS. The application comes from the vendor's Debian repository; this project adapts its runtime and desktop integration for NixOS. It is not an official OpenAI or NixOS project.

## Requirements and scope

- `x86_64-linux` only. This repository does not currently package ARM releases.
- Nix with the `nix-command` and `flakes` features enabled.
- A graphical Linux session, working graphics drivers, and a session D-Bus.
- A running Secret Service provider, such as GNOME Keyring or KeePassXC with Secret Service enabled. The launcher selects `gnome-libsecret`; your login session must unlock the keyring.
- A working XDG Desktop Portal and the backend recommended by your desktop or compositor for file dialogs and applicable sharing features.
- A vendor account and any subscription required for the application features you use.

The package installs standard desktop files and vendor icons for Linux application menus. GNOME, Niri, Hyprland, and other desktops have different portal, keyring, shortcut, and window-grouping behavior. They are not all exercised by CI. Current Electron's automatic display selection is used: native Wayland in an appropriately configured Wayland session, X11 otherwise. Pass `--ozone-platform=x11` when troubleshooting.

See the [vendor's Linux documentation](https://learn.chatgpt.com/docs/linux/linux-app) for upstream requirements and feature restrictions. This package cannot enable features unavailable in the upstream application or your plan.

## Try it

```sh
nix run github:B-Shinchan/chatgpt-desktop-nixos
```

For a temporary shell:

```sh
nix shell github:B-Shinchan/chatgpt-desktop-nixos -c chatgpt
```

These commands provide the executable for that invocation. Install declaratively for persistent application-menu and URI-handler integration.

## Install with a system flake

Add the repository to your existing flake's `inputs` and pass `inputs` to your NixOS modules using `specialArgs`. The following shows the relevant structure; keep your existing host modules and settings:

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    chatgpt-desktop.url = "github:B-Shinchan/chatgpt-desktop-nixos";
  };

  outputs = inputs@{ nixpkgs, ... }: {
    nixosConfigurations.YOUR_HOST = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      specialArgs = { inherit inputs; };
      modules = [ ./configuration.nix ];
    };
  };
}
```

In a NixOS module:

```nix
{ inputs, pkgs, ... }:
{
  environment.systemPackages = [
    inputs.chatgpt-desktop.packages.${pkgs.stdenv.hostPlatform.system}.default
  ];
}
```

The flake's package set explicitly permits the proprietary application. If you use `overlays.default` instead, permit the unfree package in your own Nixpkgs configuration. The overlay provides `pkgs.chatgpt-desktop`.

For Home Manager, pass `inputs` through `extraSpecialArgs` (or `home-manager.extraSpecialArgs` in a NixOS integration), then put the same package expression in `home.packages`.

Both standalone installation methods use this repository's `flake.lock`. You may set `chatgpt-desktop.inputs.nixpkgs.follows = "nixpkgs"` to share your system's package set, but that dependency combination is not the exact one checked by this repository's CI.

## Desktop integration and troubleshooting

The application-menu name is **ChatGPT**. The desktop file is `chatgpt.desktop`, the icon theme name is `chatgpt`, and the executable is `chatgpt`. Desktop action commands also point to the packaged launcher. Installing the package advertises its supported URI schemes; it does not guarantee your desktop selects it as the default handler.

Check browser sign-in callbacks:

```sh
xdg-mime query default x-scheme-handler/chatgpt
# If no appropriate handler is selected:
xdg-mime default chatgpt.desktop x-scheme-handler/chatgpt
xdg-mime default chatgpt.desktop x-scheme-handler/codex
```

If the application is missing from your menu, start a new desktop session after declarative installation. Duplicate entries may come from older manually installed desktop files in `~/.local/share/applications`; inspect them before removing anything. The package does not register itself as a handler for ordinary HTTP or HTTPS links.

For login persistence, verify that a Secret Service provider is running and unlocked. On a standalone compositor, configure keyring startup and PAM unlocking for your actual login method. GNOME normally supplies this session integration. For file-dialog or sharing problems, check your compositor's portal configuration and D-Bus environment. Packaging the libraries alone cannot provide a correctly configured desktop session.

For display problems, try:

```sh
chatgpt --ozone-platform=x11
```

X11 fallback requires X11/XWayland support. Native Wayland requires a working Wayland session. CI checks a headless X11 launch and a real Wayland surface/application ID in private Weston; it does not certify live Wayland window grouping, rendering, authentication, audio, screen sharing, or subscription-dependent features.

The package preserves selected bundled static helper executables, retains the vendor's custom Node runtime with ELF header ordering preserved, checks helper startup and Node child-process execution during installation, and applies a size-preserving `detect-libc` compatibility patch inside `app.asar`. A changed upstream patch target intentionally fails the build. This remains a vendor-specific workaround, not an upstream-supported modification.

The launcher no longer rewrites `~/.codex/config.toml`. If an older installation left absolute paths to a previous `/nix/store/...-chatgpt-desktop-...` directory there, back up the file and review the affected helper settings before garbage-collecting that old package. Avoid replacing unrelated configuration or copying account credentials into bug reports.

## Automatic updates

Every **Monday at 10:17 IST**, GitHub Actions checks OpenAI's stable amd64 APT feed. GitHub may start scheduled jobs late. Changes to the updater also start a check, and maintainers can use **Actions → Check & Update Upstream → Run workflow**.

The update process:

1. Selects the highest Debian version for the exact package and architecture, validates its download layout, and records its SHA256. It rejects downgrades and conflicting metadata, and detects a changed archive hash for the same version.
2. Evaluates and builds the candidate against the locked Nixpkgs revision. It runs updater tests, desktop-file/icon checks, formatting/workflow checks, an isolated headless version check, X11 window-class matching, and a headless Wayland window/identity check, plus the bundled Codex sandbox write-isolation check.
3. On the first Monday of each month, also refreshes the official NixOS/Nixpkgs lock pin and validates that candidate with the same checks.
4. After every check succeeds, a separate fresh job reconstructs only the validated version/hash and restricted Nixpkgs lock changes and commits them to `main` as `github-actions[bot]`. Only this job has repository write permission.

A failed candidate is not published. The failed Actions step and job summary explain the failure. Unchanged releases produce no package commit. Action dependencies are pinned to exact commits; Dependabot proposes weekly updates to those pins for security review.

This automates routine application releases, not every future packaging change. Vendor layout, dependency, patch, API, or licensing changes can require maintenance. Nixpkgs inputs are pinned between the monthly validated refreshes. The publisher rejects a lock candidate that changes another input, changes the NixOS repository, moves the pin timestamp backwards, or changes the input graph. GitHub can disable schedules after 60 days without repository activity, and service/account limits can interrupt jobs.

Users receive repository updates when they refresh their own flake lock and rebuild or update their profile. For example, from the system flake directory:

```sh
nix flake update chatgpt-desktop
sudo nixos-rebuild switch --flake .#YOUR_HOST
```

## Development and security

See [CONTRIBUTING.md](CONTRIBUTING.md) for local checks, contributions, and the remaining work before a potential Nixpkgs submission. See [SECURITY.md](SECURITY.md) for trust boundaries, maintenance limits, and branch-protection guidance.

The automated checks exercise the packaging and selected runtime behavior. They are not a complete graphical test matrix, a vendor-binary security audit, or proof of a reproducible upstream build.

## License and attribution

The packaging code is [MIT-licensed](LICENSE). The application, bundled components, names, and logos remain subject to their respective vendor licenses and trademark rights. Packaging does not grant permission to redistribute proprietary binaries. This project is not affiliated with or endorsed by OpenAI.
