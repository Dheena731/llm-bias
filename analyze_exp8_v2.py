"""Analyze Experiment 8 v2 (Studies 4 and 5): condition rates, family-clustered paired contrasts, placebo controls,
and the OLMo 2 training-stage comparison.

Merges every CSV for a collection (main pass plus retry passes), keeping one clean row per artifact.
Outcomes split Markdown into markup syntax (headings, emphasis, code, links, tables) and list structure.
Inference: differences are computed within prompt, averaged within each of the 12 prompt families, and tested with
an exact sign-flip test over families; Holm correction is applied within each table.
Run: uv run python analyze_exp8_v2.py
"""

from __future__ import annotations

import csv
import glob
import itertools
import json
import random
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from presentation_features import markdown_kinds, strip_wrappers

OUT = Path("analysis_output/exp8_v2")
HOSTED_GLOB = "experiment_data/exp8_v2_presentation_priors_*.csv"
CONTROLS_GLOB = "experiment_data/exp8_v2b_controls_*.csv"
LOCAL_GLOB = "experiment_data/exp8_v2_local_stagewise_*.csv"
LOCAL7B_GLOB = "experiment_data/exp8_v2_olmo7b_stagewise_*.csv"
METRICS = ["has_markup", "has_list", "has_markdown", "has_emoji", "has_placeholder", "has_polish_without_length",
           "word_count"]
STAGES = ["base", "sft", "dpo", "instruct_rlvr"]
STAGE_NAMES = {"base": "Base", "sft": "SFT", "dpo": "DPO", "instruct_rlvr": "Instruct (RLVR)"}
NAMES = {"claude-sonnet-5.5": "Claude Sonnet 5.5", "claude-haiku-5.5": "Claude Haiku 5.5", "gemini-3.8-flash": "Gemini 3.8 Flash",
         "qwen3.6-flash": "Qwen 3.6 Flash", "gpt-5.6-luna": "GPT-5.6 Luna", "llama-3.1-8b-instruct": "Llama 3.1 8B",
         "llama-3.3-70b-instruct": "Llama 3.3 70B"}
# Bracketed or braced fill-ins such as [Feature Name] or {product}: marks a template rather than a finished text.
PLACEHOLDER = re.compile(r"\[[A-Z][^\]\n]{0,40}\](?!\()|\{[A-Za-z_ ]{2,30}\}")  # (?!\() skips Markdown link text
# Conditions that do not target Markdown; used for the length-stratified stage comparison.
NON_MARKDOWN_CONDITIONS = {"neutral", "no_emoji", "placebo", "diverse_domain_specific"}


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
        text = Path(row["raw_output_path"]).read_text(encoding="utf-8")
        row["m"] = {k: float(features[k]) for k in ("has_markdown", "has_emoji", "has_polish_without_length", "word_count")}
        row["m"].update({k: float(v) for k, v in markdown_kinds(text).items()})
        row["m"]["has_placeholder"] = float(bool(PLACEHOLDER.search(text)))
        # Sensitivity: markup in the deliverable only, without lead-ins and closing notes to the user.
        row["m"]["has_markup_body"] = float(markdown_kinds(strip_wrappers(text))["has_markup"])
    return rows


def short(model: str) -> str:
    return model.split("/")[-1]


def holm(pvalues: list[float]) -> list[float]:
    order = sorted(range(len(pvalues)), key=lambda i: pvalues[i])
    adjusted, running = [0.0] * len(pvalues), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(pvalues) - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted


def family_diffs(a_rows: list[dict], b_rows: list[dict], metric: str) -> list[float]:
    """Per-family mean of within-prompt differences (a minus b), repeats averaged within prompt."""
    a, b, family = defaultdict(list), defaultdict(list), {}
    for row in a_rows:
        a[row["prompt_id"]].append(row["m"][metric])
        family[row["prompt_id"]] = row["prompt_family"]
    for row in b_rows:
        b[row["prompt_id"]].append(row["m"][metric])
        family[row["prompt_id"]] = row["prompt_family"]
    by_family = defaultdict(list)
    for prompt in set(a) & set(b):
        by_family[family[prompt]].append(mean(a[prompt]) - mean(b[prompt]))
    return [mean(v) for v in by_family.values()]


