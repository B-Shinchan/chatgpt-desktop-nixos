{
  description = "Official OpenAI ChatGPT Desktop Linux packaging";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfree = true;
      };
      chatgpt-desktop = pkgs.callPackage ./package.nix { };
    in
    {
      packages.${system} = {
        default = chatgpt-desktop;
        chatgpt-desktop = chatgpt-desktop;
      };

      formatter.${system} = pkgs.nixfmt;

      checks.${system} = {
        updater =
          pkgs.runCommand "updater-tests"
            {
              nativeBuildInputs = [
                pkgs.python3
                pkgs.dpkg
                pkgs.ruff
              ];
            }
            ''
              cp -r ${self} source
              chmod -R u+w source
              cd source
              ruff format --check scripts tests
              ruff check scripts tests
              python3 -m unittest discover -s tests -v
              touch $out
            '';
        desktop =
          pkgs.runCommand "desktop-integration"
            {
              nativeBuildInputs = [
                pkgs.python3
                pkgs.desktop-file-utils
              ];
            }
            ''
              python3 ${./scripts/check-desktop.py} ${chatgpt-desktop}
              touch $out
            '';
      };

      apps.${system}.default = {
        type = "app";
        program = "${chatgpt-desktop}/bin/chatgpt";
        meta.description = "Official ChatGPT Linux desktop application by OpenAI";
      };

      overlays.default = final: prev: {
        chatgpt-desktop = final.callPackage ./package.nix { };
      };
    };
}
