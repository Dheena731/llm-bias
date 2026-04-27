"""
Aesthetic Anchoring in LLMs — Experiment Runner
================================================
Automates API calls for Experiments 1, 2, and 4.
Experiment 3 (human study) requires manual setup via Prolific/UserTesting.

Requirements:
    pip install openai anthropic google-generativeai pandas matplotlib seaborn scipy

Setup:
    Export your API keys as environment variables:
    export OPENAI_API_KEY="sk-..."
    export ANTHROPIC_API_KEY="sk-ant-..."
    export GOOGLE_API_KEY="..."
    export TOGETHER_API_KEY="..."  # For Llama via Together AI

Usage:
    python experiment_runner.py --experiment 1 --pilot    # Pilot run (2 runs per condition)
    python experiment_runner.py --experiment 1 --full     # Full run (30 runs per condition)
    python experiment_runner.py --experiment 2 --pilot
    python experiment_runner.py --experiment 4 --pilot
    python experiment_runner.py --analyze 1               # Analyze collected data
"""

import json
import os
import re
import time
import csv
import argparse
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import os 
from dotenv import load_dotenv

load_dotenv()

# Thread-safe lock for results
results_lock = Lock()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROMPT_LIBRARY = "prompt_library.json"
OUTPUT_DIR = "experiment_data"
PILOT_RUNS = 2
FULL_RUNS = 30

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended
    "\U00002702-\U000027B0"  # dingbats
    "\U00002600-\U000026FF"  # misc symbols
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U00002B50"             # star
    "\U00002B55"             # circle
    "\U0000200D"             # zero width joiner
    "\U000023F0-\U000023FA"  # symbols
    "\U0000231A-\U0000231B"  # watch/hourglass
    "\U000025AA-\U000025FE"  # geometric shapes
    "\U00002934-\U00002935"  # arrows
    "\U00003030"             # wavy dash
    "\U0000303D"             # part alternation
    "\U00003297"             # circled ideograph
    "\U00003299"             # circled ideograph secret
    "\U0000200D"             # ZWJ
    "\U00002764"             # heart
    "\U0000FE0F"             # variation selector
    "]+", flags=re.UNICODE
)

HEX_COLOR_PATTERN = re.compile(r'#[0-9A-Fa-f]{6}')
GRADIENT_PATTERN = re.compile(r'(linear-gradient|radial-gradient|gradient)', re.IGNORECASE)
BULLET_PATTERN = re.compile(r'^\s*[-•*]\s|^\s*\d+[.)]\s', re.MULTILINE)
HEADER_PATTERN = re.compile(r'^#{1,6}\s|^\*\*[A-Z].*\*\*\s*$', re.MULTILINE)
BOLD_ITALIC_PATTERN = re.compile(r'\*{1,3}[^*]+\*{1,3}')


# ---------------------------------------------------------------------------
# API Clients (lazy-loaded)
# ---------------------------------------------------------------------------

