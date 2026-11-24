import unittest

from analyze_preference_markdown import conditional_logit


class ConditionalLogitTest(unittest.TestCase):
    def test_single_feature_matches_discordant_ratio(self):
        def pair(chosen_markup, rejected_markup):
            return ({"has_markup": chosen_markup, "has_emoji": False, "words": 100},
                    {"has_markup": rejected_markup, "has_emoji": False, "words": 100})

        pairs = [pair(True, False)] * 3000 + [pair(False, True)] * 1000 + [pair(True, True)] * 500
        fit = conditional_logit(pairs, [("a", "b")] * len(pairs), length=False, by_model=False)
        self.assertAlmostEqual(fit["has_markup"]["odds_ratio"], 3.0, delta=0.02)
        self.assertLess(fit["has_markup"]["ci_low"], 3.0)
        self.assertGreater(fit["has_markup"]["ci_high"], 3.0)


if __name__ == "__main__":
    unittest.main()
