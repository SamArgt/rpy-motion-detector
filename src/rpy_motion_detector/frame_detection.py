import cv2


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


def draw_contour(frame, contour):
    # Draw the contour on the frame
    x, y, w, h = cv2.boundingRect(contour)
    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    return frame


if __name__ == "__main__":

    video_device = "/dev/video40"
    min_area = 500
    max_area = 1000000
    threshold = 127
    blur_size = 21
    dilate_iterations = 2
    background_substractor_history = 500
    background_substractor = cv2.createBackgroundSubtractorMOG2(
        history=background_substractor_history,
        detectShadows=False,
    )
    rtsp_url = "rtsp://192.168.1.123:8554"
    video_capture = cv2.VideoCapture(video_device)
    if not video_capture.isOpened():
        print("Error: Could not open video device.")
        exit(1)
    cam_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    cam_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(video_capture.get(cv2.CAP_PROP_FPS))
    print(f"Camera resolution: {cam_width}x{cam_height}, FPS: {fps}")
    # Set the GStreamer pipelines for RTSP streaming
    # One for the frame and one for the processed frame
    gst_str_frame = (
        "appsrc ! videoconvert ! x264enc speed-preset=ultrafast tune=zerolatency ! "
        f"video/x-h264,profile=main ! queue ! rtspclientsink location={rtsp_url}/frame protocols=tcp"
    )
    print(f"GStreamer pipeline: {gst_str_frame}")
    video_writer_frame = cv2.VideoWriter(
        gst_str_frame,
        cv2.CAP_GSTREAMER,
        0,
        fps,
        (cam_width, cam_height),
    )
    if not video_writer_frame.isOpened():
        print("Error: Could not open GStreamer pipeline for frame.")
        exit(1)
    gst_str_processed = (
        "appsrc ! videoconvert ! x264enc speed-preset=ultrafast tune=zerolatency ! "
        f"video/x-h264,profile=main ! queue ! rtspclientsink location={rtsp_url}/processed_frame protocols=tcp"
    )
    print(f"GStreamer pipeline: {gst_str_processed}")
    video_writer_processed = cv2.VideoWriter(
        gst_str_processed,
        cv2.CAP_GSTREAMER,
        0,
        fps,
        (cam_width, cam_height),
    )
    if not video_writer_processed.isOpened():
        print("Error: Could not open GStreamer pipeline for processed frame.")
        exit(1)

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
        video_writer_frame.write(frame)
        # Write the processed frame to the RTSP stream
        # video_writer_processed.write(processed_frame)
