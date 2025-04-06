from dataclasses import dataclass
import configparser


@dataclass
class LogConfig:
    level: str
    file: str


@dataclass
class CameraConfig:
    device: str


@dataclass
class DetectionConfig:
    min_area: int
    max_area: int
    threshold: int
    background_substractor_history: int
    blur_size: int = 5
    dilate_iterations: int = 2


@dataclass
class MovieConfig:
    device: str
    gstreamer_exec_file: str
    dirpath: str
    precapture_seconds: int
    max_duration: int
    record_precapture: bool


@dataclass
class PictureConfig:
    dirpath: str


@dataclass
class EventConfig:
    no_motion_timeout: int  # number of seconds without motion to wait before stopping the event
    event_gap: int  # number of seconds to wait before starting a new event after the previous one ends
    on_event_start: str
    on_event_end: str
    on_movie_start: str
    on_movie_end: str
    on_picture_save: str


@dataclass
class TmpDirConfig:
    dirpath: str


@dataclass
class MotionDetectorConfig:
    camera: CameraConfig
    detection: DetectionConfig
    movie: MovieConfig
    picture: PictureConfig
    event: EventConfig
    log: LogConfig
    tmp_dir: TmpDirConfig

    def __init__(self, config_file: str):
        config = configparser.ConfigParser()
        config.read(config_file)
        self.camera = CameraConfig(
            device=config.get('camera', 'device', fallback='/dev/video0'),
        )
        self.detection = DetectionConfig(
            min_area=config.getint('detection', 'min_area', fallback=500),
            max_area=config.getint('detection', 'max_area', fallback=5000),
            threshold=config.getint('detection', 'threshold', fallback=25),
            background_substractor_history=config.getint(
                'detection', 'background_substractor_history', fallback=500),
            blur_size=config.getint('detection', 'blur_size', fallback=21),
            dilate_iterations=config.getint('detection', 'dilate_iterations', fallback=2)
        )
        self.movie = MovieConfig(
            device=config.get('movie', 'device', fallback='/dev/video50'),
            dirpath=config.get('movie', 'dirpath', fallback='/tmp'),
            precapture_seconds=config.getint('movie', 'precapture_seconds', fallback=5),
            max_duration=config.getint('movie', 'max_duration', fallback=60),
            gstreamer_exec_file=config.get('movie', 'gstreamer_exec_file', fallback='stream_to_file.sh'),
            record_precapture=config.getboolean('movie', 'record_precapture', fallback=False)
        )
        self.picture = PictureConfig(
            dirpath=config.get('picture', 'dirpath', fallback='/tmp')
        )
        self.event = EventConfig(
            no_motion_timeout=config.getint('event', 'no_motion_timeout', fallback=20),
            event_gap=config.getint('event', 'event_gap', fallback=30),
            on_event_start=config.get('event', 'on_event_start', fallback=''),
            on_event_end=config.get('event', 'on_event_end', fallback=''),
            on_movie_start=config.get('event', 'on_movie_start', fallback=''),
            on_movie_end=config.get('event', 'on_movie_end', fallback=''),
            on_picture_save=config.get('event', 'on_picture_save', fallback='')
        )
        self.log = LogConfig(
            level=config.get('log', 'level', fallback='INFO'),
            file=config.get('log', 'file', fallback=None)
        )
        self.tmp_dir = TmpDirConfig(
            dirpath=config.get('tmp', 'dirpath', fallback='/tmp')
        )
