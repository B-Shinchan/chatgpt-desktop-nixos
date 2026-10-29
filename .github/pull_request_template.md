## Summary of Changes

Describe the problem solved or the feature/improvement introduced.

## Motivation & Context

Why is this change necessary? Link to any relevant issue (`Fixes #...`).

## Pre-submission Checklist

- [ ] Evaluated and passed local flake checks: `nix flake check --print-build-logs`
- [ ] Successfully built the derivation locally: `nix build .#default`
- [ ] Ran updater test suite: `python3 -m unittest discover -s tests -v`
- [ ] Verified static-PIE restoration hooks (preserve uncorrupted `codex` / `node_repl` binaries)
- [ ] Verified Secret Service password store and Wayland/X11 flag handling
- [ ] Formatted with `nix fmt` and `ruff format`
- [ ] No hardcoded user paths or machine-specific assumptions introduced
