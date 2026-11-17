"""Collect Experiment 8 text outputs for post-training aesthetic-prior analysis."""

from __future__ import annotations

import argparse
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Callable

from aesthetic_features import extract_text_features
from experiment8_common import (
    base_row,
    build_exp8_tasks,
    call_exp8_text_model,
    config_hash,
    load_exp8_config,
    timestamped_path,
    unverified_routes,
    write_csv_rows,
)


SENSITIVE_PATTERNS = [
    re.compile(
        r"(['\"](?:user_id|api_key|authorization|access_token|refresh_token|organization_id|org_id|account_id|project_id)['\"]\s*:\s*)['\"][^'\"]+['\"]",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b((?:OPENROUTER_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|GOOGLE_API_KEY|API_KEY|ACCESS_TOKEN|REFRESH_TOKEN)\s*=\s*)[^\s,;]+",
        re.IGNORECASE,
    ),
    re.compile(r"((?:X-API-Key|OpenRouter-API-Key|api-key):\s*)[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"(Authorization:\s*Bearer\s+)[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"(Bearer\s+)[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"(sk-(?:or-v1-)?)[A-Za-z0-9._-]+", re.IGNORECASE),
]


def run_single_text_task(
    task: dict,
    raw_dir: Path,
    model_fn: Callable[[dict], str],
    reuse_existing: bool = False,
) -> dict:
    row = base_row(task)
    try:
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / f"{task['artifact_id']}.txt"
        if reuse_existing and raw_path.exists():
            text = raw_path.read_text(encoding="utf-8")
        else:
            text = model_fn(task)
            raw_path.write_text(text, encoding="utf-8")
        row["raw_output_path"] = str(raw_path)
        row["feature_json"] = json.dumps(extract_text_features(text), sort_keys=True)
    except Exception as exc:
        row["error"] = format_error(exc)
    return row


def format_error(exc: Exception) -> str:
    message = f"{type(exc).__name__}: {exc}"
    for pattern in SENSITIVE_PATTERNS:
        message = pattern.sub(r"\1[redacted]", message)
    return message


def run_text_tasks(
    tasks: list[dict],
    csv_path: Path,
    raw_dir: Path,
    model_fn: Callable[[dict], str] = call_exp8_text_model,
    max_workers: int = 6,
    reuse_existing: bool = False,
) -> list[dict]:
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
        futures = {
            executor.submit(run_single_text_task, task, raw_dir, model_fn, reuse_existing): task
            for task in tasks
        }
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            rows.sort(key=lambda item: item["artifact_id"])
            write_csv_rows(csv_path, rows)
            print(f"[{len(rows)}/{len(tasks)}] {row['artifact_id']}")
    rows.sort(key=lambda item: item["artifact_id"])
    write_csv_rows(csv_path, rows)
    return rows


def filter_tasks(tasks: list[dict], args: argparse.Namespace, raw_dir: Path) -> list[dict]:
    if args.model:
        tasks = [task for task in tasks if task["model"] == args.model]
    if args.model_family:
        tasks = [task for task in tasks if task["model_family"] == args.model_family]
    if args.route_stage_label:
        tasks = [task for task in tasks if task["route_stage_label"] == args.route_stage_label]
    if args.runs_per_cell is not None:
        tasks = [task for task in tasks if int(task["run"]) <= args.runs_per_cell]
    if args.only_missing:
        tasks = [task for task in tasks if not (raw_dir / f"{task['artifact_id']}.txt").exists()]
    return tasks


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Exp8 post-training-prior text outputs")
    parser.add_argument("--config", default="configs/exp8_post_training_priors.json")
    parser.add_argument("--dry-run", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--full", action="store_true")
    parser.add_argument("--confirm-full", action="store_true", help="Required before collecting a full Exp8 run")
    parser.add_argument(
        "--allow-unverified-routes",
        action="store_true",
        help="Allow full collection while preserving route_stage_label for unverified provenance",
    )
    parser.add_argument("--model", help="Run only one exact model route")
    parser.add_argument("--model-family", help="Run only one model family")
    parser.add_argument("--route-stage-label", help="Run only one stage label")
    parser.add_argument("--runs-per-cell", type=int, help="Run only tasks with run <= this value")
    parser.add_argument("--run-id", help="Explicit run id for resuming the same raw-output directory")
    parser.add_argument("--reuse-existing", action="store_true")
    parser.add_argument("--only-missing", action="store_true")
    parser.add_argument("--max-workers", type=int, default=6)
    parser.add_argument(
        "--max-tokens",
        type=int,
        help="Override max_tokens for this pass (e.g. retrying reasoning routes that returned empty); config hash unchanged",
    )
    args = parser.parse_args(argv)
    if not args.dry_run and not args.smoke and not args.full:
        parser.error("Choose --dry-run, --smoke, or --full explicitly")
    return args


def resolve_collection_mode(args: argparse.Namespace) -> str:
    return "smoke" if args.smoke else "full"


def validate_run_safety(args: argparse.Namespace, config: dict) -> None:
    if not args.full:
        return
    if not args.confirm_full:
        raise SystemExit("Full Exp8 collection requires --confirm-full")
    unresolved = unverified_routes(config)
    if unresolved and not args.allow_unverified_routes:
        models = ", ".join(route["model"] for route in unresolved)
        raise SystemExit(
            "Full Exp8 collection has routes with stage_provenance=verify_before_full_run. "
            f"Verify provenance or pass --allow-unverified-routes to keep route_stage_label bounded: {models}"
        )


def raw_output_dir(config: dict, run_id: str) -> Path:
    safe_run_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", run_id).strip("_") or "run"
    return Path("experiment_artifacts/exp8_text/raw") / config_hash(config)[:12] / safe_run_id


def main() -> None:
    args = parse_args()
    config = load_exp8_config(args.config)
    validate_run_safety(args, config)
    mode = resolve_collection_mode(args)
    run_id = args.run_id or datetime.now().strftime("exp8_%Y%m%d_%H%M%S")
    raw_dir = raw_output_dir(config, run_id)
    tasks = filter_tasks(build_exp8_tasks(config, mode=mode), args, raw_dir)
    if config.get("randomize_seed") is not None:
        # Randomized execution order so time-of-collection (rate limits, provider load) is not confounded with condition.
        random.Random(config["randomize_seed"]).shuffle(tasks)
    for task in tasks:
        task["run_id"] = run_id
        if args.max_tokens:
            task["api_parameters"] = {**task["api_parameters"], "max_tokens": args.max_tokens}
    if args.dry_run:
        dry_tasks = filter_tasks(build_exp8_tasks(config, mode="full"), args, raw_dir)
        print(f"Exp8 text dry run: {len(dry_tasks)} tasks")
        unresolved = unverified_routes(config)
        if unresolved:
            print(f"Routes needing provenance verification before full run: {len(unresolved)}")
        return
    output = timestamped_path(config.get("output_prefix", "exp8_post_training_priors"))
    run_text_tasks(
        tasks,
        output,
        raw_dir,
        max_workers=args.max_workers,
        reuse_existing=args.reuse_existing,
    )
    print(f"Saved results to {output}")


if __name__ == "__main__":
    main()
