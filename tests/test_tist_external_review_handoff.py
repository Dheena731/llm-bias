import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from verify_tist_external_review_handoff import verify_handoff


def _write_zip(path: Path, *, commit: str = "0123456789abcdef0123456789abcdef01234567") -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "PACKAGE_PROVENANCE.json",
            json.dumps({"git_commit": commit, "package": "tist2027_external_review"}),
        )
        archive.writestr("PACKAGE_SCAN.json", json.dumps({"status": "ok", "text_files_scanned": 3}))
        archive.writestr("README.md", "anonymous package\n")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


class TistExternalReviewHandoffTests(unittest.TestCase):
    def test_verify_handoff_accepts_matching_archive_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "package.zip"
            _write_zip(archive)
            sha = _sha256(archive)
            handoff = root / "HANDOFF.md"
            checklist = root / "CHECKLIST.md"
            handoff.write_text(
                "- Exported package source commit: `0123456 Test export`\n"
                f"- Archive SHA-256: `{sha}`\n",
                encoding="utf-8",
            )
            checklist.write_text(f"- Archive SHA-256: `{sha}`\n", encoding="utf-8")

            result = verify_handoff(handoff, checklist, archive)

        self.assertEqual(result["status"], "ok")

    def test_verify_handoff_reports_archive_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "package.zip"
            _write_zip(archive)
            handoff = root / "HANDOFF.md"
            checklist = root / "CHECKLIST.md"
            wrong_sha = "0" * 64
            handoff.write_text(
                "- Exported package source commit: `0123456 Test export`\n"
                f"- Archive SHA-256: `{wrong_sha}`\n",
                encoding="utf-8",
            )
            checklist.write_text(f"- Archive SHA-256: `{wrong_sha}`\n", encoding="utf-8")

            result = verify_handoff(handoff, checklist, archive)

        self.assertEqual(result["status"], "fail")
        self.assertIn("archive_sha256", result["failures"])

    def test_verify_handoff_reports_provenance_commit_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "package.zip"
            _write_zip(archive, commit="abcdef0123456789abcdef0123456789abcdef01")
            sha = _sha256(archive)
            handoff = root / "HANDOFF.md"
            checklist = root / "CHECKLIST.md"
            handoff.write_text(
                "- Exported package source commit: `0123456 Test export`\n"
                f"- Archive SHA-256: `{sha}`\n",
                encoding="utf-8",
            )
            checklist.write_text(f"- Archive SHA-256: `{sha}`\n", encoding="utf-8")

            result = verify_handoff(handoff, checklist, archive)

        self.assertEqual(result["status"], "fail")
        self.assertIn("source_commit", result["failures"])

    def test_verify_handoff_scans_root_docs_for_local_identifiers_and_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "package.zip"
            _write_zip(archive)
            sha = _sha256(archive)
            handoff = root / "HANDOFF.md"
            checklist = root / "CHECKLIST.md"
            handoff.write_text(
                "- Exported package source commit: `0123456 Test export`\n"
                f"- Archive SHA-256: `{sha}`\n"
                "/private/var/folders/unit/build\n",
                encoding="utf-8",
            )
            checklist.write_text(
                f"- Archive SHA-256: `{sha}`\n"
                "OPENAI_API_KEY=synthetic-secret-value\n",
                encoding="utf-8",
            )

            result = verify_handoff(handoff, checklist, archive)

        self.assertEqual(result["status"], "fail")
        self.assertIn("handoff_local_identifier_scan", result["failures"])
        self.assertIn("handoff_secret_scan", result["failures"])


if __name__ == "__main__":
    unittest.main()
