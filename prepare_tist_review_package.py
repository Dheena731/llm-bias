"""Prepare the anonymous TIST external-review package."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

from verify_tist_package import (
    CANONICAL_RAW_DIR,
    EXPECTED_ROWS,
    EXPECTED_RUN_ID,
    LOCAL_ID_PATTERNS,
    REQUIRED_PACKAGE_FILES,
    SCAN_FIXTURE_FILES,
    SENSITIVE_PATTERNS,
    git_commit,
    scan_text_paths,
)


DEFAULT_OUTPUT_DIR = Path("artifact/tist2027_external_review")
DEFAULT_ARCHIVE_PATH = DEFAULT_OUTPUT_DIR.with_suffix(".zip")
PACKAGE_PROVENANCE_PATH = Path("PACKAGE_PROVENANCE.json")
DETERMINISTIC_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
EXPORT_DIRECTORIES = [
    CANONICAL_RAW_DIR,
    Path("analysis_output/baselines/generated_images"),
]
EXCLUDED_PATHS = [
    Path(".git"),
    Path(".env"),
    Path(".pytest_cache"),
    Path("artifact/aisec2026_anonymous"),
    Path("experiment_artifacts/logs"),
    Path("experiment_artifacts/exp7_images"),
    Path("experiment_artifacts/exp7_text"),
    Path("experiment_artifacts/exp7_ui"),
    Path("experiment_artifacts/exp8_text/raw/6e5e2e0fa956"),
    Path("experiment_artifacts/exp8_text/raw/b3dd18b8bb4f/exp8_20260601_002652"),
    Path("experiment_artifacts/exp8_text/raw/d1a27ec3ad12"),
    Path("experiment_data/exp8_post_training_priors_20260601_001606.csv"),
    Path("experiment_data/exp8_post_training_priors_20260601_002652.csv"),
]
EXCLUDED_NAME_PARTS = {"__pycache__", ".DS_Store"}
DISALLOWED_EXPORT_SUFFIXES = {".pdf", ".zip", ".tar", ".tgz", ".gz", ".jpg", ".jpeg", ".pyc"}
CLAIM_BOUNDARY_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bRLHF\b.{0,60}\b(causes?|explains?|drives?|induces?|mechanism|responsible for|attributable to|accounts for|source of)\b",
        r"\bRLHF\b.{0,60}\b(shapes?|produces?|creates?|yields?|results? in|leads to)\b",
        r"\b(caused|explained|driven|induced|attributable)\s+by\b.{0,50}\bRLHF\b",
        r"\bmechanism\s+(?:is|:)\s+(?:RLHF|post[- ]training)\b",
        r"\bpost[- ]training\b.{0,60}\b(causes?|explains?|drives?|induces?|mechanism|responsible for|attributable to|accounts for|source of)\b",
        r"\bpost[- ]training\b.{0,40}\b(source|origin)\s+of\b",
        r"\b(defaults?|behaviou?r|presentation priors?)\b.{0,60}\b(results?|arises?|stems?)\s+from\b.{0,40}\b(RLHF|post[- ]training)\b",
        r"\bevidence\b.{0,40}\b(supports?|shows?|establishes?)\b.{0,40}\bpost[- ]training causality\b",
        r"\b(base[-/ ]?instruct[-/ ]?chat|base[- ]vs[- ]instruct)\b.{0,50}\b(route[- ]stage|probe|evidence|effect)\b",
        r"\broute[- ]stage\b.{0,50}\b(causal|causality|effect|mechanism|inference)\b",
        r"\broute labels?\b.{0,50}\b(reveal|show|identify|explain).{0,30}\btraining[- ]stage\b",
        r"\broute labels?\b.{0,50}\b(demonstrate|imply|separate|distinguish|differentiate)\b.{0,40}\b(training[- ]stage|base|instruct)\b",
        r"\btraining[- ]stage\b.{0,40}\b(effect|effects|mechanism|inference|causality)\b",
        r"\b(purple[- ]bias|biased toward purple|models? prefer purple|purple preference)\b",
        r"\b(broad|universal|general)\s+purple/pink\s+bias\b",
        r"\bmodels?\b.{0,40}\bprefer\b.{0,30}\b(purple|pink|purple/pink)\b",
        r"\bmodels?\b.{0,40}\bfavou?rs?\b.{0,30}\b(purple|pink|purple/pink)\b",
        r"\b(purple|pink|purple/pink)\b.{0,30}\bdominates?\b.{0,30}\b(palettes?|colors?)\b",
        r"\b(UI|image|human[- ]vs[- ]model|design[- ]system[- ]vs[- ]model).{0,60}\bhomogeni[sz]ation\b",
        r"\bgenerated (UI|artifacts?).{0,50}\bunusually homogeneous\b",
        r"\bgenerated (UI|image|artifacts?|outputs?).{0,60}\b(converge|converges|converged|convergent|similarity|same look|homogeneous style)\b",
        r"\bgenerated images?\b.{0,50}\bshare\b.{0,30}\bsame style\b",
        r"\bgenerated UI outputs?\b.{0,50}\b(highly similar|same style|same look)\b",
        r"\bUI artifacts?\b.{0,50}\b(converge|converges|converged)\b.{0,30}\bsame style\b",
        r"\bcross[- ]modal artifact similarity\b.{0,40}\b(unusually high|strong|homogeneous)\b",
    ]
]
CLAIM_BOUNDARY_SAFE_PREFIX_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bdo not\b.{0,40}\b(claim|make|frame|treat|use|generalize)\b",
        r"\bdoes not\b.{0,30}\b(show|support|prove|establish|identify|claim)\b",
        r"\bnot\b.{0,20}\b(evidence|proof|causal|causality|causally|supported|attributable|claim|bias)\b",
        r"\bunsupported\b",
        r"\brather than\b",
        r"\bwithout\b.{0,40}\b(verified|balanced|stronger|direct|base|route|provenance|baselines|evidence)\b",
        r"\brequires?\b.{0,40}\b(verified|balanced|stronger|direct|base|route|provenance|baselines|evidence)\b",
        r"\bneeded before\b",
    ]
]
CLAIM_BOUNDARY_FILE_SUFFIXES = {".md", ".tex", ".txt"}


def iter_export_inputs() -> list[Path]:
    return sorted(set(REQUIRED_PACKAGE_FILES + EXPORT_DIRECTORIES))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_file(src: Path, dest_root: Path) -> Path:
    dest = dest_root / src
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def _copy_directory(src: Path, dest_root: Path) -> list[Path]:
    if not src.exists():
        raise FileNotFoundError(f"missing required directory: {src}")
    copied = []
    for path in sorted(item for item in src.rglob("*") if item.is_file()):
        copied.append(_copy_file(path, dest_root))
    return copied


def write_export_readme(dest_root: Path) -> Path:
    path = dest_root / "README.md"
    path.write_text(
        """# Anonymous TIST 2027 External Review Package

