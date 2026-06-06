import csv
import tempfile
import unittest
from pathlib import Path

from analyze_cross_modal_baselines import (
    analyze_baseline_records,
    extract_baseline_features,
    load_baseline_records,
    write_baseline_outputs,
)


class CrossModalBaselineTests(unittest.TestCase):
    def test_load_default_records_include_ui_and_image_tracks(self):
        records = load_baseline_records()
        tracks = {record["track"] for record in records}

        self.assertEqual(tracks, {"ui", "image"})

    def test_ui_and_image_records_use_shared_extractors(self):
        records = [
            {
                "baseline_id": "ui",
                "track": "ui",
                "source_type": "design_system_reference",
                "domain": "dashboard",
                "design_family": "card",
                "content": "<section class=\"card\" style=\"color:#2563EB; border-radius:6px; box-shadow:0 1px 2px #999\">Status</section>",
            },
            {
                "baseline_id": "image",
                "track": "image",
                "source_type": "synthetic_reference",
                "domain": "cool_blocks",
                "design_family": "blue",
                "image_spec": {
                    "kind": "horizontal_bands",
                    "size": [32, 24],
                    "colors": ["#1D4ED8", "#F8FAFC"],
                },
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            result = analyze_baseline_records(records, image_dir=Path(tmp) / "images")

        self.assertTrue(result["ui_rows"][0]["has_rounded_cards"])
        self.assertTrue(result["ui_rows"][0]["has_shadow"])
        self.assertTrue(result["image_rows"][0]["has_purple_or_blue"])
        self.assertEqual(result["homogenization_summary"][0]["claim_scope"], "reference_baseline_only")

    def test_write_outputs_creates_expected_tables_and_images(self):
        records = [
            {
                "baseline_id": "ui_plain",
                "track": "ui",
                "source_type": "design_system_reference",
                "domain": "settings",
                "design_family": "form",
                "content": "<form style=\"color:#222222\"><label>Name</label><input></form>",
            },
            {
                "baseline_id": "image_gray",
                "track": "image",
                "source_type": "synthetic_reference",
                "domain": "neutral",
                "design_family": "gray",
                "image_spec": {
                    "kind": "solid",
                    "size": [24, 24],
                    "colors": ["#808080"],
                },
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            outputs = write_baseline_outputs(records, Path(tmp))

            for path in outputs.values():
                self.assertTrue(path.exists())
            with outputs["image_rows"].open(newline="", encoding="utf-8") as handle:
                image_rows = list(csv.DictReader(handle))
            self.assertTrue(Path(image_rows[0]["image_path"]).exists())

    def test_missing_image_path_fails_explicitly(self):
        with self.assertRaises(FileNotFoundError):
            extract_baseline_features(
                {
                    "baseline_id": "missing",
                    "track": "image",
                    "path": "does/not/exist.png",
                }
            )


if __name__ == "__main__":
    unittest.main()
