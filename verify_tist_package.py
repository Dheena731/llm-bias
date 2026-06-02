"""Verify the current TIST presentation-priors journal package artifacts."""

from __future__ import annotations

import csv
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


EXPECTED_ROWS = 480
EXPECTED_UI_BASELINE_ROWS = 4
EXPECTED_IMAGE_BASELINE_ROWS = 4
EXPECTED_RUN_ID = "exp8_20260601_022210"
EXPECTED_CONFIG_HASH = "b3dd18b8bb4f9863836a8905009630f66e786c1aba0efb8dd923387ca173a7dd"
CANONICAL_CSV = Path("experiment_data/exp8_post_training_priors_20260601_022210.csv")
CANONICAL_RAW_DIR = Path("experiment_artifacts/exp8_text/raw/b3dd18b8bb4f/exp8_20260601_022210")
MANIFEST = Path("analysis_output/exp8/analysis_manifest.json")
USER_HOME_PREFIX = "/" + "Users"
FILE_URI_PREFIX = "file" + "://"
PERSONAL_NAME = "A" + "dhi"
PERSONAL_HANDLE = "a" + "dhit"
ORG_NAME = "Ax" + "onome"
PERSONAL_EMAIL_DOMAIN = "gm" + "ail" + r"\.com"
REQUIRED_FILES = [
    CANONICAL_CSV,
    MANIFEST,
    Path("analysis_output/exp8/post_training_priors_report.md"),
    Path("analysis_output/exp8/matrix_completeness.csv"),
    Path("analysis_output/exp8/stage_condition_summary.csv"),
    Path("analysis_output/exp8/confidence_intervals.csv"),
    Path("analysis_output/exp8/planned_contrasts_fdr.csv"),
    Path("analysis_output/exp8/paired_condition_delta_summary.csv"),
    Path("analysis_output/exp8/cluster_paired_condition_contrasts.csv"),
    Path("analysis_output/exp8/prompt_family_holdout.csv"),
    Path("analysis_output/exp8/length_sensitivity.csv"),
    Path("analysis_output/exp8/missingness_summary.csv"),
    Path("analysis_output/baselines/text_baseline_rows.csv"),
    Path("analysis_output/baselines/text_baseline_summary.csv"),
    Path("analysis_output/baselines/ui_baseline_rows.csv"),
    Path("analysis_output/baselines/ui_baseline_summary.csv"),
    Path("analysis_output/baselines/image_baseline_rows.csv"),
    Path("analysis_output/baselines/image_baseline_summary.csv"),
    Path("analysis_output/baselines/cross_modal_homogenization_summary.csv"),
    Path("paper/tist2027_presentation_priors.tex"),
    Path("paper/tist2027_presentation_priors_refs.bib"),
    Path("paper/haips2026_refs.bib"),
    Path("paper/tist2027_journal_package_manifest.md"),
]
PACKAGE_SOURCE_FILES = [
    Path("paper/README.md"),
    Path("paper/tist2027_presentation_priors.tex"),
    Path("paper/tist2027_presentation_priors_refs.bib"),
    Path("paper/haips2026_refs.bib"),
    Path("paper/tist2027_journal_package_manifest.md"),
    Path("paper/journal_aesthetic_anchoring_presentation_priors.md"),
    Path("paper/aesthetic_anchoring_claim_audit.md"),
    Path("EXPERIMENT8_PROTOCOL.md"),
    Path("aesthetic_features.py"),
    Path("experiment8_common.py"),
    Path("experiment8_collect_text.py"),
    Path("analyze_post_training_priors.py"),
    Path("analyze_text_baselines.py"),
    Path("analyze_cross_modal_baselines.py"),
    Path("validate_feature_audit_samples.py"),
    Path("verify_tist_package.py"),
    Path("configs/exp8_post_training_priors.json"),
    Path("configs/text_baselines.json"),
    Path("configs/ui_image_baselines.json"),
    Path("configs/feature_validity_audit_samples.json"),
    Path("tests/__init__.py"),
    Path("tests/test_exp8_task_matrix.py"),
    Path("tests/test_exp8_fake_collectors.py"),
    Path("tests/test_exp8_analysis.py"),
    Path("tests/test_baseline_feature_audit.py"),
    Path("tests/test_cross_modal_baselines.py"),
    Path("tests/test_tist_package_verifier.py"),
]
PACKAGE_SUPPORT_FILES = [
    Path(".env.example"),
    Path(".gitignore"),
    Path("pyproject.toml"),
    Path("requirements.txt"),
    Path("uv.lock"),
]
REQUIRED_PACKAGE_FILES = sorted(set(REQUIRED_FILES + PACKAGE_SOURCE_FILES + PACKAGE_SUPPORT_FILES))
ANONYMITY_SCAN_FILES = [
    Path("paper/tist2027_presentation_priors.tex"),
    Path("paper/tist2027_journal_package_manifest.md"),
    Path("paper/README.md"),
    Path("EXPERIMENT8_PROTOCOL.md"),
]
EXTERNAL_REVIEW_SCAN_PATHS = [
    *PACKAGE_SOURCE_FILES,
    *PACKAGE_SUPPORT_FILES,
    Path("analysis_output/exp8"),
    Path("analysis_output/baselines"),
]
SOURCE_SECRET_SCAN_PATHS = [
    path for path in EXTERNAL_REVIEW_SCAN_PATHS if path != Path("tests/test_exp8_fake_collectors.py")
]
REVIEW_METADATA_SCAN_FILES = [
    Path("paper/tist2027_journal_package_manifest.md"),
    Path("paper/README.md"),
    Path("EXPERIMENT8_PROTOCOL.md"),
]
SENSITIVE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"sk-or-v1-[A-Za-z0-9._-]+",
        r"Authorization:\s*Bearer\s+[A-Za-z0-9._~+/=-]+",
        r"\bBearer\s+[A-Za-z0-9._~+/=-]+",
        r"\b(?:OPENROUTER_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|GOOGLE_API_KEY)\s*=\s*[^\s,;]+",
        r"(?:X-API-Key|OpenRouter-API-Key|api-key):\s*[A-Za-z0-9._~+/=-]+",
    ]
]
LOCAL_ID_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        re.escape(USER_HOME_PREFIX) + r"/[A-Za-z0-9._-]+\b",
        re.escape(FILE_URI_PREFIX),
        r"\b" + re.escape(PERSONAL_NAME) + r"\b",
        r"\b" + re.escape(PERSONAL_HANDLE) + r"\b",
        r"\b" + re.escape(ORG_NAME) + r"\b",
        PERSONAL_EMAIL_DOMAIN,
    ]
]
REVIEW_METADATA_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\b[0-9a-f]{40}\b",
        r"\buntracked\b",
        r"\bdirty\b",
        r"\bworking tree\b",
    ]
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def iter_text_files(paths: list[Path]) -> list[Path]:
    files = []
    for path in paths:
        if path.is_dir():
            files.extend(item for item in path.rglob("*") if item.is_file())
        else:
            files.append(path)
    return sorted(path for path in files if path.suffix.lower() != ".png")


