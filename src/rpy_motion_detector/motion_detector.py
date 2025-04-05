import logging
import os
import datetime
from dataclasses import dataclass
import subprocess
import cv2
from config import MotionDetectorConfig

# Set up logging configuration
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class MotionDetector:
    """Class to handle motion detection."""

    def __init__(self, config_file: str):
        self.config = MotionDetectorConfig(config_file)
        logger.debug("MotionDetector initialized with config: %s", self.config)

        # create movie directory if it doesn't exist
        if not os.path.exists(self.config.movie.dirpath):
            os.makedirs(self.config.movie.dirpath)
            logger.debug(
                "Created movie directory: %s", self.config.movie.dirpath)

        # create picture directory if it doesn't exist
        if not os.path.exists(self.config.picture.dirpath):
            os.makedirs(self.config.picture.dirpath)
            logger.debug(
                "Created picture directory: %s", self.config.picture.dirpath)

        # Initialize variables
        self.cap = None
        self.background_subtractor = cv2.bgsegm.createBackgroundSubtractorMOG(
            history=self.config.detection.background_substractor_history,
            nmixtures=self.config.detection.threshold,
            backgroundRatio=0.7,
        )
        self.last_motion_time = 0
        self.is_event_ongoing = False
        self.is_movie_recording = False
        self.gst_process = None
        self.movie_start_time = 0

        # Pre-motion buffer variables
        self.buffer_size = self.config.movie.precapture_seconds * self.config.camera.fps
        self.frame_buffer = []

    def start(self):
        logger.debug("Starting motion detection...")
        self.cap = cv2.VideoCapture(self.config.camera.device)
        if not self.cap.isOpened():
            logger.error(
                f"Error opening video stream or file: {self.config.camera.device}"
            )
            return

        self.cam_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.cam_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.cam_fps = self.cap.get(cv2.CAP_PROP_FPS)
        logger.debug(
            "Camera properties: width=%s, height=%s, fps=%s",
            self.cam_width,
            self.cam_height,
            self.cam_fps,
        )

        while True:
            ret, frame = self.cap.read()
            if not ret:
                logger.error("Failed to capture frame from camera.")
                break

            # Process the frame for motion detection
            self.process_frame(frame)

    def process_frame(self, frame):
        # Add the current frame to the buffer
        self.frame_buffer.append(frame.copy())
        if len(self.frame_buffer) > self.buffer_size:
            self.frame_buffer.pop(0)

        # Process frame for motion detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (self.config.detection.blur_size, self.config.detection.blur_size), 0)

        # Apply background subtraction
        mask = self.background_subtractor.apply(gray)

        # Apply thresholding to reduce noise
        _, thresh = cv2.threshold(mask, self.config.detection.threshold, 255, cv2.THRESH_BINARY)

        # Dilate to fill gaps
        dilated = cv2.dilate(thresh, None, iterations=self.config.detection.dilate_iterations)

        # Find contours
        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        motion_detected = False
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.config.detection.min_area < area < self.config.detection.max_area:
                motion_detected = True
                self.last_motion_time = cv2.getTickCount()
                break

        # handle motion detection or no motion
        if motion_detected:
            logger.debug("Motion detected!")
            self.handle_motion_detection(frame)
        else:
            if self.is_event_ongoing:
                time_since_last_motion = (cv2.getTickCount() - self.last_motion_time) / cv2.getTickFrequency()
                if time_since_last_motion > self.config.event.no_motion_timeout:
                    logger.info("No motion detected for a while, stopping event...")
                    self.stop_event()
                    self.stop_movie_recording()

        # Write frame to video file if recording
        if (
            self.is_event_ongoing
            and self.is_movie_recording
            and self.gst_process is not None
        ):
            movie_duration = (cv2.getTickCount() - self.movie_start_time) / cv2.getTickFrequency()
            if movie_duration > self.config.movie.max_duration:
                logger.info("Movie recording duration exceeded, stopping movie...")
                self.stop_movie_recording()
                logger.info("Starting new movie recording...")
                self.start_movie_recording()
        elif self.is_movie_recording:
            # If movie recording is ongoing but event is not, stop the movie
            self.stop_movie_recording()

    def handle_motion_detection(self, frame):

        if not self.is_event_ongoing:
            self.start_event(frame)

        if not self.is_movie_recording:
            self.start_movie_recording()

    def start_event(self, frame):
        logger.info("Starting event...")
        self.is_event_ongoing = True
        res = os.system(self.config.event.on_event_start)
        if res != 0:
            logger.error(
                f"Error executing event start command: {self.config.event.on_event_start}"
            )
        else:
            logger.info("Event start command was successfull.")
        self.take_picture(frame)

    def stop_event(self):
        logger.info("Stopping event...")
        self.is_event_ongoing = False
        res = os.system(self.config.event.on_event_end)
        if res != 0:
            logger.error(
                f"Error executing event end command: {self.config.event.on_event_end}"
            )
        else:
            logger.info("Event end command was successfull.")

    def start_movie_recording(self):
        logger.info("Starting movie recording...")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.config.movie.dirpath, f"movie_{timestamp}.mp4")
        # Construct the GStreamer pipeline command
        gst_command = [
            "gst-launch-1.0",
            "v4l2src", f"device={self.config.movie.device}",
            "!", "video/x-raw,framerate={}/1,width={},height={}".format(
                self.cam_fps, self.cam_width, self.cam_height
            ),
            "!", "videoconvert",
            "!", "x264enc", "tune=zerolatency", "bitrate=500",
            "!", "mp4mux",
            "!", f"filesink location={filename}"
        ]
        # Start the GStreamer process
        try:
            self.gst_process = subprocess.Popen(gst_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.is_movie_recording = True
            logger.info(f"GStreamer process started for recording: {filename}")
            res = os.system(self.config.event.on_movie_start)
            if res != 0:
                logger.error(
                    f"Error executing movie start command: {self.config.event.on_movie_start}"
                )
            else:
                logger.info("Movie start command was successful.")
        except Exception as e:
            logger.error(f"Failed to start GStreamer process: {e}")
        self.gst_process = None

    def stop_movie_recording(self):
        logger.info("Stopping movie recording...")
        if self.gst_process is not None:
            try:
                # Terminate the GStreamer process
                self.gst_process.terminate()
                self.gst_process.wait()
                logger.info(f"GStreamer process stopped. Movie saved to: {self.movie_filename}")
                self.gst_process = None
                self.is_movie_recording = False
                res = os.system(self.config.event.on_movie_end)
                if res != 0:
                    logger.error(
                        f"Error executing movie end command: {self.config.event.on_movie_end}"
                    )
                else:
                    logger.info("Movie end command was successful.")
            except Exception as e:
                logger.error(f"Failed to stop GStreamer process: {e}")

    def take_picture(self, frame):
        logger.info("Taking picture...")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.config.picture.dirpath, f"picture_{timestamp}.jpg")
        cv2.imwrite(filename, frame)
        res = os.system(self.config.event.on_picture_taken)
        if res != 0:
            logger.error(
                f"Error executing picture taken command: {self.config.event.on_picture_taken}"
            )
        else:
            logger.info("Picture taken command was successfull.")
