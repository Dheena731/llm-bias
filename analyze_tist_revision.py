"""Reanalyses for the TIST revision: per-model tables, censoring, palette concentration, per-route Exp8, spillover.

Reads fixed canonical CSVs and writes CSV, LaTeX tables, figures and summary.json to analysis_output/tist_revision/.
Run: uv run python analyze_tist_revision.py
"""

from __future__ import annotations

import csv
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analyze_results import parse_exp4_active_constraints
from experiment_runner import EMOJI_PATTERN, hex_to_hsl

OUT = Path("analysis_output/tist_revision")
EXP1 = "experiment_data/exp1_emoji_persistence_20260227_111102.csv"
EXP2 = ["experiment_data/exp2_color_bias_20260331_110130.csv", "experiment_data/exp2_color_bias_20260401_182557.csv"]
EXP4 = "experiment_data/exp4_multi_constraint_20260326_154209.csv"
EXP8 = "experiment_data/exp8_post_training_priors_20260601_022210.csv"
PHASE_B = "experiment_data/exp7_phase_b/exp7_text_defaults_20260706_102517.csv"

SHORT = {
    "google/gemini-2.5-flash": "Gemini 2.5 Flash",
    "openai/gpt-3.5-turbo-0613": "GPT-3.5-Turbo",
    "z-ai/glm-4.5-air:free": "GLM-4.5 Air",
    "xiaomi/mimo-v2-flash": "MiMo v2 Flash",
    "meta-llama/llama-3.3-70b-instruct": "Llama 3.3 70B",
    "meta-llama/llama-3.1-8b-instruct": "Llama 3.1 8B",
    "qwen/qwen-2.5-7b-instruct": "Qwen 2.5 7B",
    "qwen/qwen3.6-flash": "Qwen 3.6 Flash",
    "openai/gpt-4.1-mini": "GPT-4.1 mini",
    "anthropic/claude-sonnet-4.5": "Claude Sonnet 4.5",
}
LEVELS = ["L0_baseline", "L1_polite", "L2_explicit", "L3_emphatic", "L4_extreme"]
EXP8_CONDITIONS = ["neutral", "no_emoji", "plain_no_markdown", "diverse_domain_specific", "polished_but_plain"]
# Check marks, crosses-as-symbols and geometric shapes match the Exp1 emoji regex but are not pictographic emoji.
NON_PICTOGRAPHIC = {0x2713, 0x2714, 0x2717, 0x2718, 0xFE0F, 0x200D} | set(range(0x25A0, 0x2600))
PRIMARY_RE = re.compile(r"primary[^#\n]{0,40}(#[0-9a-f]{6})\b", re.IGNORECASE)


