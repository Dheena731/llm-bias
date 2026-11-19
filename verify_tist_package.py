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

from generate_tist_artifact_tables import (
    DEFAULT_ARTIFACTS as TIST_TABLE_ARTIFACTS,
    DEFAULT_OUTPUT_DIR as TIST_ARTIFACT_OUTPUT_DIR,
    verify_artifact_manifest,
)
from verify_tist_bibliography import AUDIT_MARKDOWN, audit_bibliography


EXPECTED_ROWS = 480
EXPECTED_UI_BASELINE_ROWS = 4
EXPECTED_IMAGE_BASELINE_ROWS = 4
EXPECTED_RUN_ID = "exp8_20260601_022210"
EXPECTED_CONFIG_HASH = "b3dd18b8bb4f9863836a8905009630f66e786c1aba0efb8dd923387ca173a7dd"
CANONICAL_CSV = Path("experiment_data/exp8_post_training_priors_20260601_022210.csv")
CANONICAL_RAW_DIR = Path("experiment_artifacts/exp8_text/raw/b3dd18b8bb4f/exp8_20260601_022210")
MANIFEST = Path("analysis_output/exp8/analysis_manifest.json")
TIST_ARTIFACT_MANIFEST = TIST_ARTIFACT_OUTPUT_DIR / "tist_artifact_manifest.json"
TIST_TABLE_ARTIFACT_FILES = [
    TIST_ARTIFACT_OUTPUT_DIR / artifact["path"]
    for artifact in TIST_TABLE_ARTIFACTS
]
TIST_TABLE_INPUTS = [
    r"\input{../" + (TIST_ARTIFACT_OUTPUT_DIR / artifact["path"]).as_posix() + "}"
    for artifact in TIST_TABLE_ARTIFACTS
]
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
    Path("analysis_output/exp8/stage_summary.csv"),
    Path("analysis_output/exp8/stage_condition_summary.csv"),
    Path("analysis_output/exp8/condition_summary.csv"),
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
    TIST_ARTIFACT_MANIFEST,
    *TIST_TABLE_ARTIFACT_FILES,
    Path("analysis_output/tist_revision/summary.json"),
    Path("analysis_output/tist_revision/table_study1_model_level.tex"),
    Path("analysis_output/tist_revision/table_study2_palette.tex"),
    Path("analysis_output/tist_revision/table_study3_model.tex"),
    Path("analysis_output/tist_revision/table_exp8_routes.tex"),
    Path("analysis_output/tist_revision/table_spillover.tex"),
    Path("analysis_output/tist_revision/figures/study2_primary_colors.png"),
    Path("analysis_output/tist_revision/figures/exp8_route_condition.png"),
    Path("experiment_data/exp1_emoji_persistence_20260227_111102.csv"),
    Path("experiment_data/exp2_color_bias_20260331_110130.csv"),
    Path("experiment_data/exp2_color_bias_20260401_182557.csv"),
    Path("experiment_data/exp4_multi_constraint_20260326_154209.csv"),
    Path("experiment_data/exp7_phase_b/exp7_text_defaults_20260706_102517.csv"),
    Path("experiment_data/exp8_v2_local_stagewise_base_20261117_054656.csv"),
    Path("experiment_data/exp8_v2_local_stagewise_base_20261117_101143.csv"),
    Path("experiment_data/exp8_v2_local_stagewise_dpo_20261117_041946.csv"),
    Path("experiment_data/exp8_v2_local_stagewise_instruct_rlvr_20261117_050701.csv"),
    Path("experiment_data/exp8_v2_local_stagewise_sft_20261117_035020.csv"),
    Path("experiment_data/exp8_v2_local_stagewise_sft_20261117_210352.csv"),
    Path("experiment_data/exp8_v2_local_stagewise_dpo_20261117_215543.csv"),
    Path("experiment_data/exp8_v2_local_stagewise_instruct_rlvr_20261117_232209.csv"),
    Path("experiment_data/exp8_v2_local_stagewise_base_20261118_003816.csv"),
    Path("experiment_data/exp8_v2_local_stagewise_base_20261119_130005.csv"),
    Path("experiment_data/exp8_v2_olmo7b_stagewise_base_20261119_161809.csv"),
    Path("experiment_data/exp8_v2_olmo7b_stagewise_sft_20261119_141706.csv"),
    Path("experiment_data/exp8_v2_olmo7b_stagewise_dpo_20261119_150515.csv"),
    Path("experiment_data/exp8_v2_olmo7b_stagewise_instruct_rlvr_20261117_191330.csv"),
    Path("experiment_data/exp8_v2_presentation_priors_20261117_035401.csv"),
    Path("experiment_data/exp8_v2_presentation_priors_20261117_052749.csv"),
    Path("experiment_data/exp8_v2_presentation_priors_20261117_053332.csv"),
    Path("experiment_data/exp8_v2_presentation_priors_20261117_190841.csv"),
    Path("experiment_data/exp8_v2_presentation_priors_20261117_191641.csv"),
    Path("experiment_data/exp8_v2b_controls_20261117_191641.csv"),
    Path("experiment_data/exp8_v2b_controls_20261117_200335.csv"),
    Path("configs/exp8_v2_presentation_priors.json"),
    Path("analysis_output/exp8_v2/table_v2_routes.tex"),
    Path("analysis_output/exp8_v2/table_v2_stages.tex"),
    Path("analysis_output/exp8_v2/olmo_stage_trend.png"),
    Path("analysis_output/exp8_v2/summary.json"),
    Path("analysis_output/exp8_v2/table_v2_controls.tex"),
    Path("analysis_output/exp8_v2/table_v2_length.tex"),
    Path("analysis_output/exp8_v2/table_v2_stages_7b.tex"),
    Path("analysis_output/exp8_v2/table_v2_length_7b.tex"),
    Path("analysis_output/exp8_v2/local_7b_rates.csv"),
    Path("analysis_output/exp8_v2/table_v2_families.tex"),
    Path("analysis_output/exp8_v2/hosted_rates.csv"),
    Path("analysis_output/exp8_v2/controls_rates.csv"),
    Path("analysis_output/exp8_v2/local_1b_rates.csv"),
    Path("analysis_output/preference_mix/summary.json"),
    Path("analysis_output/preference_mix/table_preference_markdown.tex"),
    Path("analysis_output/preference_mix/summary_7b.json"),
    Path("analysis_output/preference_mix/table_preference_markdown_7b.tex"),
    Path("configs/exp8_v2_openai.json"),
    Path("configs/exp8_v2b_controls.json"),
    Path("configs/exp8_v2_olmo7b.json"),
    Path("configs/exp8_v2_olmo1b_extra.json"),
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
    Path("generate_tist_artifact_tables.py"),
    Path("analyze_tist_revision.py"),
    Path("analyze_exp8_v2.py"),
    Path("analyze_preference_markdown.py"),
    Path("presentation_features.py"),
    Path("build_annotation_kit.py"),
    Path("score_annotation.py"),
    Path("experiment8_collect_local.py"),
    Path("experiment7_common.py"),
    Path("analyze_results.py"),
    Path("experiment_runner.py"),
    Path("experiment5_policy_compliance.py"),
    Path("prepare_tist_review_package.py"),
    Path("verify_tist_package.py"),
    Path("verify_tist_bibliography.py"),
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
    Path("tests/test_tist_artifact_tables.py"),
    Path("tests/test_tist_review_package.py"),
    Path("tests/test_tist_package_verifier.py"),
    Path("tests/test_tist_bibliography_verifier.py"),
    Path("tests/test_tist_revision.py"),
    Path("tests/test_exp8_v2_tasks.py"),
    Path("tests/test_score_annotation.py"),
    AUDIT_MARKDOWN,
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
    TIST_ARTIFACT_OUTPUT_DIR,
    Path("analysis_output/tist_revision"),
    Path("analysis_output/exp8_v2"),
    Path("analysis_output/preference_mix"),
]
SCAN_FIXTURE_FILES = {
    Path("tests/test_exp8_fake_collectors.py"),
    Path("tests/test_tist_package_verifier.py"),
    Path("tests/test_tist_review_package.py"),
    # Raw model outputs that the scanner misreads: OLMo base hallucinates a stranger's home paths and an invented
    # HTTP auth header; Gemini's prose explains token-based auth. No real identities or secrets.
    Path("experiment_artifacts/exp8_text/raw/cb7decc19530/exp8v2_local/exp8_text_allenai_olmo_2_0425_1b_research_tooltip_p4_no_emoji_r01.txt"),
    Path("experiment_artifacts/exp8_text/raw/cb7decc19530/exp8v2_local/exp8_text_allenai_olmo_2_0425_1b_technical_explanation_p1_no_markdown_r01.txt"),
    Path("experiment_artifacts/exp8_text/raw/cb7decc19530/exp8v2_hosted/exp8_text_google_gemini_3_8_flash_technical_explanation_p5_diverse_domain_specific_r03.txt"),
    # Same for the extra 1B and the 7B runs: an invented stranger's home path, a webmail domain in prose, a
    # password placeholder, and environment-variable lookups in generated code.
    Path("experiment_artifacts/exp8_text/raw/55cdb9400c95/exp8v2_olmo1b_extra/exp8_text_allenai_olmo_2_0425_1b_enterprise_admin_message_p5_polished_but_plain_r03.txt"),
    Path("experiment_artifacts/exp8_text/raw/55cdb9400c95/exp8v2_olmo1b_extra/exp8_text_allenai_olmo_2_0425_1b_research_tooltip_p4_diverse_domain_specific_r02.txt"),
    Path("experiment_artifacts/exp8_text/raw/55cdb9400c95/exp8v2_olmo1b_extra/exp8_text_allenai_olmo_2_0425_1b_finance_update_p2_use_markdown_r02.txt"),
    Path("experiment_artifacts/exp8_text/raw/5351ee630289/exp8v2_olmo7b/exp8_text_allenai_olmo_2_1124_7b_research_tooltip_p5_neutral_r01.txt"),
}
SOURCE_SECRET_SCAN_PATHS = [
    path for path in EXTERNAL_REVIEW_SCAN_PATHS if path not in SCAN_FIXTURE_FILES
]
LOCAL_IDENTIFIER_SCAN_PATHS = [
    path for path in EXTERNAL_REVIEW_SCAN_PATHS if path not in SCAN_FIXTURE_FILES
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
        r"\bsk-[A-Za-z0-9_-]{20,}\b",
        r"\bghp_[A-Za-z0-9_]{20,}\b",
        r"\bgithub_pat_[A-Za-z0-9_]{20,}\b",
        r"\bAIza[0-9A-Za-z_-]{20,}\b",
        r"\bAKIA[0-9A-Z]{16}\b",
        r"\bnpm_[A-Za-z0-9]{20,}\b",
        r"\b(?:api[_-]?key|token|secret|password)\b\s*[:=]\s*(?!os\.(?:environ|getenv))[\"']?[A-Za-z0-9._~+/=-]{12,}",
    ]
]
LOCAL_PATH_PATTERNS = [
    # Case-sensitive: macOS home paths are "/Users/...", while model text often says "customers/users/community".
    re.compile(re.escape(USER_HOME_PREFIX) + r"/[A-Za-z0-9._-]+\b"),
] + [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        re.escape(FILE_URI_PREFIX),
        r"/private" + r"/var/[^\s\"']+",
        r"/var" + r"/folders/[^\s\"']+",
        r"/opt" + r"/homebrew/[^\s\"']+",
        r"C:" + r"\\\\Users\\\\[A-Za-z0-9._-]+",
    ]
]
REVIEW_IDENTITY_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\b" + re.escape(PERSONAL_NAME) + r"\b",
        r"\b" + re.escape(PERSONAL_HANDLE) + r"\b",
        r"\b" + re.escape(ORG_NAME) + r"\b",
        PERSONAL_EMAIL_DOMAIN,
    ]
]
LOCAL_ID_PATTERNS = LOCAL_PATH_PATTERNS + REVIEW_IDENTITY_PATTERNS
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
    options = {option.strip() for option in class_match.group("options").split(",")} if class_match else set()
    if "anonymous" not in options:
        failures.append("documentclass missing anonymous option")
    if r"\author{Anonymous Authors}" not in text:
        failures.append("missing anonymous author placeholder")
    if r"\institution{AnonymousInstitution}" not in compact:
        failures.append("missing anonymous institution placeholder")
    if re.search(r"\\email\{", text):
        failures.append("anonymous manuscript contains email metadata")
    return failures


