"""Analyze Experiment 8 v2: per-route condition rates, prompt-clustered paired contrasts, and the OLMo 2 stage trend.

Merges every exp8_v2 CSV (main pass plus retry passes) keeping one clean row per artifact.
Run: uv run python analyze_exp8_v2.py
"""

from __future__ import annotations

import csv
import glob
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("analysis_output/exp8_v2")
HOSTED_GLOB = "experiment_data/exp8_v2_presentation_priors_*.csv"
LOCAL_GLOB = "experiment_data/exp8_v2_local_stagewise_*.csv"
METRICS = ["has_format_default", "has_markdown", "has_emoji", "has_polish_without_length", "word_count", "md_per_100w"]
CONDITIONS = ["neutral", "no_emoji", "no_markdown", "plain_no_markdown", "placebo", "diverse_domain_specific",
              "polished_but_plain", "system_plain"]
# (condition, baseline): what each contrast isolates.
CONTRASTS = [
    ("placebo", "neutral", "generic instruction effect (spillover)"),
    ("plain_no_markdown", "placebo", "content-specific effect of the plain instruction"),
    ("plain_no_markdown", "neutral", "total effect of the plain instruction"),
    ("no_emoji", "neutral", "emoji-only prohibition"),
    ("no_markdown", "neutral", "Markdown-only prohibition"),
    ("system_plain", "plain_no_markdown", "system vs user placement of the plain instruction"),
    ("diverse_domain_specific", "neutral", "diversity request"),
]
STAGES = ["base", "sft", "dpo", "instruct_rlvr"]
STAGE_NAMES = {"base": "Base", "sft": "SFT", "dpo": "DPO", "instruct_rlvr": "Instruct (RLVR)"}


