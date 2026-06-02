import json
import tempfile
import unittest
from pathlib import Path

from generate_tist_artifact_tables import (
    DEFAULT_ARTIFACTS,
    build_tist_artifact_tables,
    sha256_file,
    verify_artifact_manifest,
)


class TistArtifactTableTests(unittest.TestCase):
    def test_build_writes_expected_table_fragments_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "tables"

            manifest = build_tist_artifact_tables(output_dir=output_dir)

            expected_names = {artifact["name"] for artifact in DEFAULT_ARTIFACTS}
            self.assertEqual({artifact["name"] for artifact in manifest["artifacts"]}, expected_names)
            for artifact in manifest["artifacts"]:
                self.assertTrue((output_dir / artifact["path"]).exists())
                self.assertTrue(artifact["sha256"])
            self.assertIn("analysis_output/exp8/condition_summary.csv", manifest["source_sha256"])

    def test_generated_condition_table_uses_pipeline_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "tables"
            build_tist_artifact_tables(output_dir=output_dir)

            table = (output_dir / "table_exp8_condition_summary.tex").read_text(encoding="utf-8")

        self.assertIn(r"\texttt{neutral} & 96 & 80.2\% & 72.9\% & 19.8\% & 78.1\%", table)
        self.assertIn(r"\texttt{plain\_no\_markdown} & 96 & 2.1\% & 25.0\% & 0.0\% & 2.1\%", table)

    def test_manifest_verification_detects_stale_source_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "tables"
            manifest = build_tist_artifact_tables(output_dir=output_dir)
            manifest["source_sha256"]["analysis_output/exp8/condition_summary.csv"] = "stale"
            (output_dir / "tist_artifact_manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True),
                encoding="utf-8",
            )

            failures = verify_artifact_manifest(output_dir=output_dir)

        self.assertIn("source hash mismatch: analysis_output/exp8/condition_summary.csv", failures)

    def test_manifest_verification_detects_missing_expected_artifact_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "tables"
            manifest = build_tist_artifact_tables(output_dir=output_dir)
            manifest["artifacts"] = [
                artifact for artifact in manifest["artifacts"] if artifact["name"] != "exp8_ci_contrasts"
            ]
            (output_dir / "tist_artifact_manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True),
                encoding="utf-8",
            )

            failures = verify_artifact_manifest(output_dir=output_dir)

        self.assertIn("manifest missing artifact entry: exp8_ci_contrasts", failures)

    def test_manifest_verification_detects_missing_expected_source_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "tables"
            manifest = build_tist_artifact_tables(output_dir=output_dir)
            del manifest["source_sha256"]["analysis_output/exp8/condition_summary.csv"]
            (output_dir / "tist_artifact_manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True),
                encoding="utf-8",
            )

            failures = verify_artifact_manifest(output_dir=output_dir)

        self.assertIn("manifest missing source entry: analysis_output/exp8/condition_summary.csv", failures)

    def test_manifest_verification_can_compare_against_regenerated_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "tables"
            manifest = build_tist_artifact_tables(output_dir=output_dir)
            artifact = output_dir / "table_exp8_condition_summary.tex"
            artifact.write_text("% hand edited\n", encoding="utf-8")
            for row in manifest["artifacts"]:
                if row["path"] == "table_exp8_condition_summary.tex":
                    row["sha256"] = sha256_file(artifact)
            (output_dir / "tist_artifact_manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True),
                encoding="utf-8",
            )

            failures = verify_artifact_manifest(output_dir=output_dir, verify_regeneration=True)

        self.assertIn("regenerated artifact mismatch: table_exp8_condition_summary.tex", failures)


if __name__ == "__main__":
    unittest.main()
