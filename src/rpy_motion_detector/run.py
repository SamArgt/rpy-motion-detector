from .motion_detector import MotionDetector
from .config import MotionDetectorConfig
import signal
import sys
import logging
import os

logger = logging.getLogger(__name__)


class SignalHandler:

    def __init__(self, resources: list):
        self.resources = resources

    def handle_signal(self, signum, frame):
        logger.warning(f"Received signal {signum}, cleaning up...\n")
        for resource in self.resources:
            del resource
        sys.exit(0)


def run(config_file: str, dry_run: bool = False, log_output: str = None):

    if not os.path.exists(config_file):
        logger.error(f"Configuration file {config_file} does not exist.")
        sys.exit(1)
    config = MotionDetectorConfig(config_file)

    logging.basicConfig(
        filename=log_output,
        filemode="a",
        level=config.log.level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Configuration file {} loaded.".format(config_file))

    detector = MotionDetector(config)
    signal_handler = SignalHandler([detector])
    # Register the signal handler
    signal.signal(signal.SIGINT, signal_handler.handle_signal)
    signal.signal(signal.SIGTERM, signal_handler.handle_signal)
    signal.signal(signal.SIGQUIT, signal_handler.handle_signal)
    signal.signal(signal.SIGHUP, signal_handler.handle_signal)
    # Start the main loop
    if dry_run:
        print("Dry run mode, not starting the motion detector.")
        return
    detector.start()
