{
  description = "Home Assistant Humidity Control development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python312;
        pythonPackages = python.pkgs;
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            python
            pythonPackages.pyyaml
            pythonPackages.pytest
            pythonPackages.pytest-asyncio
            pythonPackages.mypy
            pkgs.ruff
          ];

          shellHook = ''
            echo "Humidity Control dev environment loaded"
            echo "Available: ruff, mypy, pytest, python3"
          '';
        };
      }
    );
}
