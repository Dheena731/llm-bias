"""Validate manual feature-audit samples against extractor outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aesthetic_features import extract_image_features, extract_text_features, extract_ui_features


DEFAULT_SAMPLES = "configs/feature_validity_audit_samples.json"


def load_audit_samples(path: str | Path = DEFAULT_SAMPLES) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload["samples"] if isinstance(payload, dict) else payload


def extract_sample_features(sample: dict) -> dict:
    track = sample["track"]
    if track == "text":
        return extract_text_features(sample.get("content", ""))
    if track == "ui":
        return extract_ui_features(sample.get("content", ""))
    if track == "image":
        return extract_image_features(sample["path"])
    raise ValueError(f"Unknown audit sample track: {track}")


def validate_audit_samples(samples: list[dict]) -> dict:
    failures = []
    for sample in samples:
        features = extract_sample_features(sample)
        for key, expected in sample.get("expected", {}).items():
            actual = features.get(key)
            if actual != expected:
                failures.append(
                    {
                        "sample_id": sample.get("sample_id", ""),
                        "feature": key,
                        "expected": expected,
                        "actual": actual,
                    }
                )
    return {"checked": len(samples), "failures": failures}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate manual feature-audit samples")
    parser.add_argument("--input", default=DEFAULT_SAMPLES)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = validate_audit_samples(load_audit_samples(args.input))
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
