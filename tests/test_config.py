import unittest
from rpy_motion_detector.config import MotionDetectorConfig


class TestParseExcludeZones(unittest.TestCase):
    """Test cases for the parse_exclude_zones static method."""

    def test_parse_exclude_zones_empty_string(self):
        """Test that empty string returns empty list."""
        result = MotionDetectorConfig.parse_exclude_zones("")
        self.assertEqual(result, [])

    def test_parse_exclude_zones_whitespace_only(self):
        """Test that whitespace-only string returns empty list."""
        result = MotionDetectorConfig.parse_exclude_zones("   ")
        self.assertEqual(result, [])

    def test_parse_exclude_zones_single_valid_zone(self):
        """Test parsing a single valid exclude zone."""
        result = MotionDetectorConfig.parse_exclude_zones("10,20,30,40")
        expected = [(10, 20, 30, 40)]
        self.assertEqual(result, expected)

    def test_parse_exclude_zones_multiple_valid_zones(self):
        """Test parsing multiple valid exclude zones."""
        result = MotionDetectorConfig.parse_exclude_zones("10,20,30,40;50,60,70,80")
        expected = [(10, 20, 30, 40), (50, 60, 70, 80)]
        self.assertEqual(result, expected)

    def test_parse_exclude_zones_with_whitespace(self):
        """Test parsing zones with extra whitespace."""
        result = MotionDetectorConfig.parse_exclude_zones(" 10 , 20 , 30 , 40 ; 50, 60, 70, 80 ")
        expected = [(10, 20, 30, 40), (50, 60, 70, 80)]
        self.assertEqual(result, expected)

    def test_parse_exclude_zones_invalid_too_few_coordinates(self):
        """Test that zones with fewer than 4 coordinates raise ValueError."""
        with self.assertRaises(ValueError) as context:
            MotionDetectorConfig.parse_exclude_zones("10,20,30")
        self.assertIn("must have exactly 4 coordinates", str(context.exception))

    def test_parse_exclude_zones_invalid_too_many_coordinates(self):
        """Test that zones with more than 4 coordinates raise ValueError."""
        with self.assertRaises(ValueError) as context:
            MotionDetectorConfig.parse_exclude_zones("10,20,30,40,50")
        self.assertIn("must have exactly 4 coordinates", str(context.exception))

    def test_parse_exclude_zones_invalid_non_numeric(self):
        """Test that zones with non-numeric values raise ValueError."""
        with self.assertRaises(ValueError) as context:
            MotionDetectorConfig.parse_exclude_zones("10,20,abc,40")
        self.assertIn("contains non-numeric coordinates", str(context.exception))

    def test_parse_exclude_zones_invalid_x1_greater_than_x2(self):
        """Test that zones where x1 >= x2 raise ValueError."""
        with self.assertRaises(ValueError) as context:
            MotionDetectorConfig.parse_exclude_zones("30,20,10,40")
        self.assertIn("x1 (30) must be less than x2 (10)", str(context.exception))

    def test_parse_exclude_zones_invalid_y1_greater_than_y2(self):
        """Test that zones where y1 >= y2 raise ValueError."""
        with self.assertRaises(ValueError) as context:
            MotionDetectorConfig.parse_exclude_zones("10,40,30,20")
        self.assertIn("y1 (40) must be less than y2 (20)", str(context.exception))

    def test_parse_exclude_zones_invalid_equal_x_coordinates(self):
        """Test that zones where x1 == x2 raise ValueError."""
        with self.assertRaises(ValueError) as context:
            MotionDetectorConfig.parse_exclude_zones("10,20,10,40")
        self.assertIn("x1 (10) must be less than x2 (10)", str(context.exception))

    def test_parse_exclude_zones_invalid_equal_y_coordinates(self):
        """Test that zones where y1 == y2 raise ValueError."""
        with self.assertRaises(ValueError) as context:
            MotionDetectorConfig.parse_exclude_zones("10,20,30,20")
        self.assertIn("y1 (20) must be less than y2 (20)", str(context.exception))

    def test_parse_exclude_zones_mixed_valid_invalid(self):
        """Test parsing with invalid zones raises ValueError on first invalid zone."""
        with self.assertRaises(ValueError) as context:
            MotionDetectorConfig.parse_exclude_zones("10,20,30,40;invalid;50,60,70,80;30,20,10,40")
        self.assertIn("must have exactly 4 coordinates", str(context.exception))

    def test_parse_exclude_zones_negative_coordinates(self):
        """Test parsing zones with negative coordinates (should be valid if geometry is correct)."""
        result = MotionDetectorConfig.parse_exclude_zones("-10,-20,30,40")
        expected = [(-10, -20, 30, 40)]
        self.assertEqual(result, expected)

    def test_parse_exclude_zones_zero_coordinates(self):
        """Test parsing zones with zero coordinates."""
        result = MotionDetectorConfig.parse_exclude_zones("0,0,10,10")
        expected = [(0, 0, 10, 10)]
        self.assertEqual(result, expected)

    def test_parse_exclude_zones_empty_zone_between_valid(self):
        """Test parsing with empty zone specification between valid ones."""
        result = MotionDetectorConfig.parse_exclude_zones("10,20,30,40;;50,60,70,80")
        expected = [(10, 20, 30, 40), (50, 60, 70, 80)]
        self.assertEqual(result, expected)

    def test_parse_exclude_zones_trailing_semicolon(self):
        """Test parsing with trailing semicolon."""
        result = MotionDetectorConfig.parse_exclude_zones("10,20,30,40;")
        expected = [(10, 20, 30, 40)]
        self.assertEqual(result, expected)

    def test_parse_exclude_zones_leading_semicolon(self):
        """Test parsing with leading semicolon."""
        result = MotionDetectorConfig.parse_exclude_zones(";10,20,30,40")
        expected = [(10, 20, 30, 40)]
        self.assertEqual(result, expected)

    def test_parse_exclude_zones_multiple_semicolons(self):
        """Test parsing with multiple consecutive semicolons."""
        result = MotionDetectorConfig.parse_exclude_zones("10,20,30,40;;;50,60,70,80")
        expected = [(10, 20, 30, 40), (50, 60, 70, 80)]
        self.assertEqual(result, expected)

    def test_parse_exclude_zones_empty_parts_in_zone(self):
        """Test parsing with empty parts in zone specification raises ValueError."""
        with self.assertRaises(ValueError) as context:
            MotionDetectorConfig.parse_exclude_zones("10,,30,40")
        self.assertIn("must have exactly 4 coordinates", str(context.exception))

    def test_parse_exclude_zones_large_coordinates(self):
        """Test parsing zones with large coordinate values."""
        result = MotionDetectorConfig.parse_exclude_zones("1000,2000,3000,4000")
        expected = [(1000, 2000, 3000, 4000)]
        self.assertEqual(result, expected)

    def test_parse_exclude_zones_float_values(self):
        """Test that float values raise ValueError since they're not valid integers."""
        with self.assertRaises(ValueError) as context:
            MotionDetectorConfig.parse_exclude_zones("10.5,20.9,30.1,40.8")
        self.assertIn("contains non-numeric coordinates", str(context.exception))


