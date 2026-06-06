"""Shared helpers for Experiment 8 post-training aesthetic-prior probes."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from experiment7_common import call_openrouter_chat, provider_from_model, slugify


DEFAULT_CONFIG = "configs/exp8_post_training_priors.json"
FIELDNAMES = [
    "artifact_id",
    "timestamp",
    "run_id",
    "config_hash",
    "track",
    "model",
    "provider",
    "model_family",
    "route_stage_label",
    "stage_provenance",
    "prompt_family",
    "domain",
    "condition",
    "run",
    "prompt",
    "raw_output_path",
    "error",
    "feature_json",
]
REQUIRED_ROUTE_FIELDS = {"model", "model_family", "route_stage_label", "stage_provenance"}
REQUIRED_PROMPT_FIELDS = {"id", "domain", "prompt"}


def load_exp8_config(path: str = DEFAULT_CONFIG) -> dict:
    with open(path, encoding="utf-8") as handle:
        config = json.load(handle)
    validate_exp8_config(config)
    return config


def config_hash(config: dict) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_exp8_config(config: dict) -> None:
    for key in ("routes", "prompt_families", "conditions", "tracks"):
        if key not in config:
            raise ValueError(f"Exp8 config missing required key: {key}")
    if "text" not in config["tracks"]:
        raise ValueError("Exp8 config missing tracks.text")

    seen_routes = set()
    for route in config["routes"]:
        missing = REQUIRED_ROUTE_FIELDS - set(route)
        if missing:
            raise ValueError(f"Exp8 route missing required fields: {sorted(missing)}")
        model = route["model"]
        if model in seen_routes:
            raise ValueError(f"Duplicate Exp8 route model: {model}")
        seen_routes.add(model)

    seen_families = set()
    for family in config["prompt_families"]:
        missing = REQUIRED_PROMPT_FIELDS - set(family)
        if missing:
            raise ValueError(f"Exp8 prompt family missing required fields: {sorted(missing)}")
        family_id = family["id"]
        if family_id in seen_families:
            raise ValueError(f"Duplicate Exp8 prompt family: {family_id}")
        seen_families.add(family_id)

    if not config["conditions"]:
        raise ValueError("Exp8 config must define at least one condition")
    for condition_id, condition in config["conditions"].items():
        if "suffix" not in condition:
            raise ValueError(f"Exp8 condition missing suffix: {condition_id}")

    for repeat_key in ("smoke_repeats", "full_repeats"):
        if int(config["tracks"]["text"].get(repeat_key, 0)) <= 0:
            raise ValueError(f"Exp8 tracks.text.{repeat_key} must be positive")


def unverified_routes(config: dict) -> list[dict]:
    return [
        route
        for route in config.get("routes", [])
        if "verify_before_full_run" in str(route.get("stage_provenance", "")).lower()
    ]


def model_slug(model: str) -> str:
    return slugify(model.replace(":", "_"))


def timestamped_path(prefix: str, output_dir: str | Path = "experiment_data") -> Path:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path(output_dir) / f"{prefix}_{timestamp}.csv"


def build_prompt(base_prompt: str, suffix: str) -> str:
    return "\n\n".join(part for part in [base_prompt, suffix] if part)


def _select_for_mode(items: list, mode: str) -> list:
    return items[:1] if mode == "smoke" else items


def build_exp8_tasks(config: dict, mode: str = "full") -> list[dict]:
    validate_exp8_config(config)
    if mode not in {"full", "smoke"}:
        raise ValueError(f"Unknown Exp8 task mode: {mode}")
    routes = _select_for_mode(config["routes"], mode)
    prompt_families = _select_for_mode(config["prompt_families"], mode)
    conditions = list(config["conditions"])
    repeats = int(config["tracks"]["text"]["smoke_repeats" if mode == "smoke" else "full_repeats"])
    params = config["tracks"]["text"].get("api_parameters", {})
    digest = config_hash(config)

    tasks: list[dict] = []
    for route in routes:
        for family in prompt_families:
            for condition_id in conditions:
                condition = config["conditions"][condition_id]
                prompt = build_prompt(family["prompt"], condition.get("suffix", ""))
                for run in range(1, repeats + 1):
                    artifact_id = "exp8_text_{model}_{family}_{condition}_r{run:02d}".format(
                        model=model_slug(route["model"]),
                        family=slugify(family["id"]),
                        condition=condition_id,
                        run=run,
                    )
                    tasks.append(
                        {
                            "artifact_id": artifact_id,
                            "config_hash": digest,
                            "run_id": "",
                            "track": "text",
                            "model": route["model"],
                            "provider": provider_from_model(route["model"]),
                            "model_family": route["model_family"],
                            "route_stage_label": route["route_stage_label"],
                            "stage_provenance": route.get("stage_provenance", ""),
                            "prompt_family": family["id"],
                            "domain": family["domain"],
                            "condition": condition_id,
                            "run": run,
                            "prompt": prompt,
                            "api_parameters": params,
                        }
                    )
    return tasks


def base_row(task: dict) -> dict:
    return {
        "artifact_id": task["artifact_id"],
        "timestamp": datetime.now().isoformat(),
        "run_id": task.get("run_id", ""),
        "config_hash": task.get("config_hash", ""),
        "track": task["track"],
        "model": task["model"],
        "provider": task["provider"],
        "model_family": task["model_family"],
        "route_stage_label": task["route_stage_label"],
        "stage_provenance": task["stage_provenance"],
        "prompt_family": task["prompt_family"],
        "domain": task["domain"],
        "condition": task["condition"],
        "run": task["run"],
        "prompt": task["prompt"],
        "raw_output_path": "",
        "error": "",
        "feature_json": "",
    }


def write_csv_rows(path: str | Path, rows: Iterable[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def call_exp8_text_model(task: dict) -> str:
    params = task.get("api_parameters", {})
    return call_openrouter_chat(
        task["model"],
        task["prompt"],
        max_tokens=int(params.get("max_tokens", 768)),
        temperature=float(params.get("temperature", 0.8)),
        timeout=float(params.get("timeout", 60.0)),
    )