def rows(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def clean(row: dict) -> bool:
    return not (row.get("error") or "").strip()


def truthy(value) -> bool:
    return str(value).strip().lower() in {"true", "1"}


def pct(value: float) -> str:
    return f"{100 * value:.1f}"


def cluster_ci(groups: list[list[int]], iterations: int = 2000, seed: int = 7) -> tuple[float, float]:
    """Percentile CI for a pooled rate, resampling whole clusters (prompts) with replacement."""
    groups = [group for group in groups if group]
    if not groups:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    stats = []
    for _ in range(iterations):
        sample = [groups[rng.randrange(len(groups))] for _ in groups]
        stats.append(sum(map(sum, sample)) / sum(map(len, sample)))
    stats.sort()
    return stats[int(0.025 * iterations)], stats[int(0.975 * iterations) - 1]


def is_saturated_blue(hex_color: str) -> bool:
    hue, sat, light = hex_to_hsl(hex_color)
    return 190 <= hue < 260 and sat >= 30 and 20 <= light <= 90


def parse_primary(text: str) -> str | None:
    match = PRIMARY_RE.search(text or "")
    return match.group(1).upper() if match else None


def write_csv(path: Path, data: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def write_table(path: Path, caption: str, label: str, header: list[str], body: list[list[str]], align: str,
                size: str = "") -> None:
    lines = [
        r"\begin{table}[t]", r"\centering", size, rf"\caption{{{caption}}}", rf"\label{{{label}}}",
        rf"\begin{{tabular}}{{{align}}}", r"\toprule", " & ".join(header) + r" \\", r"\midrule",
        *[" & ".join(cells) + r" \\" for cells in body],
        r"\bottomrule", r"\end{tabular}", r"\end{table}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def study1(summary: dict) -> None:
    data = rows(EXP1)
    out, body = [], []
    nonpict_only = 0
    for model in sorted({row["model"] for row in data}):
        for level in LEVELS:
            cell = [row for row in data if row["model"] == model and row["intensity_level"] == level]
            ok = [row for row in cell if clean(row)]
            by_prompt = defaultdict(list)
            for row in ok:
                by_prompt[(row["topic_category"], row["prompt"])].append(int(truthy(row["compliant"])))
            rate = mean(v for g in by_prompt.values() for v in g) if ok else float("nan")
            low, high = cluster_ci(list(by_prompt.values()))
            topics = sorted({row["topic_category"] for row in ok})
            out.append({"model": SHORT[model], "level": level, "attempted": len(cell), "clean": len(ok),
                        "missing": len(cell) - len(ok), "emoji_free_rate": rate, "ci_low": low, "ci_high": high,
                        "prompts": len(by_prompt), "topics_present": "|".join(topics)})
            shown = "--" if not ok else f"{pct(rate)} [{pct(low)}, {pct(high)}]"
            body.append([SHORT[model] if level == LEVELS[0] else "", level.split("_")[0], f"{len(ok):,}",
                         f"{len(cell) - len(ok):,}", shown])
    for row in data:
        if clean(row) and not truthy(row["compliant"]):
            chars = {ord(ch) for match in EMOJI_PATTERN.findall(row["response_text"] or "") for ch in match}
            nonpict_only += bool(chars) and chars <= NON_PICTOGRAPHIC
    write_csv(OUT / "study1_model_level.csv", out)
    write_table(OUT / "table_study1_model_level.tex",
                "Study 1 emoji-free rate by model and instruction level, with 95\\% intervals from a prompt-cluster "
                "bootstrap. Missing rows are HTTP 429 rate-limit failures on the free GLM route; GLM has no L4 rows and "
                "its L3 rows cover only academic, legal, and technical prompts.",
                "tab:study1-model-level", ["Model", "Level", "Clean", "Missing", "Emoji-free \\% [95\\% CI]"],
                body, "llrrr")
    social = {SHORT[m]: mean(1 - truthy(r["compliant"]) for r in data if clean(r) and r["model"] == m
                             and r["intensity_level"] == "L0_baseline" and r["topic_category"] == "social_media")
              for m in {r["model"] for r in data}}
    summary["study1"] = {"nonpictographic_only_noncompliant": nonpict_only,
                         "noncompliant_total": sum(clean(r) and not truthy(r["compliant"]) for r in data),
                         "social_l0_emoji_rate_by_model": social,
                         "cells": out}


def study2(summary: dict) -> None:
    data = [row for path in EXP2 for row in rows(path) if row["variant"] == "baseline"]
    out, body, figure_data = [], [], {}
    for model in sorted({row["model"] for row in data}):
        primaries = [parse_primary(row["response_text"]) for row in data if row["model"] == model]
        parsed = [p for p in primaries if p]
        counts = Counter(parsed)
        blue = sum(is_saturated_blue(p) for p in parsed)
        top = counts.most_common(3)
        purple = sum(truthy(row["has_purple_pink"]) for row in data if row["model"] == model)
        out.append({"model": SHORT[model], "responses": len(primaries), "parsed": len(parsed), "saturated_blue": blue,
                    "distinct_primaries": len(counts), "top3": "; ".join(f"{h}:{c}" for h, c in top),
                    "top3_share": sum(c for _, c in top) / len(parsed), "purple_pink_rows": purple})
        body.append([SHORT[model], f"{blue}/{len(parsed)}", str(len(counts)),
                     ", ".join(f"\\texttt{{{h.lstrip('#')}}} ({c})" for h, c in top), str(purple)])
        figure_data[SHORT[model]] = counts.most_common(8)
    write_csv(OUT / "study2_baseline_palette.csv", out)
    write_table(OUT / "table_study2_palette.tex",
                "Study 2 primary colors in the unrestricted baseline variant (150 responses per model, 5 company types). "
                "Blue: saturated-blue primaries, defined as hue 190--260$^\\circ$, saturation $\\geq$30\\%, lightness 20--90\\%.",
                "tab:study2-palette", ["Model", "Blue", "Distinct", "Top-3 primaries (count)", "Purple"], body, "lrrlr",
                size=r"\small")
    fig, axes = plt.subplots(1, len(figure_data), figsize=(10, 2.8), sharex=True)
    for ax, (model, top) in zip(axes, figure_data.items()):
        labels = [h for h, _ in top][::-1]
        ax.barh(labels, [c for _, c in top][::-1], color=labels, edgecolor="#333333", linewidth=0.4)
        ax.set_title(model, fontsize=9)
        ax.tick_params(labelsize=7)
        ax.set_xlabel("Responses (of 150)", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "figures" / "study2_primary_colors.png", dpi=300)
    plt.close(fig)
    summary["study2"] = out


def study3(summary: dict) -> None:
    data = [row for row in rows(EXP4) if clean(row)]
    names = {"C1": "No emoji", "C2": "No bullets", "C3": "No headers", "C4": "No bold/italic", "C7": "Word limit"}
    columns = {"C1": "violated_C1_emoji", "C2": "violated_C2_bullets", "C3": "violated_C3_headers",
               "C4": "violated_C4_bold_italic", "C7": "violated_C7_word_limit"}
    models = sorted({row["model"] for row in data})
    out, body = [], []
    for cid, label in names.items():
        cells = [label]
        for model in models:
            active = [r for r in data if r["model"] == model and cid in parse_exp4_active_constraints(r)]
            violations = sum(truthy(r[columns[cid]]) for r in active)
            out.append({"constraint": label, "model": SHORT[model], "active": len(active), "violations": violations})
            cells.append(f"{violations}/{len(active)}")
        body.append(cells)
    glm_conditions = sorted({r["condition"] for r in data if "glm" in r["model"]})
    write_csv(OUT / "study3_model_constraints.csv", out)
    write_table(OUT / "table_study3_model.tex",
                "Study 3 violations / active rows by model. GLM retains 104 of 1,200 rows after connection errors and has "
                "no rows in progressive conditions 4--7; its 28 word-limit rows all come from the full-constraint condition.",
                "tab:study3-model", ["Constraint", *[SHORT[m] for m in models]], body, "l" + "r" * len(models))
    summary["study3"] = {"cells": out, "glm_clean_rows": sum("glm" in r["model"] for r in data),
                         "glm_conditions": glm_conditions}


def exp8(summary: dict) -> None:
    data = [row for row in rows(EXP8) if clean(row)]
    for row in data:
        row["f"] = json.loads(row["feature_json"])
    routes = sorted({row["model"] for row in data}, key=lambda m: SHORT[m])
    out, body = [], []
    for route in routes:
        for condition in EXP8_CONDITIONS:
            cell = [row["f"] for row in data if row["model"] == route and row["condition"] == condition]
            entry = {"route": SHORT[route], "condition": condition, "n": len(cell),
                     "format_default": mean(bool(f["has_format_default"]) for f in cell),
                     "markdown": mean(bool(f["has_markdown"]) for f in cell),
                     "emoji": mean(bool(f["has_emoji"]) for f in cell),
                     "polish_without_length": mean(bool(f["has_polish_without_length"]) for f in cell),
                     "mean_words": mean(f["word_count"] for f in cell)}
            out.append(entry)
            body.append([SHORT[route] if condition == EXP8_CONDITIONS[0] else "", condition.replace("_", " "),
                         pct(entry["format_default"]), pct(entry["markdown"]), pct(entry["emoji"]),
                         pct(entry["polish_without_length"]), f"{entry['mean_words']:.0f}"])
    write_csv(OUT / "exp8_route_condition.csv", out)
    write_table(OUT / "table_exp8_routes.tex",
                "Study 4 rates (\\%) by route and condition ($n=24$ per cell: 12 prompt families $\\times$ 2 repeats). "
                "Polish excludes the length component.",
                "tab:exp8-routes", ["Route", "Condition", "Format", "Markdown", "Emoji", "Polish", "Words"], body,
                "llrrrrr")
    fig, axes = plt.subplots(1, 3, figsize=(10, 2.9), sharey=True)
    for ax, metric, title in zip(axes, ["markdown", "emoji", "polish_without_length"], ["Markdown", "Emoji", "Polish (no length)"]):
        for route in routes:
            values = [next(e[metric] for e in out if e["route"] == SHORT[route] and e["condition"] == c) * 100
                      for c in EXP8_CONDITIONS]
            ax.plot(range(len(EXP8_CONDITIONS)), values, marker="o", label=SHORT[route])
        ax.set_xticks(range(len(EXP8_CONDITIONS)), ["neutral", "no emoji", "plain", "diverse", "polished\nplain"], fontsize=7)
        ax.set_title(title, fontsize=9)
    axes[0].set_ylabel("Outputs with feature (%)", fontsize=8)
    axes[0].legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "figures" / "exp8_route_condition.png", dpi=300)
    plt.close(fig)
    pooled = {c: mean(bool(r["f"]["has_polish_without_length"]) for r in data if r["condition"] == c) for c in EXP8_CONDITIONS}
    summary["exp8"] = {"cells": out, "polish_without_length_by_condition": pooled}


def spillover(summary: dict) -> None:
    body, out = [], []
    exp8_rows = summary["exp8"]["cells"]
    for route in sorted({e["route"] for e in exp8_rows}):
        neutral = next(e for e in exp8_rows if e["route"] == route and e["condition"] == "neutral")
        no_emoji = next(e for e in exp8_rows if e["route"] == route and e["condition"] == "no_emoji")
        out.append({"study": "Study 4", "model": route, "control": "Do not use emoji.", "n_each": neutral["n"],
                    "emoji_neutral": neutral["emoji"], "emoji_control": no_emoji["emoji"],
                    "markdown_neutral": neutral["markdown"], "markdown_control": no_emoji["markdown"],
                    "words_neutral": neutral["mean_words"], "words_control": no_emoji["mean_words"]})
    phase_b = [row for row in rows(PHASE_B) if clean(row)]
    for model in sorted({row["model"] for row in phase_b}, key=lambda m: SHORT[m]):
        cells = {}
        for condition in ("neutral", "length_matched_control"):
            cells[condition] = [json.loads(r["feature_json"]) for r in phase_b if r["model"] == model and r["condition"] == condition]
        n = min(len(v) for v in cells.values())
        families = len({r["prompt_family"] for r in phase_b if r["model"] == model and r["condition"] == "neutral"})
        out.append({"study": f"Spillover set ({families} families)", "model": SHORT[model], "control": "non-aesthetic length-matched suffix",
                    "n_each": n,
                    **{f"{k}_{tag}": mean((f["word_count"] if k == "words" else bool(f[f"has_{k}"])) for f in cells[c])
                       for tag, c in (("neutral", "neutral"), ("control", "length_matched_control"))
                       for k in ("emoji", "markdown", "words")}})
    for e in out:
        body.append([e["study"], e["model"], str(e["n_each"]), f"{pct(e['emoji_neutral'])} $\\to$ {pct(e['emoji_control'])}",
                     f"{pct(e['markdown_neutral'])} $\\to$ {pct(e['markdown_control'])}",
                     f"{e['words_neutral']:.0f} $\\to$ {e['words_control']:.0f}"])
    write_csv(OUT / "spillover.csv", out)
    write_table(OUT / "table_spillover.tex",
                "Instruction spillover: neutral $\\to$ control condition. Study 4's control forbids only emoji; the spillover-set "
                "control adds an equally long instruction that forbids no presentation feature. Rates in \\%; words are means.",
                "tab:spillover", ["Source", "Model", "$n$ each", "Emoji", "Markdown", "Words"], body, "llrrrr")
    summary["spillover"] = out


def main() -> None:
    (OUT / "figures").mkdir(parents=True, exist_ok=True)
    summary: dict = {}
    study1(summary)
    study2(summary)
    study3(summary)
    exp8(summary)
    spillover(summary)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")
    print(f"Wrote {OUT}/")


if __name__ == "__main__":
    main()