This package preserves repository-relative paths so the local verifier can run
from the package root without path rewriting.

## Offline Reproduction

```bash
uv run python experiment8_collect_text.py --dry-run
uv run python analyze_post_training_priors.py --input experiment_data/exp8_post_training_priors_20260601_022210.csv --expected-runs-per-cell 2
uv run python analyze_text_baselines.py
uv run python analyze_cross_modal_baselines.py
uv run python validate_feature_audit_samples.py
uv run python verify_tist_bibliography.py --write-audit
uv run python generate_tist_artifact_tables.py
uv run python verify_tist_package.py --mode review
```

The checked evidence is the fixed 480-row Exp8 first pass. Live collection is
not required to reproduce the package tables or verifier result.

## Optional Live Collection

The following command can incur provider/API cost and should be used only after
reviewing `EXPERIMENT8_PROTOCOL.md` and setting the required API credentials:

```bash
uv run python experiment8_collect_text.py --full --confirm-full --runs-per-cell 2 --max-workers 4
```

## Contents

- `paper/`: anonymous ACM-style manuscript, bibliography, package notes, and claim audit.
- `experiment_data/`: canonical Exp8 CSV.
- `experiment_artifacts/`: canonical run-scoped raw Exp8 outputs.
- `analysis_output/`: deterministic analysis outputs, table fragments, and reference baselines.
- `tests/`: focused package, analysis, bibliography, and baseline tests.
- `PACKAGE_PROVENANCE.json`: source commit and canonical run identifiers for this export.
- `MANIFEST.sha256`: SHA-256 hashes for every bundled file except this manifest.
- `PACKAGE_SCAN.json`: export-tree anonymity, secret, excluded-path, and claim-boundary scan result.

