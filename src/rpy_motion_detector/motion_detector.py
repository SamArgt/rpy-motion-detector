from typing import Tuple
import logging
import os
import signal
import datetime
from dataclasses import dataclass
import subprocess
import cv2
import threading
import time
import shutil
from .frame_detection import draw_contour, find_contours, frame_processing
from .config import MotionDetectorConfig


logger = logging.getLogger(__name__)


@dataclass
class MotionDetector:
    """Class to handle motion detection."""

    def __init__(self, config: MotionDetectorConfig, use_default=False):

        self.config = config
        logger.debug("MotionDetector initialized with config: %s", self.config)

        # create movie directory if it doesn't exist
        try:
            os.makedirs(self.config.movie.dirpath)
            logger.debug("Created movie directory: %s", self.config.movie.dirpath)
        except FileExistsError:
            pass
        # create picture directory if it doesn't exist
        try:
            os.makedirs(self.config.picture.dirpath)
            logger.debug("Created picture directory: %s", self.config.picture.dirpath)
        except FileExistsError:
            pass

        # create tmp directory if it doesn't exist
        try:
            os.makedirs(self.config.tmp_dir.dirpath)
            logger.debug("Created tmp directory: %s", self.config.tmp_dir)
        except FileExistsError:
            pass

        # Initialize variables
        # Opencv
        self.cap = None
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=self.config.detection.background_substractor_history,
            varThreshold=self.config.detection.var_threshold,
            detectShadows=False,
        )
        # detection variables
        self.detected_motion_consecutive_frames = 0
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
        self.is_precapture_recorded = {}

    def __del__(self):
        logger.warning("Cleaning up MotionDetector...")
        if self.cap is not None:
            self.cap.release()
            logger.info("Released video capture.")
        if self.gst_process is not None:
            os.killpg(os.getpgid(self.gst_process.pid), signal.SIGINT)
            self.gst_process.wait()
            logger.info("Released GStreamer process.")
        self.stop_event()
        self.stop_movie_recording()
        # Cleanup tmp directory
        if os.path.exists(self.config.tmp_dir.dirpath):
            logger.info("Cleaning up tmp directory...")
            for filename in os.listdir(self.config.tmp_dir.dirpath):
                file_path = os.path.join(self.config.tmp_dir.dirpath, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                        logger.debug("Deleted file: %s", file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        logger.debug("Deleted directory: %s", file_path)
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}. Reason: {e}")
            logger.debug("Deleted tmp directory content.")
        cv2.destroyAllWindows()
        logger.info("Destroyed all OpenCV windows.")
        logger.warning("MotionDetector is stopped.")
        del self

    def start(self):
        logger.debug("Starting motion detection...")
        self.start_time = time.time()
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
        self.buffer_size = self.config.movie.precapture_seconds * self.cam_fps

        while True:
            ret, frame = self.cap.read()
            if not ret:
                logger.error("Failed to capture frame from camera.")
                break
            # add to the frame buffer
            self.frame_buffer.append(frame.copy())
            if len(self.frame_buffer) > self.buffer_size:
                self.frame_buffer.pop(0)
            # Process the frame for motion detection
            self.process_frame(frame)

    def process_frame(self, frame):
        processed_frame = frame_processing(
            frame,
            self.background_subtractor,
            self.config.detection.bin_threshold,
            self.config.detection.blur_size,
            self.config.detection.dilate_iterations,
        )
        # Find contours
        contours = find_contours(
            processed_frame,
            min_area=self.config.detection.min_area,
            max_area=self.config.detection.max_area,
        )
        # detect motion after a soak time period
        if time.time() - self.start_time > 10:
            self.detect_motion(frame, contours)

    def detect_motion(self, frame, contours):
        motion_detected = False
        if len(contours) > 0:
            logger.debug(
                "Motion detected"
            )
            self.detected_motion_consecutive_frames += 1
            motion_detected = True
            self.last_motion_time = cv2.getTickCount()

        # handle motion detection or no motion
        if (
            motion_detected
            and self.detected_motion_consecutive_frames
            >= self.config.detection.consecutive_frames
        ):
            logger.debug(
                "Motion detected and number of consecutive frames: %s",
                self.detected_motion_consecutive_frames,
            )
            self.handle_motion_detection(frame, contours)
        elif motion_detected:
            logger.debug(
                "Motion detected but not enough consecutive frames %s",
                self.detected_motion_consecutive_frames,
            )
        else:
            self.detected_motion_consecutive_frames = 0
            if self.is_event_ongoing:
                time_since_last_motion = (
                    cv2.getTickCount() - self.last_motion_time
                ) / cv2.getTickFrequency()
                if time_since_last_motion > self.config.event.no_motion_timeout:
                    logger.info("No motion detected for a while, stopping event...")
                    self.stop_event()
                    self.stop_movie_recording()

        # Check if the movie recording should be stopped or restarted
        if (
            self.is_event_ongoing
            and self.is_movie_recording
            and self.gst_process is not None
        ):
            movie_duration = (
                cv2.getTickCount() - self.movie_start_time
            ) / cv2.getTickFrequency()
            if movie_duration > self.config.movie.max_duration:
                logger.info("Movie recording duration exceeded, stopping movie...")
                self.stop_movie_recording()
                logger.info("Starting new movie recording...")
                self.start_movie_recording()
        elif self.is_movie_recording:
            # If movie recording is ongoing but event is not, stop the movie
            self.stop_movie_recording()

    def handle_motion_detection(self, frame, contours):

        if not self.is_event_ongoing:
            self.start_event(frame, contours)

        if not self.is_movie_recording and not self.config.movie.enable:
            self.start_movie_recording()

    def start_event(self, frame, contours):
        logger.info("Starting event...")
        self.is_event_ongoing = True
        completed = subprocess.run(
            self.config.event.on_event_start, shell=True, capture_output=True
        )
        if completed.returncode != 0:
            logger.error(
                f"Error executing event start command: {completed.stderr.decode()}"
            )
        else:
            logger.info(
                f"Event start command was successfull: {completed.stdout.decode()}"
            )
        if self.config.picture.enable:
            self.take_picture(frame, contours)

    def stop_event(self):
        logger.info("Stopping event...")
        self.is_event_ongoing = False
        completed = subprocess.run(
            self.config.event.on_event_end, shell=True, capture_output=True
        )
        if completed.returncode != 0:
            logger.error(
                f"Error executing event end command: {completed.stderr.decode()}"
            )
        else:
            logger.info(
                f"Event end command was successfull: {completed.stdout.decode()}"
            )

    def record_precapture_frames(self, frame_buffer: list, movie_filename: str):
        logger.info("Recording pre-capture frames to %s", {movie_filename})
        gst_str = (
            f"appsrc ! "
            f"videoconvert ! "
            f"textoverlay text=TRIGGER valignment=top halignment=left "
            f'font-desc="Sans, 10" xpad=5 ypad=5 ! '
            f'clockoverlay valignment=bottom halignment=right font-desc="Sans, 10"'
            f'time-format="%Y-%m-%d %H:%M:%S" xpad=5 ypad=5 !'
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
            True,
        )
        for frame in frame_buffer:
            # Write the frame 4 times to the video writer
            for _ in range(4):
                video_writer.write(frame)
        video_writer.release()
        self.is_precapture_recorded[movie_filename] = True
        logger.info("Pre-capture frames recorded.")

    def start_movie_recording(self):
        logger.info("Starting movie recording...")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.config.movie.record_precapture:
            self.movie_filename = os.path.join(
                self.config.tmp_dir.dirpath, f"movie_{timestamp}.mp4"
            )
            self.precapture_movie_filename = os.path.join(
                self.config.tmp_dir.dirpath, f"precapture_movie_{timestamp}.mp4"
            )
            self.final_movie_filename = os.path.join(
                self.config.movie.dirpath, f"final_movie_{timestamp}.mp4"
            )
        else:
            self.movie_filename = os.path.join(
                self.config.movie.dirpath, f"movie_{timestamp}.mp4"
            )
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
        logger.debug("Starting GStreamer process...")
        gst_command = [
            "gst-launch-1.0",
            "-e",
            "v4l2src",
            "device={}".format(self.config.movie.device),
            "!",
            "video/x-raw,framerate={}/1,width={},height={},format=NV12".format(
                int(self.cam_fps), int(self.cam_width), int(self.cam_height)
            ),
            "!",
            "videoconvert",
            "!",
            "clockoverlay",
            "valignment=bottom",
            "halignment=right",
            'font-desc="Sans, 10"',
            'time-format="%Y-%m-%d %H:%M:%S"',
            "xpad=5",
            "ypad=5",
            "!",
            "x264enc",
            "speed-preset=ultrafast",
            "tune=zerolatency",
            "!",
            "mp4mux",
            "!",
            "queue",
            "!",
            "filesink",
            "location={}".format(self.movie_filename),
        ]
        gst_command_printed = " ".join(gst_command)
        logger.debug(f"GStreamer command: {gst_command_printed}")
        # Start the GStreamer process
        try:
            self.gst_process = subprocess.Popen(
                gst_command, shell=False, preexec_fn=os.setsid
            )
        except Exception as e:
            logger.error(f"Failed to start GStreamer process: {e}")
        else:
            self.is_movie_recording = True
            self.movie_start_time = cv2.getTickCount()
            logger.info(
                f"GStreamer process started for recording: {self.movie_filename}"
            )
            movie_start_command = self.config.event.on_movie_start.format(
                filename=self.final_movie_filename
            )
            logger.debug(f"Running movie start command: {movie_start_command}")
            completed = subprocess.run(
                movie_start_command, shell=True, capture_output=True
            )
            if completed.returncode != 0:
                logger.error(
                    f"Error executing movie start command: {completed.stderr.decode()}"
                )
            else:
                logger.info(
                    f"Movie start command was successful: {completed.stdout.decode()}"
                )

    def concatenate_movies(
        self, movie1: str, movie2: str, output_movie: str
    ) -> Tuple[bool, str]:
        # Check if precapture movie exists. Wait at most 60 seconds for it to be created
        movie1_exists = False
        for _ in range(30):
            if self.is_precapture_recorded.get(movie1):
                movie1_exists = True
                break
            time.sleep(1)
        if not movie1_exists:
            logger.warning("Pre-capture movie not found, skipping concatenation.")
            return (False, "Pre-capture movie not found.")
        # create a temporary file to store the list of files
        # Use ffmpeg to concatenate the movies
        logger.info(
            "Concatenating movies {} and {} to {}".format(movie1, movie2, output_movie)
        )
        file_list = os.path.join(self.config.tmp_dir.dirpath, "file_list.txt")
        with open(file_list, "wb") as temp_file:
            temp_file.write(f"file '{movie1}'\n".encode())
            temp_file.write(f"file '{movie2}'\n".encode())

        cmd = f"ffmpeg -f concat -safe 0 -i {file_list} -c copy {output_movie}"
        logger.debug(f"Running command: {cmd}")
        completed = subprocess.run(cmd, capture_output=True, shell=True)
        # TODO: investigate why ffmpeg returns 1 even if the command succeeds
        return (completed.returncode == 0, completed.stderr.decode())

    def on_movie_end_action(
        self, precapture_movie_filename: str, movie_filename: str, final_movie_name: str
    ):
        # Concatenate the pre-capture and movie files
        if self.config.movie.record_precapture:
            success, error_message = self.concatenate_movies(
                precapture_movie_filename, movie_filename, final_movie_name
            )
            if success:
                logger.error(f"Error concatenating movies: {error_message}")
                final_movie_name = movie_filename
            else:
                logger.info(f"Movies concatenated successfully: {final_movie_name}")
        # Run the movie end command
        completed = subprocess.run(
            self.config.event.on_movie_end.format(filename=final_movie_name),
            shell=True,
            capture_output=True,
        )
        if completed.returncode != 0:
            logger.error(
                f"Error executing movie end command: {completed.stderr.decode()}"
            )
        else:
            logger.info(
                f"Movie end command was successful: {completed.stdout.decode()}"
            )

    def stop_movie_recording(self):
        logger.info("Stopping movie recording...")
        if self.gst_process is not None:
            try:
                # Terminate the GStreamer process
                os.killpg(os.getpgid(self.gst_process.pid), signal.SIGINT)
                self.gst_process.wait()
                logger.info(
                    f"GStreamer process stopped. Movie saved to: {self.movie_filename}"
                )
                self.gst_process = None
                self.is_movie_recording = False
                self.movie_start_time = 0
                _ = threading.Thread(
                    target=self.on_movie_end_action,
                    args=(
                        self.precapture_movie_filename,
                        self.movie_filename,
                        self.final_movie_filename,
                    ),
                ).start()
                self.precapture_movie_filename = (None,)
                self.movie_filename = None
                self.final_movie_filename = None
            except Exception as e:
                logger.error(f"Failed to stop GStreamer process: {e}")

    def take_picture(self, frame, contours=None):
        if contours is not None:
            for contour in contours:
                frame = draw_contour(frame, contour, put_area=True)
        logger.info("Taking picture...")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.config.picture.dirpath, f"picture_{timestamp}.jpg")
        cv2.imwrite(filename, frame)
        picture_command = self.config.event.on_picture_save.format(filename=filename)
        logger.debug(f"Running picture command: {picture_command}")
        completed = subprocess.run(picture_command, shell=True, capture_output=True)
        if completed.returncode != 0:
            logger.error(
                f"Error executing picture taken command: {completed.stderr.decode()}"
            )
        else:
            logger.info(
                f"Picture taken command was successfull: {completed.stdout.decode()}"
            )
