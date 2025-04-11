# rpy_motion_detector

`rpy_motion_detector` is a simple motion detection application designed to run on a Raspberry Pi. It uses the Raspberry Pi camera module and OpenCV to detect motion, capture pictures, and record videos when motion is detected. The application is configurable and supports custom event handling through shell commands.
It is heavily inspired by [motionplus](https://github.com/Motion-Project/motionplus)

## Features

- Motion detection using OpenCV.
- Configurable camera settings (resolution, FPS, etc.).
- Captures pictures and records videos when motion is detected.
- Pre-capture buffering to include frames before motion is detected.
- Configurable event hooks for custom actions (e.g., notifications).
- Easy-to-use configuration via a TOML file.

## Requirements

- Raspberry Pi with a camera module
- GStream installed
- FFmpeg installed
- Python 3.8 or higher.
- Dependencies:
  - `opencv`

### Set up virtual devices

```bash
sudo vim /etc/modprobe.d/v4l2loopback.conf
>> options v4l2loopback video_nr=40,50 card_label="Motion,Movie"
```

### Stream to virtual devices
```bash
WIDTH=640
HEIGHT=480
FPS=30
DEV1=/dev/video40
DEV2=/dev/video50
gst-launch-1.0 -e \
 libcamerasrc \
  ! video/x-raw,width=$WIDTH,height=$HEIGHT,framerate=$FPS/1,format=NV12 \
  ! videoconvert \
  ! tee name=t \
  t. ! queue leaky=downstream max-size-buffers=2 ! v4l2sink device=$DEV1 sync=false \
  t. ! queue leaky=downstream max-size-buffers=2 ! v4l2sink device=$DEV2 sync=false
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/SamArgt/rpy-motion-detector.git
cd rpy-motion-detector
```

2. Install with pipx
```bash
pipx install rpy_motion_detector
```

3. Run
```bash
rpy_motion_detector --config <CONFIG_FILE>
```

## Configuration
The application is configured using a TOML file located at [default.toml](./config/default.ini). Below is an example configuration:

Key Configuration Options:

-  Detection Settings
    - `threshold`: Sensitivity of motion detection. Lower values make the detector more sensitive to small movements.
    - `min_area`: Minimum area (in pixels) of motion required to trigger detection. Helps filter out small, irrelevant movements.
    - `blur_size`: Size of the Gaussian blur applied to frames to reduce noise and improve detection accuracy.
- Movie Settings
    - `dirpath`: Directory where recorded videos will be saved.
    - `precapture_seconds`: Number of seconds to include in the video before motion is detected.
    - `max_record_seconds`: Maximum duration (in seconds) of a single video recording.
- Event Hooks
    - `on_event_start`: Command to execute when motion is first detected.
    - `on_event_end`: Command to execute when motion stops.
    - `on_movie_start`: Command to execute when video recording begins.
    - `on_movie_end`: Command to execute when video recording ends.
    - `on_picture_taken`: Command to execute when a picture is captured.
