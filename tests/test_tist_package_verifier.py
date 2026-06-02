import tempfile
import unittest
from pathlib import Path

from verify_tist_package import (
    LOCAL_ID_PATTERNS,
    PACKAGE_SOURCE_FILES,
    REVIEW_METADATA_PATTERNS,
    SOURCE_SECRET_SCAN_PATHS,
    USER_HOME_PREFIX,
    scan_pdf_metadata,
    scan_text_paths,
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

    def test_pdf_metadata_scan_catches_local_path_and_author_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "paper.pdf"
            pdf.write_bytes(f"%PDF\n/Author (Named Author)\n/CreationPath ({USER_HOME_PREFIX}/reviewer/build)\n".encode())

            hits = scan_pdf_metadata(pdf)

        self.assertEqual(hits, [f"{pdf}:author_metadata", f"{pdf}:local_identifier"])

    def test_source_secret_scan_excludes_known_redaction_fixture(self):
        self.assertNotIn(Path("tests/test_exp8_fake_collectors.py"), SOURCE_SECRET_SCAN_PATHS)

    def test_package_source_files_include_bibliography_audit_gate(self):
        self.assertIn(Path("verify_tist_bibliography.py"), PACKAGE_SOURCE_FILES)
        self.assertIn(Path("paper/tist2027_bibliography_audit.md"), PACKAGE_SOURCE_FILES)
        self.assertIn(Path("tests/test_tist_bibliography_verifier.py"), PACKAGE_SOURCE_FILES)


if __name__ == "__main__":
    unittest.main()