def validate_review_mode_metadata(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    failures = []
    class_match = re.search(r"\\documentclass\[(?P<options>[^\]]+)\]\{acmart\}", text)
    options = {option.strip() for option in class_match.group("options").split(",")} if class_match else set()
    if "review" not in options:
        failures.append("documentclass missing review option")
    if r"\setcopyright{none}" not in text:
        failures.append("review manuscript must use setcopyright none")
    if r"\settopmatter{printacmref=false}" not in text:
        failures.append("review manuscript must suppress ACM reference block")
    if r"\renewcommand\footnotetextcopyrightpermission[1]{}" not in text:
        failures.append("review manuscript must suppress ACM copyright footnote")
    for field in ["acmVolume", "acmNumber", "acmArticle"]:
        if not re.search(rf"\\{field}\{{0\}}", text):
            failures.append(f"review manuscript missing placeholder {field}=0")
    return failures


def validate_camera_ready_metadata(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    failures = []
    class_match = re.search(r"\\documentclass\[(?P<options>[^\]]+)\]\{acmart\}", text)
    options = {option.strip() for option in class_match.group("options").split(",")} if class_match else set()
    if "review" in options:
        failures.append("camera-ready metadata still has review option")
    if "anonymous" in options:
        failures.append("camera-ready metadata still has anonymous option")
    if r"\author{Anonymous Authors}" in text:
        failures.append("camera-ready metadata still uses anonymous author placeholder")
    if r"\setcopyright{none}" in text:
        failures.append("camera-ready metadata still has setcopyright none")
    if r"\settopmatter{printacmref=false}" in text:
        failures.append("camera-ready metadata still suppresses ACM reference block")
    if r"\renewcommand\footnotetextcopyrightpermission[1]{}" in text:
        failures.append("camera-ready metadata still suppresses ACM copyright footnote")
    for field in ["acmVolume", "acmNumber", "acmArticle"]:
        if re.search(rf"\\{field}\{{0\}}", text):
            failures.append(f"camera-ready metadata still has placeholder {field}=0")
    if not re.search(r"\\email\{[^}]+\}", text):
        failures.append("camera-ready metadata missing author email")
    return failures


def scan_pdf_metadata(path: Path, mode: str = "review") -> list[str]:
    text = path.read_bytes().decode("latin-1", errors="ignore")
    hits = []
    identifier_patterns = LOCAL_ID_PATTERNS if mode == "review" else LOCAL_PATH_PATTERNS
    if any(pattern.search(text) for pattern in identifier_patterns):
        hits.append(f"{path}:local_identifier")
    if any(pattern.search(text) for pattern in SENSITIVE_PATTERNS):
        hits.append(f"{path}:sensitive_token")
    author_match = re.search(r"/Author\s*(?:\((?P<paren>[^)]*)\)|<(?P<hex>[^>]*)>|(?P<plain>\S+))", text)
    if mode == "review" and author_match:
        author_value = next((value for value in author_match.groupdict().values() if value), "")
        if "Anonymous" not in author_value:
            hits.insert(0, f"{path}:author_metadata")
    return hits


def validate_analysis_manifest_inputs(manifest: dict, canonical_csv: Path = CANONICAL_CSV) -> list[str]:
    failures = []
    canonical_input = canonical_csv.as_posix()
    if manifest.get("input_files") != [canonical_input]:
        failures.append("analysis manifest input_files mismatch")
    input_hashes = manifest.get("input_file_sha256", {})
    if input_hashes.get(canonical_input) != sha256_file(canonical_csv):
        failures.append("analysis manifest input_file_sha256 mismatch")
    return failures


def validate_tist_table_inputs(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [table_input for table_input in TIST_TABLE_INPUTS if table_input not in text]


def verify(pdf_path: str | Path | None = None, mode: str = "review") -> dict:
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
    analysis_input_failures = validate_analysis_manifest_inputs(manifest, CANONICAL_CSV)
    assert_condition(
        not analysis_input_failures,
        f"analysis manifest input provenance failures: {analysis_input_failures}",
    )

    artifact_table_failures = verify_artifact_manifest(TIST_ARTIFACT_OUTPUT_DIR, verify_regeneration=True)
    assert_condition(
        not artifact_table_failures,
        f"generated TIST table artifact manifest failures: {artifact_table_failures}",
    )
    missing_table_inputs = validate_tist_table_inputs(Path("paper/tist2027_presentation_priors.tex"))
    assert_condition(
        not missing_table_inputs,
        f"manuscript missing generated TIST table inputs: {missing_table_inputs}",
    )

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
        [
            CANONICAL_CSV,
            CANONICAL_RAW_DIR,
            Path("analysis_output/exp8"),
            Path("analysis_output/baselines"),
            TIST_ARTIFACT_OUTPUT_DIR,
        ]
    )
    assert_condition(not sensitive_hits, f"sensitive-looking tokens found in: {sensitive_hits}")
    source_sensitive_hits = scan_text_paths(SOURCE_SECRET_SCAN_PATHS, SENSITIVE_PATTERNS)
    assert_condition(not source_sensitive_hits, f"sensitive-looking tokens found in package text: {source_sensitive_hits}")
    local_identifier_patterns = LOCAL_ID_PATTERNS if mode == "review" else LOCAL_PATH_PATTERNS
    local_id_hits = scan_text_paths(LOCAL_IDENTIFIER_SCAN_PATHS, local_identifier_patterns)
    assert_condition(not local_id_hits, f"local identifying strings found in: {local_id_hits}")
    review_metadata_hits = scan_text_paths(REVIEW_METADATA_SCAN_FILES, REVIEW_METADATA_PATTERNS)
    assert_condition(not review_metadata_hits, f"stale review metadata found in: {review_metadata_hits}")
    manuscript_path = Path("paper/tist2027_presentation_priors.tex")
    metadata_status_key = "review_mode_metadata" if mode == "review" else "camera_ready_metadata"
    if mode == "review":
        anonymous_failures = validate_anonymous_manuscript(manuscript_path)
        assert_condition(not anonymous_failures, f"anonymous manuscript metadata failures: {anonymous_failures}")
        review_mode_failures = validate_review_mode_metadata(manuscript_path)
        assert_condition(not review_mode_failures, f"review-mode ACM metadata failures: {review_mode_failures}")
    elif mode == "camera-ready":
        camera_ready_failures = validate_camera_ready_metadata(manuscript_path)
        assert_condition(not camera_ready_failures, f"camera-ready ACM metadata failures: {camera_ready_failures}")
    else:
        raise AssertionError(f"unsupported verifier mode: {mode}")
    bibliography_audit = audit_bibliography()
    assert_condition(
        bibliography_audit["status"] == "ok",
        f"bibliography metadata audit failed: {bibliography_audit}",
    )
    pdf_metadata_status = "not_requested"
    if pdf_path:
        pdf_hits = scan_pdf_metadata(Path(pdf_path), mode=mode)
        assert_condition(not pdf_hits, f"PDF metadata/local identifier hits found in: {pdf_hits}")
        pdf_metadata_status = "ok"

    return {
        "status": "ok",
        "git_commit": git_commit(),
        "python_version": sys.version.split()[0],
        "csv_sha256": sha256_file(CANONICAL_CSV),
        "raw_dir_sha256": directory_digest(CANONICAL_RAW_DIR),
        "analysis_manifest_sha256": sha256_file(MANIFEST),
        "tist_artifact_manifest_sha256": sha256_file(TIST_ARTIFACT_MANIFEST),
        "rows": len(rows),
        "run_id": EXPECTED_RUN_ID,
        "config_hash": EXPECTED_CONFIG_HASH,
        "mode": mode,
        "external_review_scan": {
            "bibliography_metadata": "ok",
            "generated_table_artifacts": "ok",
            "generated_table_inputs": "ok",
            metadata_status_key: "ok",
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
    parser.add_argument("--mode", choices=["review", "camera-ready"], default="review")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    print(json.dumps(verify(pdf_path=args.pdf, mode=args.mode), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
