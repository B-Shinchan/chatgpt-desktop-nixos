#!/usr/bin/env bash
set -euo pipefail
# The bundled Codex CLI refuses helper aliases under /tmp. Keep all test
# profiles and workspaces in the ignored repository cache instead.
repo=$(pwd)
result=$(realpath "${1:-./result}")
mkdir -p "$repo/.cache"
check_home=$(mktemp -d "$repo/.cache/runtime-home.XXXXXX")
trap 'rm -rf "$check_home"' EXIT
# This exercises the packaged launcher under a real (headless) X11 display.
expected=$(nix eval --raw .#packages.x86_64-linux.default.version)
actual=$(env -u CODEX_HOME HOME="$check_home" XDG_CONFIG_HOME="$check_home/config" XDG_CACHE_HOME="$check_home/cache" XDG_DATA_HOME="$check_home/data" timeout 60s xvfb-run -a dbus-run-session --config-file="$repo/tests/dbus-session.conf" -- "$result/bin/chatgpt" --ozone-platform=x11 --version)
printf 'Packaged version: %s\n' "$actual"
test "$actual" = "$expected"
env -u CODEX_HOME HOME="$check_home" "$result/lib/chatgpt/resources/codex" --version
# Supply bubblewrap from this flake's pinned nixpkgs and
# verify that the sandbox can write inside its work directory but not outside.
work=$(mktemp -d "$repo/.cache/runtime-work.XXXXXX")
trap 'rm -rf "$work" "$check_home"' EXIT
mkdir -p "$work/workspace" "$work/outside"
codex=$(realpath "$result/lib/chatgpt/resources/codex")
cd "$work/workspace"
nix shell --inputs-from "$repo" nixpkgs#bubblewrap -c env -u CODEX_HOME HOME="$check_home" "$codex" sandbox -c 'sandbox_mode="workspace-write"' -- /bin/sh -eu -c '
  echo sandbox_ok > allowed
  if echo forbidden > ../outside/forbidden; then
    echo "Sandbox allowed a write outside the workspace" >&2
    exit 1
  fi
'
test "$(cat allowed)" = sandbox_ok
test ! -e ../outside/forbidden
