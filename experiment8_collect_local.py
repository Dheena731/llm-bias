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
    if (target / "converted.ok").exists():
        return str(target)
    import torch
    from safetensors.torch import save_file

    source = Path(snapshot_download(model_id, allow_patterns=["*.json", "*.bin", "*.txt", "*.model", "tokenizer*"]))
    target.mkdir(parents=True, exist_ok=True)
    shards = sorted(source.glob("pytorch_model*.bin"))  # one file, or several for 7B checkpoints
    for index, shard in enumerate(shards, start=1):
        state = torch.load(shard, map_location="cpu", weights_only=True, mmap=True)
        # save_file rejects tensors that share storage (tied embeddings); clone only those, so a checkpoint
        # is not held in memory twice.
        seen, tensors = set(), {}
        for name, tensor in state.items():
            pointer = tensor.untyped_storage().data_ptr()
            tensors[name] = tensor.contiguous().clone() if pointer in seen else tensor.contiguous()
            seen.add(pointer)
        save_file(tensors, target / f"model-{index:05d}-of-{len(shards):05d}.safetensors", metadata={"format": "pt"})
        del state, tensors
        shard.resolve().unlink()  # free each downloaded shard as soon as it is converted
    for path in source.iterdir():
        if path.suffix != ".bin" and path.name != "pytorch_model.bin.index.json" and path.exists():
            shutil.copy(path, target / path.name)
    (target / "converted.ok").touch()
    return str(target)


def sweep_orphan_blobs(hub: Path) -> None:
    """Newer huggingface_hub keeps weights in a shared store (hub/blobs/xx/<sha>) with a .refs file naming the repo
    folders that use each blob; removing a repo folder leaves its blobs behind. Delete blobs no remaining repo uses."""
    for refs in (hub / "blobs").glob("*/*.refs"):
        if not any((hub / line.split("/")[0]).exists() for line in refs.read_text().split()):
            blob = refs.with_suffix("")
            for path in (blob, refs, blob.with_name(blob.name + ".lock")):
                path.unlink(missing_ok=True)


def free_cached(model_id: str) -> None:
    """Remove a checkpoint from the Hugging Face cache and any unquantized converted copy."""
    from huggingface_hub import scan_cache_dir
    from huggingface_hub.constants import HF_HUB_CACHE

    for repo in scan_cache_dir().repos:
        if repo.repo_id == model_id:
            shutil.rmtree(repo.repo_path, ignore_errors=True)
    shutil.rmtree(CONVERTED_DIR / model_id.replace("/", "__"), ignore_errors=True)
    sweep_orphan_blobs(Path(HF_HUB_CACHE))


def quantized_path(model_id: str, bits: int) -> Path:
    return CONVERTED_DIR / f"{model_id.replace('/', '__')}-q{bits}"


def stream_to_bf16(model_id: str) -> str:
    """Download weight shards one at a time, cast each to bfloat16, and delete it, so a 7B fp32 checkpoint never sits
    on disk whole (peak: one source shard plus the half-size copy). Used only before quantization."""
    import torch
    from huggingface_hub import hf_hub_download, list_repo_files, snapshot_download
    from safetensors import safe_open
    from safetensors.torch import save_file

    target = CONVERTED_DIR / f"{model_id.replace('/', '__')}-bf16"
    if (target / "converted.ok").exists():
        return str(target)
    target.mkdir(parents=True, exist_ok=True)
    meta = Path(snapshot_download(model_id, allow_patterns=["*.json", "*.txt", "*.model", "tokenizer*"]))
    for path in meta.iterdir():
        if not path.name.endswith(".index.json"):
            shutil.copy(path, target / path.name)
    names = list_repo_files(model_id)
    shards = sorted(n for n in names if n.endswith(".safetensors")) or sorted(n for n in names if n.endswith(".bin"))
    for index, name in enumerate(shards, start=1):
        local = Path(hf_hub_download(model_id, name))
        if name.endswith(".safetensors"):
            with safe_open(str(local), framework="pt") as handle:
                tensors = {key: handle.get_tensor(key).to(torch.bfloat16) for key in handle.keys()}
        else:
            state = torch.load(local, map_location="cpu", weights_only=True, mmap=True)
            tensors = {key: value.to(torch.bfloat16).contiguous().clone() for key, value in state.items()}
            del state
        save_file(tensors, target / f"model-{index:05d}-of-{len(shards):05d}.safetensors", metadata={"format": "pt"})
        del tensors
        local.resolve().unlink()
    (target / "converted.ok").touch()
    return str(target)


def quantized(model_id: str, bits: int) -> str:
    """Quantize once (all stages of a family get the same treatment); 7B weights do not fit 32 GB RAM unquantized.
    The unquantized weights are freed right after, since the disk cannot hold several 7B copies."""
    from mlx_lm import convert

    target = quantized_path(model_id, bits)
    if not (target / "config.json").exists():
        source = stream_to_bf16(model_id)
        convert(hf_path=source, mlx_path=str(target), quantize=True, q_bits=bits)
        shutil.rmtree(source, ignore_errors=True)
        free_cached(model_id)
    return str(target)


def make_model_fn(model_id: str, is_base: bool, params: dict):
    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler

    bits = params.get("quantize_bits")
    path = quantized(model_id, int(bits)) if bits else ensure_safetensors(model_id)
    model, tokenizer = load(path)
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
        free_cached(args.model)
        for converted in CONVERTED_DIR.glob(f"{args.model.replace('/', '__')}*"):
            shutil.rmtree(converted, ignore_errors=True)
        print(f"Deleted cached {args.model}")


if __name__ == "__main__":
    main()
