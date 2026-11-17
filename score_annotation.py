"""Score the annotation kit: per-detector precision, recall and F1 against human labels, and Cohen's kappa.

Precision and recall use inverse-probability weights from the stratified sample, so they estimate population values.
Run after both sheets are filled: uv run python score_annotation.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

KIT = Path("annotation_kit")
OUT = Path("analysis_output/annotation")
FEATURES = ["markdown", "emoji", "decorative", "polish"]


def read(path: Path) -> dict[str, dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["item_id"]: row for row in csv.DictReader(handle)}


def kappa(a: list[int], b: list[int]) -> float:
    n = len(a)
    if not n:
        return float("nan")
    observed = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def weighted_scores(detector: list[int], human: list[int], weights: list[float]) -> dict:
    tp = sum(w for d, h, w in zip(detector, human, weights) if d and h)
    fp = sum(w for d, h, w in zip(detector, human, weights) if d and not h)
    fn = sum(w for d, h, w in zip(detector, human, weights) if not d and h)
    precision = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else float("nan")
    return {"precision": precision, "recall": recall, "f1": f1}


def score(key: dict[str, dict], sheets: dict[str, dict[str, dict]]) -> list[dict]:
    results = []
    names = sorted(sheets)
    for feature in FEATURES:
        items = [i for i in key if all(sheets[s].get(i, {}).get(feature, "").strip() in {"0", "1"} for s in names)]
        detector = [int(key[i][f"det_{feature}"]) for i in items]
        weights = [float(key[i]["weight"]) for i in items]
        human = {s: [int(sheets[s][i][feature]) for i in items] for s in names}
        row = {"feature": feature, "items_labeled": len(items)}
        if len(names) == 2:
            row["kappa_annotators"] = kappa(human[names[0]], human[names[1]])
            # Consensus: both annotators agree on 1 (conservative); disagreements should be adjudicated before reporting.
            consensus = [int(x and y) for x, y in zip(human[names[0]], human[names[1]])]
            row["disagreements"] = sum(x != y for x, y in zip(human[names[0]], human[names[1]]))
        else:
            consensus = human[names[0]]
        row["kappa_detector_consensus"] = kappa(detector, consensus)
        row.update(weighted_scores(detector, consensus, weights))
        results.append(row)
    return results


def main() -> None:
    key = read(KIT / "_key" / "key.csv")
    sheets = {path.stem.split("_")[-1]: read(path) for path in sorted(KIT.glob("labels_annotator_*.csv"))}
    results = score(key, sheets)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "detector_validation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({k for r in results for k in r}, key=lambda k: (k != "feature", k)))
        writer.writeheader()
        writer.writerows(results)
    print(json.dumps(results, indent=2, default=lambda v: None))


if __name__ == "__main__":
    main()
