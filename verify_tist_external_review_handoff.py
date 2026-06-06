"""Verify root handoff metadata for the TIST external-review archive."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

from prepare_tist_review_package import DEFAULT_ARCHIVE_PATH, DEFAULT_OUTPUT_DIR, PACKAGE_PROVENANCE_PATH
from verify_tist_package import LOCAL_ID_PATTERNS, SENSITIVE_PATTERNS, scan_text_paths, sha256_file


DEFAULT_HANDOFF_PATH = Path("TIST_EXTERNAL_REVIEW_HANDOFF.md")
DEFAULT_CHECKLIST_PATH = Path("TIST_EXTERNAL_REVIEW_CHECKLIST.md")
DEFAULT_WORKSHEET_PATH = Path("TIST_EXTERNAL_REVIEW_WORKSHEET.md")
DEFAULT_RESPONSE_LOG_PATH = Path("TIST_EXTERNAL_REVIEW_RESPONSE_LOG.md")
ARCHIVE_SHA_PATTERN = re.compile(r"Archive SHA-256:\s*(?:\n\s*)?`([0-9a-f]{64})`", re.IGNORECASE)
SOURCE_COMMIT_PATTERN = re.compile(
    r"Exported package source commit:\s*`([0-9a-f]{7,40})(?:\s+([^`]+))?`",
    re.IGNORECASE,
)
EXCLUDED_ARCHIVE_NAME_PARTS = {"__pycache__", ".DS_Store"}
EXCLUDED_ARCHIVE_SUFFIXES = {".pyc"}


def _read_archive_json(archive_path: Path, member: str) -> dict[str, Any]:
    with zipfile.ZipFile(archive_path) as archive:
        try:
            with archive.open(member) as handle:
                return json.loads(handle.read().decode("utf-8"))
        except KeyError as exc:
            raise AssertionError(f"archive missing {member}") from exc


def _archive_names(archive_path: Path) -> list[str]:
    with zipfile.ZipFile(archive_path) as archive:
        return archive.namelist()


def _documented_archive_shas(paths: list[Path]) -> dict[str, list[str]]:
    documented = {}
    for path in paths:
        text = path.read_text(encoding="utf-8")
        documented[path.as_posix()] = ARCHIVE_SHA_PATTERN.findall(text)
    return documented


def _source_commit_from_handoff(path: Path) -> tuple[str | None, str | None]:
    match = SOURCE_COMMIT_PATTERN.search(path.read_text(encoding="utf-8"))
    if not match:
        return None, None
    return match.group(1), (match.group(2) or "").strip() or None


def _commit_subject(commit: str) -> str | None:
    try:
        return subprocess.check_output(["git", "show", "-s", "--format=%s", commit], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _archive_hygiene_failures(names: list[str]) -> list[str]:
    failures = []
    for name in names:
        path = Path(name)
        if any(part in EXCLUDED_ARCHIVE_NAME_PARTS for part in path.parts):
            failures.append(name)
        elif path.suffix.lower() in EXCLUDED_ARCHIVE_SUFFIXES:
            failures.append(name)
    return sorted(set(failures))


def verify_handoff(
    handoff_path: Path = DEFAULT_HANDOFF_PATH,
    checklist_path: Path = DEFAULT_CHECKLIST_PATH,
    archive_path: Path = DEFAULT_ARCHIVE_PATH,
    worksheet_path: Path = DEFAULT_WORKSHEET_PATH,
    response_log_path: Path = DEFAULT_RESPONSE_LOG_PATH,
) -> dict[str, Any]:
    failures: dict[str, Any] = {}
    docs_with_archive_sha = [handoff_path, checklist_path]
    review_control_docs = [handoff_path, checklist_path, worksheet_path, response_log_path]
    for path in review_control_docs + [archive_path]:
        if not path.exists():
            failures.setdefault("missing_files", []).append(path.as_posix())
    if failures:
        return {"status": "fail", "failures": failures}

    archive_sha256 = sha256_file(archive_path)
    documented_shas = _documented_archive_shas(docs_with_archive_sha)
    bad_sha_docs = {
        path: values
        for path, values in documented_shas.items()
        if not values or any(value != archive_sha256 for value in values)
    }
    if bad_sha_docs:
        failures["archive_sha256"] = bad_sha_docs

    source_commit, documented_subject = _source_commit_from_handoff(handoff_path)
    provenance = _read_archive_json(archive_path, PACKAGE_PROVENANCE_PATH.as_posix())
    provenance_commit = str(provenance.get("git_commit", ""))
    if not source_commit:
        failures["source_commit"] = "missing exported package source commit"
    elif not provenance_commit.startswith(source_commit):
        failures["source_commit"] = {
            "documented": source_commit,
            "package_provenance": provenance_commit,
        }
    elif documented_subject:
        actual_subject = _commit_subject(source_commit)
        if actual_subject and actual_subject != documented_subject:
            failures["source_commit_subject"] = {
                "documented": documented_subject,
                "git": actual_subject,
            }

    package_scan = _read_archive_json(archive_path, "PACKAGE_SCAN.json")
    if package_scan.get("status") != "ok":
        failures["package_scan"] = package_scan

    local_hits = scan_text_paths(review_control_docs, LOCAL_ID_PATTERNS)
    if local_hits:
        failures["handoff_local_identifier_scan"] = local_hits
    secret_hits = scan_text_paths(review_control_docs, SENSITIVE_PATTERNS)
    if secret_hits:
        failures["handoff_secret_scan"] = secret_hits

    archive_hygiene = _archive_hygiene_failures(_archive_names(archive_path))
    if archive_hygiene:
        failures["archive_hygiene"] = archive_hygiene

    return {
        "status": "ok" if not failures else "fail",
        "archive_path": archive_path.as_posix(),
        "archive_sha256": archive_sha256,
        "documented_archive_sha256": documented_shas,
        "package_provenance": provenance,
        "package_scan_status": package_scan.get("status"),
        "package_scan_text_files": package_scan.get("text_files_scanned"),
        "review_control_docs": [path.as_posix() for path in review_control_docs],
        "export_dir": DEFAULT_OUTPUT_DIR.as_posix(),
        "failures": failures,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify TIST external-review handoff metadata")
    parser.add_argument("--handoff", default=str(DEFAULT_HANDOFF_PATH))
    parser.add_argument("--checklist", default=str(DEFAULT_CHECKLIST_PATH))
    parser.add_argument("--worksheet", default=str(DEFAULT_WORKSHEET_PATH))
    parser.add_argument("--response-log", default=str(DEFAULT_RESPONSE_LOG_PATH))
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE_PATH))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = verify_handoff(
        Path(args.handoff),
        Path(args.checklist),
        Path(args.archive),
        Path(args.worksheet),
        Path(args.response_log),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
