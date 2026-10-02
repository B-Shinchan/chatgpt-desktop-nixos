{
  description = "Official OpenAI ChatGPT Desktop Linux packaging";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
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

      apps.${system}.default = {
        type = "app";
        program = "${chatgpt-desktop}/bin/chatgpt";
        meta.description = "Official ChatGPT Linux desktop application by OpenAI";
      };
    };
}
