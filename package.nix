{
  lib,
  stdenv,
  fetchurl,
  dpkg,
  autoPatchelfHook,
  wrapGAppsHook3,
  makeWrapper,
  addDriverRunpath,
  bubblewrap,
  cacert,
  diffutils,
  git,
  gnused,
  imagemagick,
  gsettings-desktop-schemas,
  libglvnd,
  python3,
  xdg-utils,
  alsa-lib,
  at-spi2-atk,
  at-spi2-core,
  cairo,
  cups,
  dbus,
  expat,
  gdk-pixbuf,
  glib,
  gtk3,
  libdrm,
  libnotify,
  libpulseaudio,
  libsecret,
  libusb1,
  libxkbcommon,
  mesa,
  nspr,
  nss,
  pango,
  pipewire,
  systemd,
  libx11,
  libxcomposite,
  libxdamage,
  libxext,
  libxfixes,
  libxrandr,
  libxcb,
  libxkbfile,
}:

stdenv.mkDerivation (finalAttrs: {
  pname = "chatgpt-desktop";
  version = "26.930.51102";

  src = fetchurl {
    url = "https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_amd64.deb";
    hash = "sha256-Y3w8lLxQ+O4zoV4uKOx/kqeH8JQ+cA7+ERvAvw1IE7Q=";
  };

  nativeBuildInputs = [
    dpkg
    autoPatchelfHook
    wrapGAppsHook3
    makeWrapper
    addDriverRunpath
    imagemagick
    python3
  ];

  buildInputs = [
    alsa-lib
    at-spi2-atk
    at-spi2-core
    bubblewrap
    cairo
    cups
    dbus
    expat
    gdk-pixbuf
    git
    glib
    gsettings-desktop-schemas
    gtk3
    libdrm
    libnotify
    libpulseaudio
    libsecret
    libusb1
    libxkbcommon
    mesa
    nspr
    nss
    pango
    systemd
    libx11
    libxcomposite
    libxdamage
    libxext
    libxfixes
    libxrandr
    libxcb
    libxkbfile
  ];

  runtimeDependencies = [
    (lib.getLib systemd)
    libsecret
    libnotify
    libpulseaudio
    libglvnd
    pipewire
  ];

  autoPatchelfIgnoreMissingDeps = [
    "libc.musl-x86_64.so.1"
  ];

  appendRunpaths = [
    "$out/lib/chatgpt"
  ];

  dontWrapGApps = true;

  installPhase = ''
    runHook preInstall

    mkdir -p $out/lib/chatgpt $out/bin $out/share/applications $out/share/pixmaps $out/share/icons/hicolor/1024x1024/apps

    # Move application files
    cp -r usr/lib/chatgpt/* $out/lib/chatgpt/

    # Eliminate broken and unused Qt shims completely so Electron never attempts to dlopen them
    rm -f $out/lib/chatgpt/libqt5_shim.so $out/lib/chatgpt/libqt6_shim.so

    # Backup uncorrupted static-pie binaries before autoPatchelf alters them
    mkdir -p "$TMPDIR/static-binaries"
    cp -a usr/lib/chatgpt/resources/codex "$TMPDIR/static-binaries/codex"
    cp -a usr/lib/chatgpt/resources/codex-code-mode-host "$TMPDIR/static-binaries/codex-code-mode-host"
    cp -a usr/lib/chatgpt/resources/rg "$TMPDIR/static-binaries/rg"
    cp -a usr/lib/chatgpt/resources/tectonic/tectonic "$TMPDIR/static-binaries/tectonic"
    cp -a usr/lib/chatgpt/resources/cua_node/bin/node_repl "$TMPDIR/static-binaries/node_repl"

    # Install desktop entry
    install -Dm644 usr/share/applications/chatgpt.desktop $out/share/applications/chatgpt.desktop
    substituteInPlace $out/share/applications/chatgpt.desktop \
      --replace-fail "Exec=chatgpt %U" "Exec=$out/bin/chatgpt %U" \
      --replace-fail "x-scheme-handler/codex;x-scheme-handler/http;x-scheme-handler/https;" "x-scheme-handler/chatgpt;x-scheme-handler/codex;"

    # Inject StartupWMClass so Wayland compositors (Niri, GNOME Wayland, Hyprland, Sway)
    # and X11 taskbars accurately associate the running window (app_id="Chatgpt") with this desktop file and icon
    echo "StartupWMClass=Chatgpt" >> $out/share/applications/chatgpt.desktop

    # Install desktop entry aliases for reverse-DNS and case variations
    ln -s chatgpt.desktop $out/share/applications/Chatgpt.desktop
    ln -s chatgpt.desktop $out/share/applications/ChatGPT.desktop
    ln -s chatgpt.desktop $out/share/applications/com.openai.chatgpt.desktop

    # Generate and install icons in all standard FreeDesktop hicolor resolutions
    for size in 16 24 32 48 64 128 256 512; do
      mkdir -p $out/share/icons/hicolor/''${size}x''${size}/apps
      magick usr/share/pixmaps/chatgpt.png -filter Lanczos -resize ''${size}x''${size} $out/share/icons/hicolor/''${size}x''${size}/apps/chatgpt.png
      ln -s chatgpt.png $out/share/icons/hicolor/''${size}x''${size}/apps/Chatgpt.png
      ln -s chatgpt.png $out/share/icons/hicolor/''${size}x''${size}/apps/ChatGPT.png
      ln -s chatgpt.png $out/share/icons/hicolor/''${size}x''${size}/apps/com.openai.chatgpt.png
    done

    # 1024x1024 high-res icon
    mkdir -p $out/share/icons/hicolor/1024x1024/apps
    install -Dm644 usr/share/pixmaps/chatgpt.png $out/share/icons/hicolor/1024x1024/apps/chatgpt.png
    ln -s chatgpt.png $out/share/icons/hicolor/1024x1024/apps/Chatgpt.png
    ln -s chatgpt.png $out/share/icons/hicolor/1024x1024/apps/ChatGPT.png
    ln -s chatgpt.png $out/share/icons/hicolor/1024x1024/apps/com.openai.chatgpt.png

    # Install pixmaps with case variants
    install -Dm644 usr/share/pixmaps/chatgpt.png $out/share/pixmaps/chatgpt.png
    ln -s chatgpt.png $out/share/pixmaps/Chatgpt.png
    ln -s chatgpt.png $out/share/pixmaps/ChatGPT.png
    ln -s chatgpt.png $out/share/pixmaps/com.openai.chatgpt.png

    # Symlink launcher
    ln -s $out/lib/chatgpt/ChatGPT $out/bin/chatgpt

    # Patch detect-libc inside app.asar to neutralize the process.report SIGILL trap
    # and short-circuit glibc detection for @parcel/watcher when workspace folders are opened.
    python3 -c "
asar_path = '$out/lib/chatgpt/resources/app.asar'
with open(asar_path, 'rb') as f:
    content = f.read()

# 1. Neutralize process.report trap in detect-libc/lib/process.js
t1 = b'if (isLinux() && process.report) {'
r1 = b'if (false && (process.report)) {  '
assert len(t1) == len(r1), 'Length mismatch for t1'
assert t1 in content, 'Target t1 not found in app.asar'
content = content.replace(t1, r1, 1)

# 2. Prevent process.report.getReport() call in detect-libc/lib/process.js
t2 = b'report = process.report.getReport();'
r2 = b'report = {};                        '
assert len(t2) == len(r2), 'Length mismatch for t2'
assert t2 in content, 'Target t2 not found in app.asar'
content = content.replace(t2, r2, 1)

# 3. Short-circuit familyFromReport in detect-libc/lib/detect-libc.js to return GLIBC immediately
t3 = b'const familyFromReport = () => {\n  const report = getReport();'
r3 = b'const familyFromReport = () => {\n  return GLIBC;              '
assert len(t3) == len(r3), 'Length mismatch for t3'
assert t3 in content, 'Target t3 not found in app.asar'
content = content.replace(t3, r3, 1)

with open(asar_path, 'wb') as f:
    f.write(content)
print('Successfully patched detect-libc inside app.asar')
"

    runHook postInstall
  '';

  preFixup = ''
    gappsWrapperArgs+=(
      --prefix PATH : ${lib.makeBinPath [ xdg-utils git diffutils bubblewrap stdenv.cc.libc.bin ]}
      --prefix XDG_DATA_DIRS : "${gsettings-desktop-schemas}/share/gsettings-schemas/${gsettings-desktop-schemas.name}"
      --prefix XDG_DATA_DIRS : "${gtk3}/share/gsettings-schemas/${gtk3.name}"
      --set SSL_CERT_FILE "${cacert}/etc/ssl/certs/ca-bundle.crt"
      --set NIX_SSL_CERT_FILE "${cacert}/etc/ssl/certs/ca-bundle.crt"
      --set-default GTK_USE_PORTAL 1
      --set-default CODEX_CLI_PATH "$out/lib/chatgpt/resources/codex"
      --set-default CODEX_ELECTRON_RESOURCES_PATH "$out/lib/chatgpt/resources"
      --add-flags "--ozone-platform-hint=auto --enable-features=WaylandWindowDecorations,WebRTCPipeWireCapturer --password-store=gnome-libsecret"
      --run 'if [ -f "$HOME/.codex/config.toml" ] && [ -w "$HOME/.codex/config.toml" ]; then ${gnused}/bin/sed -i -E "s|/nix/store/[a-z0-9]+-chatgpt-desktop-[^/]+|'"$out"'|g" "$HOME/.codex/config.toml"; fi'
    )

    # autoPatchelfHook runs in postFixupHooks and corrupts static-pie binaries.
    # We append a hook to postFixupHooks so it executes AFTER autoPatchelfPostFixup.
    restoreStaticBinaries() {
      echo "Restoring uncorrupted static-pie binaries after autoPatchelf..."
      cp -fa "$TMPDIR/static-binaries/codex" "$out/lib/chatgpt/resources/codex"
      cp -fa "$TMPDIR/static-binaries/codex-code-mode-host" "$out/lib/chatgpt/resources/codex-code-mode-host"
      cp -fa "$TMPDIR/static-binaries/rg" "$out/lib/chatgpt/resources/rg"
      cp -fa "$TMPDIR/static-binaries/tectonic" "$out/lib/chatgpt/resources/tectonic/tectonic"
      cp -fa "$TMPDIR/static-binaries/node_repl" "$out/lib/chatgpt/resources/cua_node/bin/node_repl"
      chmod +x $out/lib/chatgpt/resources/{codex,codex-code-mode-host,rg}
      chmod +x $out/lib/chatgpt/resources/tectonic/tectonic
      chmod +x $out/lib/chatgpt/resources/cua_node/bin/node_repl
    }
    postFixupHooks+=(restoreStaticBinaries)
  '';

  postFixup = ''
    addDriverRunpath $out/lib/chatgpt/ChatGPT
    wrapProgram $out/bin/chatgpt \
      "''${gappsWrapperArgs[@]}"
  '';

  doInstallCheck = true;
  installCheckPhase = ''
    echo "Running install checks..."
    $out/lib/chatgpt/resources/codex --version
    $out/lib/chatgpt/resources/rg --version
    $out/lib/chatgpt/resources/tectonic/tectonic --version
    $out/lib/chatgpt/resources/codex-code-mode-host --help
    $out/lib/chatgpt/resources/cua_node/bin/node --version
    $out/lib/chatgpt/resources/cua_node/bin/node_repl --help
    echo "Install checks passed successfully!"
  '';

  meta = with lib; {
    description = "Official ChatGPT Linux desktop application by OpenAI";
    homepage = "https://chatgpt.com";
    license = licenses.unfree;
    platforms = [ "x86_64-linux" ];
    mainProgram = "chatgpt";
  };
})
