import unittest
from unittest.mock import patch
import os
from rpy_motion_detector.run import run


class TestRunFunction(unittest.TestCase):
    """Test cases for the run function."""

    def setUp(self):
        """Set up test fixtures."""
        self.config_filepath = os.path.join(os.path.dirname(__file__), 'resources/test.ini')

    @patch('sys.exit')
    def test_run_nonexistent_config_file(self, mock_exit):
        """Test that run exits with error for non-existent config file."""
        run('nonexistent/config.ini', dry_run=True)
        mock_exit.assert_called_once_with(1)

    @patch('rpy_motion_detector.run.MotionDetector')
    @patch('rpy_motion_detector.run.signal')
    @patch('rpy_motion_detector.run.logging.basicConfig')
    def test_run_dry_run_mode(self, mock_logging, mock_signal, mock_detector_class):
        """Test run function in dry run mode."""
        with patch('builtins.print') as mock_print:
            run(self.config_filepath, dry_run=True)
            mock_print.assert_called_once_with("Dry run mode, not starting the motion detector.")
            # Ensure MotionDetector was created but start() was not called
            mock_detector_class.assert_called_once()
            mock_detector_instance = mock_detector_class.return_value
            mock_detector_instance.start.assert_not_called()

    @patch('rpy_motion_detector.run.MotionDetector')
    @patch('rpy_motion_detector.run.signal')
    @patch('rpy_motion_detector.run.logging.basicConfig')
    def test_run_normal_mode(self, mock_logging, mock_signal, mock_detector_class):
        """Test run function in normal mode."""
        run(self.config_filepath, dry_run=False)
        # Ensure MotionDetector was created and start() was called
        mock_detector_class.assert_called_once()
        mock_detector_instance = mock_detector_class.return_value
        mock_detector_instance.start.assert_called_once()

    @patch('rpy_motion_detector.run.MotionDetector')
    @patch('rpy_motion_detector.run.signal')
    @patch('rpy_motion_detector.run.logging.basicConfig')
    def test_run_with_log_output(self, mock_logging, mock_signal, mock_detector_class):
        """Test run function with log output file."""
        log_file = "tmp/test.log"
        run(self.config_filepath, dry_run=True, log_output=log_file)
        mock_logging.assert_called_once()
        args, kwargs = mock_logging.call_args
        self.assertEqual(kwargs['filename'], log_file)

    @patch('rpy_motion_detector.run.MotionDetector')
    @patch('rpy_motion_detector.run.signal')
    @patch('rpy_motion_detector.run.logging.basicConfig')
    def test_run_with_overrides(self, mock_logging, mock_signal, mock_detector_class):
        """Test run function with configuration overrides."""
        overrides = {
            'detection': {'min_area': '15000', 'max_area': '80000'},
            'camera': {'device': '/dev/video2'}
        }
        run(self.config_filepath, dry_run=True, overrides=overrides)
        # Check that MotionDetector was called with a config that includes overrides
        mock_detector_class.assert_called_once()
        config_arg = mock_detector_class.call_args[0][0]
        # Verify that the overrides were applied
        self.assertEqual(config_arg.detection.min_area, 15000)
        self.assertEqual(config_arg.detection.max_area, 80000)
        self.assertEqual(config_arg.camera.device, '/dev/video2')
        # Verify that non-overridden values remain from config file
        self.assertEqual(config_arg.detection.var_threshold, 50)

    @patch('rpy_motion_detector.run.MotionDetector')
    @patch('rpy_motion_detector.run.signal')
    @patch('rpy_motion_detector.run.logging.basicConfig')
    def test_run_with_complex_overrides(self, mock_logging, mock_signal, mock_detector_class):
        """Test run function with complex configuration overrides."""
        overrides = {
            'event': {
                'on_event_start': 'echo "Custom start message"',
                'no_motion_timeout': '45'
            },
            'log': {'level': 'DEBUG'},
            'movie': {'enable': 'false'}
        }
        run(self.config_filepath, dry_run=True, overrides=overrides)
        # Check that MotionDetector was called with a config that includes overrides
        mock_detector_class.assert_called_once()
        config_arg = mock_detector_class.call_args[0][0]
        # Verify that the overrides were applied
        self.assertEqual(config_arg.event.on_event_start, 'echo "Custom start message"')
        self.assertEqual(config_arg.event.no_motion_timeout, 45)
        self.assertEqual(config_arg.log.level, 'DEBUG')
        self.assertEqual(config_arg.movie.enable, False)
        # Verify that non-overridden values remain from config file
        self.assertEqual(config_arg.event.event_gap, 30)

    @patch('rpy_motion_detector.run.MotionDetector')
    @patch('rpy_motion_detector.run.signal')
    @patch('rpy_motion_detector.run.logging.basicConfig')
    def test_run_signal_handler_registration(self, mock_logging, mock_signal, mock_detector_class):
        """Test that signal handlers are properly registered."""
        run(self.config_filepath, dry_run=True)
        # Check that signal handlers were registered
        expected_signals = [
            mock_signal.SIGINT,
            mock_signal.SIGTERM,
            mock_signal.SIGQUIT,
            mock_signal.SIGHUP
        ]
        # Verify signal.signal was called for each expected signal
        self.assertEqual(mock_signal.signal.call_count, len(expected_signals))
        for call in mock_signal.signal.call_args_list:
            signal_type = call[0][0]
            self.assertIn(signal_type, expected_signals)

    @patch('rpy_motion_detector.run.MotionDetector')
    @patch('rpy_motion_detector.run.signal')
    @patch('rpy_motion_detector.run.logging.basicConfig')
    def test_run_with_new_section_override(self, mock_logging, mock_signal, mock_detector_class):
        """Test run function with override that creates a new section."""
        overrides = {
            'new_section': {'new_option': 'new_value'},
            'detection': {'min_area': '25000'}
        }
        run(self.config_filepath, dry_run=True, overrides=overrides)
        # Should not raise an error and should complete successfully
        mock_detector_class.assert_called_once()
        config_arg = mock_detector_class.call_args[0][0]
        # Verify that existing overrides were applied
        self.assertEqual(config_arg.detection.min_area, 25000)

    @patch('rpy_motion_detector.run.MotionDetector')
    @patch('rpy_motion_detector.run.signal')
    @patch('rpy_motion_detector.run.logging.basicConfig')
    def test_run_with_exclude_zones_override(self, mock_logging, mock_signal, mock_detector_class):
        """Test run function with exclude_zones override."""
        overrides = {
            'detection': {'exclude_zones': '10,20,30,40;50,60,70,80'}
        }
        run(self.config_filepath, dry_run=True, overrides=overrides)
        mock_detector_class.assert_called_once()
        config_arg = mock_detector_class.call_args[0][0]
        # Verify that exclude_zones were parsed correctly
        expected_zones = [(10, 20, 30, 40), (50, 60, 70, 80)]
        self.assertEqual(config_arg.detection.exclude_zones, expected_zones)

    @patch('rpy_motion_detector.run.MotionDetector')
    @patch('rpy_motion_detector.run.signal')
    @patch('rpy_motion_detector.run.logging.basicConfig')
    def test_run_with_invalid_exclude_zones_override(self, mock_logging, mock_signal, mock_detector_class):
        """Test run function with invalid exclude_zones override raises ValueError."""
        overrides = {
            'detection': {'exclude_zones': 'invalid,zone,spec'}
        }
        with self.assertRaises(ValueError):
            run(self.config_filepath, dry_run=True, overrides=overrides)

    @patch('rpy_motion_detector.run.MotionDetector')
    @patch('rpy_motion_detector.run.signal')
    @patch('rpy_motion_detector.run.logging.basicConfig')
    def test_run_with_empty_exclude_zones_override(self, mock_logging, mock_signal, mock_detector_class):
        """Test run function with empty exclude_zones override."""
        overrides = {
            'detection': {'exclude_zones': ''}
        }
        run(self.config_filepath, dry_run=True, overrides=overrides)
        mock_detector_class.assert_called_once()
        config_arg = mock_detector_class.call_args[0][0]
        # Verify that empty exclude_zones result in empty list
        self.assertEqual(config_arg.detection.exclude_zones, [])


if __name__ == '__main__':
    unittest.main()
