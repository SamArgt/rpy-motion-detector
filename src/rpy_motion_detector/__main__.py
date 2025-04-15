if __name__ == "__main__":
    import argparse
    from rpy_motion_detector.run import run
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
