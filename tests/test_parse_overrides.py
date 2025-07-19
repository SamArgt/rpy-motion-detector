import unittest
from rpy_motion_detector.run import parse_overrides


class TestParseOverrides(unittest.TestCase):
    """Test cases for the parse_overrides function."""

    def test_parse_overrides_empty_list(self):
        """Test that empty list returns empty dict."""
        result = parse_overrides([])
        self.assertEqual(result, {})

    def test_parse_overrides_none_input(self):
        """Test that None input returns empty dict."""
        result = parse_overrides(None)
        self.assertEqual(result, {})

    def test_parse_overrides_valid_single_override(self):
        """Test parsing a single valid override."""
        result = parse_overrides(["detection.min_area=5000"])
        expected = {"detection": {"min_area": "5000"}}
        self.assertEqual(result, expected)

    def test_parse_overrides_valid_multiple_overrides_same_section(self):
        """Test parsing multiple overrides in the same section."""
        result = parse_overrides(
            ["detection.min_area=5000", "detection.max_area=15000"]
        )
        expected = {"detection": {"min_area": "5000", "max_area": "15000"}}
        self.assertEqual(result, expected)

    def test_parse_overrides_valid_multiple_overrides_different_sections(self):
        """Test parsing multiple overrides in different sections."""
        result = parse_overrides(
            ["detection.min_area=5000", "camera.device=/dev/video1"]
        )
        expected = {
            "detection": {"min_area": "5000"},
            "camera": {"device": "/dev/video1"},
        }
        self.assertEqual(result, expected)

    def test_parse_overrides_value_with_equals_sign(self):
        """Test parsing override with equals sign in the value."""
        result = parse_overrides(['event.on_event_start=echo "test=value"'])
        expected = {"event": {"on_event_start": 'echo "test=value"'}}
        self.assertEqual(result, expected)

    def test_parse_overrides_complex_values(self):
        """Test parsing overrides with complex values."""
        overrides = [
            "camera.device=/dev/video0",
            "detection.min_area=20000",
            'event.on_event_start=echo "Motion detected at $(date)"',
            "log.level=DEBUG",
        ]
        result = parse_overrides(overrides)
        expected = {
            "camera": {"device": "/dev/video0"},
            "detection": {"min_area": "20000"},
            "event": {"on_event_start": 'echo "Motion detected at $(date)"'},
            "log": {"level": "DEBUG"},
        }
        self.assertEqual(result, expected)

    def test_parse_overrides_invalid_no_equals(self):
        """Test that invalid override without equals raises ValueError."""
        with self.assertRaises(ValueError) as context:
            parse_overrides(["detection.min_area"])
        self.assertIn("Expected format section.option=value", str(context.exception))

    def test_parse_overrides_invalid_no_dot(self):
        """Test that invalid override without dot raises ValueError."""
        with self.assertRaises(ValueError) as context:
            parse_overrides(["min_area=5000"])
        self.assertIn(
            "Invalid override 'min_area=5000'. Expected format section.option=value",
            str(context.exception),
        )

    def test_parse_overrides_invalid_empty_key(self):
        """Test that invalid override with empty key raises ValueError."""
        with self.assertRaises(ValueError) as context:
            parse_overrides(["=5000"])
        self.assertIn(
            "Invalid override '=5000'. Expected format section.option=value",
            str(context.exception),
        )

    def test_parse_overrides_invalid_empty_value(self):
        """Test that invalid override with empty value raises ValueError."""
        with self.assertRaises(ValueError) as context:
            parse_overrides(["detection.min_area="])
        self.assertIn(
            "Invalid override 'detection.min_area='. Expected format section.option=value",
            str(context.exception),
        )

    def test_parse_overrides_invalid_empty_section(self):
        """Test that invalid override with empty section raises ValueError."""
        with self.assertRaises(ValueError) as context:
            parse_overrides([".min_area=5000"])
        self.assertIn(
            "Invalid override '.min_area=5000'. Expected format section.option=value",
            str(context.exception),
        )

    def test_parse_overrides_invalid_empty_option(self):
        """Test that invalid override with empty option raises ValueError."""
        with self.assertRaises(ValueError) as context:
            parse_overrides(["detection.=5000"])
        self.assertIn(
            "Invalid override 'detection.=5000'. Expected format section.option=value",
            str(context.exception),
        )

    def test_parse_overrides_multiple_dots_in_key(self):
        """Test parsing override with multiple dots in the key (should use first dot as separator)."""
        result = parse_overrides(["section.sub.option=value"])
        expected = {"section": {"sub.option": "value"}}
        self.assertEqual(result, expected)

    def test_parse_overrides_exclude_zones_valid(self):
        """Test parsing exclude_zones override with valid zones."""
        result = parse_overrides(["detection.exclude_zones=10,20,30,40;50,60,70,80"])
        expected = {"detection": {"exclude_zones": "10,20,30,40;50,60,70,80"}}
        self.assertEqual(result, expected)

    def test_parse_overrides_exclude_zones_empty(self):
        """Test parsing exclude_zones override with empty value."""
        with self.assertRaises(ValueError) as context:
            parse_overrides(["detection.exclude_zones="])
        self.assertIn(
            "Invalid override 'detection.exclude_zones='. Expected format section.option=value",
            str(context.exception),
        )

    def test_parse_overrides_exclude_zones_complex(self):
        """Test parsing exclude_zones override with complex coordinate values."""
        result = parse_overrides(["detection.exclude_zones=100,200,300,400;-10,-20,50,60"])
        expected = {"detection": {"exclude_zones": "100,200,300,400;-10,-20,50,60"}}
        self.assertEqual(result, expected)

    def test_parse_overrides_exclude_zones_with_other_detection_params(self):
        """Test parsing exclude_zones along with other detection parameters."""
        overrides = [
            "detection.exclude_zones=10,20,30,40",
            "detection.min_area=15000",
            "detection.max_area=90000"
        ]
        result = parse_overrides(overrides)
        expected = {
            "detection": {
                "exclude_zones": "10,20,30,40",
                "min_area": "15000",
                "max_area": "90000"
            }
        }
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
