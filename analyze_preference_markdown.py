"""Markdown and emoji in chosen vs rejected responses of the OLMo 2 1B preference mix (its DPO training data).

Data: Hugging Face dataset allenai/olmo-2-0425-1b-preference-mix (data/*.parquet), downloaded separately.
Run (data dir passed as an argument; -I keeps the download dir off sys.path):
  uv run --with pyarrow python -I analyze_preference_markdown.py --data /path/to/prefmix
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


def main() -> None:
    import pyarrow.parquet as pq

    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    args = parser.parse_args()
    pairs, sources = [], Counter()
    for path in sorted(glob.glob(str(Path(args.data) / "data" / "*.parquet"))):
        table = pq.read_table(path, columns=None)
        names = table.column_names
        for row in table.to_pylist():
            chosen, rejected = last_assistant(row.get("chosen")), last_assistant(row.get("rejected"))
            if chosen and rejected:
                pairs.append((features(chosen), features(rejected)))
                sources[str(row.get("source", ""))] += 1
    matched = [(c, r) for c, r in pairs if 0.8 <= (c["words"] + 1) / (r["words"] + 1) <= 1.25]
    summary = {
        "pairs": len(pairs), "columns": names, "top_sources": sources.most_common(8),
        "mean_words": {"chosen": sum(c["words"] for c, _ in pairs) / len(pairs),
                       "rejected": sum(r["words"] for _, r in pairs) / len(pairs)},
        "all_pairs": {m: paired(pairs, m) for m in METRICS},
        "length_matched_pairs": {m: paired(matched, m) for m in METRICS},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    rows = []
    for label, key in (("All pairs", "all_pairs"), ("Length-matched", "length_matched_pairs")):
        for metric, name in (("has_markup", "Markup"), ("has_list", "List lines"), ("has_emoji", "Emoji")):
            s = summary[key][metric]
            rows.append(f"{label} & {name} & {s['pairs']:,} & {100 * s['chosen_rate']:.1f} & {100 * s['rejected_rate']:.1f} & "
                        f"{s['chosen_only']:,} / {s['rejected_only']:,} \\\\")
    (OUT / "table_preference_markdown.tex").write_text("\n".join([
        r"\begin{table}[t]", r"\centering", r"\small",
        r"\caption{Markdown and emoji in the OLMo 2 1B preference mix used for DPO. Rates are the share of chosen and "
        r"rejected responses with the feature; the last column counts pairs where only the chosen (or only the rejected) "
        r"response has it. Length-matched pairs differ in length by at most 25\%.}",
        r"\label{tab:preference-markdown}", r"\begin{tabular}{llrrrr}", r"\toprule",
        r"Pairs & Feature & $n$ & Chosen \% & Rejected \% & Chosen-only / rejected-only \\", r"\midrule",
        *rows, r"\bottomrule", r"\end{tabular}", r"\end{table}"]) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("pairs", "mean_words")}),
          json.dumps({k: {m: round(v["chosen_rate"] - v["rejected_rate"], 4) for m, v in summary[k].items()}
                      for k in ("all_pairs", "length_matched_pairs")}))


if __name__ == "__main__":
    main()
