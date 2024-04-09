# Calibration GUI discussion repository

This is a discussion repository for the GUI design of the calibration process

## Quick setup instructions

Your system must have [`conda`][conda] installed, this setup has been tested
mainly on Linux systems. Though Unix-like system should also work.

```bash
git clone http://github.com/yimuchen/gui_example

cd gui_example
conda env create -f ./environment.yml
conda activate qca_control
CC=$(which clang) CXX=$(which clang++) python3 -m pip install -e ./
```

Once the installation is done you should be able to consistently set up the
environment by starting the `conda` environment.

```bash
conda activate qca_control
cd gui_example
python3 ./bin/run_cli.py --help
```

- *Some catches installing on OSX*: because we cannot set up programmable
  dependencies on certain packages, you will need to remove the following line
  in the `environment.yml` when installing on an OSX machine:
  - `qt-wayland=5.15.8`: The wayland server is only required for Linux systems

## Adding procedures (for physicists)

To add a procedure routine to system, consult the documentation in the
[procedures](src/qcmanager/procedures) directory. If you want to also add plots
to be automatically presented to the user, consult the documentation in the
[plotting](src/qcmanager/plotting).


## Core development philosophies

As the QA/QC procedures will likely be continuously evolving as we learn more
about the tileboard systems, this repository attempts to incorporate the ideas
of the procedure codes being easy to define for physicists, while also being
sufficiently rigid for GUI operators.

Some of the key ideas we are trying to include in the design of the software:

### Minimum prior knowledge

Attempt to require minimum knowledge outside the typical HEP physicist tool
kit. Python will be the key technology chosen for the flexibility. `PyQt` is
chosen to drive the GUI interface, though we aim to have physicists interact
with as little with this process as possible.

### Minimum editing

Adding processes should require as few file edits over as few files as
possible. This ensures that features will not be lost when setting up the
configurations files.

### Single truth

As we anticipate that during the full QA/QC processes, tileboard may be moved to
different stations with hardware capabilities, we want a single source of truth
of what measurements has been carried out by on the tileboard in question
regardless of the hardware configuration.

All tileboard will be represented by a `session.yaml` file, which records all
measurements and related data file, and a summary of the results. For details
of how these data formats are defined, see documentation in the
[`qcmanager`](src/qcmanager) directory.

## Missing/Incomplete features:

If there are any feature requests, feel free to add an issue on GitHub

- Interface locking: certain buttons should be disabled when configurations are
  not met.
- Multiple procedure running (how do we define multi-procedures?)

[conda]: https://conda.io/projects/conda/en/latest/user-guide/install/index.html
