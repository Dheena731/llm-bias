import tempfile
import unittest
from pathlib import Path

from generate_tist_artifact_tables import DEFAULT_SOURCES as TIST_TABLE_SOURCES
from verify_tist_package import (
    LOCAL_ID_PATTERNS,
    LOCAL_PATH_PATTERNS,
    PACKAGE_SOURCE_FILES,
    REQUIRED_FILES,
    REVIEW_METADATA_PATTERNS,
    REVIEW_IDENTITY_PATTERNS,
    SENSITIVE_PATTERNS,
    SOURCE_SECRET_SCAN_PATHS,
    TIST_TABLE_INPUTS,
    USER_HOME_PREFIX,
    EXTERNAL_REVIEW_SCAN_PATHS,
    scan_pdf_metadata,
    scan_text_paths,
    validate_analysis_manifest_inputs,
    validate_camera_ready_metadata,
    validate_review_mode_metadata,
    validate_tist_table_inputs,
    validate_anonymous_manuscript,
)


class TistPackageVerifierTests(unittest.TestCase):
    def test_text_path_scan_recurses_directories_and_reports_line_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "package" / "manifest.md"
            nested.parent.mkdir()
            nested.write_text(f"clean\nlocal path {USER_HOME_PREFIX}/reviewer/project\n", encoding="utf-8")

            hits = scan_text_paths([root / "package"], LOCAL_ID_PATTERNS)

        self.assertEqual(hits, [f"{nested}:2"])

    def test_review_metadata_scan_rejects_commit_hash_and_untracked_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.md"
            manifest.write_text(
                "git_commit: 0123456789abcdef0123456789abcdef01234567\n"
                "package files are still untracked\n",
                encoding="utf-8",
            )

            hits = scan_text_paths([manifest], REVIEW_METADATA_PATTERNS)

        self.assertEqual(hits, [f"{manifest}:1", f"{manifest}:2"])

    def test_validate_anonymous_manuscript_requires_anonymous_class_and_author(self):
        with tempfile.TemporaryDirectory() as tmp:
            tex = Path(tmp) / "paper.tex"
            tex.write_text(
                "\\documentclass[acmsmall,screen,review]{acmart}\n"
                "\\author{Named Author}\n"
                "\\affiliation{\\institution{Named Lab}}\n",
                encoding="utf-8",
            )

            failures = validate_anonymous_manuscript(tex)

        self.assertIn("documentclass missing anonymous option", failures)
        self.assertIn("missing anonymous author placeholder", failures)
        self.assertIn("missing anonymous institution placeholder", failures)

    def test_validate_anonymous_manuscript_accepts_anonymous_placeholder_with_spacing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tex = Path(tmp) / "paper.tex"
            tex.write_text(
                "\\documentclass[acmsmall,screen,review,anonymous]{acmart}\n"
                "\\author{Anonymous Authors}\n"
                "\\affiliation{%\n"
                "  \\institution{Anonymous Institution}\n"
                "}\n",
                encoding="utf-8",
            )

            failures = validate_anonymous_manuscript(tex)

        self.assertEqual(failures, [])

    def test_validate_review_mode_metadata_requires_review_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            tex = Path(tmp) / "paper.tex"
            tex.write_text(
                "\\documentclass[acmsmall,screen,anonymous]{acmart}\n"
                "\\setcopyright{none}\n"
                "\\settopmatter{printacmref=false}\n"
                "\\acmJournal{TIST}\n"
                "\\acmVolume{0}\n"
                "\\acmNumber{0}\n"
                "\\acmArticle{0}\n",
                encoding="utf-8",
            )

            failures = validate_review_mode_metadata(tex)

        self.assertIn("documentclass missing review option", failures)

    def test_validate_camera_ready_metadata_rejects_review_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            tex = Path(tmp) / "paper.tex"
            tex.write_text(
                "\\documentclass[acmsmall,screen,review,anonymous]{acmart}\n"
                "\\setcopyright{none}\n"
                "\\settopmatter{printacmref=false}\n"
                "\\acmVolume{0}\n"
                "\\acmNumber{0}\n"
                "\\acmArticle{0}\n"
                "\\author{Anonymous Authors}\n",
                encoding="utf-8",
            )

            failures = validate_camera_ready_metadata(tex)

        self.assertIn("camera-ready metadata still has review option", failures)
        self.assertIn("camera-ready metadata still has anonymous option", failures)
        self.assertIn("camera-ready metadata still uses anonymous author placeholder", failures)

    def test_pdf_metadata_scan_catches_local_path_and_author_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "paper.pdf"
            pdf.write_bytes(f"%PDF\n/Author (Named Author)\n/CreationPath ({USER_HOME_PREFIX}/reviewer/build)\n".encode())

            hits = scan_pdf_metadata(pdf)

        self.assertEqual(hits, [f"{pdf}:author_metadata", f"{pdf}:local_identifier"])

    def test_pdf_metadata_scan_camera_ready_allows_named_author_but_keeps_path_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "paper.pdf"
            pdf.write_bytes(b"%PDF\n/Author (Named Author)\n")

            hits = scan_pdf_metadata(pdf, mode="camera-ready")

        self.assertEqual(hits, [])

    def test_local_path_patterns_do_not_include_author_identity_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "identity.txt"
            path.write_text("Contact: author@example.gmail.com from Axonome\n", encoding="utf-8")

            path_hits = scan_text_paths([path], LOCAL_PATH_PATTERNS)
            review_hits = scan_text_paths([path], REVIEW_IDENTITY_PATTERNS)

        self.assertEqual(path_hits, [])
        self.assertEqual(review_hits, [f"{path}:1"])

    def test_source_secret_scan_excludes_known_redaction_fixture(self):
        self.assertNotIn(Path("tests/test_exp8_fake_collectors.py"), SOURCE_SECRET_SCAN_PATHS)
        self.assertNotIn(Path("tests/test_tist_package_verifier.py"), SOURCE_SECRET_SCAN_PATHS)
        self.assertNotIn(Path("tests/test_tist_review_package.py"), SOURCE_SECRET_SCAN_PATHS)

    def test_package_source_files_include_bibliography_audit_gate(self):
        self.assertIn(Path("verify_tist_bibliography.py"), PACKAGE_SOURCE_FILES)
        self.assertIn(Path("paper/tist2027_bibliography_audit.md"), PACKAGE_SOURCE_FILES)
        self.assertIn(Path("tests/test_tist_bibliography_verifier.py"), PACKAGE_SOURCE_FILES)

    def test_package_source_files_include_tist_artifact_table_gate(self):
        self.assertIn(Path("generate_tist_artifact_tables.py"), PACKAGE_SOURCE_FILES)
        self.assertIn(Path("tests/test_tist_artifact_tables.py"), PACKAGE_SOURCE_FILES)

    def test_package_source_files_include_tist_review_package_gate(self):
        self.assertIn(Path("prepare_tist_review_package.py"), PACKAGE_SOURCE_FILES)
        self.assertIn(Path("tests/test_tist_review_package.py"), PACKAGE_SOURCE_FILES)

    def test_required_files_include_generated_tist_table_artifacts(self):
        required_paths = set(REQUIRED_FILES)

        for source in TIST_TABLE_SOURCES:
            self.assertIn(source, required_paths)
        self.assertIn(Path("analysis_output/tist_package/tist_artifact_manifest.json"), required_paths)
        self.assertIn(Path("analysis_output/tist_package/table_exp8_completeness.tex"), required_paths)
        self.assertIn(Path("analysis_output/tist_package/table_exp8_stage_summary.tex"), required_paths)
        self.assertIn(Path("analysis_output/tist_package/table_exp8_condition_summary.tex"), required_paths)
        self.assertIn(Path("analysis_output/tist_package/table_exp8_ci_contrasts.tex"), required_paths)

    def test_external_review_scan_includes_generated_tist_package_outputs(self):
        self.assertIn(Path("analysis_output/tist_package"), EXTERNAL_REVIEW_SCAN_PATHS)

    def test_validate_tist_table_inputs_reports_missing_generated_fragment_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tex = Path(tmp) / "paper.tex"
            tex.write_text("\n".join(TIST_TABLE_INPUTS[:-1]) + "\n", encoding="utf-8")

            failures = validate_tist_table_inputs(tex)

        self.assertEqual(failures, [TIST_TABLE_INPUTS[-1]])

    def test_validate_analysis_manifest_inputs_checks_canonical_csv_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "exp8.csv"
            csv_path.write_text("artifact_id\nunit\n", encoding="utf-8")
            manifest = {
                "input_files": [csv_path.as_posix()],
                "input_file_sha256": {csv_path.as_posix(): "stale"},
            }

            failures = validate_analysis_manifest_inputs(manifest, csv_path)

        self.assertEqual(failures, ["analysis manifest input_file_sha256 mismatch"])

    def test_secret_scan_catches_common_assignment_and_token_forms(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "leak.txt"
            path.write_text(
                "api_key = abcdefghijklmnop\n"
                "github_pat_abcdefghijklmnopqrstuvwxyz\n",
                encoding="utf-8",
            )

            hits = scan_text_paths([path], SENSITIVE_PATTERNS)

        self.assertEqual(hits, [f"{path}:1", f"{path}:2"])

    def test_local_identifier_scan_catches_common_build_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "paths.txt"
            path.write_text(
                "/private/var/folders/unit/build\n"
                "C:\\\\Users\\\\reviewer\\\\project\n",
                encoding="utf-8",
            )

            hits = scan_text_paths([path], LOCAL_ID_PATTERNS)

        self.assertEqual(hits, [f"{path}:1", f"{path}:2"])


if __name__ == "__main__":
    unittest.main()