def contrast(a_rows: list[dict], b_rows: list[dict], metric: str, seed: int = 11) -> dict:
    diffs = family_diffs(a_rows, b_rows, metric)
    if not diffs:
        return {}
    observed = mean(diffs)
    flips = [abs(sum(d * s for d, s in zip(diffs, signs)) / len(diffs)) for signs in itertools.product((1, -1), repeat=len(diffs))]
    p = sum(f >= abs(observed) - 1e-12 for f in flips) / len(flips)
    rng = random.Random(seed)
    boot = sorted(mean(rng.choice(diffs) for _ in diffs) for _ in range(4000))
    return {"delta": observed, "ci_low": boot[100], "ci_high": boot[3899], "p": p, "families": len(diffs)}


def select(rows: list[dict], **keys) -> list[dict]:
    return [r for r in rows if all(r[k] == v for k, v in keys.items())]


def rate(rows: list[dict], metric: str) -> float:
    return mean(r["m"][metric] for r in rows) if rows else float("nan")


def fmt_p(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def cell(c: dict, adjusted_p: float, scale: float = 100) -> str:
    star = "*" if adjusted_p < 0.05 else ""
    return f"{scale * c['delta']:+.1f}{star}"


def hosted_tables(hosted: list[dict], controls: list[dict], write_table) -> dict:
    models = sorted({r["model"] for r in hosted}, key=lambda m: -rate(select(hosted, model=m, condition="neutral"), "has_markup"))
    spec = [("no_emoji", "has_markup"), ("no_markdown", "has_markup"), ("plain_no_markdown", "has_markup"),
            ("placebo", "has_markup"), ("placebo", "has_emoji")]
    results, flat = {}, []
    for m in models:
        neutral = select(hosted, model=m, condition="neutral")
        for condition, metric in spec:
            c = contrast(select(hosted, model=m, condition=condition), neutral, metric)
            results[(m, condition, metric)] = c
            flat.append((m, condition, metric))
    adjusted = dict(zip(flat, holm([results[k]["p"] for k in flat])))
    body = []
    for m in models:
        neutral = select(hosted, model=m, condition="neutral")
        body.append([NAMES.get(short(m), short(m)), f"{100 * rate(neutral, 'has_markup'):.1f}", f"{100 * rate(neutral, 'has_list'):.1f}",
                     f"{100 * rate(neutral, 'has_emoji'):.1f}"] + [cell(results[(m, c, k)], adjusted[(m, c, k)]) for c, k in spec])
    write_table(OUT / "table_v2_routes.tex",
                "Study 1 (60 prompts in 12 families, 3 repeats per cell). Neutral rates (\\%) for markup syntax (headings, "
                "emphasis, code, links, tables), list lines, and emoji. Other columns: change versus neutral in percentage "
                "points, computed within prompt and averaged within family; * marks Holm-adjusted $p<0.05$ (exact sign-flip "
                "test over the 12 families, 35 tests). NE, No-MD, Plain: markup change under the no-emoji, bare no-Markdown, and "
                "enumerated plain-prose instructions; P: mk and P: em: markup and emoji change under the placebo.",
                "tab:v2-routes", ["Model", "Markup", "Lists", "Emoji", "NE", "No-MD", "Plain", "P: mk", "P: em"], body, "lrrrrrrrr",
                size=r"\footnotesize")
    out = {"routes": {f"{short(m)}|{c}|{k}": {**results[(m, c, k)], "p_holm": adjusted[(m, c, k)]} for m, c, k in flat}}

    if controls:
        cspec = [("placebo", "has_emoji", "hosted"), ("placebo_irrelevant", "has_emoji", "controls"),
                 ("placebo_ablated", "has_emoji", "controls"), ("placebo_placeholder_only", "has_emoji", "controls"),
                 ("placebo", "has_markup", "hosted"), ("placebo_irrelevant", "has_markup", "controls"),
                 ("placebo_ablated", "has_markup", "controls"), ("placebo_placeholder_only", "has_markup", "controls"),
                 ("destination_plaintext", "has_markup", "controls")]
        cmodels = [m for m in models if select(controls, model=m)]
        cres, cflat = {}, []
        for m in cmodels:
            neutral = select(hosted, model=m, condition="neutral")
            for condition, metric, source in cspec:
                pool = hosted if source == "hosted" else controls
                cres[(m, condition, metric)] = contrast(select(pool, model=m, condition=condition), neutral, metric)
                cflat.append((m, condition, metric))
            for condition, user, metric in (("system_no_emoji", "no_emoji", "has_emoji"), ("system_no_markdown", "no_markdown", "has_markup")):
                cres[(m, condition, metric)] = contrast(select(controls, model=m, condition=condition),
                                                        select(hosted, model=m, condition=user), metric)
                cflat.append((m, condition, metric))
        # The Orig. columns repeat Table 1's placebo contrasts: they keep Table 1's adjustment and are not re-tested here.
        new = [k for k in cflat if k[1] != "placebo"]
        cadj = {**{k: adjusted[k] for k in cflat if k[1] == "placebo"}, **dict(zip(new, holm([cres[k]["p"] for k in new])))}
        body = [[NAMES.get(short(m), short(m))] + [cell(cres[(m, c, k)], cadj[(m, c, k)]) for c, k, _ in cspec]
                + [cell(cres[(m, "system_no_emoji", "has_emoji")], cadj[(m, "system_no_emoji", "has_emoji")]),
                   cell(cres[(m, "system_no_markdown", "has_markup")], cadj[(m, "system_no_markdown", "has_markup")])]
                for m in cmodels]
        write_table(OUT / "table_v2_controls.tex",
                    "Placebo and placement controls (change in percentage points). The first four columns are emoji changes and "
                    "the next five markup changes, each versus neutral: the original placebo (Orig., repeated from "
                    "Table~\\ref{tab:v2-routes} with its adjustment there), a content-irrelevant instruction (Irr.), the original "
                    "without its placeholder and invent-facts clauses (Abl.), the placeholder clause alone (Ph.), and a named "
                    "plain-text destination (Dest.). Sys: the bare prohibition in the system prompt minus the same prohibition in "
                    f"the user prompt. * marks Holm-adjusted $p<0.05$ (exact family sign-flip test) over the {len(new)} tests new "
                    "to this table.",
                    "tab:v2-controls", ["Model", "Orig.", "Irr.", "Abl.", "Ph.", "Orig.", "Irr.", "Abl.", "Ph.", "Dest.",
                                        "Sys: emoji", "Sys: markup"], body, "l" + "r" * 11, size=r"\scriptsize")
        out["controls"] = {f"{short(m)}|{c}|{k}": {**cres[(m, c, k)], "p_holm": cadj[(m, c, k)]} for m, c, k in cflat}

    # Templates versus finished texts: how much of each neutral feature sits in placeholder outputs.
    out["placeholder"] = {short(m): {"neutral_placeholder_rate": rate(select(hosted, model=m, condition="neutral"), "has_placeholder"),
                                     "placebo_placeholder_rate": rate(select(hosted, model=m, condition="placebo"), "has_placeholder"),
                                     **{f"neutral_{k}_{tag}": rate([r for r in select(hosted, model=m, condition="neutral")
                                                                     if r["m"]["has_placeholder"] == flag], k)
                                        for k in ("has_emoji", "has_markup") for tag, flag in (("template", 1.0), ("finished", 0.0))},
                                     **{f"placebo_{k}": rate(select(hosted, model=m, condition="placebo"), k) for k in ("has_emoji", "has_markup")}}
                          for m in models}
    return out


def robustness(hosted: list[dict], controls: list[dict], write_table) -> dict:
    """Wrapper sensitivity, per-family neutral rates, and a placement equivalence check (margin 5 points)."""
    out = {"wrapper_max_change": max(abs(rate(select(hosted, model=m, condition=c), "has_markup")
                                         - rate(select(hosted, model=m, condition=c), "has_markup_body"))
                                     for m in {r["model"] for r in hosted} for c in {r["condition"] for r in hosted}),
           "markup_flag_changed": sum(r["m"]["has_markup"] != r["m"]["has_markup_body"] for r in hosted),
           "families": {}, "placement": {}}
    body = []
    for family in sorted({r["prompt_family"] for r in hosted}):
        neutral = select(hosted, prompt_family=family, condition="neutral")
        cells = {k: rate(neutral, k) for k in ("has_markup", "has_list", "has_emoji")}
        out["families"][family] = cells
        body.append([family.replace("_", " "), *[f"{100 * cells[k]:.1f}" for k in ("has_markup", "has_list", "has_emoji")]])
    write_table(OUT / "table_v2_families.tex",
                "Study 1 neutral rates (\\%) by prompt family, pooled over the seven models (105 outputs per family).",
                "tab:v2-families", ["Prompt family", "Markup", "Lists", "Emoji"], body, "lrrr", size=r"\footnotesize")
    for m in sorted({r["model"] for r in controls}):
        for sys_c, user_c, metric in (("system_no_emoji", "no_emoji", "has_emoji"), ("system_no_markdown", "no_markdown", "has_markup")):
            diffs = family_diffs(select(controls, model=m, condition=sys_c), select(hosted, model=m, condition=user_c), metric)
            rng = random.Random(5)
            boot = sorted(mean(rng.choice(diffs) for _ in diffs) for _ in range(4000))
            out["placement"][f"{short(m)}|{metric}"] = {"delta": mean(diffs), "ci90_low": boot[200], "ci90_high": boot[3799],
                                                         "equivalent_5pt": -0.05 < boot[200] and boot[3799] < 0.05}
    return out


def stage_tables(local: list[dict], label: str, write_table) -> dict:
    stages = [s for s in STAGES if select(local, route_stage_label=s)]
    out = {"neutral": {}, "vs_neutral": {}, "condition_rates": {}, "adjacent": {}, "adjacent_emoji": {}, "length_bins": {}}
    for s in stages:
        neutral = select(local, route_stage_label=s, condition="neutral")
        out["neutral"][s] = {k: rate(neutral, k) for k in ("has_markup", "has_list", "has_emoji", "word_count")}
        out["neutral"][s]["median_words"] = median(r["m"]["word_count"] for r in neutral)
        stage_rows = select(local, route_stage_label=s)
        out["neutral"][s]["outputs_over_450_words"] = [sum(r["m"]["word_count"] > 450 for r in stage_rows), len(stage_rows)]
        for condition in ("plain_no_markdown", "no_markdown", "use_markdown"):
            rows = select(local, route_stage_label=s, condition=condition)
            if rows:
                out["vs_neutral"][f"{s}|{condition}"] = contrast(rows, neutral, "has_markup")
                out["condition_rates"][f"{s}|{condition}"] = rate(rows, "has_markup")
    # Holm within the table (base excluded, as in the table) and across the three adjacent steps.
    shown = [k for k in out["vs_neutral"] if not k.startswith("base|")]
    for k, adjusted in zip(shown, holm([out["vs_neutral"][k]["p"] for k in shown])):
        out["vs_neutral"][k]["p_holm"] = adjusted
    for key, metric in (("adjacent", "has_markup"), ("adjacent_emoji", "has_emoji")):
        for earlier, later in zip(stages, stages[1:]):
            out[key][f"{earlier}->{later}"] = contrast(select(local, route_stage_label=later, condition="neutral"),
                                                       select(local, route_stage_label=earlier, condition="neutral"), metric)
        for k, adjusted in zip(list(out[key]), holm([c["p"] for c in out[key].values()])):
            out[key][k]["p_holm"] = adjusted
    bins = [(0, 100), (100, 150), (150, 250), (250, 10**6)]
    pool = [r for r in local if r["condition"] in NON_MARKDOWN_CONDITIONS]
    for lo, hi in bins:
        out["length_bins"][f"{lo}-{hi}"] = {s: {"markup": rate([r for r in pool if r["route_stage_label"] == s and lo <= r["m"]["word_count"] < hi], "has_markup"),
                                                "n": len([r for r in pool if r["route_stage_label"] == s and lo <= r["m"]["word_count"] < hi])}
                                            for s in stages}
    conditions = ["plain_no_markdown", "no_markdown"] + (["use_markdown"] if select(local, condition="use_markdown") else [])
    body = []
    for s in stages:
        n = out["neutral"][s]
        row = [STAGE_NAMES[s], f"{100 * n['has_markup']:.1f}", f"{100 * n['has_list']:.1f}", f"{100 * n['has_emoji']:.1f}", f"{n['median_words']:.0f}"]
        for condition in conditions:
            c = out["vs_neutral"].get(f"{s}|{condition}")
            row.append("--" if not c or s == "base" else f"{100 * c['delta']:+.1f} ({fmt_p(c['p_holm'])})")
        body.append(row)
    names = {"plain_no_markdown": ("Plain", "the plain-prose instruction"), "no_markdown": ("No-MD", "the bare no-Markdown instruction"),
             "use_markdown": ("Use MD", "an instruction to use Markdown")}
    write_table(OUT / f"table_v2_stages{label}.tex",
                f"Study 3 ({'7B, 4-bit' if label else '1B'}): OLMo 2 checkpoints by training stage. Neutral rates (\\%) and median "
                "words; then change in markup versus neutral (percentage points, exact family sign-flip $p$, Holm-adjusted within the table) for "
                + (", ".join(names[c][1] for c in conditions[:-1]) + (", and " if len(conditions) > 2 else " and ")
                   + names[conditions[-1]][1]) + ". The base checkpoint is excluded from these contrasts because "
                "it continues the prompt rather than completing a task.",
                f"tab:v2-stages{label}", ["Stage", "Markup", "Lists", "Emoji", "Words", *[names[c][0] for c in conditions]],
                body, "lrrrr" + "r" * len(conditions), size=r"\footnotesize")
    body = [[f"{lo}--{hi if hi < 10**6 else ''}"] + [f"{100 * out['length_bins'][f'{lo}-{hi}'][s]['markup']:.1f} ({out['length_bins'][f'{lo}-{hi}'][s]['n']})"
                                                  for s in stages] for lo, hi in bins]
    write_table(OUT / f"table_v2_length{label}.tex",
                f"Study 3 ({'7B, 4-bit' if label else '1B'}): markup rate (\\%, with $n$) by output length in words and training stage, pooled over the conditions that do "
                "not target Markdown (neutral, no-emoji, placebo, diverse).",
                f"tab:v2-length{label}", ["Words", *[STAGE_NAMES[s] for s in stages]], body, "l" + "r" * len(stages), size=r"\footnotesize")
    return out


def stage_figure(families: dict[str, dict]) -> None:
    fig, ax = plt.subplots(figsize=(5.2, 3))
    for label, out in families.items():
        stages = list(out["neutral"])
        for metric, style in (("has_markup", "-"), ("has_list", "--")):
            ax.plot([STAGE_NAMES[s] for s in stages], [100 * out["neutral"][s][metric] for s in stages], style, marker="o",
                    label=f"{label} {'markup' if metric == 'has_markup' else 'lists'}")
    ax.set_ylabel("Neutral outputs with feature (%)")
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "olmo_stage_trend.png", dpi=300)
    plt.close(fig)


