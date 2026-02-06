# Agent Guide: rpy_motion_detector

## Project Summary
`rpy_motion_detector` is a Raspberry Pi-oriented motion detection application using OpenCV for frame processing and GStreamer/FFmpeg for video capture and recording. It detects motion, captures still images, and records clips with optional pre-capture buffering. Behavior is driven by INI configuration files and can be overridden from the CLI.

Key capabilities:
- Motion detection via background subtraction and contour filtering.
- Picture capture on event start.
- Video recording with optional pre-capture concatenation.
- Event hooks for custom shell commands on start/end and for picture/movie actions.

## Repository Layout
- `src/main.py`: Script entry point (direct run).
- `src/rpy_motion_detector/__main__.py`: Module entry point (`python -m rpy_motion_detector`).
- `src/rpy_motion_detector/run.py`: CLI runner. Parses overrides, validates config, sets logging, registers signal handlers, and starts the detector.
- `src/rpy_motion_detector/config.py`: Dataclasses for config sections + INI parsing + `exclude_zones` parsing.
- `src/rpy_motion_detector/motion_detector.py`: Main motion detection loop, event lifecycle, movie recording, pre-capture handling, cleanup.
- `src/rpy_motion_detector/frame_detection.py`: Frame preprocessing, contour detection, and optional RTSP streaming helper.
- `config/default.ini`: Default config template for development.
- `tests/`: Unit tests for config parsing and runner behavior.
- `docs/DEVELOPER_GUIDE.md`: Contributor setup and linting guidance (note: it says no tests, but `tests/` does exist).

## Dev Setup
Python: >= 3.8 (project metadata). The app assumes system-level access to a video device and GStreamer/FFmpeg for recording.

System dependencies for full runtime behavior:
- GStreamer (`gst-launch-1.0` is invoked from Python).
- FFmpeg (used for concatenation when pre-capture is enabled).
- A video device (e.g., `/dev/video0`, `/dev/video50`).

Python dependencies are declared in `pyproject.toml`:
- `opencv-python`

Install in editable mode:
```bash
pip install -e .
```

## Run Locally
Module entry point:
```bash
python -m rpy_motion_detector --config config/default.ini
```

Dry run (validate config only, no capture loop):
```bash
python -m rpy_motion_detector --config config/default.ini --dry-run
```

CLI overrides (multiple `-o` allowed):
```bash
python -m rpy_motion_detector \
  --config config/default.ini \
  -o detection.min_area=15000 \
  -o camera.device=/dev/video2
```

Installed console script:
```bash
rpy-motion-detector --config config/default.ini
```

## Configuration Overview
Config is read from an INI file (see `config/default.ini`). You can override any `section.option` via CLI.

Key sections and options:
- `camera`
  - `device`: camera device path (default `/dev/video0`).
- `detection`
  - `min_area`, `max_area`: contour area bounds.
  - `var_threshold`: background subtractor sensitivity.
  - `bin_threshold`: threshold for binarization.
  - `background_substractor_history`: history length for MOG2.
  - `blur_size`, `dilate_iterations`, `consecutive_frames`.
  - `exclude_zones`: semicolon-separated rectangles `x1,y1,x2,y2;...`.
- `movie`
  - `enable`, `device`, `dirpath`.
  - `precapture_seconds`, `max_duration`.
  - `record_precapture` (if true, records pre-capture buffer to tmp dir, then concatenates).
- `picture`
  - `enable`, `dirpath`.
- `event`
  - `no_motion_timeout`, `event_gap`.
  - `on_event_start`, `on_event_end`, `on_movie_start`, `on_movie_end`, `on_picture_save`.
- `log`
  - `level`.
- `tmp`
  - `dirpath` for pre-capture and temp files.

### Override parsing rules
Overrides must be `section.option=value`. Invalid formats raise `ValueError` in `parse_overrides()`.

### `exclude_zones` parsing
`exclude_zones` is parsed into `[(x1,y1,x2,y2), ...]`. Values must be numeric and satisfy `x1 < x2` and `y1 < y2`. Invalid zones raise `ValueError`.

## Runtime Behavior Details
- `MotionDetector.start()` opens the camera device and loops forever, reading frames.
- A pre-capture buffer stores frames for `movie.precapture_seconds`.
- Frames are processed (blur, background subtraction, threshold, dilation).
- Contours are filtered by `min_area`/`max_area` and `exclude_zones`.
- Motion triggers after `detection.consecutive_frames` frames.
- Event lifecycle:
  - Event starts -> `on_event_start` runs and a picture may be captured.
  - Event ends -> `on_event_end` runs after `no_motion_timeout` seconds without motion.
- Movie recording:
  - Starts on event start if `movie.enable`.
  - Stops and restarts if `max_duration` is exceeded.
  - If `record_precapture`, pre-capture frames are recorded in a separate file and concatenated via FFmpeg.

## Testing
Tests use pytest, with heavy mocking of hardware and subprocess interactions. Run:
```bash
python -m pytest
```

## Linting
```bash
flake8
```

## Gotchas and Constraints
- GStreamer and FFmpeg must be installed for runtime recording/concatenation.
- `motion_detector.py` uses subprocess calls and OS signals; keep this in mind if adding Windows support.
- `MotionDetector.__del__` does cleanup and uses `del self` (be careful when modifying lifecycle logic).
- `docs/DEVELOPER_GUIDE.md` says “no automated tests,” but the repo does include pytest tests.

## Change Guidance
- If you change config parsing in `src/rpy_motion_detector/config.py`, update tests in `tests/` and adjust `config/default.ini` accordingly.
- If you alter motion detection logic in `src/rpy_motion_detector/motion_detector.py`, consider mocking external dependencies in tests (OpenCV, GStreamer, FFmpeg, subprocess).
- If you modify CLI behavior, update both `src/main.py` and `src/rpy_motion_detector/__main__.py` (they are duplicated).
