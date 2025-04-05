from rpy_motion_detector.run import run
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Motion Detector")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to the configuration file",
    )
    args = parser.parse_args()
    run(args.config)
