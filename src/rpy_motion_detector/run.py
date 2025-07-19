from .motion_detector import MotionDetector
from .config import MotionDetectorConfig
from typing import Dict, Optional
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


def parse_overrides(entries: Optional[list]) -> Dict[str, Dict[str, str]]:
    overrides: Dict[str, Dict[str, str]] = {}
    if not entries:
        return overrides
    for item in entries:
        try:
            key, value = item.split("=", 1)
            if not key or not value:
                raise ValueError(
                    f"Invalid override '{item}'. Both key and value must be non-empty."
                )
            if "." not in key:
                raise ValueError(
                    f"Invalid override '{item}'. Key must contain a section and option separated by a '.'."
                )
            section, option = key.split(".", 1)
            if not section or not option:
                raise ValueError(
                    f"Invalid override '{item}'. Section and option must be non-empty."
                )
            if not section or not option:
                raise ValueError(
                    f"Invalid override '{item}'. Both section and option must be non-empty."
                )
        except ValueError as exc:
            raise ValueError(
                f"Invalid override '{item}'. Expected format section.option=value"
            ) from exc
        overrides.setdefault(section, {})[option] = value
    return overrides


def run(
    config_file: str,
    dry_run: bool = False,
    log_output: str = "rpy_motion_detector.log",
    overrides: Optional[Dict[str, Dict[str, str]]] = None,
):

    if not os.path.exists(config_file):
        logger.error(f"Configuration file {config_file} does not exist.")
        sys.exit(1)
    config = MotionDetectorConfig(config_file, overrides)

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
