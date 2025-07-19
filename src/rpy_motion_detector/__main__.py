if __name__ == "__main__":
    import argparse
    from rpy_motion_detector.run import run, parse_overrides
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
    parser.add_argument(
        "-o",
        "--override",
        action="append",
        help="Override configuration values using section.option=value",
    )
    args = parser.parse_args()
    overrides = parse_overrides(args.override)
    run(args.config, args.dry_run, args.log_output, overrides)
