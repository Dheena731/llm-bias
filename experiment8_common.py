"""Shared helpers for Experiment 8 post-training aesthetic-prior probes."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

import os

from experiment7_common import provider_from_model, slugify


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
    "prompt_id",
    "system_prompt",
    "served_provider",
    "finish_reason",
    "reasoning_tokens",
    "max_tokens_used",
]
REQUIRED_ROUTE_FIELDS = {"model", "model_family", "route_stage_label", "stage_provenance"}
REQUIRED_PROMPT_FIELDS = {"id", "domain"}  # plus "prompt" (one prompt) or "prompts" (several)


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
        if not (family.get("prompt") or family.get("prompts")):
            raise ValueError(f"Exp8 prompt family needs 'prompt' or 'prompts': {family['id']}")
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


def build_exp8_tasks(config: dict, mode: str = "full", local: bool = False) -> list[dict]:
    """Expand the config into tasks. local=True uses local_routes, local_repeats and local_parameters."""
    validate_exp8_config(config)
    if mode not in {"full", "smoke"}:
        raise ValueError(f"Unknown Exp8 task mode: {mode}")
    track = config["tracks"]["text"]
    routes = _select_for_mode(config.get("local_routes", []) if local else config["routes"], mode)
    prompt_families = _select_for_mode(config["prompt_families"], mode)
    excluded = set(config.get("local_excluded_conditions", [])) if local else set()
    conditions = [condition_id for condition_id in config["conditions"] if condition_id not in excluded]
    repeat_key = "smoke_repeats" if mode == "smoke" else ("local_repeats" if local else "full_repeats")
    repeats = int(track.get(repeat_key, track["full_repeats"]))
    # A run offset adds repeats to an earlier collection without reusing its artifact ids.
    start = 0 if mode == "smoke" else int(track.get("local_run_offset" if local else "run_offset", 0))
    params = track.get("local_parameters" if local else "api_parameters", {})
    digest = config_hash(config)

    tasks: list[dict] = []
    for route in routes:
        for family in prompt_families:
            prompts = _select_for_mode(family.get("prompts") or [family["prompt"]], mode)
            for prompt_index, base_prompt in enumerate(prompts, start=1):
                # Single-prompt families keep the original artifact-id format.
                prompt_tag = f"_p{prompt_index}" if len(family.get("prompts") or []) > 1 else ""
                for condition_id in conditions:
                    condition = config["conditions"][condition_id]
                    prompt = build_prompt(base_prompt, condition.get("suffix", ""))
                    for run in range(start + 1, start + repeats + 1):
                        artifact_id = "exp8_text_{model}_{family}{tag}_{condition}_r{run:02d}".format(
                            model=model_slug(route["model"]),
                            family=slugify(family["id"]),
                            tag=prompt_tag,
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
                                "backend": route.get("backend", "openrouter"),
                                "prompt_family": family["id"],
                                "prompt_id": f"{family['id']}{prompt_tag}",
                                "domain": family["domain"],
                                "condition": condition_id,
                                "run": run,
                                "prompt": prompt,
                                "system_prompt": condition.get("system", ""),
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
        "prompt_id": task.get("prompt_id", task["prompt_family"]),
        "system_prompt": task.get("system_prompt", ""),
    }


def write_csv_rows(path: str | Path, rows: Iterable[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def call_exp8_text_model(task: dict) -> str:
    """Call OpenRouter and keep response metadata (served provider, finish reason, reasoning tokens) on the task."""
    from openai import OpenAI

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for Exp8 collection")
    params = task.get("api_parameters", {})
    max_tokens = int(params.get("max_tokens", 768))
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1", timeout=float(params.get("timeout", 60.0)))
    messages = [{"role": "system", "content": task["system_prompt"]}] if task.get("system_prompt") else []
    response = client.chat.completions.create(
        model=task["model"],
        messages=messages + [{"role": "user", "content": task["prompt"]}],
        max_tokens=max_tokens,
        temperature=float(params.get("temperature", 0.8)),
    )
    choice = response.choices[0]
    details = getattr(response.usage, "completion_tokens_details", None)
    task["response_meta"] = {
        "served_provider": (response.model_extra or {}).get("provider", ""),
        "finish_reason": choice.finish_reason or "",
        "reasoning_tokens": getattr(details, "reasoning_tokens", None) or "",
        "max_tokens_used": max_tokens,
    }
    text = choice.message.content or ""
    if not text.strip():
        # Raise before the raw file is written so --only-missing retries it (e.g. reasoning used the token budget).
        raise RuntimeError("empty response")
    return text
