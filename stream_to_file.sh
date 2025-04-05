#!/bin/bash
# This script streams video from a camera source to a file using GStreamer.
# It uses the v4l2src element to capture video and the filesink element to output to a file.

DEVICE="/dev/video50"
OUTPUT_FILE="test.mp4"
WIDTH=640
HEIGHT=480
FPS=30
# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --device)
      DEVICE="$2"
      shift
      shift
      ;;
    --output-file)
      OUTPUT_FILE="$2"
      shift
      shift
      ;;
    --width)
      WIDTH="$2"
      shift
      shift
      ;;
    --height)
      HEIGHT="$2"
      shift
      shift
      ;;
    --fps)
      FPS="$2"
      shift
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done
echo "Starting camera stream to file $OUTPUT_FILE"
echo "Device: $DEVICE, Resolution: ${WIDTH}x${HEIGHT}, FPS: $FPS"
# Start the GStreamer pipeline
gst-launch-1.0 -e \
    v4l2src device=$DEVICE \
    ! video/x-raw,framerate=$FPS/1,width=$WIDTH,height=$HEIGHT \
    ! videoconvert \
    ! clockoverlay valignment=bottom halignment=right font-desc="Sans, 18" xpad=5 ypad=5 \
    ! x264enc speed-preset=ultrafast tune=zerolatency \
    ! mp4mux \
    ! queue \
    ! filesink location=$OUTPUT_FILE