def call_model(model_id: str, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
    """Unified interface to call any supported model. Returns response text."""

    api_key = os.getenv("OPENROUTER_API_KEY")
    if model_id == "qwen3:latest":
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage

        client = ChatOllama(
            model="qwen3:latest",
            temperature=temperature
        )

        response = client.invoke([
            HumanMessage(content=prompt)
        ])
        return response.content
    
    elif model_id.startswith("z-ai/"):
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content
    
    elif model_id.startswith("xiaomi/"):
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    elif model_id.startswith("openai/"):
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    elif model_id.startswith("claude"):
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    elif model_id.startswith("google/"):
        from openai import OpenAI
        client = OpenAI(
            api_key=os.environ.get("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )
    
        response = client.chat.completions.create(
            model=model_id,  # change if needed
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
    
        return response.choices[0].message.content

    elif "llama" in model_id.lower():
        from openai import OpenAI
        client = OpenAI(
            api_key=os.environ.get("TOGETHER_API_KEY"),
            base_url="https://api.together.xyz/v1",
        )
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    else:
        raise ValueError(f"Unknown model: {model_id}")


# ---------------------------------------------------------------------------
# Evaluation Functions
# ---------------------------------------------------------------------------

def count_emojis(text: str) -> dict:
    """Count and classify emojis in text."""
    matches = EMOJI_PATTERN.findall(text)
    all_emojis = list("".join(matches))
    return {
        "emoji_count": len(all_emojis),
        "unique_emojis": list(set(all_emojis)),
        "compliant": len(all_emojis) == 0,
    }


def hex_to_hsl(hex_color: str) -> tuple:
    """Convert hex color to HSL. Returns (hue, saturation, lightness)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = [int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4)]

    max_c = max(r, g, b)
    min_c = min(r, g, b)
    l = (max_c + min_c) / 2.0

    if max_c == min_c:
        h = s = 0.0
    else:
        d = max_c - min_c
        s = d / (2.0 - max_c - min_c) if l > 0.5 else d / (max_c + min_c)
        if max_c == r:
            h = (g - b) / d + (6 if g < b else 0)
        elif max_c == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        h /= 6.0

    return (h * 360, s * 100, l * 100)


def analyze_colors(text: str) -> dict:
    """Extract hex colors and check for purple/pink bias."""
    hex_colors = HEX_COLOR_PATTERN.findall(text)
    has_gradient = bool(GRADIENT_PATTERN.search(text))

    purple_pink_colors = []
    for color in hex_colors:
        hue, sat, light = hex_to_hsl(color)
        # Purple-pink spectrum: hue 270-330 with reasonable saturation
        if 270 <= hue <= 330 and sat > 15:
            purple_pink_colors.append({"hex": color, "hue": hue, "sat": sat, "light": light})

    return {
        "all_colors": hex_colors,
        "color_hsl": [{"hex": c, "hsl": hex_to_hsl(c)} for c in hex_colors],
        "purple_pink_colors": purple_pink_colors,
        "has_purple_pink": len(purple_pink_colors) > 0,
        "has_gradient": has_gradient,
        "compliant": len(purple_pink_colors) == 0 and not has_gradient,
    }


def analyze_formatting(text: str) -> dict:
    """Check for various formatting constraint violations."""
    word_count = len(text.split())
    return {
        "has_emoji": not count_emojis(text)["compliant"],
        "has_bullets": bool(BULLET_PATTERN.search(text)),
        "has_headers": bool(HEADER_PATTERN.search(text)),
        "has_bold_italic": bool(BOLD_ITALIC_PATTERN.search(text)),
        "word_count": word_count,
        "exceeds_150_words": word_count > 150,
    }


# ---------------------------------------------------------------------------
# Experiment Runners
# ---------------------------------------------------------------------------

def run_experiment_1(config: dict, n_runs: int, max_workers: int = 8):
    """Emoji Persistence Experiment with parallel execution."""
    exp = config["experiment_1_emoji_persistence"]
    models = [m["id"] for m in config["metadata"]["models"]]
    results = []
    total = 0

    # Build all tasks
    tasks = []
    for model_id in models:
        for intensity_key, intensity in exp["variables"]["intensity_levels"].items():
            for topic_key, topic_data in exp["variables"]["topic_categories"].items():
                for prompt_text in topic_data["prompts"]:
                    for run in range(n_runs):
                        full_prompt = prompt_text
                        if intensity["suffix"]:
                            full_prompt += "\n\n" + intensity["suffix"]
                        
                        tasks.append({
                            "model": model_id,
                            "intensity_key": intensity_key,
                            "intensity_label": intensity["label"],
                            "topic_key": topic_key,
                            "formality_score": topic_data["formality_score"],
                            "prompt": prompt_text[:80],
                            "run": run + 1,
                            "full_prompt": full_prompt,
                        })

    print(f"Total tasks: {len(tasks)}")

    def run_single_task(task):
        try:
            response = call_model(task["model"], task["full_prompt"])
            emoji_analysis = count_emojis(response)
            
            return {
                "timestamp": datetime.now().isoformat(),
                "model": task["model"],
                "intensity_level": task["intensity_key"],
                "intensity_label": task["intensity_label"],
                "topic_category": task["topic_key"],
                "formality_score": task["formality_score"],
                "prompt": task["prompt"],
                "run": task["run"],
                "response_length": len(response),
                "word_count": len(response.split()),
                "emoji_count": emoji_analysis["emoji_count"],
                "unique_emojis": "|".join(emoji_analysis["unique_emojis"]),
                "compliant": emoji_analysis["compliant"],
                "response_text": response,
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "model": task["model"],
                "intensity_level": task["intensity_key"],
                "topic_category": task["topic_key"],
                "run": task["run"],
                "error": str(e),
            }

    # Execute with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_single_task, task): idx for idx, task in enumerate(tasks)}
        
        for future in as_completed(futures):
            result = future.result()
            with results_lock:
                results.append(result)
                print(f"  [{len(results)}/{len(tasks)}] {result.get('model', 'ERROR')} | "
                      f"{result.get('intensity_level', '?')} | {result.get('topic_category', '?')} | "
                      f"run {result.get('run', '?')}")

    return results


def run_experiment_2(config: dict, n_runs: int, max_workers: int = 8):
    """Color/Gradient Bias Experiment with parallel execution."""
    exp = config["experiment_2_color_gradient_bias"]
    models = [m["id"] for m in config["metadata"]["models"]]
    results = []

    # Build all tasks
    tasks = []
    for model_id in models:
        for company_type in exp["variables"]["company_types"]:
            for variant_key, variant in exp["variables"]["prompt_variants"].items():
                prompt = variant["template"].replace("{company_type}", company_type)
                for run in range(n_runs):
                    tasks.append({
                        "model": model_id,
                        "company_type": company_type,
                        "variant_key": variant_key,
                        "variant_label": variant["label"],
                        "prompt": prompt,
                        "run": run + 1,
                    })

    print(f"Total tasks: {len(tasks)}")

    def run_single_task(task):
        try:
            response = call_model(task["model"], task["prompt"])
            color_analysis = analyze_colors(response)

            return {
                "timestamp": datetime.now().isoformat(),
                "model": task["model"],
                "company_type": task["company_type"],
                "variant": task["variant_key"],
                "variant_label": task["variant_label"],
                "run": task["run"],
                "all_colors": "|".join(color_analysis["all_colors"]),
                "purple_pink_count": len(color_analysis["purple_pink_colors"]),
                "has_purple_pink": color_analysis["has_purple_pink"],
                "has_gradient": color_analysis["has_gradient"],
                "compliant": color_analysis["compliant"],
                "response_text": response,
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "model": task["model"],
                "company_type": task["company_type"],
                "variant": task["variant_key"],
                "run": task["run"],
                "error": str(e),
            }

    # Execute with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_single_task, task): idx for idx, task in enumerate(tasks)}
        
        for future in as_completed(futures):
            result = future.result()
            with results_lock:
                results.append(result)
                print(f"  [{len(results)}/{len(tasks)}] {result.get('model', 'ERROR')} | "
                      f"{result.get('company_type', '?')} | {result.get('variant', '?')} | "
                      f"run {result.get('run', '?')}")

    return results


def run_experiment_4(config: dict, n_runs: int, max_workers: int = 8):
    """Multi-Constraint Stress Test with parallel execution."""
    exp = config["experiment_4_multi_constraint_stress"]
    models = [m["id"] for m in config["metadata"]["models"]]
    constraints = exp["variables"]["constraints"]
    topics = exp["variables"]["topics"]
    results = []

    # Build all tasks
    tasks = []
    for model_id in models:
        for topic in topics:
            # Full constraint condition
            constraint_text = "\n".join(
                f"{i+1}. {c['instruction']}" for i, c in enumerate(constraints)
            )
            full_prompt = (
                f"{topic}\n\n"
                f"Strict requirements (you MUST follow ALL of these):\n{constraint_text}\n\n"
                f"Please follow every single requirement. Violating any of them is unacceptable."
            )
            
            for run in range(n_runs):
                tasks.append({
                    "model": model_id,
                    "condition": "full_constraint",
                    "topic": topic[:60],
                    "prompt": full_prompt,
                    "run": run + 1,
                    "n_constraints": len(constraints),
                })
            
            # Progressive constraint conditions
            for n_constraints in range(1, len(constraints) + 1):
                active = constraints[:n_constraints]
                constraint_text = "\n".join(
                    f"{i+1}. {c['instruction']}" for i, c in enumerate(active)
                )
                prog_prompt = (
                    f"{topic}\n\n"
                    f"Strict requirements:\n{constraint_text}\n\n"
                    f"Follow all listed requirements."
                )

                for run in range(n_runs):
                    tasks.append({
                        "model": model_id,
                        "condition": f"progressive_{n_constraints}",
                        "topic": topic[:60],
                        "prompt": prog_prompt,
                        "run": run + 1,
                        "n_constraints": n_constraints,
                    })

    print(f"Total tasks: {len(tasks)}")

    def run_single_task(task):
        try:
            response = call_model(task["model"], task["prompt"])
            fmt = analyze_formatting(response)
            emoji = count_emojis(response)

            violations = {
                "C1_emoji": emoji["emoji_count"] > 0,
                "C2_bullets": fmt["has_bullets"],
                "C3_headers": fmt["has_headers"],
                "C4_bold_italic": fmt["has_bold_italic"],
                "C7_word_limit": fmt["exceeds_150_words"],
            }
            compliance_score = task["n_constraints"] - sum(violations.values()) if task["n_constraints"] <= 5 else 7 - sum(violations.values())

            return {
                "timestamp": datetime.now().isoformat(),
                "model": task["model"],
                "condition": task["condition"],
                "topic": task["topic"],
                "run": task["run"],
                "word_count": fmt["word_count"],
                **{f"violated_{k}": v for k, v in violations.items()},
                "compliance_score": compliance_score,
                "compliance_out_of": task["n_constraints"] if "progressive" in task["condition"] else 7,
                "response_text": response,
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "model": task["model"],
                "condition": task["condition"],
                "topic": task["topic"],
                "run": task["run"],
                "error": str(e),
            }

    # Execute with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_single_task, task): idx for idx, task in enumerate(tasks)}
        
        for future in as_completed(futures):
            result = future.result()
            with results_lock:
                results.append(result)
                print(f"  [{len(results)}/{len(tasks)}] {result.get('model', 'ERROR')} | "
                      f"{result.get('condition', '?')} | run {result.get('run', '?')}")

    return results


# ---------------------------------------------------------------------------
# Analysis Functions
# ---------------------------------------------------------------------------

def analyze_experiment_1(data_file: str):
    """Generate summary statistics and visualizations for Experiment 1."""
    try:
        import pandas as pd
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import seaborn as sns
        from scipy import stats
    except ImportError:
        print("Install required packages: pip install pandas matplotlib seaborn scipy")
        return

    df = pd.read_csv(data_file)
    df = df[df["error"].isna()] if "error" in df.columns else df

    print("\n" + "=" * 60)
    print("EXPERIMENT 1: EMOJI PERSISTENCE — SUMMARY")
    print("=" * 60)

    # Compliance rate by model × intensity
    pivot = df.groupby(["model", "intensity_level"])["compliant"].mean().unstack()
    print("\nCompliance Rate by Model × Intensity Level:")
    print(pivot.round(3).to_string())

    # Compliance rate by topic × intensity
    pivot2 = df.groupby(["topic_category", "intensity_level"])["compliant"].mean().unstack()
    print("\nCompliance Rate by Topic × Intensity Level:")
    print(pivot2.round(3).to_string())

    # Correlation: formality vs compliance
    corr_data = df.groupby("topic_category").agg(
        formality=("formality_score", "first"),
        compliance=("compliant", "mean")
    )
    r, p = stats.pearsonr(corr_data["formality"], corr_data["compliance"])
    print(f"\nPearson Correlation (formality vs compliance): r={r:.3f}, p={p:.4f}")

    # Heatmap
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    sns.heatmap(pivot, annot=True, fmt=".2f", cmap="RdYlGn", vmin=0, vmax=1, ax=axes[0])
    axes[0].set_title("Compliance Rate: Model × Intensity")
    axes[0].set_ylabel("Model")
    axes[0].set_xlabel("Intensity Level")

    sns.heatmap(pivot2, annot=True, fmt=".2f", cmap="RdYlGn", vmin=0, vmax=1, ax=axes[1])
    axes[1].set_title("Compliance Rate: Topic × Intensity")
    axes[1].set_ylabel("Topic Category")
    axes[1].set_xlabel("Intensity Level")

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "exp1_compliance_heatmap.png"), dpi=150)
    print(f"\nSaved heatmap to {OUTPUT_DIR}/exp1_compliance_heatmap.png")

    # Most common emojis
    all_emojis = []
    for emojis_str in df[df["emoji_count"] > 0]["unique_emojis"].dropna():
        all_emojis.extend(emojis_str.split("|"))
    if all_emojis:
        from collections import Counter
        emoji_freq = Counter(all_emojis).most_common(15)
        print("\nTop 15 Most Frequent Emojis:")
        for emoji, count in emoji_freq:
            print(f"  {emoji}: {count}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def save_results(results: list, experiment_name: str):
    """Save results to CSV."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{experiment_name}_{timestamp}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)

    if not results:
        print("No results to save.")
        return

    keys = set()
    for r in results:
        keys.update(r.keys())
    keys = sorted(keys)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nSaved {len(results)} results to {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Aesthetic Anchoring Experiment Runner")
    parser.add_argument("--experiment", type=int, choices=[1, 2, 4],
                        help="Experiment number to run")
    parser.add_argument("--pilot", action="store_true",
                        help="Run pilot (2 runs per condition)")
    parser.add_argument("--full", action="store_true",
                        help="Run full experiment (30 runs per condition)")
    parser.add_argument("--analyze", type=int, choices=[1, 2, 4],
                        help="Analyze data for experiment N (provide CSV path as next arg)")
    parser.add_argument("--data", type=str,
                        help="Path to CSV data file for analysis")
    parser.add_argument("--workers", type=int,
                        help="Number of parallel threads (default: 1, sequential)")
    args = parser.parse_args()

    with open(PROMPT_LIBRARY, "r") as f:
        config = json.load(f)

    if args.experiment:
        n_runs = PILOT_RUNS if args.pilot else FULL_RUNS
        mode = "PILOT" if args.pilot else "FULL"
        max_workers = args.workers if args.workers else 1
        print(f"\n{'='*60}")
        print(f"Running Experiment {args.experiment} ({mode} mode, {n_runs} runs/condition)")
        print(f"Using {max_workers} parallel threads")
        print(f"{'='*60}\n")

        if args.experiment == 1:
            results = run_experiment_1(config, n_runs, max_workers=max_workers)
            save_results(results, "exp1_emoji_persistence")
        elif args.experiment == 2:
            results = run_experiment_2(config, n_runs, max_workers=max_workers)
            save_results(results, "exp2_color_bias")
        elif args.experiment == 4:
            results = run_experiment_4(config, n_runs, max_workers=max_workers)
            save_results(results, "exp4_multi_constraint")

    elif args.analyze and args.data:
        if args.analyze == 1:
            analyze_experiment_1(args.data)
        else:
            print(f"Analysis for experiment {args.analyze} not yet implemented.")
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python experiment_runner.py --experiment 1 --pilot")
        print("  python experiment_runner.py --experiment 1 --full")
        print("  python experiment_runner.py --experiment 1 --full --workers 16")
        print("  python experiment_runner.py --analyze 1 --data experiment_data/exp1_*.csv")


if __name__ == "__main__":
    main()