def scan_sensitive(paths: list[Path]) -> list[str]:
    hits = []
    for path in paths:
        if path.is_dir():
            scan_paths = [item for item in path.rglob("*") if item.is_file()]
        else:
            scan_paths = [path]
        for item in scan_paths:
            text = item.read_text(encoding="utf-8", errors="ignore")
            for pattern in SENSITIVE_PATTERNS:
                if pattern.search(text):
                    hits.append(str(item))
                    break
    return sorted(set(hits))


def scan_patterns(paths: list[Path], patterns: list[re.Pattern]) -> list[str]:
    return scan_text_paths(paths, patterns)


def scan_text_paths(paths: list[Path], patterns: list[re.Pattern]) -> list[str]:
    hits = []
    for path in iter_text_files(paths):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in patterns):
                hits.append(f"{path}:{line_number}")
    return hits


def validate_anonymous_manuscript(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    compact = re.sub(r"\s+", "", text)
    failures = []
    class_match = re.search(r"\\documentclass\[(?P<options>[^\]]+)\]\{acmart\}", text)
    if not class_match or "anonymous" not in {option.strip() for option in class_match.group("options").split(",")}:
        failures.append("documentclass missing anonymous option")
    if r"\author{Anonymous Authors}" not in text:
        failures.append("missing anonymous author placeholder")
    if r"\institution{AnonymousInstitution}" not in compact:
        failures.append("missing anonymous institution placeholder")
    if re.search(r"\\email\{", text):
        failures.append("anonymous manuscript contains email metadata")
    return failures


def scan_pdf_metadata(path: Path) -> list[str]:
    text = path.read_bytes().decode("latin-1", errors="ignore")
    hits = []
    if any(pattern.search(text) for pattern in LOCAL_ID_PATTERNS):
        hits.append(f"{path}:local_identifier")
    if any(pattern.search(text) for pattern in SENSITIVE_PATTERNS):
        hits.append(f"{path}:sensitive_token")
    author_match = re.search(r"/Author\s*(?:\((?P<paren>[^)]*)\)|<(?P<hex>[^>]*)>|(?P<plain>\S+))", text)
    if author_match:
        author_value = next((value for value in author_match.groupdict().values() if value), "")
        if "Anonymous" not in author_value:
            hits.insert(0, f"{path}:author_metadata")
    return hits


def verify(pdf_path: str | Path | None = None) -> dict:
    for path in REQUIRED_PACKAGE_FILES:
        assert_condition(path.exists(), f"missing required file: {path}")
    assert_condition(CANONICAL_RAW_DIR.exists(), f"missing raw output directory: {CANONICAL_RAW_DIR}")

    rows = read_csv(CANONICAL_CSV)
    assert_condition(len(rows) == EXPECTED_ROWS, f"expected {EXPECTED_ROWS} CSV rows, found {len(rows)}")
    assert_condition(sum(bool(row.get("error")) for row in rows) == 0, "canonical CSV contains error rows")
    assert_condition(all(row.get("feature_json") for row in rows), "canonical CSV has empty feature_json")
    assert_condition(len({row["artifact_id"] for row in rows}) == EXPECTED_ROWS, "artifact IDs are not unique")
    assert_condition({row["run_id"] for row in rows} == {EXPECTED_RUN_ID}, "unexpected run_id in canonical CSV")
    assert_condition({row["config_hash"] for row in rows} == {EXPECTED_CONFIG_HASH}, "unexpected config_hash in CSV")

    raw_paths = [Path(row["raw_output_path"]) for row in rows]
    assert_condition(all(path.exists() for path in raw_paths), "one or more raw output paths are missing")
    assert_condition(len({str(path) for path in raw_paths}) == EXPECTED_ROWS, "raw output paths are not unique")
    actual_raw_paths = sorted(path for path in CANONICAL_RAW_DIR.rglob("*") if path.is_file())
    assert_condition(len(actual_raw_paths) == EXPECTED_ROWS, "canonical raw directory has unexpected file count")
    assert_condition(
        {path.resolve() for path in actual_raw_paths} == {path.resolve() for path in raw_paths},
        "canonical raw directory membership does not match CSV raw_output_path values",
    )

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert_condition(manifest["completeness_status"] == "complete", "manifest is not complete")
    assert_condition(manifest["expected_matrix_rows"] == EXPECTED_ROWS, "manifest expected row count mismatch")
    assert_condition(manifest["observed_expected_rows"] == EXPECTED_ROWS, "manifest observed row count mismatch")
    assert_condition(manifest["missing_expected_rows"] == 0, "manifest reports missing expected rows")
    assert_condition(manifest["errored_rows_after_dedupe"] == 0, "manifest reports errored rows")
    assert_condition(manifest["unexpected_artifact_ids"] == 0, "manifest reports unexpected artifacts")

    ui_baseline_rows = read_csv(Path("analysis_output/baselines/ui_baseline_rows.csv"))
    image_baseline_rows = read_csv(Path("analysis_output/baselines/image_baseline_rows.csv"))
    assert_condition(
        len(ui_baseline_rows) == EXPECTED_UI_BASELINE_ROWS,
        f"expected {EXPECTED_UI_BASELINE_ROWS} UI baseline rows, found {len(ui_baseline_rows)}",
    )
    assert_condition(
        len(image_baseline_rows) == EXPECTED_IMAGE_BASELINE_ROWS,
        f"expected {EXPECTED_IMAGE_BASELINE_ROWS} image baseline rows, found {len(image_baseline_rows)}",
    )
    image_paths = [Path(row["image_path"]) for row in image_baseline_rows]
    assert_condition(all(path.exists() for path in image_paths), "one or more image baseline outputs are missing")

    sensitive_hits = scan_sensitive(
        [CANONICAL_CSV, CANONICAL_RAW_DIR, Path("analysis_output/exp8"), Path("analysis_output/baselines")]
    )
    assert_condition(not sensitive_hits, f"sensitive-looking tokens found in: {sensitive_hits}")
    source_sensitive_hits = scan_text_paths(SOURCE_SECRET_SCAN_PATHS, SENSITIVE_PATTERNS)
    assert_condition(not source_sensitive_hits, f"sensitive-looking tokens found in package text: {source_sensitive_hits}")
    local_id_hits = scan_text_paths(EXTERNAL_REVIEW_SCAN_PATHS, LOCAL_ID_PATTERNS)
    assert_condition(not local_id_hits, f"local identifying strings found in: {local_id_hits}")
    review_metadata_hits = scan_text_paths(REVIEW_METADATA_SCAN_FILES, REVIEW_METADATA_PATTERNS)
    assert_condition(not review_metadata_hits, f"stale review metadata found in: {review_metadata_hits}")
    anonymous_failures = validate_anonymous_manuscript(Path("paper/tist2027_presentation_priors.tex"))
    assert_condition(not anonymous_failures, f"anonymous manuscript metadata failures: {anonymous_failures}")
    pdf_metadata_status = "not_requested"
    if pdf_path:
        pdf_hits = scan_pdf_metadata(Path(pdf_path))
        assert_condition(not pdf_hits, f"PDF metadata/local identifier hits found in: {pdf_hits}")
        pdf_metadata_status = "ok"

    return {
        "status": "ok",
        "git_commit": git_commit(),
        "python_version": sys.version.split()[0],
        "csv_sha256": sha256_file(CANONICAL_CSV),
        "raw_dir_sha256": directory_digest(CANONICAL_RAW_DIR),
        "analysis_manifest_sha256": sha256_file(MANIFEST),
        "rows": len(rows),
        "run_id": EXPECTED_RUN_ID,
        "config_hash": EXPECTED_CONFIG_HASH,
        "external_review_scan": {
            "anonymous_manuscript": "ok",
            "local_identifier_scan": "ok",
            "review_metadata_scan": "ok",
            "source_secret_scan": "ok",
            "pdf_metadata_scan": pdf_metadata_status,
            "text_files_scanned": len(iter_text_files(EXTERNAL_REVIEW_SCAN_PATHS)),
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the TIST journal package artifacts")
    parser.add_argument("--pdf", help="Optional compiled PDF path to scan for metadata/local identifiers")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    print(json.dumps(verify(pdf_path=args.pdf), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
