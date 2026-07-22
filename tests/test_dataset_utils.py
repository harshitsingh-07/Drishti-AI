import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dataset_utils import parse_filename


class ParseFilenameTests(unittest.TestCase):
    def test_parses_simple_filename(self) -> None:
        object_name, distance = parse_filename("chair_1m_01.jpg")
        self.assertEqual(object_name, "chair")
        self.assertEqual(distance, 1.0)

    def test_parses_decimal_distance(self) -> None:
        object_name, distance = parse_filename("water_bottle_2.5m_03.jpg")
        self.assertEqual(object_name, "water bottle")
        self.assertEqual(distance, 2.5)

    def test_returns_none_for_invalid_name(self) -> None:
        result = parse_filename("not_a_valid_name.jpg")
        self.assertEqual(result, (None, None))


if __name__ == "__main__":
    unittest.main()
