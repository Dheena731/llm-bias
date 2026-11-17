"""Analyze Experiment 8 post-training aesthetic-prior outputs."""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import math
import os
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

from aesthetic_features import derive_text_default_features
from experiment8_common import (
    DEFAULT_CONFIG,
    build_exp8_tasks,
    load_exp8_config,
)

try:
    from scipy.stats import fisher_exact
except ModuleNotFoundError:  # pragma: no cover - exercised only without scipy
    fisher_exact = None


OUT_DIR = Path("analysis_output/exp8")
BINARY_FEATURES = [
    "has_emoji",
    "has_markdown",
    "has_stock_phrase",
    "has_format_default",
    "has_polish_default",
]
NUMERIC_FEATURES = [
    "emoji_count",
    "markdown_marker_count",
    "heading_lines",
    "bullet_lines",
    "numbered_lines",
    "decorative_symbol_count",
    "exclamation_count",
    "word_count",
]
SUMMARY_GROUPS = {
    "condition": ["condition"],
    "route_stage": ["route_stage_label"],
    "stage_condition": ["model_family", "route_stage_label", "condition"],
    "model": ["model_family", "route_stage_label", "model"],
    "prompt_family": ["domain", "prompt_family"],
}


def parse_features(value: str) -> dict:
    if not value:
        return {}
    try:
        features = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return derive_text_default_features(features)


def read_rows(paths: list[str]) -> list[dict]:
    rows = []
    for path in paths:
        with open(path, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                row["source_file"] = path
                row["features"] = parse_features(row.get("feature_json", ""))
                rows.append(row)
    return rows


def row_rank(row: dict) -> tuple[int, float]:
    clean = int(not row.get("error") and bool(row.get("feature_json")))
    try:
        mtime = os.path.getmtime(row.get("source_file", ""))
    except OSError:
        mtime = 0.0
    return clean, mtime


def dedupe_rows(rows: list[dict]) -> list[dict]:
    selected: dict[tuple[str, str, str], dict] = {}
    anonymous_index = 0
    for row in rows:
        artifact_id = row.get("artifact_id")
        if not artifact_id:
            anonymous_index += 1
            artifact_id = f"__row_{anonymous_index}"
        dedupe_key = (row.get("config_hash", ""), row.get("run_id", ""), artifact_id)
        current = selected.get(dedupe_key)
        if current is None or row_rank(row) > row_rank(current):
            selected[dedupe_key] = row
    return sorted(selected.values(), key=lambda item: item.get("artifact_id", ""))


def clean_rows(rows: list[dict]) -> list[dict]:
    return [row for row in rows if not row.get("error") and row.get("feature_json")]


def group_by(rows: list[dict], keys: list[str]) -> dict[tuple, list[dict]]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(key, "") for key in keys)].append(row)
    return groups


def _neutral_word_medians(rows: list[dict]) -> tuple[dict[str, float], float | None]:
    by_family: dict[str, list[float]] = defaultdict(list)
    all_neutral = []
    for row in rows:
        if row.get("condition") != "neutral":
            continue
        word_count = feature_float(row, "word_count")
        by_family[row.get("prompt_family", "")].append(word_count)
        all_neutral.append(word_count)
    family_medians = {family: median(values) for family, values in by_family.items() if values}
    global_median = median(all_neutral) if all_neutral else None
    return family_medians, global_median


def annotate_polish_defaults(rows: list[dict]) -> list[dict]:
    family_medians, global_median = _neutral_word_medians(rows)
    annotated = []
    for row in rows:
        copy = dict(row)
        neutral_median = family_medians.get(row.get("prompt_family", ""), global_median)
        copy["features"] = derive_text_default_features(row.get("features", {}), neutral_median)
        annotated.append(copy)
    return annotated


def truthy(value) -> bool:
    return bool(value) and str(value).lower() not in {"false", "0", "none", ""}


def feature_bool(row: dict, name: str) -> bool:
    return truthy(row.get("features", {}).get(name))


