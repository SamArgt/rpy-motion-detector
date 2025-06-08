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


def get_video_writer(rtsp_url, path, cam_width, cam_height, fps, is_color=True):
    gst_str = (
        f"appsrc ! videoconvert ! "
        "x264enc speed-preset=ultrafast tune=zerolatency bitrate=2000 ! "
        "video/x-h264,profile=baseline ! "
        f"rtspclientsink location={rtsp_url}/{path} protocols=tcp"
    )
    video_writer = cv2.VideoWriter(
        gst_str,
        cv2.CAP_GSTREAMER,
        0,
        fps,
        (cam_width, cam_height),
        is_color
    )
    if not video_writer.isOpened():
        raise RuntimeError(
            f"Could not open GStreamer pipeline for {path} at {rtsp_url}. "
        )
    return video_writer


def stream_frames(
    video_capture,
    video_writer_frame,
    video_writer_processed,
    background_substractor,
    min_area=50,
    max_area=1000000,
    threshold=127,
    blur_size=21,
    dilate_iterations=2,
    stream_frame=True,
    stream_processed_frame=True
):
    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Error: Could not read frame.")
            break

        # Process the frame
        processed_frame = frame_processing(
            frame,
            blur_size,
            background_substractor,
            threshold,
            dilate_iterations,
        )

        # Find contours
        contours = find_contours(processed_frame, min_area, max_area)

        # Draw contours on the original frame
        for contour in contours:
            frame = draw_contour(frame, contour)

        # Write the frame to the RTSP stream
        if stream_frame:
            video_writer_frame.write(frame)
        if stream_processed_frame:
            video_writer_processed.write(processed_frame)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Motion Detection with RTSP Streaming")
    parser.add_argument(
        "--video_device", type=str, default="/dev/video40",
        help="Path to the video device (default: /dev/video40)"
    )
    parser.add_argument(
        "--rtsp_url", type=str, default="rtsp://192.168.1.123:8554",
        help="RTSP URL for streaming (default: rtsp://192.168.1.123:8554)"
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
        "--disable_stream_frame", action="store_false",
        default=True,
        dest="stream_frame",
        help="Disable streaming the frame with contours"
    )
    parser.add_argument(
        "--disable_stream_processed_frame", action="store_false",
        default=True,
        dest="stream_processed_frame",
        help="Disable streaming the processed frame"
    )
    args = parser.parse_args()
    print(f"Arguments: {args.__dict__}")

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
    if args.stream_frame:
        video_writer_frame = get_video_writer(
            args.rtsp_url,
            "frame_with_contours",
            cam_width,
            cam_height,
            fps,
            is_color=True
        )
    # Processed frame
    if args.stream_processed_frame:
        video_writer_processed = get_video_writer(
            args.rtsp_url,
            "processed_frame",
            cam_width,
            cam_height,
            fps,
            is_color=False
        )
    try:
        stream_frames(
            video_capture,
            video_writer_frame if not args.disable_stream_frame else None,
            video_writer_processed if not args.disable_stream_processed_frame else None,
            background_substractor,
            min_area=args.min_area,
            max_area=args.max_area,
            threshold=args.threshold,
            blur_size=args.blur_size,
            dilate_iterations=args.dilate_iterations,
            stream_frame=args.stream_frame,
            stream_processed_frame=args.stream_processed_frame
        )
    except KeyboardInterrupt:
        print("Interrupted by user, exiting...")
    finally:
        video_capture.release()
        if args.stream_frame:
            video_writer_frame.release()
        if args.stream_processed_frame:
            video_writer_processed.release()
        cv2.destroyAllWindows()
        print("Cleanup done, exiting.")
        exit(0)
