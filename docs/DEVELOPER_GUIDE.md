# Developer Guide

This document provides an overview of the code base for **rpy_motion_detector** and explains how to get started as a contributor.

## Repository layout

```
src/
  main.py                - CLI entry point used when installing via `python -m` or running the script directly.
  rpy_motion_detector/
    __init__.py          - Package marker.
    __main__.py          - Module entry point (`python -m rpy_motion_detector`).
    config.py            - Dataclasses that read settings from `config/*.ini` files.
    frame_detection.py   - Low level frame processing utilities.
    motion_detector.py   - High level `MotionDetector` class driving the application.
    run.py               - Function invoked by the command line interfaces that sets up logging and starts the detector.
config/
  default.ini            - Example configuration file used during development.
docs/
  DEVELOPER_GUIDE.md     - This document.
```

## Setup

Install the package in editable mode to run the application locally:

```bash
pip install -e .
```

The application can then be started using:

```bash
python -m rpy_motion_detector --config config/default.ini
```

Use the `--dry-run` option if you only want to validate the configuration without starting the detector.

## Linting and tests

The project uses **flake8** for linting. Run it before submitting code:

```bash
flake8
```

There are currently no automated tests but a GitHub workflow runs linting on every pull request.

## Contributing

1. Fork the repository and create a new branch for your changes.
2. Keep code style simple; the default flake8 configuration only enforces a maximum line length of 120 characters.
3. After making changes run `flake8` to ensure coding standards are met.
4. Submit a pull request describing your changes.