def main() -> None:
    from analyze_tist_revision import write_table

    OUT.mkdir(parents=True, exist_ok=True)
    hosted, controls, local, local7b = load(HOSTED_GLOB), load(CONTROLS_GLOB), load(LOCAL_GLOB), load(LOCAL7B_GLOB)
    # Extra 1B repeats (runs 2-3) enter only once every stage has them, so stages stay comparable.
    if not {r["route_stage_label"] for r in local if int(r["run"]) > 1} >= set(STAGES):
        local = [r for r in local if int(r["run"]) == 1]
    summary = {"rows": {"hosted": len(hosted), "controls": len(controls), "local_1b": len(local), "local_7b": len(local7b)}}
    summary.update(hosted_tables(hosted, controls, write_table))
    summary["robustness"] = robustness(hosted, controls, write_table)
    families = {"1B": stage_tables(local, "", write_table)}
    if {r["route_stage_label"] for r in local7b} >= set(STAGES):  # only once all four 7B stages are collected
        families["7B"] = stage_tables(local7b, "_7b", write_table)
    summary["stages"] = families
    stage_figure(families)
    for name, rows in (("hosted", hosted), ("controls", controls), ("local_1b", local), ("local_7b", local7b)):
        cells = defaultdict(list)
        for r in rows:
            cells[(short(r["model"]), r["condition"])].append(r["m"])
        with (OUT / f"{name}_rates.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["model", "condition", "n", *METRICS])
            for (m, c), v in sorted(cells.items()):
                writer.writerow([m, c, len(v), *[f"{mean(x[k] for x in v):.4f}" for k in METRICS]])
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary["rows"]))


if __name__ == "__main__":
    main()
