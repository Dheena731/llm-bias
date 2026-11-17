"""Collect Exp8 v2 outputs from local stage-wise checkpoints (OLMo 2 base/SFT/DPO/instruct) with MLX.

mlx-lm (and torch, only for converting .bin checkpoints) are ephemeral dependencies so the project's own
dependencies stay unchanged:
  uv run --with mlx-lm --with torch python experiment8_collect_local.py --model allenai/OLMo-2-0425-1B-SFT --delete-after
"""

from __future__ import annotations

import argparse
import random
import shutil
import time
from pathlib import Path

from experiment8_collect_text import raw_output_dir, run_text_tasks
from experiment8_common import build_exp8_tasks, load_exp8_config, timestamped_path

CONVERTED_DIR = Path.home() / ".cache" / "exp8_local_models"


def ensure_safetensors(model_id: str) -> str:
    """Return a local path mlx-lm can load. Checkpoints published only as pytorch_model.bin are converted once."""
    from huggingface_hub import list_repo_files, snapshot_download

    if any(name.endswith(".safetensors") for name in list_repo_files(model_id)):
        return model_id
    target = CONVERTED_DIR / model_id.replace("/", "__")
    if (target / "model.safetensors").exists():
        return str(target)
    import torch
    from safetensors.torch import save_file

    source = Path(snapshot_download(model_id, allow_patterns=["*.json", "*.bin", "*.txt", "*.model", "tokenizer*"]))
    target.mkdir(parents=True, exist_ok=True)
    state = torch.load(source / "pytorch_model.bin", map_location="cpu", weights_only=True)
    # Clone so tied tensors do not share storage, which save_file rejects.
    save_file({name: tensor.contiguous().clone() for name, tensor in state.items()}, target / "model.safetensors",
              metadata={"format": "pt"})
    for path in source.iterdir():
        if path.suffix != ".bin":
            shutil.copy(path, target / path.name)
    (source / "pytorch_model.bin").resolve().unlink()  # free the 3 GB download once converted
    return str(target)


def make_model_fn(model_id: str, is_base: bool, params: dict):
    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler

    model, tokenizer = load(ensure_safetensors(model_id))
    sampler = make_sampler(temp=float(params.get("temperature", 0.8)))
    max_tokens = int(params.get("max_tokens", 768))

    def model_fn(task: dict) -> str:
        if is_base:
            # Base checkpoints have no chat template: give the bare instruction and let the model continue.
            prompt = task["prompt"] + "\n\n"
        else:
            prompt = tokenizer.apply_chat_template(
                [{"role": "user", "content": task["prompt"]}], add_generation_prompt=True, tokenize=False
            )
        text = generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens, sampler=sampler)
        if not text.strip():
            raise RuntimeError("empty response")
        return text

    return model_fn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Exp8 v2 outputs from local MLX checkpoints")
    parser.add_argument("--config", default="configs/exp8_v2_presentation_priors.json")
    parser.add_argument("--model", required=True, help="Exact local_routes model id")
    parser.add_argument("--run-id", default="exp8v2_local")
    parser.add_argument("--only-missing", action="store_true")
    parser.add_argument("--limit", type=int, help="Run only the first N shuffled tasks (smoke test)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--delete-after", action="store_true", help="Remove the checkpoint from the Hugging Face cache afterwards")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_exp8_config(args.config)
    route = next((r for r in config.get("local_routes", []) if r["model"] == args.model), None)
    if route is None:
        raise SystemExit(f"No local route {args.model} in {args.config}")
    raw_dir = raw_output_dir(config, args.run_id)
    tasks = [task for task in build_exp8_tasks(config, local=True) if task["model"] == args.model]
    if args.only_missing:
        tasks = [task for task in tasks if not (raw_dir / f"{task['artifact_id']}.txt").exists()]
    random.Random(config.get("randomize_seed", 0)).shuffle(tasks)
    tasks = tasks[: args.limit] if args.limit else tasks
    for task in tasks:
        task["run_id"] = args.run_id
    if args.dry_run:
        print(f"{args.model}: {len(tasks)} tasks")
        return
    started = time.time()
    model_fn = make_model_fn(args.model, route["route_stage_label"] == "base", config["tracks"]["text"].get("local_parameters", {}))
    output = timestamped_path(f"{config.get('local_output_prefix', 'exp8_local')}_{route['route_stage_label']}")
    run_text_tasks(tasks, output, raw_dir, model_fn=model_fn, max_workers=1)  # MLX generation is not thread-safe
    print(f"Saved results to {output} ({time.time() - started:.0f}s)")
    if args.delete_after:
        from huggingface_hub import scan_cache_dir

        for repo in scan_cache_dir().repos:
            if repo.repo_id == args.model:
                shutil.rmtree(repo.repo_path)
                print(f"Deleted cached {args.model}")
        shutil.rmtree(CONVERTED_DIR / args.model.replace("/", "__"), ignore_errors=True)


if __name__ == "__main__":
    main()