class TestMotionDetectorConfigExcludeZones(unittest.TestCase):
    """Test cases for exclude_zones integration in MotionDetectorConfig."""

    def setUp(self):
        """Set up test fixtures."""
        import os
        self.config_filepath = os.path.join(os.path.dirname(__file__), 'resources/test.ini')
        self.config_with_zones_filepath = os.path.join(
            os.path.dirname(__file__), 'resources/test_with_exclude_zones.ini'
        )

    def test_config_exclude_zones_from_file_missing(self):
        """Test that missing exclude_zones in config file results in empty list."""
        config = MotionDetectorConfig(self.config_filepath)
        self.assertEqual(config.detection.exclude_zones, [])

    def test_config_exclude_zones_from_file_present(self):
        """Test that exclude_zones in config file are parsed correctly."""
        config = MotionDetectorConfig(self.config_with_zones_filepath)
        expected = [(10, 20, 100, 80), (200, 150, 300, 250)]
        self.assertEqual(config.detection.exclude_zones, expected)

    def test_config_exclude_zones_from_overrides_valid(self):
        """Test that exclude_zones can be set via overrides."""
        overrides = {
            'detection': {'exclude_zones': '10,20,30,40;50,60,70,80'}
        }
        config = MotionDetectorConfig(self.config_filepath, overrides)
        expected = [(10, 20, 30, 40), (50, 60, 70, 80)]
        self.assertEqual(config.detection.exclude_zones, expected)

    def test_config_exclude_zones_from_overrides_invalid(self):
        """Test that invalid exclude_zones in overrides raises ValueError."""
        overrides = {
            'detection': {'exclude_zones': 'invalid,zone,spec'}
        }
        with self.assertRaises(ValueError):
            MotionDetectorConfig(self.config_filepath, overrides)

    def test_config_exclude_zones_from_overrides_empty(self):
        """Test that empty exclude_zones in overrides results in empty list."""
        overrides = {
            'detection': {'exclude_zones': ''}
        }
        config = MotionDetectorConfig(self.config_filepath, overrides)
        self.assertEqual(config.detection.exclude_zones, [])

    def test_config_exclude_zones_partial_override(self):
        """Test that exclude_zones override doesn't affect other detection settings."""
        overrides = {
            'detection': {
                'exclude_zones': '10,20,30,40',
                'min_area': '25000'
            }
        }
        config = MotionDetectorConfig(self.config_filepath, overrides)
        self.assertEqual(config.detection.exclude_zones, [(10, 20, 30, 40)])
        self.assertEqual(config.detection.min_area, 25000)
        # Verify other settings remain unchanged
        self.assertEqual(config.detection.max_area, 100000)
        self.assertEqual(config.detection.var_threshold, 50)


if __name__ == '__main__':
    unittest.main()
