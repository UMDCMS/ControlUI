{
  description = "Develop environment for HEP python packages";
  inputs = { nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable"; };

  outputs = { self, nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
    in {

      # Adding shell that is required for developement using editors, this is
      # mainly to include additional language servers and formatters that are
      # not listed for interactive use.
      devShells.${system}.default = pkgs.mkShell {
        packages = [
          pkgs.micromamba # For setting up the development environments
          pkgs.yq-go # For getting the information from the environment yaml
        ];

        shellHook = ''
          set -e
          eval "$(micromamba shell hook -s zsh)" # Setting the various items off
          # Setting the envrionment to be a local path
          if [ -z "$MAMBA_ROOT_PREFIX" ]; then
            export MAMBA_ROOT_PREFIX="$HOME/.mamba"
          fi
          # Create the environment if the directory doesn't already exist
          ENV_NAME=$(yq ".name" environment.yml)
          if [[ ! -d $MAMBA_ROOT_PREFIX/envs/$ENV_NAME ]]; then
            echo "Creating envrionment directory..."
            micromamba create -f environment.yml -y > /dev/null
          fi
          # Always attempt to update the environment
          micromamba activate $ENV_NAME
          echo "Updating environment..."
          micromamba install --name $ENV_NAME -f environment.yml -y > /dev/null
          # Additional update if a additional developement yaml file exists
          if [[ -f $PWD/dev_environment.yaml ]] ; then
            echo "Installing development packages ..."
            micromamba install --name $ENV_NAME -f dev_environment.yaml -y > /dev/null
          fi
          echo "Python executable:" $(which python) $(python --version)
        '';
      };
      # We need to treat this as a package,
      defaultPackage.x86_64-linux = pkgs.micromamba;
    };
}
