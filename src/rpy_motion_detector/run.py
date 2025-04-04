from motion_detector import MotionDetector


def run():
    detector = MotionDetector("config/default.toml")
    detector.start()


if __name__ == "__main__":
    run()
