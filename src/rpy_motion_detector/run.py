from .motion_detector import MotionDetector
from .config import MotionDetectorConfig
import argparse
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Motion Detector")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to the configuration file",
    )
    parser.add_argument(
        "--dry-run",
        help="Dry run mode, do not start the motion detector",
        action="store_true",
    )
    parser.add_argument(
        "--log-output",
        help=(
            "Specify a file path for logging. If not provided, logs will be printed to stdout "
            "unless configured otherwise."
        ),
        default=None,
    )
    args = parser.parse_args()
    run(args.config, args.dry_run, args.log_output)
