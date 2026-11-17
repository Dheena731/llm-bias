import unittest

from score_annotation import kappa, score, weighted_scores


class ScoreAnnotationTests(unittest.TestCase):
    def test_kappa_perfect_and_chance(self):
        self.assertEqual(kappa([1, 0, 1, 0], [1, 0, 1, 0]), 1.0)
        self.assertAlmostEqual(kappa([1, 1, 0, 0], [1, 0, 1, 0]), 0.0)

    def test_weights_change_recall(self):
        # One missed positive from a heavily weighted (rare-in-sample) stratum lowers population recall.
        unweighted = weighted_scores([1, 1, 0], [1, 1, 1], [1, 1, 1])
        weighted = weighted_scores([1, 1, 0], [1, 1, 1], [1, 1, 8])
        self.assertAlmostEqual(unweighted["recall"], 2 / 3)
        self.assertAlmostEqual(weighted["recall"], 0.2)
        self.assertEqual(weighted["precision"], 1.0)

    def test_score_skips_unlabeled_items(self):
        key = {"i1": {"det_markdown": "1", "weight": "1", **{f"det_{f}": "0" for f in ("emoji", "decorative", "polish")}},
               "i2": {"det_markdown": "0", "weight": "1", **{f"det_{f}": "0" for f in ("emoji", "decorative", "polish")}}}
        sheet = {"i1": {"markdown": "1", "emoji": "0", "decorative": "0", "polish": "0"},
                 "i2": {"markdown": "", "emoji": "0", "decorative": "0", "polish": "0"}}
        markdown = next(r for r in score(key, {"A": sheet}) if r["feature"] == "markdown")
        self.assertEqual(markdown["items_labeled"], 1)
        self.assertEqual(markdown["precision"], 1.0)


if __name__ == "__main__":
    unittest.main()
