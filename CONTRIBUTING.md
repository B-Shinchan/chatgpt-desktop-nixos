# Contributing

Please report reproducible packaging problems with your NixOS version, application version, compositor, installation method, and relevant logs. Remove account details, tokens, conversation contents, and private paths before sharing logs. Account and subscription problems belong with the application vendor.

## Local checks

Use an x86_64 Linux machine with Nix and flakes enabled. All Nix tools below come from the repository's locked Nixpkgs revision:

```sh
nix fmt -- *.nix
nix shell --inputs-from . nixpkgs#ruff -c ruff format scripts tests
nix fmt -- --check *.nix
nix shell --inputs-from . nixpkgs#actionlint nixpkgs#shellcheck -c sh -c 'actionlint && shellcheck scripts/*.sh'
nix flake check --print-build-logs
nix build .#default --print-build-logs
nix shell --inputs-from . nixpkgs#xvfb-run nixpkgs#dbus -c bash scripts/check-runtime.sh
nix shell --inputs-from . nixpkgs#xvfb-run nixpkgs#dbus nixpkgs#xprop nixpkgs#xwininfo -c xvfb-run -a dbus-run-session -- python3 scripts/check-x11.py
nix shell --inputs-from . nixpkgs#weston nixpkgs#dbus -c python3 scripts/check-wayland.py
```

The runtime check uses temporary profiles under the ignored `.cache` directory. It does not sign in or read your application profile. Linux user namespaces must be available for sandbox checks. GitHub's Ubuntu runner needs the workflow's AppArmor adjustment; do not disable sandboxing on your desktop to make a test pass.

To inspect an upstream package update locally:

```sh
nix shell --inputs-from . nixpkgs#dpkg nixpkgs#python3 -c python3 scripts/update.py
```

This changes `package.nix` but does not commit or push. Run all checks before submitting the diff. Preserve the fixed source hash and versioned vendor URL. Do not silence missing-library errors, bypass failed patches, or add `--no-sandbox` to make a build green.

## Change review

Use focused pull requests describing the problem, resulting behavior, checks performed, and limitations. Workflow, permission, dependency, and application patch changes need particular care. CODEOWNERS requests owner review; it does not enforce a review without repository branch rules. Dependency updates proposed by Dependabot are intentionally reviewed rather than automatically merging changes to privileged workflows.

Please test graphical changes in the affected desktop session. A headless version check cannot establish OAuth, app grouping, portal dialogs, keyring unlocking, screen sharing, audio, or virtualization behavior.

## Potential Nixpkgs submission

`package.nix` uses `callPackage`, explicit dependencies, fixed-output fetching, unfree licensing, and binary source provenance. These are foundations, not evidence of Nixpkgs acceptance. Before a submission, check whether an equivalent package already exists, identify an active Nixpkgs maintainer, review vendor terms and redistribution permissions, move to the appropriate `pkgs/by-name` layout, and follow current Nixpkgs review and update-script conventions. Explain and minimize the vendor-specific binary patches and wrappers. Keep the GUI/FHS runtime requirements and remaining test limitations explicit.

The vendor application is precompiled proprietary software. Pinning it makes the input identifiable; it does not make the vendor's build reproducible from source or establish that it is free of vulnerabilities.

See the [Nixpkgs manual](https://nixos.org/manual/nixpkgs/unstable/) and [contribution guide](https://github.com/NixOS/nixpkgs/blob/master/CONTRIBUTING.md).
