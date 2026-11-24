"""Markdown and emoji in chosen vs rejected responses of an OLMo 2 preference mix (the DPO training data).

Data: Hugging Face dataset allenai/olmo-2-0425-1b-preference-mix or allenai/olmo-2-1124-7b-preference-mix
(data/*.parquet), downloaded separately.
Run (data dir passed as an argument; -I keeps the download dir off sys.path):
  uv run --with pyarrow python -I analyze_preference_markdown.py --data /path/to/prefmix [--size 7B]
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # repo modules, also under python -I

from aesthetic_features import extract_text_features  # noqa: E402
from presentation_features import markdown_kinds  # noqa: E402

OUT = Path(__file__).resolve().parent / "analysis_output" / "preference_mix"
METRICS = ["has_markup", "has_list", "has_markdown", "has_emoji"]
MIN_MODEL_RESPONSES = 500  # responding models below this are pooled as "other" (the reference level)


def last_assistant(value) -> str:
    if isinstance(value, str):
        return value
    turns = [t for t in (value or []) if isinstance(t, dict) and t.get("role") == "assistant"]
    return (turns[-1].get("content") or "") if turns else ""


def features(text: str) -> dict:
    base = extract_text_features(text)
    return {**markdown_kinds(text), "has_markdown": bool(base["has_markdown"]), "has_emoji": bool(base["has_emoji"]),
            "words": int(base["word_count"])}


def paired(pairs: list[tuple[dict, dict]], metric: str) -> dict:
    """Rates and an exact-enough McNemar test (normal approximation; n is large)."""
    chosen_only = sum(c[metric] and not r[metric] for c, r in pairs)
    rejected_only = sum(r[metric] and not c[metric] for c, r in pairs)
    discordant = chosen_only + rejected_only
    z = (chosen_only - rejected_only) / math.sqrt(discordant) if discordant else 0.0
    return {"pairs": len(pairs), "chosen_rate": sum(c[metric] for c, _ in pairs) / len(pairs),
            "rejected_rate": sum(r[metric] for _, r in pairs) / len(pairs),
            "chosen_only": chosen_only, "rejected_only": rejected_only,
            "p_two_sided": math.erfc(abs(z) / math.sqrt(2))}


def conditional_logit(pairs: list[tuple[dict, dict]], models: list[tuple[str, str]], length: bool, by_model: bool) -> dict:
    """Pairwise conditional logit: P(chosen) = sigmoid(b . (x_chosen - x_rejected)), fitted by Newton steps with a unit
    ridge (keeps rarely-rejected models finite); Wald 95% CIs. Model terms are +1/-1 indicators of who wrote each side."""
    import numpy as np

    names = ["has_markup", "has_emoji"] + (["log_length_ratio"] if length else [])
    columns = [[c[n] - r[n] for c, r in pairs] for n in names[:2]]
    if length:
        columns.append([math.log((c["words"] + 1) / (r["words"] + 1)) for c, r in pairs])
    x = np.array(columns, dtype=float).T
    if by_model:
        counts = Counter(m for pair in models for m in pair)
        kept = sorted(m for m, n in counts.items() if n >= MIN_MODEL_RESPONSES and m != "other")
        index = {m: i for i, m in enumerate(kept)}
        indicators = np.zeros((len(pairs), len(kept)))
        for row, (chosen, rejected) in enumerate(models):
            if chosen in index:
                indicators[row, index[chosen]] += 1
            if rejected in index:
                indicators[row, index[rejected]] -= 1
        x = np.hstack([x, indicators])
    beta = np.zeros(x.shape[1])
    for _ in range(100):
        p = 1 / (1 + np.exp(-(x @ beta)))
        hessian = (x * (p * (1 - p))[:, None]).T @ x + np.eye(x.shape[1])
        step = np.linalg.solve(hessian, x.T @ (1 - p) - beta)
        beta += step
        if np.abs(step).max() < 1e-9:
            break
    se = np.sqrt(np.diag(np.linalg.inv(hessian)))
    out = {n: {"odds_ratio": math.exp(beta[i]), "ci_low": math.exp(beta[i] - 1.96 * se[i]),
               "ci_high": math.exp(beta[i] + 1.96 * se[i])} for i, n in enumerate(names)}
    out["responding_models"] = int(x.shape[1] - len(names)) if by_model else 0
    return out


def adjusted_table() -> None:
    """One table for both sizes, from whichever summaries exist."""
    rows = []
    for size, suffix in (("1B", ""), ("7B", "_7b")):
        path = OUT / f"summary{suffix}.json"
        if not path.exists():
            continue
        fits = json.loads(path.read_text(encoding="utf-8")).get("conditional_logit", {})
        for key, label in (("features", "None"), ("length", "Length"), ("length_model", "Length + responding model")):
            if key in fits:
                rows.append(f"{size} & {label} & " + " & ".join(
                    f"{f['odds_ratio']:.2f} ({f['ci_low']:.2f}--{f['ci_high']:.2f})"
                    for f in (fits[key]["has_markup"], fits[key]["has_emoji"])) + r" \\")
    (OUT / "table_preference_adjusted.tex").write_text("\n".join([
        r"\begin{table}[t]", r"\centering", r"\small",
        r"\caption{Which response in a pair is chosen, OLMo 2 preference mixes: odds ratios (95\% Wald interval) from a "
        r"pairwise conditional logit with markup and emoji as features. Adjustments add the log ratio of the two responses' "
        rf"word counts and indicators for the model that wrote each response (models with at least {MIN_MODEL_RESPONSES:,} "
        r"responses; the rest pooled).}",
        r"\label{tab:preference-adjusted}", r"\begin{tabular}{llrr}", r"\toprule",
        r"Mix & Adjustment & Markup & Emoji \\", r"\midrule", *rows, r"\bottomrule", r"\end{tabular}", r"\end{table}"]) + "\n",
        encoding="utf-8")


def main() -> None:
    import pyarrow.parquet as pq

    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--size", default="1B", choices=["1B", "7B"])
    args = parser.parse_args()
    pairs, models, sources = [], [], Counter()
    for path in sorted(glob.glob(str(Path(args.data) / "data" / "*.parquet"))):
        table = pq.read_table(path, columns=None)
        names = table.column_names
        for row in table.to_pylist():
            chosen, rejected = last_assistant(row.get("chosen")), last_assistant(row.get("rejected"))
            if chosen and rejected:
                pairs.append((features(chosen), features(rejected)))
                models.append((str(row.get("chosen_model") or "other"), str(row.get("rejected_model") or "other")))
                sources[str(row.get("source", ""))] += 1
    matched = [(c, r) for c, r in pairs if 0.8 <= (c["words"] + 1) / (r["words"] + 1) <= 1.25]
    summary = {
        "pairs": len(pairs), "columns": names, "top_sources": sources.most_common(8),
        "mean_words": {"chosen": sum(c["words"] for c, _ in pairs) / len(pairs),
                       "rejected": sum(r["words"] for _, r in pairs) / len(pairs)},
        "all_pairs": {m: paired(pairs, m) for m in METRICS},
        "length_matched_pairs": {m: paired(matched, m) for m in METRICS},
        "same_model_pairs": {m: paired(same, m) for m in METRICS} if (same := [p for p, (c, r) in zip(pairs, models) if c == r]) else {},
        "conditional_logit": {key: conditional_logit(pairs, models, length, by_model) for key, length, by_model in
                              (("features", False, False), ("length", True, False), ("length_model", True, True))},
        "top_responding_models": Counter(m for pair in models for m in pair).most_common(12),
    }
    suffix = "" if args.size == "1B" else "_" + args.size.lower()  # 1B keeps its original file names
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"summary{suffix}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    rows = []
    for label, key in (("All pairs", "all_pairs"), ("Length-matched", "length_matched_pairs")):
        for metric, name in (("has_markup", "Markup"), ("has_list", "List lines"), ("has_emoji", "Emoji")):
            s = summary[key][metric]
            rows.append(f"{label} & {name} & {s['pairs']:,} & {100 * s['chosen_rate']:.1f} & {100 * s['rejected_rate']:.1f} & "
                        f"{s['chosen_only']:,} / {s['rejected_only']:,} \\\\")
    (OUT / f"table_preference_markdown{suffix}.tex").write_text("\n".join([
        r"\begin{table}[t]", r"\centering", r"\small",
        rf"\caption{{Markup, list lines, and emoji in the OLMo 2 {args.size} preference mix used for DPO. Rates are the share of chosen and "
        r"rejected responses with the feature; the last column counts pairs where only the chosen (or only the rejected) "
        r"response has it. Length-matched pairs differ in length by at most 25\%.}",
        rf"\label{{tab:preference-markdown{suffix.replace('_', '-')}}}", r"\begin{tabular}{llrrrr}", r"\toprule",
        r"Pairs & Feature & $n$ & Chosen \% & Rejected \% & Chosen-only / rejected-only \\", r"\midrule",
        *rows, r"\bottomrule", r"\end{tabular}", r"\end{table}"]) + "\n", encoding="utf-8")
    adjusted_table()
    print(json.dumps({k: summary[k] for k in ("pairs", "mean_words")}),
          json.dumps({k: {m: round(v["chosen_rate"] - v["rejected_rate"], 4) for m, v in summary[k].items()}
                      for k in ("all_pairs", "length_matched_pairs")}))


if __name__ == "__main__":
    main()
