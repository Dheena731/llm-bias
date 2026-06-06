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
    def _write_review_docs(self, root: Path, sha: str, *, handoff_extra: str = "", checklist_extra: str = ""):
        handoff = root / "HANDOFF.md"
        checklist = root / "CHECKLIST.md"
        worksheet = root / "WORKSHEET.md"
        response_log = root / "RESPONSE_LOG.md"
        handoff.write_text(
            "- Exported package source commit: `0123456 Test export`\n"
            f"- Archive SHA-256: `{sha}`\n"
            f"{handoff_extra}",
            encoding="utf-8",
        )
        checklist.write_text(f"- Archive SHA-256: `{sha}`\n{checklist_extra}", encoding="utf-8")
        worksheet.write_text("review worksheet\n", encoding="utf-8")
        response_log.write_text("review response log\n", encoding="utf-8")
        return handoff, checklist, worksheet, response_log

    def test_verify_handoff_accepts_matching_archive_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "package.zip"
            _write_zip(archive)
            sha = _sha256(archive)
            docs = self._write_review_docs(root, sha)

            result = verify_handoff(docs[0], docs[1], archive, docs[2], docs[3])

        self.assertEqual(result["status"], "ok")
        self.assertIn("WORKSHEET.md", result["review_control_docs"][2])

    def test_verify_handoff_reports_archive_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "package.zip"
            _write_zip(archive)
            wrong_sha = "0" * 64
            docs = self._write_review_docs(root, wrong_sha)

            result = verify_handoff(docs[0], docs[1], archive, docs[2], docs[3])

        self.assertEqual(result["status"], "fail")
        self.assertIn("archive_sha256", result["failures"])

    def test_verify_handoff_reports_provenance_commit_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "package.zip"
            _write_zip(archive, commit="abcdef0123456789abcdef0123456789abcdef01")
            sha = _sha256(archive)
            docs = self._write_review_docs(root, sha)

            result = verify_handoff(docs[0], docs[1], archive, docs[2], docs[3])

        self.assertEqual(result["status"], "fail")
        self.assertIn("source_commit", result["failures"])

    def test_verify_handoff_scans_all_root_review_docs_for_local_identifiers_and_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "package.zip"
            _write_zip(archive)
            sha = _sha256(archive)
            docs = self._write_review_docs(root, sha)
            docs[2].write_text("/private/var/folders/unit/build\n", encoding="utf-8")
            docs[3].write_text("OPENAI_API_KEY=synthetic-secret-value\n", encoding="utf-8")

            result = verify_handoff(docs[0], docs[1], archive, docs[2], docs[3])

        self.assertEqual(result["status"], "fail")
        self.assertIn("handoff_local_identifier_scan", result["failures"])
        self.assertIn("handoff_secret_scan", result["failures"])

    def test_verify_handoff_reports_missing_review_control_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "package.zip"
            _write_zip(archive)
            sha = _sha256(archive)
            handoff, checklist, worksheet, response_log = self._write_review_docs(root, sha)
            worksheet.unlink()

            result = verify_handoff(handoff, checklist, archive, worksheet, response_log)

        self.assertEqual(result["status"], "fail")
        self.assertIn("missing_files", result["failures"])


if __name__ == "__main__":
    unittest.main()
