import tempfile
import unittest
from pathlib import Path

from analyze_text_baselines import analyze_baseline_records, write_baseline_outputs
from validate_feature_audit_samples import validate_audit_samples


class TextBaselineTests(unittest.TestCase):
    def test_baseline_records_use_text_feature_extractor(self):
        records = [
            {
                "baseline_id": "human_launch_plain",
                "source_type": "hand_authored",
                "domain": "marketing",
                "text": "The app update adds account filters for monthly review.",
            },
            {
                "baseline_id": "human_notice_plain",
                "source_type": "hand_authored",
                "domain": "public_service",
                "text": "Library hours change on Monday. The front desk opens at nine.",
            },
        ]

        rows, summary = analyze_baseline_records(records)

        self.assertEqual(len(rows), 2)
        self.assertIn("has_format_default", rows[0])
        self.assertEqual(summary[0]["n"], 1)

    def test_write_baseline_outputs_creates_rows_and_summary(self):
        records = [
            {
                "baseline_id": "plain",
                "source_type": "hand_authored",
                "domain": "technical",
                "text": "Latency affects how quickly a page responds to input.",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            outputs = write_baseline_outputs(records, Path(tmp))

            self.assertTrue(outputs["rows"].exists())
            self.assertTrue(outputs["summary"].exists())


class FeatureAuditSampleTests(unittest.TestCase):
    def test_feature_audit_samples_match_expected_labels(self):
        samples = [
            {
                "sample_id": "markdown_text",
                "track": "text",
                "content": "## Launch\n- Plain update",
                "expected": {"has_markdown": True, "has_format_default": True},
            },
            {
                "sample_id": "plain_text",
                "track": "text",
                "content": "Plain prose without decorative formatting.",
                "expected": {"has_markdown": False, "has_format_default": False},
            },
        ]

        result = validate_audit_samples(samples)

        self.assertEqual(result["checked"], 2)
        self.assertEqual(result["failures"], [])


if __name__ == "__main__":
    unittest.main()
