"""Verify the current TIST presentation-priors journal package artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


EXPECTED_ROWS = 480
EXPECTED_RUN_ID = "exp8_20260601_022210"
EXPECTED_CONFIG_HASH = "b3dd18b8bb4f9863836a8905009630f66e786c1aba0efb8dd923387ca173a7dd"
CANONICAL_CSV = Path("experiment_data/exp8_post_training_priors_20260601_022210.csv")
CANONICAL_RAW_DIR = Path("experiment_artifacts/exp8_text/raw/b3dd18b8bb4f/exp8_20260601_022210")
MANIFEST = Path("analysis_output/exp8/analysis_manifest.json")
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
    Path("paper/tist2027_presentation_priors.tex"),
    Path("paper/tist2027_presentation_priors_refs.bib"),
    Path("paper/haips2026_refs.bib"),
    Path("paper/tist2027_journal_package_manifest.md"),
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


def verify() -> dict:
    for path in REQUIRED_FILES:
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

    sensitive_hits = scan_sensitive([CANONICAL_CSV, CANONICAL_RAW_DIR, Path("analysis_output/exp8")])
    assert_condition(not sensitive_hits, f"sensitive-looking tokens found in: {sensitive_hits}")

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
    }


def main() -> None:
    print(json.dumps(verify(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