def feature_float(row: dict, name: str) -> float:
    value = row.get("features", {}).get(name, 0.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def metric_value(row: dict, metric: str) -> float:
    if metric.startswith("has_"):
        return float(feature_bool(row, metric))
    return feature_float(row, metric)


def wilson_ci(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 0.0
    phat = successes / n
    denominator = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denominator
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def bootstrap_mean_ci(values: list[float], iterations: int = 1000, seed: int = 13) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return values[0], values[0]
    rng = random.Random(seed)
    n = len(values)
    samples = [mean(values[rng.randrange(n)] for _ in range(n)) for _ in range(iterations)]
    samples.sort()
    return samples[int(0.025 * iterations)], samples[int(0.975 * iterations)]


def stable_seed(*parts: object) -> int:
    payload = json.dumps([str(part) for part in parts], separators=(",", ":"))
    return int(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8], 16)


def write_csv(path: Path, rows: list[dict], fallback_fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) or fallback_fieldnames or ["n"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def summarize_groups(rows: list[dict], keys: list[str]) -> list[dict]:
    output = []
    for key_values, group in sorted(group_by(rows, keys).items()):
        record = dict(zip(keys, key_values))
        record["n"] = len(group)
        for feature in BINARY_FEATURES:
            successes = sum(1 for row in group if feature_bool(row, feature))
            ci_low, ci_high = wilson_ci(successes, len(group))
            record[f"{feature}_rate"] = successes / len(group) if group else ""
            record[f"{feature}_successes"] = successes
            record[f"{feature}_ci_low"] = ci_low
            record[f"{feature}_ci_high"] = ci_high
        for feature in NUMERIC_FEATURES:
            values = [feature_float(row, feature) for row in group]
            record[f"mean_{feature}"] = mean(values) if values else ""
        output.append(record)
    return output


def confidence_intervals(rows: list[dict]) -> list[dict]:
    output = []
    metrics = BINARY_FEATURES + NUMERIC_FEATURES
    for group_type, keys in SUMMARY_GROUPS.items():
        for key_values, group in sorted(group_by(rows, keys).items()):
            base = {"group_type": group_type, "group_label": "|".join(key_values), "n": len(group)}
            base.update(dict(zip(keys, key_values)))
            for metric in metrics:
                values = [metric_value(row, metric) for row in group]
                record = dict(base)
                record["metric"] = metric
                if metric in BINARY_FEATURES:
                    successes = int(sum(values))
                    ci_low, ci_high = wilson_ci(successes, len(values))
                    record.update(
                        {
                            "metric_type": "rate",
                            "estimate": successes / len(values) if values else "",
                            "ci_low": ci_low if values else "",
                            "ci_high": ci_high if values else "",
                            "successes": successes,
                        }
                    )
                else:
                    ci_low, ci_high = bootstrap_mean_ci(values, seed=stable_seed(group_type, key_values, metric))
                    record.update(
                        {
                            "metric_type": "mean",
                            "estimate": mean(values) if values else "",
                            "ci_low": ci_low if values else "",
                            "ci_high": ci_high if values else "",
                            "successes": "",
                        }
                    )
                output.append(record)
    return output


def expected_tasks_for_analysis(
    config_path: str | Path | None,
    raw_rows: list[dict],
    expected_runs_per_cell: int | None = None,
) -> list[dict]:
    if not config_path:
        return []
    config = load_exp8_config(str(config_path))
    if expected_runs_per_cell is None:
        # The planned design, not the observed maximum: a run stopped early must show up as missing rows.
        expected_runs_per_cell = int(config["tracks"]["text"]["full_repeats"])
    if expected_runs_per_cell <= 0:
        raise ValueError("--expected-runs-per-cell must be positive")
    return [
        task
        for task in build_exp8_tasks(config, mode="full")
        if int(task.get("run", 0)) <= expected_runs_per_cell
    ]


def matrix_completeness(raw_rows: list[dict], expected_tasks: list[dict]) -> list[dict]:
    if not expected_tasks:
        return []
    rows_by_artifact = group_by(raw_rows, ["artifact_id"])
    expected_ids = {task["artifact_id"] for task in expected_tasks}
    output = []
    for task in expected_tasks:
        observed = rows_by_artifact.get((task["artifact_id"],), [])
        clean_count = len(clean_rows(observed))
        error_count = len([row for row in observed if row.get("error")])
        missing = not observed
        status = "missing" if missing else "clean"
        if observed and clean_count == 0 and error_count:
            status = "errored"
        elif observed and clean_count and error_count:
            status = "mixed"
        output.append(
            {
                "artifact_id": task["artifact_id"],
                "expected": 1,
                "unexpected": 0,
                "missing": int(missing),
                "status": status,
                "observed_rows": len(observed),
                "clean_rows": clean_count,
                "error_rows": error_count,
                "config_hash": task.get("config_hash", ""),
                "observed_config_hashes": "|".join(
                    sorted({row.get("config_hash", "") for row in observed if row.get("config_hash")})
                ),
                "run_ids": "|".join(sorted({row.get("run_id", "") for row in observed if row.get("run_id")})),
                "model_family": task.get("model_family", ""),
                "route_stage_label": task.get("route_stage_label", ""),
                "model": task.get("model", ""),
                "condition": task.get("condition", ""),
                "prompt_family": task.get("prompt_family", ""),
                "domain": task.get("domain", ""),
                "run": task.get("run", ""),
            }
        )

    for artifact_id, observed in sorted(rows_by_artifact.items()):
        artifact = artifact_id[0]
        if artifact in expected_ids:
            continue
        output.append(
            {
                "artifact_id": artifact,
                "expected": 0,
                "unexpected": 1,
                "missing": 0,
                "status": "unexpected",
                "observed_rows": len(observed),
                "clean_rows": len(clean_rows(observed)),
                "error_rows": len([row for row in observed if row.get("error")]),
                "config_hash": "",
                "observed_config_hashes": "|".join(
                    sorted({row.get("config_hash", "") for row in observed if row.get("config_hash")})
                ),
                "run_ids": "|".join(sorted({row.get("run_id", "") for row in observed if row.get("run_id")})),
                "model_family": observed[0].get("model_family", "") if observed else "",
                "route_stage_label": observed[0].get("route_stage_label", "") if observed else "",
                "model": observed[0].get("model", "") if observed else "",
                "condition": observed[0].get("condition", "") if observed else "",
                "prompt_family": observed[0].get("prompt_family", "") if observed else "",
                "domain": observed[0].get("domain", "") if observed else "",
                "run": observed[0].get("run", "") if observed else "",
            }
        )
    return output


def missingness_summary(raw_rows: list[dict], expected_tasks: list[dict] | None = None) -> list[dict]:
    summary = []
    keys = ["model_family", "route_stage_label", "model", "condition"]
    observed_groups = group_by(raw_rows, keys)
    expected_groups = group_by(expected_tasks or [], keys)
    observed_by_artifact = {row.get("artifact_id") for row in raw_rows}
    all_expected_ids = {task.get("artifact_id") for task in expected_tasks or []}
    for key_values in sorted(set(observed_groups) | set(expected_groups)):
        group = observed_groups.get(key_values, [])
        expected_group = expected_groups.get(key_values, [])
        clean_count = len(clean_rows(group))
        error_count = len([row for row in group if row.get("error")])
        missing_expected = len(
            [task for task in expected_group if task.get("artifact_id") not in observed_by_artifact]
        )
        expected_count = len(expected_group)
        unexpected_count = len(
            {row.get("artifact_id") for row in group if row.get("artifact_id") not in all_expected_ids}
        )
        record = dict(zip(keys, key_values))
        record.update(
            {
                "total_rows": len(group),
                "clean_rows": clean_count,
                "error_rows": error_count,
                "clean_rate": clean_count / len(group) if group else "",
                "unique_artifact_ids": len({row.get("artifact_id") for row in group}),
                "expected_rows": expected_count if expected_tasks else "",
                "missing_expected_rows": missing_expected if expected_tasks else "",
                "unexpected_artifact_ids": unexpected_count if expected_tasks else "",
                "matrix_completeness_rate": (
                    (expected_count - missing_expected) / expected_count
                    if expected_tasks and expected_count
                    else ""
                ),
            }
        )
        summary.append(record)
    return summary


def paired_condition_delta_summary(rows: list[dict], baseline_condition: str = "neutral") -> list[dict]:
    output = []
    metrics = BINARY_FEATURES + NUMERIC_FEATURES
    for (model_family, route_stage_label, model), model_rows in sorted(
        group_by(rows, ["model_family", "route_stage_label", "model"]).items()
    ):
        units = group_by(model_rows, ["prompt_family", "domain", "run"])
        conditions = sorted({row.get("condition") for row in model_rows if row.get("condition") != baseline_condition})
        for condition in conditions:
            for metric in metrics:
                baseline_values = []
                condition_values = []
                deltas = []
                for unit_rows in units.values():
                    by_condition = {row.get("condition"): row for row in unit_rows}
                    baseline = by_condition.get(baseline_condition)
                    current = by_condition.get(condition)
                    if not baseline or not current:
                        continue
                    baseline_value = metric_value(baseline, metric)
                    current_value = metric_value(current, metric)
                    baseline_values.append(baseline_value)
                    condition_values.append(current_value)
                    deltas.append(current_value - baseline_value)
                if not deltas:
                    continue
                ci_low, ci_high = bootstrap_mean_ci(deltas, seed=stable_seed(model, condition, metric))
                output.append(
                    {
                        "model_family": model_family,
                        "route_stage_label": route_stage_label,
                        "model": model,
                        "condition": condition,
                        "baseline_condition": baseline_condition,
                        "metric": metric,
                        "metric_type": "rate" if metric in BINARY_FEATURES else "mean",
                        "paired_n": len(deltas),
                        "baseline_estimate": mean(baseline_values),
                        "condition_estimate": mean(condition_values),
                        "mean_paired_delta": mean(deltas),
                        "ci_low": ci_low,
                        "ci_high": ci_high,
                    }
                )
    return output


def _paired_unit_records(rows: list[dict], condition: str, metric: str, baseline_condition: str) -> list[dict]:
    records = []
    unit_keys = ["model_family", "route_stage_label", "model", "prompt_family", "domain", "run"]
    units = group_by(rows, unit_keys)
    for unit_values, unit_rows in units.items():
        by_condition = {row.get("condition"): row for row in unit_rows}
        baseline = by_condition.get(baseline_condition)
        current = by_condition.get(condition)
        if not baseline or not current:
            continue
        baseline_value = metric_value(baseline, metric)
        condition_value = metric_value(current, metric)
        model_family, route_stage_label, model, prompt_family, domain, run = unit_values
        records.append(
            {
                "model_family": model_family,
                "route_stage_label": route_stage_label,
                "model": model,
                "prompt_family": prompt_family,
                "domain": domain,
                "run": run,
                "baseline_value": baseline_value,
                "condition_value": condition_value,
                "delta": condition_value - baseline_value,
            }
        )
    return records


def _mean_delta_range(records: list[dict], keys: list[str]) -> tuple[int, float, float, bool]:
    deltas_by_group: dict[tuple, list[float]] = defaultdict(list)
    for record in records:
        group_key = tuple(record.get(key, "") for key in keys)
        deltas_by_group[group_key].append(float(record["delta"]))
    group_means = [mean(values) for values in deltas_by_group.values()]
    if not group_means:
        return 0, 0.0, 0.0, False
    observed = mean(group_means)
    if observed == 0:
        same_direction = all(value == 0 for value in group_means)
    else:
        same_direction = all((value == 0) or ((value > 0) == (observed > 0)) for value in group_means)
    return len(group_means), min(group_means), max(group_means), same_direction


def _cluster_bootstrap_ci(
    values_by_cluster: dict[str, list[float]],
    iterations: int = 2000,
    seed: int = 13,
) -> tuple[float, float]:
    clusters = sorted(values_by_cluster)
    if not clusters:
        return 0.0, 0.0
    if len(clusters) == 1:
        value = mean(values_by_cluster[clusters[0]])
        return value, value
    rng = random.Random(seed)
    samples = []
    for _ in range(iterations):
        values = []
        for _ in clusters:
            values.extend(values_by_cluster[rng.choice(clusters)])
        samples.append(mean(values))
    samples.sort()
    return samples[int(0.025 * iterations)], samples[int(0.975 * iterations)]


def _cluster_signflip_p_value(
    values_by_cluster: dict[str, list[float]],
    observed: float,
    iterations: int = 2000,
    seed: int = 13,
) -> float:
    clusters = sorted(values_by_cluster)
    if not clusters:
        return 1.0
    if all(value == 0 for values in values_by_cluster.values() for value in values):
        return 1.0
    rng = random.Random(seed)
    extreme = 0
    for _ in range(iterations):
        flipped = []
        for cluster in clusters:
            sign = -1 if rng.random() < 0.5 else 1
            flipped.extend(sign * value for value in values_by_cluster[cluster])
        if abs(mean(flipped)) >= abs(observed):
            extreme += 1
    return (extreme + 1) / (iterations + 1)


def cluster_paired_condition_contrasts(
    rows: list[dict],
    baseline_condition: str = "neutral",
    features: list[str] | None = None,
) -> list[dict]:
    metrics = features or BINARY_FEATURES + NUMERIC_FEATURES
    conditions = sorted({row.get("condition") for row in rows if row.get("condition") != baseline_condition})
    output = []
    for condition in conditions:
        for metric in metrics:
            unit_records = _paired_unit_records(rows, condition, metric, baseline_condition)
            if not unit_records:
                continue
            deltas_by_family: dict[str, list[float]] = defaultdict(list)
            for record in unit_records:
                deltas_by_family[record["prompt_family"]].append(float(record["delta"]))
            deltas = [float(record["delta"]) for record in unit_records]
            baseline_values = [float(record["baseline_value"]) for record in unit_records]
            condition_values = [float(record["condition_value"]) for record in unit_records]
            observed = mean(deltas)
            route_count, route_min, route_max, routes_same_direction = _mean_delta_range(
                unit_records, ["model_family", "route_stage_label", "model"]
            )
            family_count, family_min, family_max, families_same_direction = _mean_delta_range(
                unit_records, ["prompt_family"]
            )
            seed = stable_seed("cluster_paired_condition_contrasts", condition, metric)
            ci_low, ci_high = _cluster_bootstrap_ci(deltas_by_family, seed=seed)
            p_value = _cluster_signflip_p_value(deltas_by_family, observed, seed=seed)
            output.append(
                {
                    "condition": condition,
                    "baseline_condition": baseline_condition,
                    "metric": metric,
                    "metric_type": "rate" if metric in BINARY_FEATURES else "mean",
                    "inference_scope": "prompt_family_clustered_condition_effect",
                    "cluster_level": "prompt_family",
                    "cluster_count": len(deltas_by_family),
                    "paired_unit_count": len(unit_records),
                    "route_count": route_count,
                    "route_delta_min": route_min,
                    "route_delta_max": route_max,
                    "routes_same_direction": routes_same_direction,
                    "prompt_family_delta_min": family_min,
                    "prompt_family_delta_max": family_max,
                    "prompt_families_same_direction": families_same_direction,
                    "baseline_estimate": mean(baseline_values),
                    "condition_estimate": mean(condition_values),
                    "mean_paired_delta": observed,
                    "cluster_bootstrap_ci_low": ci_low,
                    "cluster_bootstrap_ci_high": ci_high,
                    "cluster_signflip_p_value": p_value,
                }
            )
    adjusted = benjamini_hochberg([float(row["cluster_signflip_p_value"]) for row in output])
    for row, p_value_fdr in zip(output, adjusted):
        row["p_value_fdr"] = p_value_fdr
        row["reject_fdr_0_05"] = p_value_fdr <= 0.05
    return output


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    if not p_values:
        return []
    m = len(p_values)
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [1.0] * m
    running = 1.0
    for rank_from_zero, (index, p_value) in reversed(list(enumerate(indexed))):
        rank = rank_from_zero + 1
        running = min(running, p_value * m / rank)
        adjusted[index] = round(min(running, 1.0), 12)
    return adjusted


def _two_proportion_p_value(left_successes: int, left_n: int, right_successes: int, right_n: int) -> float:
    if left_n <= 0 or right_n <= 0:
        return 1.0
    if fisher_exact is not None:
        _, p_value = fisher_exact(
            [
                [left_successes, left_n - left_successes],
                [right_successes, right_n - right_successes],
            ],
            alternative="two-sided",
        )
        return float(p_value)

    pooled = (left_successes + right_successes) / (left_n + right_n)
    stderr = math.sqrt(pooled * (1 - pooled) * (1 / left_n + 1 / right_n))
    if stderr == 0:
        return 1.0
    z_score = abs((left_successes / left_n) - (right_successes / right_n)) / stderr
    return math.erfc(z_score / math.sqrt(2))


def _contrast_record(
    contrast_type: str,
    feature: str,
    left_label: str,
    left_rows: list[dict],
    right_label: str,
    right_rows: list[dict],
    context: dict | None = None,
) -> dict:
    left_successes = sum(1 for row in left_rows if feature_bool(row, feature))
    right_successes = sum(1 for row in right_rows if feature_bool(row, feature))
    left_n = len(left_rows)
    right_n = len(right_rows)
    left_rate = left_successes / left_n if left_n else 0.0
    right_rate = right_successes / right_n if right_n else 0.0
    record = {
        "contrast_type": contrast_type,
        "feature": feature,
        "left_label": left_label,
        "right_label": right_label,
        "left_n": left_n,
        "right_n": right_n,
        "left_successes": left_successes,
        "right_successes": right_successes,
        "left_rate": left_rate,
        "right_rate": right_rate,
        "effect_delta": left_rate - right_rate,
        "p_value": _two_proportion_p_value(left_successes, left_n, right_successes, right_n),
    }
    if context:
        record.update(context)
    return record


def planned_contrasts_fdr(rows: list[dict], features: list[str] | None = None) -> list[dict]:
    features = features or BINARY_FEATURES
    contrasts = []
    by_condition = group_by(rows, ["condition"])
    neutral = by_condition.get(("neutral",), [])
    for condition_key, condition_rows in sorted(by_condition.items()):
        condition = condition_key[0]
        if condition == "neutral" or not neutral:
            continue
        for feature in features:
            contrasts.append(
                _contrast_record("condition_vs_neutral", feature, condition, condition_rows, "neutral", neutral)
            )

    for (model_family, condition), group in sorted(group_by(rows, ["model_family", "condition"]).items()):
        by_stage = group_by(group, ["route_stage_label"])
        base = by_stage.get(("base_candidate",), [])
        if not base:
            continue
        for stage_key, stage_rows in sorted(by_stage.items()):
            stage = stage_key[0]
            if stage == "base_candidate":
                continue
            for feature in features:
                contrasts.append(
                    _contrast_record(
                        "stage_vs_base_candidate",
                        feature,
                        stage,
                        stage_rows,
                        "base_candidate",
                        base,
                        {"model_family": model_family, "condition": condition},
                    )
                )

    adjusted = benjamini_hochberg([float(row["p_value"]) for row in contrasts])
    for row, p_value_fdr in zip(contrasts, adjusted):
        row["p_value_fdr"] = p_value_fdr
        row["reject_fdr_0_05"] = p_value_fdr <= 0.05
    return contrasts


def prompt_family_holdout_summary(rows: list[dict], features: list[str] | None = None) -> list[dict]:
    features = features or BINARY_FEATURES
    output = []
    families = sorted({row.get("prompt_family", "") for row in rows})
    for family in families:
        holdout = [row for row in rows if row.get("prompt_family") == family]
        train = [row for row in rows if row.get("prompt_family") != family]
        train_family_count = len({row.get("prompt_family") for row in train})
        for feature in features:
            train_successes = sum(1 for row in train if feature_bool(row, feature))
            holdout_successes = sum(1 for row in holdout if feature_bool(row, feature))
            output.append(
                {
                    "held_out_prompt_family": family,
                    "feature": feature,
                    "train_n": len(train),
                    "holdout_n": len(holdout),
                    "train_prompt_family_count": train_family_count,
                    "train_successes": train_successes,
                    "holdout_successes": holdout_successes,
                    "train_rate": train_successes / len(train) if train else "",
                    "holdout_rate": holdout_successes / len(holdout) if holdout else "",
                }
            )
    return output


def _length_sensitivity_record(rows: list[dict], context: dict) -> dict:
    n = len(rows)
    polish = sum(1 for row in rows if feature_bool(row, "has_polish_default"))
    polish_without_length = sum(1 for row in rows if feature_bool(row, "has_polish_without_length"))
    record = dict(context)
    record.update(
        {
            "n": n,
            "polish_default_rate": polish / n if n else "",
            "polish_without_length_rate": polish_without_length / n if n else "",
            "delta_length_component": (polish - polish_without_length) / n if n else "",
        }
    )
    return record


def length_exclusion_sensitivity(rows: list[dict]) -> list[dict]:
    output = [_length_sensitivity_record(rows, {"group_type": "all", "group_label": "all"})]
    for key_values, group in sorted(group_by(rows, ["model_family", "route_stage_label", "condition"]).items()):
        model_family, route_stage_label, condition = key_values
        output.append(
            _length_sensitivity_record(
                group,
                {
                    "group_type": "stage_condition",
                    "group_label": "|".join(key_values),
                    "model_family": model_family,
                    "route_stage_label": route_stage_label,
                    "condition": condition,
                },
            )
        )
    return output


def _matrix_counts(matrix_rows: list[dict]) -> dict[str, int]:
    expected_rows = [row for row in matrix_rows if int(row.get("expected", 0))]
    return {
        "expected_rows": len(expected_rows),
        "missing_expected_rows": sum(int(row.get("missing", 0)) for row in expected_rows),
        "unexpected_artifact_ids": sum(int(row.get("unexpected", 0)) for row in matrix_rows),
        "errored_expected_rows": len([row for row in expected_rows if row.get("status") in {"errored", "mixed"}]),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(
    paths: list[str],
    rows: list[dict],
    raw_rows: list[dict],
    matrix_rows: list[dict],
    output_dir: Path,
) -> Path:
    counts = _matrix_counts(matrix_rows)
    manifest = {
        "input_files": paths,
        "input_file_sha256": {path: sha256_file(Path(path)) for path in paths},
        "source_file_count": len(paths),
        "raw_rows_after_dedupe": len(raw_rows),
        "clean_analyzed_rows": len(rows),
        "errored_rows_after_dedupe": len([row for row in raw_rows if row.get("error")]),
        "run_ids": sorted({row.get("run_id", "") for row in raw_rows if row.get("run_id")}),
        "config_hashes": sorted({row.get("config_hash", "") for row in raw_rows if row.get("config_hash")}),
        "expected_matrix_rows": counts["expected_rows"],
        "observed_expected_rows": counts["expected_rows"] - counts["missing_expected_rows"],
        "missing_expected_rows": counts["missing_expected_rows"],
        "errored_expected_rows": counts["errored_expected_rows"],
        "unexpected_artifact_ids": counts["unexpected_artifact_ids"],
        "completeness_status": (
            "not_checked"
            if not matrix_rows
            else "complete"
            if counts["missing_expected_rows"] == 0 and counts["unexpected_artifact_ids"] == 0
            else "incomplete"
        ),
    }
    path = output_dir / "analysis_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_report(
    rows: list[dict],
    raw_rows: list[dict],
    output_dir: Path,
    paths: list[str] | None = None,
    matrix_rows: list[dict] | None = None,
) -> Path:
    path = output_dir / "post_training_priors_report.md"
    by_stage = summarize_groups(rows, ["route_stage_label"])
    by_condition = summarize_groups(rows, ["condition"])
    error_rows = len([row for row in raw_rows if row.get("error")])
    paths = paths or []
    matrix_rows = matrix_rows or []
    counts = _matrix_counts(matrix_rows)
    run_ids = sorted({row.get("run_id", "") for row in raw_rows if row.get("run_id")})
    config_hashes = sorted({row.get("config_hash", "") for row in raw_rows if row.get("config_hash")})
    completeness_status = "not checked"
    if matrix_rows:
        completeness_status = (
            "complete"
            if counts["missing_expected_rows"] == 0 and counts["unexpected_artifact_ids"] == 0
            else "incomplete"
        )
    lines = [
        "# Experiment 8 Route-Labeled Presentation Priors Report",
        "",
        f"Clean analyzed rows: {len(rows)}",
        f"Errored rows after dedupe: {error_rows}",
        f"Input files: {', '.join(paths) if paths else 'not recorded'}",
        f"Run IDs: {', '.join(run_ids) if run_ids else 'not recorded'}",
        f"Config hashes: {', '.join(config_hashes) if config_hashes else 'not recorded'}",
        f"Matrix completeness status: {completeness_status}",
        f"Expected matrix rows: {counts['expected_rows']}",
        f"Observed expected rows: {counts['expected_rows'] - counts['missing_expected_rows']}",
        f"Missing expected rows: {counts['missing_expected_rows']}",
        f"Unexpected artifact IDs: {counts['unexpected_artifact_ids']}",
        "",
        "## Stage Summary",
        "",
        "| Stage label | n | Format default rate | Polish default rate | Emoji rate | Markdown rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in by_stage:
        lines.append(
            "| {stage} | {n} | {fmt:.1%} | {polish:.1%} | {emoji:.1%} | {markdown:.1%} |".format(
                stage=row["route_stage_label"],
                n=row["n"],
                fmt=float(row["has_format_default_rate"]),
                polish=float(row["has_polish_default_rate"]),
                emoji=float(row["has_emoji_rate"]),
                markdown=float(row["has_markdown_rate"]),
            )
        )
    lines.extend(
        [
            "",
            "## Condition Summary",
            "",
            "| Condition | n | Format default rate | Polish default rate | Emoji rate | Markdown rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in by_condition:
        lines.append(
            "| {condition} | {n} | {fmt:.1%} | {polish:.1%} | {emoji:.1%} | {markdown:.1%} |".format(
                condition=row["condition"],
                n=row["n"],
                fmt=float(row["has_format_default_rate"]),
                polish=float(row["has_polish_default_rate"]),
                emoji=float(row["has_emoji_rate"]),
                markdown=float(row["has_markdown_rate"]),
            )
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "Route labels are provenance metadata, not proof of a training mechanism. Causal claims about RLHF or post-training require verified route provenance.",
            "Clustered condition contrasts pair each condition against neutral within model family, route label, model, prompt family, domain, and run; they resample prompt-family clusters and include route-level consistency diagnostics.",
            "",
            "Required companion outputs: `confidence_intervals.csv`, `planned_contrasts_fdr.csv`, `paired_condition_delta_summary.csv`, `cluster_paired_condition_contrasts.csv`, `prompt_family_holdout.csv`, `length_sensitivity.csv`, `missingness_summary.csv`, `matrix_completeness.csv`, and `analysis_manifest.json`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def find_exp8_files() -> list[str]:
    return sorted(glob.glob("experiment_data/exp8_post_training_priors_*.csv"))


def run_analysis(
    paths: list[str],
    output_dir: str | Path = OUT_DIR,
    config_path: str | Path | None = None,
    expected_runs_per_cell: int | None = None,
) -> dict[str, Path]:
    raw_rows = dedupe_rows(read_rows(paths))
    rows = annotate_polish_defaults(clean_rows(raw_rows))
    expected_tasks = expected_tasks_for_analysis(config_path, raw_rows, expected_runs_per_cell)
    completeness_rows = matrix_completeness(raw_rows, expected_tasks)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = {
        "stage_condition": output_dir / "stage_condition_summary.csv",
        "stage": output_dir / "stage_summary.csv",
        "model": output_dir / "model_summary.csv",
        "prompt_family": output_dir / "prompt_family_summary.csv",
        "condition": output_dir / "condition_summary.csv",
        "confidence_intervals": output_dir / "confidence_intervals.csv",
        "planned_contrasts_fdr": output_dir / "planned_contrasts_fdr.csv",
        "paired_condition_delta_summary": output_dir / "paired_condition_delta_summary.csv",
        "cluster_paired_condition_contrasts": output_dir / "cluster_paired_condition_contrasts.csv",
        "prompt_family_holdout": output_dir / "prompt_family_holdout.csv",
        "length_sensitivity": output_dir / "length_sensitivity.csv",
        "missingness_summary": output_dir / "missingness_summary.csv",
        "matrix_completeness": output_dir / "matrix_completeness.csv",
    }
    write_csv(outputs["stage_condition"], summarize_groups(rows, ["model_family", "route_stage_label", "condition"]))
    write_csv(outputs["stage"], summarize_groups(rows, ["route_stage_label"]))
    write_csv(outputs["model"], summarize_groups(rows, ["model_family", "route_stage_label", "model"]))
    write_csv(outputs["prompt_family"], summarize_groups(rows, ["domain", "prompt_family"]))
    write_csv(outputs["condition"], summarize_groups(rows, ["condition"]))
    write_csv(outputs["confidence_intervals"], confidence_intervals(rows))
    write_csv(outputs["planned_contrasts_fdr"], planned_contrasts_fdr(rows))
    write_csv(outputs["paired_condition_delta_summary"], paired_condition_delta_summary(rows))
    write_csv(outputs["cluster_paired_condition_contrasts"], cluster_paired_condition_contrasts(rows))
    write_csv(outputs["prompt_family_holdout"], prompt_family_holdout_summary(rows))
    write_csv(outputs["length_sensitivity"], length_exclusion_sensitivity(rows))
    write_csv(outputs["missingness_summary"], missingness_summary(raw_rows, expected_tasks))
    write_csv(
        outputs["matrix_completeness"],
        completeness_rows,
        fallback_fieldnames=[
            "artifact_id",
            "expected",
            "unexpected",
            "missing",
            "status",
            "observed_rows",
            "clean_rows",
            "error_rows",
            "config_hash",
            "observed_config_hashes",
            "run_ids",
            "model_family",
            "route_stage_label",
            "model",
            "condition",
            "prompt_family",
            "domain",
            "run",
        ],
    )
    outputs["manifest"] = write_manifest(paths, rows, raw_rows, completeness_rows, output_dir)
    outputs["report"] = write_report(rows, raw_rows, output_dir, paths, completeness_rows)
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Exp8 post-training aesthetic-prior outputs")
    parser.add_argument("--exp8-all", action="store_true", help="Analyze all Exp8 CSV files under experiment_data")
    parser.add_argument("--input", nargs="+", help="Specific Exp8 CSV files")
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG,
        help="Exp8 config used to build the expected matrix for completeness checks",
    )
    parser.add_argument(
        "--expected-runs-per-cell",
        type=int,
        help="Expected repeats per route/prompt/condition cell; defaults to max observed run",
    )
    parser.add_argument(
        "--no-completeness-check",
        action="store_true",
        help="Skip expected-matrix completeness checks",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = args.input or (find_exp8_files() if args.exp8_all else [])
    if not paths:
        raise SystemExit("No Exp8 CSV files found. Pass --exp8-all after collection or use --input.")
    outputs = run_analysis(
        paths,
        args.output_dir,
        None if args.no_completeness_check else args.config,
        args.expected_runs_per_cell,
    )
    print(f"Analyzed {len(clean_rows(dedupe_rows(read_rows(paths))))} clean rows")
    manifest = json.loads(outputs["manifest"].read_text(encoding="utf-8"))
    print(
        "Matrix completeness: {status} ({observed}/{expected} observed, {missing} missing)".format(
            status=manifest["completeness_status"],
            observed=manifest["observed_expected_rows"],
            expected=manifest["expected_matrix_rows"],
            missing=manifest["missing_expected_rows"],
        )
    )
    for path in outputs.values():
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
