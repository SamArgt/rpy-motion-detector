from rpy_motion_detector.run import run
import argparse


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
    args = parser.parse_args()
    run(args.config, args.dry_run)
