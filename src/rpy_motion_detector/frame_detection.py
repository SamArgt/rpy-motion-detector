import cv2
import argparse


def frame_processing(frame, blur_size, substractor, threshold, dilate_iterations):
    # Apply Gaussian blur to the frame
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(
        gray, (blur_size, blur_size), 0
    )

    # Apply background subtraction
    mask = substractor.apply(gray)

    # Apply thresholding to reduce noise
    _, thresh = cv2.threshold(
        mask, threshold, 255, cv2.THRESH_BINARY
    )

    # Dilate to fill gaps
    dilated = cv2.dilate(
        thresh, None, iterations=dilate_iterations
    )

    return dilated


def find_contours(processed_frame, min_area, max_area):
    # Find contours
    contours, _ = cv2.findContours(
        processed_frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    matching_contours = []
    for contour in contours:
        # Calculate the area of each contour
        area = cv2.contourArea(contour)
        if min_area < area < max_area:
            matching_contours.append(contour)
    return matching_contours


def draw_contour(frame, contour, put_area=True):
    # Draw the contour on the frame
    x, y, w, h = cv2.boundingRect(contour)
    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    # Add text label with the area of the contour
    if put_area:
        area = cv2.contourArea(contour)
        cv2.putText(
            frame, f"Area: {area}", (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
        )
    return frame


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Motion Detection with RTSP Streaming")
    parser.add_argument(
        "--video_device", type=str, default="/dev/video0",
        help="Path to the video device (default: /dev/video0)"
    )
    parser.add_argument(
        "--rtsp_url", type=str, default="rtsp://localhost:8554",
        help="RTSP URL for streaming (default: rtsp://localhost:8554)"
    )
    # Detection parameters
    parser.add_argument(
        "--min_area", type=int, default=500,
        help="Minimum contour area to detect (default: 500)"
    )
    parser.add_argument(
        "--max_area", type=int, default=1000000,
        help="Maximum contour area to detect (default: 1000000)"
    )
    parser.add_argument(
        "--threshold", type=int, default=127,
        help="Threshold value for binarization (default: 127)"
    )
    parser.add_argument(
        "--blur_size", type=int, default=21,
        help="Gaussian blur kernel size (default: 21)"
    )
    parser.add_argument(
        "--dilate_iterations", type=int, default=2,
        help="Number of dilation iterations (default: 2)"
    )
    parser.add_argument(
        "--background_substractor_history", type=int, default=500,
        help="History for background subtractor (default: 500)"
    )
    parser.add_argument(
        "--disable-stream-frame", action="store_false",
        dest="stream_frame",
        help="Disable streaming the frame with contours"
    )
    parser.add_argument(
        "--disable-stream-processed-frame", action="store_false",
        dest="stream_processed_frame",
        help="Disable streaming the processed frame"
    )
    args = parser.parse_args()

    background_substractor_history = args.background_substractor_history
    background_substractor = cv2.createBackgroundSubtractorMOG2(
        history=args.background_substractor_history,
        detectShadows=False,
    )
    video_capture = cv2.VideoCapture(args.video_device)
    if not video_capture.isOpened():
        print("Error: Could not open video device.")
        exit(1)
    cam_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    cam_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(video_capture.get(cv2.CAP_PROP_FPS))
    print(f"Camera resolution: {cam_width}x{cam_height}, FPS: {fps}")
    # Set the GStreamer pipelines for RTSP streaming
    # Frame with contours
    if not args.disable_stream_frame:
        gst_str_frame = (
            "appsrc ! videoconvert ! "
            "x264enc speed-preset=ultrafast tune=zerolatency bitrate=2000 ! "
            "video/x-h264,profile=baseline ! "
            f"rtspclientsink location={args.rtsp_url}/frame protocols=tcp"
        )
        print(f"GStreamer pipeline: {gst_str_frame}")
        video_writer_frame = cv2.VideoWriter(
            gst_str_frame,
            cv2.CAP_GSTREAMER,
            0,
            fps,
            (cam_width, cam_height),
            True
        )
        if not video_writer_frame.isOpened():
            print("Error: Could not open GStreamer pipeline for frame.")
            exit(1)

    # Processed frame
    if not args.disable_stream_processed_frame:
        gst_str_processed = (
            "appsrc ! videoconvert ! x264enc speed-preset=ultrafast tune=zerolatency bitrate=2000 ! "
            "video/x-h264,profile=baseline ! "
            f"rtspclientsink location={args.rtsp_url}/processed_frame protocols=tcp"
        )
        print(f"GStreamer pipeline: {gst_str_processed}")
        video_writer_processed = cv2.VideoWriter(
            gst_str_processed,
            cv2.CAP_GSTREAMER,
            0,
            fps,
            (cam_width, cam_height),
            isColor=False
        )
        if not video_writer_processed.isOpened():
            print("Error: Could not open GStreamer pipeline for processed frame.")
            exit(1)

    counter = 0
    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Error: Could not read frame.")
            break

        # Process the frame
        processed_frame = frame_processing(
            frame,
            args.blur_size,
            background_substractor,
            args.threshold,
            args.dilate_iterations,
        )

        # Find contours
        contours = find_contours(processed_frame, args.min_area, args.max_area)

        # Draw contours on the original frame
        for contour in contours:
            frame = draw_contour(frame, contour)

        # Write the frame to the RTSP stream
        if not args.disable_stream_frame:
            video_writer_frame.write(frame)
        if not args.disable_stream_processed_frame:
            video_writer_processed.write(processed_frame)
        counter += 1
