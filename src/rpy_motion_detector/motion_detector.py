import logging
import os
import signal
import datetime
from dataclasses import dataclass
import subprocess
import cv2
import threading
import time
from .config import MotionDetectorConfig


@dataclass
class MotionDetector:
    """Class to handle motion detection."""

    def __init__(self, config_file: str, use_default=False, log_to_stdout=False):
        if not use_default:
            if not os.path.exists(config_file):
                raise FileNotFoundError(f"Configuration file not found: {config_file}")
        self.config = MotionDetectorConfig(config_file)
        if log_to_stdout:
            self.config.log.file = None
        logging.basicConfig(
            filename=self.config.log.file,
            filemode="a",
            level=self.config.log.level,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)
        self.logger.debug("MotionDetector initialized with config: %s", self.config)

        # create movie directory if it doesn't exist
        try:
            os.makedirs(self.config.movie.dirpath)
            self.logger.debug(
                "Created movie directory: %s", self.config.movie.dirpath)
        except FileExistsError:
            pass
        # create picture directory if it doesn't exist
        try:
            os.makedirs(self.config.picture.dirpath)
            self.logger.debug(
                "Created picture directory: %s", self.config.picture.dirpath)
        except FileExistsError:
            pass

        # create tmp directory if it doesn't exist
        try:
            os.makedirs(self.config.tmp_dir.dirpath)
            self.logger.debug(
                "Created tmp directory: %s", self.config.tmp_dir)
        except FileExistsError:
            pass

        # Initialize variables
        # Opencv
        self.cap = None
        self.background_subtractor = cv2.bgsegm.createBackgroundSubtractorMOG(
            history=self.config.detection.background_substractor_history,
            nmixtures=self.config.detection.threshold,
            backgroundRatio=0.7,
        )
        # motion variables
        self.last_motion_time = 0
        self.is_event_ongoing = False
        # movie variables
        self.is_movie_recording = False
        self.gst_process = None
        self.movie_start_time = 0
        self.movie_filename = None
        self.precapture_movie_filename = None
        self.final_movie_filename = None
        # Pre-motion buffer variables
        self.frame_buffer = []

    def __del__(self):
        self.logger.warning("Cleaning up MotionDetector...")
        if self.cap is not None:
            self.cap.release()
            self.logger.debug("Released video capture.")
        if self.gst_process is not None:
            os.killpg(os.getpgid(self.gst_process.pid), signal.SIGINT)
            self.gst_process.wait()
            self.logger.debug("Released GStreamer process.")
        cv2.destroyAllWindows()
        self.logger.debug("Destroyed all OpenCV windows.")
        self.logger.warning("MotionDetector is stopped.")
        del self

    def start(self):
        self.logger.debug("Starting motion detection...")
        self.start_time = time.time()
        self.cap = cv2.VideoCapture(self.config.camera.device)
        if not self.cap.isOpened():
            self.logger.error(
                f"Error opening video stream or file: {self.config.camera.device}"
            )
            return

        self.cam_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.cam_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.cam_fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.logger.debug(
            "Camera properties: width=%s, height=%s, fps=%s",
            self.cam_width,
            self.cam_height,
            self.cam_fps,
        )
        self.buffer_size = self.config.movie.precapture_seconds * self.cam_fps

        while True:
            ret, frame = self.cap.read()
            if not ret:
                self.logger.error("Failed to capture frame from camera.")
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
        # detect motion after a soak time period
        if time.time() - self.start_time > 10:
            self.detect_motion(frame, contours)

    def detect_motion(self, frame, contours):
        motion_detected = False
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.config.detection.min_area < area < self.config.detection.max_area:
                motion_detected = True
                self.last_motion_time = cv2.getTickCount()
                break

        # handle motion detection or no motion
        if motion_detected:
            self.logger.debug("Motion detected!")
            self.handle_motion_detection(frame)
        else:
            if self.is_event_ongoing:
                time_since_last_motion = (cv2.getTickCount() - self.last_motion_time) / cv2.getTickFrequency()
                if time_since_last_motion > self.config.event.no_motion_timeout:
                    self.logger.info("No motion detected for a while, stopping event...")
                    self.stop_event()
                    self.stop_movie_recording()

        # Check if the movie recording should be stopped or restarted
        if (
            self.is_event_ongoing
            and self.is_movie_recording
            and self.gst_process is not None
        ):
            movie_duration = (cv2.getTickCount() - self.movie_start_time) / cv2.getTickFrequency()
            if movie_duration > self.config.movie.max_duration:
                self.logger.info("Movie recording duration exceeded, stopping movie...")
                self.stop_movie_recording()
                self.logger.info("Starting new movie recording...")
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
        self.logger.info("Starting event...")
        self.is_event_ongoing = True
        completed = subprocess.run(
            self.config.event.on_event_start,
            shell=True,
            capture_output=True
        )
        if completed.returncode != 0:
            self.logger.error(
                f"Error executing event start command: {completed.stderr.decode()}"
            )
        else:
            self.logger.info(f"Event start command was successfull: {completed.stdout.decode()}")
        self.take_picture(frame)

    def stop_event(self):
        self.logger.info("Stopping event...")
        self.is_event_ongoing = False
        completed = subprocess.run(
            self.config.event.on_event_end,
            shell=True,
            capture_output=True
        )
        if completed.returncode != 0:
            self.logger.error(
                f"Error executing event end command: {completed.stderr.decode()}"
            )
        else:
            self.logger.info(f"Event end command was successfull: {completed.stdout.decode()}")

    def record_precapture_frames(self, frame_buffer: list, movie_filename: str):
        self.logger.info("Recording pre-capture frames to %s", {movie_filename})
        gst_str = (
            f"appsrc ! "
            f"videoconvert ! "
            f"textoverlay text=TRIGGER valignment=top halignment=left "
            f"font-desc=\"Sans, 10\" xpad=5 ypad=5 ! "
            f"clockoverlay valignment=bottom halignment=right font-desc=\"Sans, 10\""
            f"time-format=\"%Y-%m-%d %H:%M:%S\" xpad=5 ypad=5 !"
            f"x264enc speed-preset=ultrafast tune=zerolatency ! "
            f"mp4mux ! "
            f"filesink location={movie_filename}"
        )
        video_writer = cv2.VideoWriter(
            gst_str,
            cv2.CAP_GSTREAMER,
            0,
            int(self.cam_fps),
            (int(self.cam_width), int(self.cam_height)),
            True
        )
        for frame in frame_buffer:
            # Write the frame 4 times to the video writer
            for _ in range(4):
                video_writer.write(frame)
        video_writer.release()
        self.logger.info("Pre-capture frames recorded.")

    def start_movie_recording(self):
        self.logger.info("Starting movie recording...")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.config.movie.record_precapture:
            self.movie_filename = os.path.join(self.config.tmp_dir.dirpath, f"movie_{timestamp}.mp4")
            self.precapture_movie_filename = os.path.join(
                self.config.tmp_dir.dirpath, f"precapture_movie_{timestamp}.mp4"
            )
            self.final_movie_filename = os.path.join(
                self.config.movie.dirpath, f"final_movie_{timestamp}.mp4"
            )
        else:
            self.movie_filename = os.path.join(self.config.movie.dirpath, f"movie_{timestamp}.mp4")
            self.precapture_movie_filename = None
            self.final_movie_filename = self.movie_filename
        # Record pre-capture frames in a separate thread
        if self.config.movie.record_precapture:
            # Create a thread to record the pre-capture frames
            _ = threading.Thread(
                target=self.record_precapture_frames,
                args=(self.frame_buffer, self.precapture_movie_filename),
            ).start()
        # Record movie using GStreamer
        self.logger.debug("Starting GStreamer process...")
        gst_command = [
            "gst-launch-1.0",
            "-e",
            "v4l2src",
            "device={}".format(self.config.movie.device),
            "!", "video/x-raw,framerate={}/1,width={},height={},format=NV12".format(
                int(self.cam_fps), int(self.cam_width), int(self.cam_height)
            ),
            "!", "videoconvert",
            "!", "clockoverlay", "valignment=bottom", "halignment=right", "font-desc=\"Sans, 10\"",
            "time-format=\"%Y-%m-%d %H:%M:%S\"", "xpad=5", "ypad=5",
            "!", "x264enc", "speed-preset=ultrafast", "tune=zerolatency",
            "!", "mp4mux",
            "!", "queue",
            "!", "filesink", "location={}".format(self.movie_filename),
        ]
        gst_command_printed = " ".join(gst_command)
        self.logger.debug(f"GStreamer command: {gst_command_printed}")
        # Start the GStreamer process
        try:
            self.gst_process = subprocess.Popen(gst_command, shell=False, preexec_fn=os.setsid)
        except Exception as e:
            self.logger.error(f"Failed to start GStreamer process: {e}")
        else:
            self.is_movie_recording = True
            self.movie_start_time = cv2.getTickCount()
            self.logger.info(f"GStreamer process started for recording: {self.movie_filename}")
            movie_start_command = self.config.event.on_movie_start.format(filename=self.final_movie_filename)
            self.logger.debug(f"Running movie start command: {movie_start_command}")
            completed = subprocess.run(
                movie_start_command,
                shell=True,
                capture_output=True
            )
            if completed.returncode != 0:
                self.logger.error(
                    f"Error executing movie start command: {completed.stderr.decode()}"
                )
            else:
                self.logger.info(f"Movie start command was successful: {completed.stdout.decode()}")

    def concatenate_movies(self, movie1: str, movie2: str, output_movie: str) -> subprocess.CompletedProcess:
        self.logger.info("Concatenating movies {} and {} to {}".format(movie1, movie2, output_movie))
        # Use ffmpeg to concatenate the movies
        # create a temporary file to store the list of files
        file_list = os.path.join(self.config.tmp_dir.dirpath, 'file_list.txt')
        with open(file_list, 'wb') as temp_file:
            temp_file.write(f"file '{movie1}'\n".encode())
            temp_file.write(f"file '{movie2}'\n".encode())

        cmd = f"ffmpeg -f concat -safe 0 -i {file_list} -c copy {output_movie}"
        self.logger.debug(f"Running command: {cmd}")
        completed = subprocess.run(
            cmd,
            capture_output=True,
            shell=True
        )
        return completed

    def on_movie_end_action(self, precapture_movie_filename: str, movie_filename: str, final_movie_name: str):
        # Concatenate the pre-capture and movie files
        if self.config.movie.record_precapture:
            completed = self.concatenate_movies(precapture_movie_filename, movie_filename, final_movie_name)
            if completed.returncode != 0:
                self.logger.error(f"Error concatenating movies: {completed.stderr.decode()}")
                final_movie_name = movie_filename
            else:
                self.logger.info(f"Movies concatenated successfully: {final_movie_name}")
        # Run the movie end command
        completed = subprocess.run(
            self.config.event.on_movie_end.format(filename=final_movie_name),
            shell=True,
            capture_output=True
        )
        if completed.returncode != 0:
            self.logger.error(
                f"Error executing movie end command: {completed.stderr.decode()}"
            )
        else:
            self.logger.info(f"Movie end command was successful: {completed.stdout.decode()}")

    def stop_movie_recording(self):
        self.logger.info("Stopping movie recording...")
        if self.gst_process is not None:
            try:
                # Terminate the GStreamer process
                os.killpg(os.getpgid(self.gst_process.pid), signal.SIGINT)
                self.gst_process.wait()
                self.logger.info(f"GStreamer process stopped. Movie saved to: {self.movie_filename}")
                self.gst_process = None
                self.is_movie_recording = False
                self.movie_start_time = 0
                _ = threading.Thread(
                    target=self.on_movie_end_action,
                    args=(self.precapture_movie_filename, self.movie_filename, self.final_movie_filename),
                ).start()
                self.precapture_movie_filename = None,
                self.movie_filename = None
                self.final_movie_filename = None
            except Exception as e:
                self.logger.error(f"Failed to stop GStreamer process: {e}")

    def take_picture(self, frame):
        self.logger.info("Taking picture...")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.config.picture.dirpath, f"picture_{timestamp}.jpg")
        cv2.imwrite(filename, frame)
        picture_command = self.config.event.on_picture_save.format(filename=filename)
        self.logger.debug(f"Running picture command: {picture_command}")
        completed = subprocess.run(
            picture_command,
            shell=True,
            capture_output=True
        )
        if completed.returncode != 0:
            self.logger.error(
                f"Error executing picture taken command: {completed.stderr.decode()}"
            )
        else:
            self.logger.info(f"Picture taken command was successfull: {completed.stdout.decode()}")
