from motion_detector import MotionDetector
import argparse


def run(config_file: str = "config/default.toml"):
    detector = MotionDetector(config_file)
    detector.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Motion Detector")
    parser.add_argument(
        "--config",
        type=str,
        default="config/default.toml",
        help="Path to the configuration file",
    )
    args = parser.parse_args()
    run()
