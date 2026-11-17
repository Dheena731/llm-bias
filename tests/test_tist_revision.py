import unittest

from analyze_tist_revision import cluster_ci, is_saturated_blue, parse_primary


class TistRevisionTests(unittest.TestCase):
    def test_primary_color_parsing_and_blue_classification(self):
        self.assertEqual(parse_primary("Primary: #1a73e8  \nSecondary: #202124"), "#1A73E8")
        self.assertIsNone(parse_primary("Secondary: #202124"))
        self.assertTrue(is_saturated_blue("#1A73E8"))
        self.assertFalse(is_saturated_blue("#2C3E50"))  # dark slate: blue hue, low saturation
        self.assertFalse(is_saturated_blue("#7C3AED"))  # purple

    def test_cluster_ci_brackets_pooled_rate(self):
        low, high = cluster_ci([[1, 1, 1], [0, 0], [1, 0]])
        self.assertLessEqual(low, 4 / 7)
        self.assertGreaterEqual(high, 4 / 7)


if __name__ == "__main__":
    unittest.main()
