"""Analyze UI and image reference baselines with the shared feature extractors."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from aesthetic_features import extract_image_features, extract_ui_features


DEFAULT_BASELINES = "configs/ui_image_baselines.json"
DEFAULT_OUTPUT_DIR = Path("analysis_output/baselines")
DEFAULT_IMAGE_DIR_NAME = "generated_images"

UI_BINARY_FIELDS = [
    "has_purple_or_blue",
    "has_gradient",
    "has_rounded_cards",
    "has_shadow",
    "has_blur_or_glass",
    "has_hero_section",
    "has_centered_layout",
]
IMAGE_BINARY_FIELDS = ["has_purple_or_blue"]
SUMMARY_KEYS = ["track", "source_type", "domain", "design_family"]


def load_baseline_records(path: str | Path = DEFAULT_BASELINES) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload["records"] if isinstance(payload, dict) else payload


def _image_module():
    try:
        from PIL import Image, ImageDraw
    except ModuleNotFoundError as exc:
        raise RuntimeError("Pillow is required for image baseline generation. Install pillow>=11.") from exc
    return Image, ImageDraw


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    color = value.strip().lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    if len(color) != 6:
        raise ValueError(f"Expected hex color in #RRGGBB form, got {value!r}")
    return tuple(int(color[index : index + 2], 16) for index in (0, 2, 4))


def render_image_spec(spec: dict[str, Any], output_path: str | Path) -> Path:
    """Render a deterministic synthetic image baseline from a small JSON spec."""
    Image, ImageDraw = _image_module()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    width, height = spec.get("size", [160, 120])
    colors = [_hex_to_rgb(color) for color in spec.get("colors", ["#808080"])]
    kind = spec.get("kind", "solid")
    image = Image.new("RGB", (int(width), int(height)), colors[0])
    draw = ImageDraw.Draw(image)

    if kind == "solid":
        pass
    elif kind == "horizontal_bands":
        band_height = max(1, int(height) // len(colors))
        for index, color in enumerate(colors):
            y0 = index * band_height
            y1 = int(height) if index == len(colors) - 1 else (index + 1) * band_height
            draw.rectangle([0, y0, int(width), y1], fill=color)
    elif kind == "vertical_bands":
        band_width = max(1, int(width) // len(colors))
        for index, color in enumerate(colors):
            x0 = index * band_width
            x1 = int(width) if index == len(colors) - 1 else (index + 1) * band_width
            draw.rectangle([x0, 0, x1, int(height)], fill=color)
    elif kind == "center_square":
        background = colors[0]
        foreground = colors[1] if len(colors) > 1 else colors[0]
        image.paste(background, [0, 0, int(width), int(height)])
        margin_x = int(width) // 4
        margin_y = int(height) // 4
        draw.rectangle([margin_x, margin_y, int(width) - margin_x, int(height) - margin_y], fill=foreground)
    else:
        raise ValueError(f"Unknown image baseline kind: {kind}")

    image.save(output_path)
    return output_path


def _materialize_image(record: dict[str, Any], image_dir: Path) -> Path:
    if record.get("path"):
        path = Path(record["path"])
        if not path.exists():
            raise FileNotFoundError(f"Image baseline path does not exist: {path}")
        return path
    if "image_spec" not in record:
        raise ValueError(f"Image baseline {record.get('baseline_id', '<unknown>')} needs path or image_spec")
    return render_image_spec(record["image_spec"], image_dir / f"{record['baseline_id']}.png")


def extract_baseline_features(record: dict[str, Any], image_dir: str | Path | None = None) -> dict[str, Any]:
    track = record["track"]
    if track == "ui":
        return extract_ui_features(record.get("content", ""))
    if track == "image":
        output_dir = Path(image_dir or DEFAULT_OUTPUT_DIR / DEFAULT_IMAGE_DIR_NAME)
        image_path = _materialize_image(record, output_dir)
        features = extract_image_features(image_path)
        features["image_path"] = str(image_path)
        return features
    raise ValueError(f"Unsupported cross-modal baseline track: {track}")


def _group_by(rows: list[dict[str, Any]], keys: list[str]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(key, "") for key in keys)].append(row)
    return groups


def _feature_signature(row: dict[str, Any]) -> str:
    if row["track"] == "ui":
        fields = [
            "has_purple_or_blue",
            "has_gradient",
            "has_rounded_cards",
            "has_shadow",
            "has_blur_or_glass",
            "has_hero_section",
            "has_centered_layout",
        ]
        return "|".join(f"{field}={int(bool(row.get(field)))}" for field in fields)
    return "|".join(
        [
            f"has_purple_or_blue={int(bool(row.get('has_purple_or_blue')))}",
            f"phash={row.get('perceptual_hash', '')}",
        ]
    )


def _summarize(rows: list[dict[str, Any]], binary_fields: list[str]) -> list[dict[str, Any]]:
    summary = []
    numeric_fields = sorted(
        {
            key
            for row in rows
            for key, value in row.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
    )
    for group_key, group in sorted(_group_by(rows, SUMMARY_KEYS).items()):
        item = dict(zip(SUMMARY_KEYS, group_key, strict=True))
        item["n"] = len(group)
        for field in binary_fields:
            item[f"{field}_rate"] = mean(1.0 if row.get(field) else 0.0 for row in group)
        for field in numeric_fields:
            values = [float(row.get(field, 0) or 0) for row in group]
            item[f"mean_{field}"] = mean(values) if values else 0.0
        summary.append(item)
    return summary


def _homogenization_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary = []
    for group_key, group in sorted(_group_by(rows, ["track", "source_type"]).items()):
        signatures = [_feature_signature(row) for row in group]
        counts: dict[str, int] = defaultdict(int)
        for signature in signatures:
            counts[signature] += 1
        n = len(group)
        dominant = max(counts.values()) if counts else 0
        summary.append(
            {
                "track": group_key[0],
                "source_type": group_key[1],
                "n": n,
                "unique_signature_count": len(counts),
                "duplicate_signature_rate": 1.0 - (len(counts) / n) if n else 0.0,
                "dominant_signature_share": dominant / n if n else 0.0,
                "claim_scope": "reference_baseline_only",
            }
        )
    return summary


def analyze_baseline_records(
    records: list[dict[str, Any]],
    image_dir: str | Path | None = None,
) -> dict[str, list[dict[str, Any]]]:
    rows_by_track = {"ui": [], "image": []}
    for record in records:
        features = extract_baseline_features(record, image_dir=image_dir)
        row = {
            "baseline_id": record["baseline_id"],
            "track": record["track"],
            "source_type": record.get("source_type", "reference"),
            "domain": record.get("domain", ""),
            "design_family": record.get("design_family", ""),
            "license_note": record.get("license_note", ""),
        }
        row.update(features)
        rows_by_track[record["track"]].append(row)

    all_rows = rows_by_track["ui"] + rows_by_track["image"]
    return {
        "ui_rows": rows_by_track["ui"],
        "ui_summary": _summarize(rows_by_track["ui"], UI_BINARY_FIELDS),
        "image_rows": rows_by_track["image"],
        "image_summary": _summarize(rows_by_track["image"], IMAGE_BINARY_FIELDS),
        "homogenization_summary": _homogenization_summary(all_rows),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) or ["n"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_baseline_outputs(
    records: list[dict[str, Any]],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Path]:
    output_dir = Path(output_dir)
    image_dir = output_dir / DEFAULT_IMAGE_DIR_NAME
    tables = analyze_baseline_records(records, image_dir=image_dir)
    outputs = {
        "ui_rows": output_dir / "ui_baseline_rows.csv",
        "ui_summary": output_dir / "ui_baseline_summary.csv",
        "image_rows": output_dir / "image_baseline_rows.csv",
        "image_summary": output_dir / "image_baseline_summary.csv",
        "homogenization_summary": output_dir / "cross_modal_homogenization_summary.csv",
    }
    for name, path in outputs.items():
        write_csv(path, tables[name])
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze UI and image reference baselines")
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
