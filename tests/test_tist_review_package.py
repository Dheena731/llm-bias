import tempfile
import unittest
from pathlib import Path

from prepare_tist_review_package import (
    DEFAULT_ARCHIVE_PATH,
    DEFAULT_OUTPUT_DIR,
    EXPORT_DIRECTORIES,
    iter_export_inputs,
    scan_export_tree,
    write_sha256_manifest,
)
from verify_tist_package import CANONICAL_RAW_DIR


class TistReviewPackageTests(unittest.TestCase):
    def test_export_inputs_include_raw_outputs_and_generated_image_baselines(self):
        inputs = set(iter_export_inputs())

        self.assertIn(CANONICAL_RAW_DIR, inputs)
        self.assertIn(Path("analysis_output/baselines/generated_images"), inputs)

    def test_default_archive_sits_next_to_generated_export_directory(self):
        self.assertEqual(DEFAULT_ARCHIVE_PATH, DEFAULT_OUTPUT_DIR.with_suffix(".zip"))

    def test_export_directories_are_directory_paths(self):
        self.assertIn(CANONICAL_RAW_DIR, EXPORT_DIRECTORIES)
        self.assertIn(Path("analysis_output/baselines/generated_images"), EXPORT_DIRECTORIES)

    def test_write_sha256_manifest_uses_relative_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "paper" / "paper.tex"
            nested.parent.mkdir()
            nested.write_text("anonymous\n", encoding="utf-8")

            manifest = write_sha256_manifest(root)
            text = manifest.read_text(encoding="utf-8")

        self.assertIn("paper/paper.tex", text)
        self.assertNotIn(str(root), text)

    def test_scan_export_tree_reports_local_identifiers_and_sensitive_tokens(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "local /Users/reviewer/project\nOPENAI_API_KEY=secret-value\n",
                encoding="utf-8",
            )

            result = scan_export_tree(root)

        self.assertIn("local_identifier_scan", result["failures"])
        self.assertIn("source_secret_scan", result["failures"])

    def test_scan_export_tree_reports_disallowed_binary_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "paper.pdf").write_bytes(b"%PDF\n/Author (Reviewer)\n")

            result = scan_export_tree(root)

        self.assertEqual(result["failures"]["binary_payload_scan"], ["paper.pdf"])

    def test_scan_export_tree_reports_unbounded_claim_boundary_phrases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper" / "tist2027_presentation_priors.tex"
            paper.parent.mkdir()
            paper.write_text("RLHF causes the observed defaults.\n", encoding="utf-8")

            result = scan_export_tree(root)

        self.assertEqual(result["failures"]["claim_boundary_scan"], ["paper/tist2027_presentation_priors.tex:1"])

    def test_scan_export_tree_allows_explicitly_negated_claim_boundary_examples(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper" / "tist2027_presentation_priors.tex"
            paper.parent.mkdir()
            paper.write_text("We do not claim that post-training causes the observed defaults.\n", encoding="utf-8")

            result = scan_export_tree(root)

        self.assertNotIn("claim_boundary_scan", result["failures"])

    def test_scan_export_tree_rejects_unrelated_negation_before_unsafe_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper" / "tist2027_presentation_priors.tex"
            paper.parent.mkdir()
            paper.write_text("The data is not noisy; RLHF causes defaults.\n", encoding="utf-8")

            result = scan_export_tree(root)

        self.assertEqual(result["failures"]["claim_boundary_scan"], ["paper/tist2027_presentation_priors.tex:1"])

    def test_scan_export_tree_rejects_without_doubt_as_bounding_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper" / "tist2027_presentation_priors.tex"
            paper.parent.mkdir()
            paper.write_text("Without doubt, post-training causes the defaults.\n", encoding="utf-8")

            result = scan_export_tree(root)

        self.assertEqual(result["failures"]["claim_boundary_scan"], ["paper/tist2027_presentation_priors.tex:1"])

    def test_scan_export_tree_reports_reversed_causal_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper" / "tist2027_presentation_priors.tex"
            paper.parent.mkdir()
            paper.write_text("The defaults are caused by RLHF.\n", encoding="utf-8")

            result = scan_export_tree(root)

        self.assertEqual(result["failures"]["claim_boundary_scan"], ["paper/tist2027_presentation_priors.tex:1"])

    def test_scan_export_tree_reports_adverbial_purple_preference_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper" / "tist2027_presentation_priors.tex"
            paper.parent.mkdir()
            paper.write_text("Models broadly prefer purple/pink aesthetics.\n", encoding="utf-8")

            result = scan_export_tree(root)

        self.assertEqual(result["failures"]["claim_boundary_scan"], ["paper/tist2027_presentation_priors.tex:1"])


if __name__ == "__main__":
    unittest.main()