def load(pattern: str) -> list[dict]:
    """One row per artifact: prefer clean rows, then the most recent file."""
    best: dict[str, dict] = {}
    for path in sorted(glob.glob(pattern)):
        with open(path, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                clean = not row["error"].strip() and bool(row["feature_json"])
                if clean or row["artifact_id"] not in best:
                    best[row["artifact_id"]] = row
    rows = [row for row in best.values() if not row["error"].strip()]
    for row in rows:
        features = json.loads(row["feature_json"])
        row["m"] = {k: float(features[k]) for k in METRICS if k in features}
        # Density separates "uses Markdown" from "writes longer" (base and DPO outputs are much longer).
        row["m"]["md_per_100w"] = 100 * float(features["markdown_marker_count"]) / max(float(features["word_count"]), 1.0)
    return rows


def short(model: str) -> str:
    return model.split("/")[-1]


def paired_contrast(rows: list[dict], route: str, condition: str, baseline: str, metric: str,
                    iterations: int = 4000, seed: int = 11) -> dict:
    """Mean paired difference over prompts (repeats averaged within prompt), with prompt-cluster bootstrap CI
    and a sign-flip p-value over prompts."""
    by_prompt = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row["model"] == route and row["condition"] in (condition, baseline):
            by_prompt[row["prompt_id"]][row["condition"]].append(row["m"][metric])
    diffs = [mean(v[condition]) - mean(v[baseline]) for v in by_prompt.values() if v[condition] and v[baseline]]
    if not diffs:
        return {}
    rng = random.Random(seed)
    observed = mean(diffs)
    boot = sorted(mean(rng.choice(diffs) for _ in diffs) for _ in range(iterations))
    extreme = sum(abs(mean(d * rng.choice((1, -1)) for d in diffs)) >= abs(observed) - 1e-12 for _ in range(iterations))
    return {"route": short(route), "condition": condition, "baseline": baseline, "metric": metric, "prompts": len(diffs),
            "delta": observed, "ci_low": boot[int(0.025 * iterations)], "ci_high": boot[int(0.975 * iterations) - 1],
            "p_signflip": (extreme + 1) / (iterations + 1)}


def rate_table(rows: list[dict], key: str) -> list[dict]:
    cells = defaultdict(list)
    for row in rows:
        cells[(row[key], row["condition"])].append(row["m"])
    return [{key: short(k) if key == "model" else k, "condition": c, "n": len(v),
             **{metric: mean(m[metric] for m in v) for metric in METRICS}}
            for (k, c), v in sorted(cells.items())]


def write_csv(path: Path, data: list[dict]) -> None:
    if not data:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def stage_contrasts(local: list[dict], iterations: int = 4000, seed: int = 13) -> list[dict]:
    """Adjacent training stages compared on the same prompts (neutral condition), sign-flip test over prompts."""
    out = []
    for earlier, later in zip(STAGES, STAGES[1:]):
        for metric in ("has_markdown", "md_per_100w", "has_emoji", "word_count"):
            value = {(r["route_stage_label"], r["prompt_id"]): r["m"][metric] for r in local if r["condition"] == "neutral"}
            diffs = [value[(later, p)] - value[(earlier, p)] for (s, p) in value if s == later and (earlier, p) in value]
            if not diffs:
                continue
            rng = random.Random(seed)
            observed = mean(diffs)
            extreme = sum(abs(mean(d * rng.choice((1, -1)) for d in diffs)) >= abs(observed) - 1e-12 for _ in range(iterations))
            out.append({"from": earlier, "to": later, "metric": metric, "prompts": len(diffs), "delta": observed,
                        "p_signflip": (extreme + 1) / (iterations + 1)})
    return out


def pct(value: float) -> str:
    return f"{100 * value:.1f}"


def write_tex_tables(hosted_rates: list[dict], local_rates: list[dict], contrasts: list[dict]) -> None:
    from analyze_tist_revision import write_table

    def rate(rows, key, name, condition, metric):
        return next(r[metric] for r in rows if r[key] == name and r["condition"] == condition)

    def contrast(route, condition, baseline, metric):
        c = next(c for c in contrasts if c["route"] == route and c["condition"] == condition and c["baseline"] == baseline
                 and c["metric"] == metric)
        stars = "*" if c["p_signflip"] < 0.05 else ""
        return f"{100 * c['delta']:+.1f}{stars}"

    routes = sorted({r["model"] for r in hosted_rates}, key=lambda m: -rate(hosted_rates, "model", m, "neutral", "has_markdown"))
    names = {"claude-sonnet-5.5": "Claude Sonnet 5.5", "claude-haiku-5.5": "Claude Haiku 5.5", "gemini-3.8-flash": "Gemini 3.8 Flash",
             "qwen3.6-flash": "Qwen 3.6 Flash", "llama-3.1-8b-instruct": "Llama 3.1 8B", "llama-3.3-70b-instruct": "Llama 3.3 70B"}
    body = [[names.get(r, r), pct(rate(hosted_rates, "model", r, "neutral", "has_markdown")), pct(rate(hosted_rates, "model", r, "neutral", "has_emoji")),
             contrast(r, "placebo", "neutral", "has_markdown"), contrast(r, "placebo", "neutral", "has_emoji"),
             contrast(r, "no_emoji", "neutral", "has_markdown"), contrast(r, "plain_no_markdown", "placebo", "has_markdown"),
             contrast(r, "system_plain", "plain_no_markdown", "has_markdown")] for r in routes]
    write_table(OUT / "table_v2_routes.tex",
                "Study 4 (60 prompts $\\times$ 3 repeats per cell). MD and Emoji: neutral rates in \\%. Remaining columns are paired "
                "differences in percentage points, averaged within prompt: placebo minus neutral (P: MD, P: Emoji), no-emoji minus "
                "neutral (NE: MD), plain minus placebo (Plain$-$P), and system minus user placement of the plain instruction "
                "(Sys$-$User). * marks $p<0.05$ in a sign-flip test over the 60 prompts.",
                "tab:v2-routes", ["Model", "MD", "Emoji", "P: MD", "P: Emoji", "NE: MD", "Plain$-$P", "Sys$-$User"], body,
                "lrrrrrrr", size=r"\small")
    stages = [s for s in STAGES if any(r["route_stage_label"] == s for r in local_rates)]
    body = []
    for s in stages:
        cells = [STAGE_NAMES[s]]
        for condition in ("neutral", "placebo", "plain_no_markdown"):
            cells += [pct(rate(local_rates, "route_stage_label", s, condition, "has_markdown")),
                      pct(rate(local_rates, "route_stage_label", s, condition, "has_emoji"))]
        cells.append(f"{rate(local_rates, 'route_stage_label', s, 'neutral', 'md_per_100w'):.1f}")
        cells.append(f"{rate(local_rates, 'route_stage_label', s, 'neutral', 'word_count'):.0f}")
        body.append(cells)
    write_table(OUT / "table_v2_stages.tex",
                "Study 5: OLMo 2 1B checkpoints by training stage (60 prompts, one output each per condition). "
                "Rates in \\%; MD/100w (Markdown markers per 100 words) and words are neutral-condition means.",
                "tab:v2-stages", ["Stage", "Neutral MD", "Emoji", "Placebo MD", "Emoji", "Plain MD", "Emoji", "MD/100w", "Words"],
                body, "lrrrrrrrr", size=r"\small")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    hosted, local = load(HOSTED_GLOB), load(LOCAL_GLOB)
    hosted_rates, local_rates = rate_table(hosted, "model"), rate_table(local, "route_stage_label")
    write_csv(OUT / "hosted_route_condition.csv", hosted_rates)
    write_csv(OUT / "local_stage_condition.csv", local_rates)
    contrasts = []
    for rows in (hosted, local):
        for route in sorted({row["model"] for row in rows}):
            for condition, baseline, _ in CONTRASTS:
                for metric in ("has_emoji", "has_markdown", "has_format_default", "word_count"):
                    result = paired_contrast(rows, route, condition, baseline, metric)
                    if result:
                        contrasts.append(result)
    write_csv(OUT / "paired_contrasts.csv", contrasts)
    write_csv(OUT / "stage_contrasts.csv", stage_contrasts(local))
    write_tex_tables(hosted_rates, local_rates, contrasts)

    # Stage trend under the neutral prompt (OLMo 2 1B, one family of checkpoints).
    stage_rates = {s: {m: mean(r["m"][m] for r in local if r["route_stage_label"] == s and r["condition"] == "neutral")
                       for m in METRICS} for s in STAGES if any(r["route_stage_label"] == s for r in local)}
    if stage_rates:
        fig, ax = plt.subplots(figsize=(5, 3))
        for metric, label in [("has_markdown", "Markdown"), ("has_emoji", "Emoji"), ("has_polish_without_length", "Polish (no length)")]:
            ax.plot([STAGE_NAMES[s] for s in stage_rates], [stage_rates[s][metric] * 100 for s in stage_rates], marker="o", label=label)
        ax.set_ylabel("Neutral outputs with feature (%)")
        ax.set_title("OLMo 2 1B by training stage", fontsize=9)
        ax.legend(fontsize=7, frameon=False)
        fig.tight_layout()
        fig.savefig(OUT / "olmo_stage_trend.png", dpi=300)
        plt.close(fig)
    summary = {"hosted_rows": len(hosted), "local_rows": len(local),
               "hosted_routes": sorted({short(r["model"]) for r in hosted}),
               "local_stages": sorted({r["route_stage_label"] for r in local}),
               "neutral_stage_rates": stage_rates}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "neutral_stage_rates"}))


if __name__ == "__main__":
    main()
