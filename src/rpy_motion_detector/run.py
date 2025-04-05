from .motion_detector import MotionDetector
import argparse


def run(config_file: str, dry_run: bool = False):
    detector = MotionDetector(config_file)
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
        type=str,
        help="Dry run mode, do not start the motion detector",
        action="store_true",
    )
    args = parser.parse_args()
    run(args.config, args.dry_run)
