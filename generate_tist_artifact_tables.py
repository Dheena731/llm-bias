"""Generate final TIST LaTeX table artifacts from checked analysis outputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("analysis_output/tist_package")
ANALYSIS_MANIFEST = Path("analysis_output/exp8/analysis_manifest.json")
STAGE_SUMMARY = Path("analysis_output/exp8/stage_summary.csv")
CONDITION_SUMMARY = Path("analysis_output/exp8/condition_summary.csv")
CONFIDENCE_INTERVALS = Path("analysis_output/exp8/confidence_intervals.csv")
PLANNED_CONTRASTS = Path("analysis_output/exp8/planned_contrasts_fdr.csv")

DEFAULT_SOURCES = [ANALYSIS_MANIFEST, STAGE_SUMMARY, CONDITION_SUMMARY, CONFIDENCE_INTERVALS, PLANNED_CONTRASTS]
DEFAULT_ARTIFACTS = [
    {"name": "exp8_completeness", "path": "table_exp8_completeness.tex"},
    {"name": "exp8_stage_summary", "path": "table_exp8_stage_summary.tex"},
    {"name": "exp8_condition_summary", "path": "table_exp8_condition_summary.tex"},
    {"name": "exp8_ci_contrasts", "path": "table_exp8_ci_contrasts.tex"},
]

CONDITION_ORDER = [
    "neutral",
    "no_emoji",
    "plain_no_markdown",
    "diverse_domain_specific",
    "polished_but_plain",
]
CI_ROWS = [
    ("neutral", "has_format_default", "Neutral format default"),
    ("neutral", "has_markdown", "Neutral Markdown"),
    ("neutral", "has_emoji", "Neutral emoji"),
    ("no_emoji", "has_emoji", "No-emoji emoji"),
    ("plain_no_markdown", "has_format_default", "Plain-no-Markdown format default"),
    ("plain_no_markdown", "has_markdown", "Plain-no-Markdown Markdown"),
    ("polished_but_plain", "has_format_default", "Polished-but-plain format default"),
    ("polished_but_plain", "has_polish_default", "Polished-but-plain polish default"),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def pct(value: str | float) -> str:
    return f"{float(value) * 100:.1f}\\%"


def ci_pct(low: str | float, high: str | float) -> str:
    return f"[{float(low) * 100:.1f}, {float(high) * 100:.1f}]\\%"


def texttt(value: str) -> str:
    return r"\texttt{" + value.replace("_", r"\_") + "}"


def q_value(value: str) -> str:
    number = float(value)
    if number == 0.0 or abs(number) < 1e-12:
        return r"$<10^{-12}$"
    if abs(number) < 0.001:
        exponent = 0
        mantissa = number
        while abs(mantissa) < 1:
            mantissa *= 10
            exponent -= 1
        return rf"${mantissa:.2f}\times10^{{{exponent}}}$"
    return f"{number:.3f}"


def signed_decimal(value: str | float) -> str:
    return f"{float(value):.3f}"


def table_exp8_completeness() -> str:
    manifest = json.loads(ANALYSIS_MANIFEST.read_text(encoding="utf-8"))
    rows = [
        ("Expected matrix rows", manifest["expected_matrix_rows"]),
        ("Observed expected rows", manifest["observed_expected_rows"]),
        ("Missing expected rows", manifest["missing_expected_rows"]),
        ("Errored rows after dedupe", manifest["errored_rows_after_dedupe"]),
        ("Unexpected artifact IDs", manifest["unexpected_artifact_ids"]),
    ]
    body = "\n".join(f"{label} & {count} \\\\" for label, count in rows)
    return "\n".join(
        [
            r"\begin{table}[t]",
            r"\centering",
            r"\caption{Experiment 8 first-pass completeness.}",
            r"\label{tab:exp8-completeness}",
            r"\begin{tabular}{lr}",
            r"\toprule",
            r"Artifact & Count \\",
            r"\midrule",
            body,
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
            "",
        ]
    )


def table_exp8_stage_summary() -> str:
    rows = sorted(read_csv(STAGE_SUMMARY), key=lambda row: row["route_stage_label"])
    body = "\n".join(
        " & ".join(
            [
                texttt(row["route_stage_label"]),
                row["n"],
                pct(row["has_format_default_rate"]),
                pct(row["has_polish_default_rate"]),
                pct(row["has_emoji_rate"]),
                pct(row["has_markdown_rate"]),
            ]
        )
        + r" \\"
        for row in rows
    )
    return "\n".join(
        [
            r"\begin{table}[t]",
            r"\centering",
            r"\caption{Experiment 8 route-label summary.}",
            r"\label{tab:exp8-stage-summary}",
            r"\begin{tabular}{lrrrrr}",
            r"\toprule",
            r"Route-stage label & $n$ & Format default & Polish default & Emoji & Markdown \\",
            r"\midrule",
            body,
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
            "",
        ]
    )


def table_exp8_condition_summary() -> str:
    rows_by_condition = {row["condition"]: row for row in read_csv(CONDITION_SUMMARY)}
    body = "\n".join(
        " & ".join(
            [
                texttt(condition),
                row["n"],
                pct(row["has_format_default_rate"]),
                pct(row["has_polish_default_rate"]),
                pct(row["has_emoji_rate"]),
                pct(row["has_markdown_rate"]),
            ]
        )
        + r" \\"
        for condition in CONDITION_ORDER
        for row in [rows_by_condition[condition]]
    )
    return "\n".join(
        [
            r"\begin{table}[t]",
            r"\centering",
            r"\caption{Experiment 8 condition summary across 480 clean outputs.}",
            r"\label{tab:exp8-condition-summary}",
            r"\begin{tabular}{lrrrrr}",
            r"\toprule",
            r"Condition & $n$ & Format default & Polish default & Emoji & Markdown \\",
            r"\midrule",
            body,
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
            "",
        ]
    )


def table_exp8_ci_contrasts() -> str:
    ci_by_key = {
        (row["condition"], row["metric"]): row
        for row in read_csv(CONFIDENCE_INTERVALS)
        if row["group_type"] == "condition" and row["metric_type"] == "rate"
    }
    contrast_by_key = {
        (row["left_label"], row["feature"]): row
        for row in read_csv(PLANNED_CONTRASTS)
        if row["contrast_type"] == "condition_vs_neutral"
    }
    lines = []
    for condition, feature, label in CI_ROWS:
        ci = ci_by_key[(condition, feature)]
        if condition == "neutral":
            delta = "--"
            q = "--"
        else:
            contrast = contrast_by_key[(condition, feature)]
            delta = signed_decimal(contrast["effect_delta"])
            q = q_value(contrast["p_value_fdr"])
        lines.append(
            f"{label} & {pct(ci['estimate'])} & {ci_pct(ci['ci_low'], ci['ci_high'])} & {delta} & {q} \\\\"
        )
    return "\n".join(
        [
            r"\begin{table}[t]",
            r"\centering",
            r"\caption{Experiment 8 selected intervals and planned contrasts.}",
            r"\label{tab:exp8-ci-contrast}",
            r"\begin{tabular}{lrrrr}",
            r"\toprule",
            r"Condition/feature & Rate & 95\% CI & Delta vs. neutral & FDR q \\",
            r"\midrule",
            *lines,
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
            "",
        ]
    )


def build_tist_artifact_tables(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    table_builders = {
        "exp8_completeness": table_exp8_completeness,
        "exp8_stage_summary": table_exp8_stage_summary,
        "exp8_condition_summary": table_exp8_condition_summary,
        "exp8_ci_contrasts": table_exp8_ci_contrasts,
    }
    artifacts = []
    for artifact in DEFAULT_ARTIFACTS:
        path = output_dir / artifact["path"]
        path.write_text(table_builders[artifact["name"]](), encoding="utf-8")
        artifacts.append({**artifact, "sha256": sha256_file(path)})
    manifest = {
        "status": "ok",
        "generated_by": "generate_tist_artifact_tables.py",
        "source_sha256": {path.as_posix(): sha256_file(path) for path in DEFAULT_SOURCES},
        "artifacts": artifacts,
    }
    (output_dir / "tist_artifact_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def verify_artifact_manifest(
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    verify_regeneration: bool = False,
) -> list[str]:
    output_dir = Path(output_dir)
    manifest_path = output_dir / "tist_artifact_manifest.json"
    if not manifest_path.exists():
        return [f"missing artifact manifest: {manifest_path}"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = []
    expected_sources = {path.as_posix() for path in DEFAULT_SOURCES}
    manifest_sources = set(manifest.get("source_sha256", {}))
    for source in sorted(expected_sources - manifest_sources):
        failures.append(f"manifest missing source entry: {source}")
    for source in sorted(manifest_sources - expected_sources):
        failures.append(f"manifest unexpected source entry: {source}")
    for source, expected_hash in manifest.get("source_sha256", {}).items():
        path = Path(source)
        if not path.exists():
            failures.append(f"missing source: {source}")
        elif sha256_file(path) != expected_hash:
            failures.append(f"source hash mismatch: {source}")
    expected_artifacts = {artifact["name"]: artifact["path"] for artifact in DEFAULT_ARTIFACTS}
    manifest_artifacts = {artifact.get("name"): artifact for artifact in manifest.get("artifacts", [])}
    for name in sorted(set(expected_artifacts) - set(manifest_artifacts)):
        failures.append(f"manifest missing artifact entry: {name}")
    for name in sorted(set(manifest_artifacts) - set(expected_artifacts)):
        failures.append(f"manifest unexpected artifact entry: {name}")
    for artifact in manifest.get("artifacts", []):
        if artifact.get("path") != expected_artifacts.get(artifact.get("name")):
            failures.append(f"manifest artifact path mismatch: {artifact.get('name')}")
            continue
        path = output_dir / artifact["path"]
        if not path.exists():
            failures.append(f"missing artifact: {path}")
        elif sha256_file(path) != artifact.get("sha256"):
            failures.append(f"artifact hash mismatch: {path}")
    if verify_regeneration:
        with tempfile.TemporaryDirectory() as tmp:
            generated_dir = Path(tmp) / "tist_package"
            build_tist_artifact_tables(generated_dir)
            for artifact in DEFAULT_ARTIFACTS:
                actual = output_dir / artifact["path"]
                expected = generated_dir / artifact["path"]
                if actual.exists() and actual.read_bytes() != expected.read_bytes():
                    failures.append(f"regenerated artifact mismatch: {artifact['path']}")
            generated_manifest = generated_dir / "tist_artifact_manifest.json"
            if manifest_path.exists() and manifest_path.read_bytes() != generated_manifest.read_bytes():
                failures.append("regenerated artifact manifest mismatch")
    return failures


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate TIST final table artifacts")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    manifest = build_tist_artifact_tables(args.output_dir)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
