{
  lib,
  stdenv,
  fetchurl,
  dpkg,
  autoPatchelfHook,
  wrapGAppsHook3,
  makeWrapper,
  addDriverRunpath,
  cacert,
  libglvnd,
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
  version = "42.3.0";

  src = fetchurl {
    url = "https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_amd64.deb";
    hash = "sha256-YP222JXXdviDH/NaeD3gTNv6KA8PPZclhDFfmOV6olY=";
  };

  nativeBuildInputs = [
    dpkg
    autoPatchelfHook
    wrapGAppsHook3
    makeWrapper
    addDriverRunpath
  ];

  buildInputs = [
    alsa-lib
    at-spi2-atk
    at-spi2-core
    cairo
    cups
    dbus
    expat
    gdk-pixbuf
    glib
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
  ];

  autoPatchelfIgnoreMissingDeps = [
    "libQt5Core.so.5"
    "libQt5Gui.so.5"
    "libQt5Widgets.so.5"
    "libQt6Core.so.6"
    "libQt6Gui.so.6"
    "libQt6Widgets.so.6"
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

    # Backup uncorrupted static-pie binaries before autoPatchelf alters them
    mkdir -p "$TMPDIR/static-binaries"
    cp -a usr/lib/chatgpt/resources/codex "$TMPDIR/static-binaries/codex"
    cp -a usr/lib/chatgpt/resources/codex-code-mode-host "$TMPDIR/static-binaries/codex-code-mode-host"
    cp -a usr/lib/chatgpt/resources/rg "$TMPDIR/static-binaries/rg"

    # Install desktop entry
    install -Dm644 usr/share/applications/chatgpt.desktop $out/share/applications/chatgpt.desktop
    substituteInPlace $out/share/applications/chatgpt.desktop \
      --replace-fail "Exec=chatgpt %U" "Exec=$out/bin/chatgpt %U" \
      --replace-fail "x-scheme-handler/codex;x-scheme-handler/http;x-scheme-handler/https;" "x-scheme-handler/chatgpt;x-scheme-handler/codex;"

    # Install icons
    install -Dm644 usr/share/pixmaps/chatgpt.png $out/share/pixmaps/chatgpt.png
    install -Dm644 usr/share/pixmaps/chatgpt.png $out/share/icons/hicolor/1024x1024/apps/chatgpt.png

    # Symlink launcher
    ln -s $out/lib/chatgpt/ChatGPT $out/bin/chatgpt

    runHook postInstall
  '';

  preFixup = ''
    gappsWrapperArgs+=(
      --prefix PATH : ${lib.makeBinPath [ xdg-utils ]}
      --set SSL_CERT_FILE "${cacert}/etc/ssl/certs/ca-bundle.crt"
      --set NIX_SSL_CERT_FILE "${cacert}/etc/ssl/certs/ca-bundle.crt"
      --add-flags "--ozone-platform-hint=auto --enable-features=WaylandWindowDecorations --password-store=gnome-libsecret"
    )

    # autoPatchelfHook runs in postFixupHooks and corrupts static-pie binaries.
    # We append a hook to postFixupHooks so it executes AFTER autoPatchelfPostFixup.
    restoreStaticBinaries() {
      echo "Restoring uncorrupted static-pie binaries after autoPatchelf..."
      cp -fa "$TMPDIR/static-binaries/codex" "$out/lib/chatgpt/resources/codex"
      cp -fa "$TMPDIR/static-binaries/codex-code-mode-host" "$out/lib/chatgpt/resources/codex-code-mode-host"
      cp -fa "$TMPDIR/static-binaries/rg" "$out/lib/chatgpt/resources/rg"
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
