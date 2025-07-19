
import unittest
from unittest.mock import patch
import os
from rpy_motion_detector.run import run, parse_overrides


class TestIntegration(unittest.TestCase):
    """Integration tests combining parse_overrides and run functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.config_filepath = os.path.join(os.path.dirname(__file__), 'resources/test.ini')

    @patch('rpy_motion_detector.run.MotionDetector')
    @patch('rpy_motion_detector.run.signal')
    @patch('rpy_motion_detector.run.logging.basicConfig')
    def test_parse_overrides_and_run_integration(self, mock_logging, mock_signal, mock_detector_class):
        """Test the full workflow: parse overrides and use them in run function."""
        override_strings = [
            'detection.min_area=15000',
            'camera.device=/dev/video2',
            'log.level=DEBUG'
        ]
        # Parse overrides
        overrides = parse_overrides(override_strings)
        # Use parsed overrides in run function
        run(self.config_filepath, dry_run=True, overrides=overrides)
        # Verify the overrides were correctly applied
        mock_detector_class.assert_called_once()
        config_arg = mock_detector_class.call_args[0][0]
        self.assertEqual(config_arg.detection.min_area, 15000)
        self.assertEqual(config_arg.camera.device, '/dev/video2')
        self.assertEqual(config_arg.log.level, 'DEBUG')
        # Verify non-overridden value remains from config
        self.assertEqual(config_arg.detection.max_area, 100000)


if __name__ == '__main__':
    unittest.main()
