"""Analyze hand-authored text baselines with the Exp8 feature schema."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from aesthetic_features import extract_text_features


DEFAULT_BASELINES = "configs/text_baselines.json"
DEFAULT_OUTPUT_DIR = Path("analysis_output/baselines")
BINARY_FIELDS = [
    "has_emoji",
    "has_markdown",
    "has_stock_phrase",
    "has_format_default",
    "has_polish_default",
]


def load_baseline_records(path: str | Path = DEFAULT_BASELINES) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload["records"] if isinstance(payload, dict) else payload


def _group_by(rows: list[dict], keys: list[str]) -> dict[tuple, list[dict]]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(key, "") for key in keys)].append(row)
    return groups


def analyze_baseline_records(records: list[dict]) -> tuple[list[dict], list[dict]]:
    rows = []
    for record in records:
        features = extract_text_features(record.get("text", ""))
        row = {
            "baseline_id": record["baseline_id"],
            "source_type": record.get("source_type", "hand_authored"),
            "domain": record.get("domain", ""),
            "text": record.get("text", ""),
        }
        row.update(features)
        rows.append(row)

    summary = []
    for (source_type, domain), group in sorted(_group_by(rows, ["source_type", "domain"]).items()):
        item = {"source_type": source_type, "domain": domain, "n": len(group)}
        for field in BINARY_FIELDS:
            item[f"{field}_rate"] = mean(1.0 if row.get(field) else 0.0 for row in group)
        item["mean_word_count"] = mean(float(row.get("word_count", 0) or 0) for row in group)
        summary.append(item)
    return rows, summary


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) or ["n"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_baseline_outputs(records: list[dict], output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Path]:
    output_dir = Path(output_dir)
    rows, summary = analyze_baseline_records(records)
    outputs = {
        "rows": output_dir / "text_baseline_rows.csv",
        "summary": output_dir / "text_baseline_summary.csv",
    }
    write_csv(outputs["rows"], rows)
    write_csv(outputs["summary"], summary)
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze text baselines for Exp8 presentation-prior comparisons")
    parser.add_argument("--input", default=DEFAULT_BASELINES)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = write_baseline_outputs(load_baseline_records(args.input), args.output_dir)
    for path in outputs.values():
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
