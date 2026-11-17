"""Build a blinded, stratified annotation kit for validating the text detectors used in Studies 4 and 5.

Writes annotation_kit/items.csv (text only, shuffled), two blank label sheets, GUIDELINES.md, and
annotation_kit/_key/key.csv (artifact ids, detector labels, strata and sampling weights; annotators must not open it).
Run: uv run python build_annotation_kit.py
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path

from analyze_exp8_v2 import HOSTED_GLOB, LOCAL_GLOB, load

OUT = Path("annotation_kit")
SEED = 20261117
FEATURES = ["markdown", "emoji", "decorative", "polish"]
# Stratum -> target sample size. Positives are oversampled so precision and recall can both be estimated.
STRATA = {"emoji": 70, "markdown_only": 90, "decorative": 30, "polish_only": 50, "none": 60}


def detector_labels(row: dict) -> dict:
    m = row["m"]
    return {"markdown": int(m["has_markdown"]), "emoji": int(m["has_emoji"]),
            "decorative": int(row["decorative"]), "polish": int(m["has_polish_without_length"])}


def stratum(labels: dict) -> str:
    if labels["emoji"]:
        return "emoji"
    if labels["decorative"]:
        return "decorative"
    if labels["markdown"]:
        return "markdown_only"
    if labels["polish"]:
        return "polish_only"
    return "none"


def sample_balanced(rows: list[dict], n: int, rng: random.Random) -> list[dict]:
    """Round-robin across models so no single model dominates a stratum."""
    by_model = defaultdict(list)
    for row in rows:
        by_model[row["model"]].append(row)
    for group in by_model.values():
        rng.shuffle(group)
    picked, models = [], sorted(by_model)
    while len(picked) < min(n, len(rows)):
        for model in models:
            if by_model[model] and len(picked) < n:
                picked.append(by_model[model].pop())
    return picked


def main() -> None:
    import json

    rows = load(HOSTED_GLOB) + load(LOCAL_GLOB)
    for row in rows:
        row["decorative"] = json.loads(row["feature_json"]).get("decorative_symbol_count", 0) > 0
        row["labels"] = detector_labels(row)
        row["stratum"] = stratum(row["labels"])
    rng = random.Random(SEED)
    population = defaultdict(list)
    for row in rows:
        population[row["stratum"]].append(row)
    sample = []
    for name, target in STRATA.items():
        chosen = sample_balanced(population[name], target, rng)
        weight = len(population[name]) / len(chosen)
        for row in chosen:
            row["weight"] = weight
        sample.extend(chosen)
    rng.shuffle(sample)

    (OUT / "_key").mkdir(parents=True, exist_ok=True)
    with (OUT / "items.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["item_id", "text"])
        for index, row in enumerate(sample, start=1):
            row["item_id"] = f"item_{index:03d}"
            writer.writerow([row["item_id"], Path(row["raw_output_path"]).read_text(encoding="utf-8")])
    for annotator in ("A", "B"):
        with (OUT / f"labels_annotator_{annotator}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["item_id", *FEATURES, "notes"])
            for row in sample:
                writer.writerow([row["item_id"], "", "", "", "", ""])
    with (OUT / "_key" / "key.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["item_id", "artifact_id", "model", "condition", "stratum", "weight", *[f"det_{f}" for f in FEATURES]])
        for row in sample:
            writer.writerow([row["item_id"], row["artifact_id"], row["model"], row["condition"], row["stratum"],
                             f"{row['weight']:.4f}", *[row["labels"][f] for f in FEATURES]])
    counts = {name: len(population[name]) for name in STRATA}
    print(f"Wrote {len(sample)} items to {OUT}/ (population per stratum: {counts})")


if __name__ == "__main__":
    main()