Do not add author names, affiliations, acknowledgements, local paths, API keys,
or noncanonical experiment artifacts to this anonymous review package.
""",
        encoding="utf-8",
    )
    return path


def resolve_source_commit(source_commit: str | None = None) -> str:
    commit = source_commit or os.environ.get("TIST_REVIEW_SOURCE_COMMIT") or git_commit()
    try:
        return subprocess.check_output(["git", "rev-parse", commit], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return commit


def write_package_provenance(dest_root: Path, source_commit: str | None = None) -> Path:
    path = dest_root / PACKAGE_PROVENANCE_PATH
    resolved_source_commit = resolve_source_commit(source_commit)
    provenance = {
        "archive_sha256_location": "tracked outside the archive in TIST_EXTERNAL_REVIEW_HANDOFF.md",
        "canonical_exp8_rows": EXPECTED_ROWS,
        "canonical_exp8_run_id": EXPECTED_RUN_ID,
        "git_commit": resolved_source_commit,
        "package": "tist2027_external_review",
    }
    path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def prepare_package(output_dir: Path = DEFAULT_OUTPUT_DIR, source_commit: str | None = None) -> dict[str, Any]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    copied = []
    for src in iter_export_inputs():
        if src.is_dir():
            copied.extend(_copy_directory(src, output_dir))
        elif src.exists():
            copied.append(_copy_file(src, output_dir))
        else:
            raise FileNotFoundError(f"missing required file: {src}")
    copied.append(write_export_readme(output_dir))
    copied.append(write_package_provenance(output_dir, source_commit))
    manifest = write_sha256_manifest(output_dir)
    scan_result = scan_export_tree(output_dir)
    scan_path = output_dir / "PACKAGE_SCAN.json"
    scan_path.write_text(json.dumps(scan_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_sha256_manifest(output_dir)
    return {
        "output_dir": output_dir.as_posix(),
        "copied_files": len(copied),
        "manifest": manifest.as_posix(),
        "scan": scan_path.as_posix(),
        "scan_status": scan_result["status"],
    }


def remove_generated_export_state(root: Path) -> None:
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if path.name == "__pycache__" and path.is_dir():
            shutil.rmtree(path)
        elif path.name == ".DS_Store" and path.is_file():
            path.unlink()
        elif path.suffix.lower() == ".pyc" and path.is_file():
            path.unlink()


def refresh_export_scan(output_dir: Path) -> dict[str, Any]:
    remove_generated_export_state(output_dir)
    (output_dir / "PACKAGE_SCAN.json").touch(exist_ok=True)
    (output_dir / "MANIFEST.sha256").touch(exist_ok=True)
    scan_result = scan_export_tree(output_dir)
    scan_path = output_dir / "PACKAGE_SCAN.json"
    scan_path.write_text(json.dumps(scan_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_sha256_manifest(output_dir)
    return scan_result


def write_sha256_manifest(root: Path) -> Path:
    lines = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.name == "MANIFEST.sha256":
            continue
        relative = path.relative_to(root).as_posix()
        lines.append(f"{sha256_file(path)}  {relative}")
    manifest = root / "MANIFEST.sha256"
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def _relative_hits(root: Path, hits: list[str]) -> list[str]:
    relative_hits = []
    root_text = root.as_posix()
    for hit in hits:
        relative_hits.append(hit.replace(root_text + "/", ""))
    return relative_hits


def _excluded_path_hits(root: Path) -> list[str]:
    hits = []
    for path in EXCLUDED_PATHS:
        if (root / path).exists():
            hits.append(path.as_posix())
    for path in root.rglob("*"):
        if any(part in EXCLUDED_NAME_PARTS for part in path.parts):
            hits.append(path.relative_to(root).as_posix())
    return sorted(set(hits))


def _claim_boundary_hits(root: Path) -> list[str]:
    hits = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.suffix.lower() not in CLAIM_BOUNDARY_FILE_SUFFIXES:
            continue
        rel = path.relative_to(root)
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        in_code_block = False
        for line_number, line in enumerate(lines, start=1):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            for pattern in CLAIM_BOUNDARY_PATTERNS:
                for match in pattern.finditer(line):
                    if not _is_bounded_claim_context(lines, line_number, match.start(), match.end()):
                        hits.append(f"{rel.as_posix()}:{line_number}")
                        break
                else:
                    continue
                break
    return hits


def _is_bounded_claim_context(lines: list[str], line_number: int, span_start: int, span_end: int) -> bool:
    line = lines[line_number - 1].lower()
    prefix_segment = re.split(r"[.;!?,:]\s+", line[:span_start])[-1]
    if any(pattern.search(prefix_segment) for pattern in CLAIM_BOUNDARY_SAFE_PREFIX_PATTERNS):
        return True
    previous = [item.strip().lower() for item in lines[max(0, line_number - 4) : line_number - 1]]
    if any(item.rstrip(":") in {"avoid", "unsafe exp8 claim", "do not claim", "do not use"} for item in previous):
        return True
    if line.lstrip().startswith((">", "-", "*")) and any("unsafe" in item or item.rstrip(":") == "avoid" for item in previous):
        return True
    return False


def _disallowed_binary_hits(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in DISALLOWED_EXPORT_SUFFIXES
    )


def scan_export_tree(root: Path) -> dict[str, Any]:
    text_roots = [root]
    local_hits = _filter_fixture_hits(_relative_hits(root, scan_text_paths(text_roots, LOCAL_ID_PATTERNS)))
    secret_hits = _filter_fixture_hits(_relative_hits(root, scan_text_paths(text_roots, SENSITIVE_PATTERNS)))
    excluded_hits = _excluded_path_hits(root)
    claim_hits = _claim_boundary_hits(root)
    binary_hits = _disallowed_binary_hits(root)
    failures = {}
    if local_hits:
        failures["local_identifier_scan"] = local_hits
    if secret_hits:
        failures["source_secret_scan"] = secret_hits
    if excluded_hits:
        failures["excluded_path_scan"] = excluded_hits
    if claim_hits:
        failures["claim_boundary_scan"] = claim_hits
    if binary_hits:
        failures["binary_payload_scan"] = binary_hits
    return {
        "status": "ok" if not failures else "fail",
        "failures": failures,
        "text_files_scanned": len([path for path in root.rglob("*") if path.is_file() and path.suffix.lower() != ".png"]),
    }


def _filter_fixture_hits(hits: list[str]) -> list[str]:
    filtered = []
    fixture_prefixes = tuple(path.as_posix() + ":" for path in SCAN_FIXTURE_FILES)
    for hit in hits:
        if hit.startswith(fixture_prefixes):
            continue
        filtered.append(hit)
    return filtered


def create_zip(output_dir: Path = DEFAULT_OUTPUT_DIR, archive_path: Path = DEFAULT_ARCHIVE_PATH) -> Path:
    scan_result = refresh_export_scan(output_dir)
    if scan_result["status"] != "ok":
        raise AssertionError(f"refusing to archive package with scan failures: {scan_result['failures']}")
    if archive_path.exists():
        archive_path.unlink()
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(item for item in output_dir.rglob("*") if item.is_file()):
            relative = path.relative_to(output_dir).as_posix()
            info = zipfile.ZipInfo(relative, DETERMINISTIC_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return archive_path


def run_bundle_verifier(output_dir: Path) -> dict[str, Any]:
    command = [sys.executable, "verify_tist_package.py", "--mode", "review"]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(command, cwd=output_dir, env=env, text=True, capture_output=True, check=True)
    return json.loads(completed.stdout)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare anonymous TIST external-review package")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--archive-path", default=str(DEFAULT_ARCHIVE_PATH))
    parser.add_argument(
        "--source-commit",
        help="Commit recorded in PACKAGE_PROVENANCE.json; use this after committing outside-archive handoff docs.",
    )
    parser.add_argument("--skip-zip", action="store_true")
    parser.add_argument("--verify", action="store_true", help="Run verify_tist_package.py inside the package")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    output_dir = Path(args.output_dir)
    archive_path = Path(args.archive_path)
    result = prepare_package(output_dir, source_commit=args.source_commit)
    if result["scan_status"] != "ok":
        raise SystemExit(json.dumps(result, indent=2, sort_keys=True))
    if args.verify:
        result["bundle_verifier"] = run_bundle_verifier(output_dir)
        final_scan = refresh_export_scan(output_dir)
        result["scan_status"] = final_scan["status"]
        if final_scan["status"] != "ok":
            raise SystemExit(json.dumps(result, indent=2, sort_keys=True))
    if not args.skip_zip:
        result["archive_path"] = create_zip(output_dir, archive_path).as_posix()
        result["archive_sha256"] = sha256_file(archive_path)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
