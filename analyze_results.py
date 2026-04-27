"""
Analyze All Experiments — Aesthetic Anchoring Study
====================================================
Analyzes results from Experiments 1, 2, 3, and 4.

Usage:
    python analyze_results.py --experiment 1 --input exp1_data.csv
    python analyze_results.py --experiment 2 --input exp2_data.csv
    python analyze_results.py --experiment 3 --input exp3_survey.csv --answer-key answer_key.json
    python analyze_results.py --experiment 4 --input exp4_data.csv
    python analyze_results.py --all   # Analyze everything in current directory
"""

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats
import numpy as np
import json
import os
import argparse
import glob
from collections import Counter

sns.set_theme(style="whitegrid", font_scale=1.05)
OUT = "analysis_output"
os.makedirs(OUT, exist_ok=True)

INTENSITY_ORDER = ["L0_baseline", "L1_polite", "L2_explicit", "L3_emphatic", "L4_extreme"]
TOPIC_ORDER = ["social_media", "marketing", "recipe", "technical", "legal", "academic"]
FORMALITY_MAP = {"academic": 9, "legal": 9, "technical": 7, "recipe": 5, "marketing": 3, "social_media": 2}

MODEL_COLORS = {
    "Gemini 2.5 Flash": "#4285F4",
    "GPT-3.5-Turbo": "#10A37F",
    "GLM-4.5 Air": "#FF6B35",
    "Qwen 3.5": "#7C3AED",
}

MODEL_SHORT = {
    "google/gemini-2.5-flash": "Gemini 2.5 Flash",
    "openai/gpt-3.5-turbo-0613": "GPT-3.5-Turbo",
    "z-ai/glm-4.5-air:free": "GLM-4.5 Air",
    "ollama:qwen3.5:cloud": "Qwen 3.5",
}


# ═══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT 1: EMOJI PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_experiment_1(filepath):
    print("\n" + "=" * 70)
    print("EXPERIMENT 1: EMOJI PERSISTENCE ANALYSIS")
    print("=" * 70)

    df = pd.read_csv(filepath, low_memory=False)
    df = df[df.get("error", pd.Series(dtype=str)).isna()].copy()

    if df["compliant"].dtype == object:
        df["compliant"] = df["compliant"].map({"True": True, "False": False})
    df["compliant"] = df["compliant"].astype(bool)
    df["emoji_count"] = pd.to_numeric(df["emoji_count"], errors="coerce").fillna(0).astype(int)
    df["intensity_level"] = pd.Categorical(df["intensity_level"], categories=INTENSITY_ORDER, ordered=True)
    df["model_short"] = df["model"].map(MODEL_SHORT).fillna(df["model"])
    df["formality"] = df["topic_category"].map(FORMALITY_MAP)

    print(f"Clean rows: {len(df):,}")
    print(f"Models: {sorted(df['model_short'].unique())}")

    # Key metrics
    overall = df.groupby("intensity_level", observed=True)["compliant"].mean()
    pivot_mi = df.groupby(["model_short", "intensity_level"], observed=True)["compliant"].mean().unstack()
    pivot_ti = df.groupby(["topic_category", "intensity_level"], observed=True)["compliant"].mean().unstack()

    l0 = df[df["intensity_level"] == "L0_baseline"]
    pivot_l0 = l0.groupby(["model_short", "topic_category"], observed=True)["compliant"].mean().unstack()

    # Formality correlation
    fc = df.groupby("topic_category").agg(
        formality=("formality", "first"), compliance=("compliant", "mean")
    ).sort_values("formality")
    r, p = stats.pearsonr(fc["formality"], fc["compliance"])

    print(f"\nFormality-compliance correlation: r={r:.3f}, p={p:.4f}")
    print(f"\nBaseline compliance by topic:")
    for topic in TOPIC_ORDER:
        rate = l0[l0["topic_category"]==topic]["compliant"].mean()
        print(f"  {topic}: {rate:.1%}")

    # Non-compliant emoji analysis
    nc = df[~df["compliant"]]
    print(f"\nNon-compliant: {len(nc):,} / {len(df):,} ({len(nc)/len(df):.1%})")

    all_emojis = []
    for s in nc["unique_emojis"].dropna():
        if isinstance(s, str) and s.strip():
            all_emojis.extend(s.split("|"))
    if all_emojis:
        top = Counter(all_emojis).most_common(10)
        print(f"Top emojis: {', '.join(f'{e}({c})' for e,c in top)}")

    # ── Figures ──
    # Fig 1: Line chart by model
    fig, ax = plt.subplots(figsize=(11, 6))
    for model in sorted(pivot_mi.index):
        vals = [pivot_mi.loc[model].get(l, np.nan) for l in INTENSITY_ORDER]
        ax.plot(range(len(INTENSITY_ORDER)), vals, "o-", label=model, linewidth=2.5,
                markersize=8, color=MODEL_COLORS.get(model, "#888"))
    ax.set_xticks(range(len(INTENSITY_ORDER)))
    ax.set_xticklabels(["L0\nBaseline", "L1\nPolite", "L2\nExplicit", "L3\nEmphatic", "L4\nExtreme"])
    ax.set_ylim(-0.02, 1.08); ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.set_ylabel("Compliance Rate"); ax.set_xlabel("Instruction Intensity")
    ax.set_title("Emoji Compliance by Model and Intensity", fontweight="bold")
    ax.legend(loc="lower right"); plt.tight_layout()
    fig.savefig(f"{OUT}/exp1_compliance_by_model.png", dpi=200); plt.close()

    # Fig 2: Heatmap topic × intensity
    fig, ax = plt.subplots(figsize=(11, 5))
    sns.heatmap(pivot_ti.reindex(TOPIC_ORDER), annot=True, fmt=".2f", cmap="RdYlGn",
                vmin=0, vmax=1, ax=ax, linewidths=1, linecolor="white",
                annot_kws={"fontsize": 12, "fontweight": "bold"})
    ax.set_title("Emoji Compliance: Topic × Intensity", fontweight="bold")
    plt.tight_layout(); fig.savefig(f"{OUT}/exp1_topic_intensity.png", dpi=200); plt.close()

    # Fig 3: Baseline model × topic
    fig, ax = plt.subplots(figsize=(12, 4))
    sns.heatmap(pivot_l0.reindex(columns=TOPIC_ORDER), annot=True, fmt=".2f", cmap="RdYlGn",
                vmin=0, vmax=1, ax=ax, linewidths=1, linecolor="white",
                annot_kws={"fontsize": 13, "fontweight": "bold"})
    ax.set_title("Baseline (No Restriction) Compliance: Model × Topic", fontweight="bold")
    plt.tight_layout(); fig.savefig(f"{OUT}/exp1_baseline_heatmap.png", dpi=200); plt.close()

    # Fig 4: Formality scatter
    fig, ax = plt.subplots(figsize=(9, 6))
    for model in sorted(df["model_short"].unique()):
        mfc = df[df["model_short"]==model].groupby("topic_category").agg(
            formality=("formality", "first"), compliance=("compliant", "mean"))
        ax.scatter(mfc["formality"], mfc["compliance"], s=120,
                   c=MODEL_COLORS.get(model, "#888"), label=model, edgecolors="white", linewidth=1.5)
    z = np.polyfit(fc["formality"], fc["compliance"], 1)
    ax.plot(np.linspace(1, 10, 100), np.polyval(z, np.linspace(1, 10, 100)),
            "--", color="#EF4444", linewidth=2, alpha=0.6, label=f"Trend (r={r:.2f})")
    ax.set_xlabel("Topic Formality Score"); ax.set_ylabel("Compliance Rate")
    ax.set_title(f"Formality vs Compliance (r={r:.2f}, p={p:.3f})", fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0)); ax.legend()
    plt.tight_layout(); fig.savefig(f"{OUT}/exp1_formality_scatter.png", dpi=200); plt.close()

    print(f"\nFigures saved to {OUT}/exp1_*.png")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT 2: COLOR/GRADIENT BIAS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_experiment_2(filepath):
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: COLOR/GRADIENT BIAS ANALYSIS")
    print("=" * 70)

    df = pd.read_csv(filepath, low_memory=False)
    if df["compliant"].dtype == object:
        df["compliant"] = df["compliant"].map({"True": True, "False": False})
    df["compliant"] = df["compliant"].astype(bool)
    df["model_short"] = df["model"].map(MODEL_SHORT).fillna(df["model"])

    print(f"Total rows: {len(df):,}")
    print(f"Models: {sorted(df['model_short'].unique())}")

    print(f"\nOverall purple/pink rate: {df['has_purple_pink'].mean():.1%}")
    print(f"Overall gradient rate: {df['has_gradient'].mean():.1%}")
    print(f"Overall compliance: {df['compliant'].mean():.1%}")

    # By model
    print("\nBy model:")
    by_model = df.groupby("model_short").agg(
        compliance=("compliant", "mean"),
        purple=("has_purple_pink", "mean"),
        gradient=("has_gradient", "mean"),
        n=("compliant", "count"),
    )
    print(by_model.round(3).to_string())

    # By company type
    print("\nBy company type:")
    by_company = df.groupby("company_type").agg(
        compliance=("compliant", "mean"),
        purple=("has_purple_pink", "mean"),
        n=("compliant", "count"),
    )
    print(by_company.round(3).to_string())

    # By variant
    print("\nBy variant:")
    by_variant = df.groupby("variant").agg(
        compliance=("compliant", "mean"),
        purple=("has_purple_pink", "mean"),
        n=("compliant", "count"),
    )
    print(by_variant.round(3).to_string())

    # Figure: Model × variant compliance
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    pivot_comp = df.groupby(["model_short", "variant"])["compliant"].mean().unstack()
    sns.heatmap(pivot_comp, annot=True, fmt=".2f", cmap="RdYlGn", vmin=0, vmax=1,
                ax=axes[0], linewidths=1, linecolor="white",
                annot_kws={"fontsize": 13, "fontweight": "bold"})
    axes[0].set_title("Compliance: Model × Variant", fontweight="bold")

    pivot_purple = df.groupby(["model_short", "company_type"])["has_purple_pink"].mean().unstack()
    sns.heatmap(pivot_purple, annot=True, fmt=".2f", cmap="Purples", vmin=0, vmax=1,
                ax=axes[1], linewidths=1, linecolor="white",
                annot_kws={"fontsize": 12, "fontweight": "bold"})
    axes[1].set_title("Purple/Pink Rate: Model × Company", fontweight="bold")
    plt.tight_layout(); fig.savefig(f"{OUT}/exp2_color_bias.png", dpi=200); plt.close()

    print(f"\nFigures saved to {OUT}/exp2_*.png")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT 3: HUMAN UI DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_experiment_3(survey_csv, answer_key_json):
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: HUMAN UI DETECTION ANALYSIS")
    print("=" * 70)

    responses = pd.read_csv(survey_csv)
    with open(answer_key_json) as f:
        answer_key = {item["survey_id"]: item["true_source"] for item in json.load(f)}

    print(f"Survey responses: {len(responses)}")
    print(f"Answer key entries: {len(answer_key)}")

    # Expected columns: participant_id, image_id, guess (ai/human), confidence (1-5), signals
    # Adjust column names based on your actual survey export

    # Merge ground truth
    if "image_id" in responses.columns:
        responses["true_source"] = responses["image_id"].map(answer_key)

        # Overall accuracy
        responses["correct"] = responses["guess"] == responses["true_source"]
        overall_acc = responses["correct"].mean()
        print(f"\nOverall detection accuracy: {overall_acc:.1%}")
        print(f"  (50% = random chance)")

        # Accuracy for AI vs human
        ai_acc = responses[responses["true_source"]=="ai"]["correct"].mean()
        human_acc = responses[responses["true_source"]=="human"]["correct"].mean()
        print(f"  Accuracy on AI images: {ai_acc:.1%}")
        print(f"  Accuracy on human images: {human_acc:.1%}")

        # Binomial test: is accuracy significantly above chance?
        n_correct = responses["correct"].sum()
        n_total = len(responses)
        binom_p = stats.binom_test(n_correct, n_total, 0.5, alternative="greater")
        print(f"\nBinomial test (accuracy > 50%): p={binom_p:.4f}")

        # Confidence analysis
        if "confidence" in responses.columns:
            conf_correct = responses[responses["correct"]]["confidence"].mean()
            conf_incorrect = responses[~responses["correct"]]["confidence"].mean()
            print(f"\nMean confidence when correct: {conf_correct:.2f}")
            print(f"Mean confidence when incorrect: {conf_incorrect:.2f}")

        # Signal analysis
        if "signals" in responses.columns:
            all_signals = []
            for s in responses[responses["correct"] & (responses["true_source"]=="ai")]["signals"].dropna():
                all_signals.extend([x.strip() for x in str(s).split(",")])
            if all_signals:
                print(f"\nTop signals for correctly identifying AI UIs:")
                for signal, count in Counter(all_signals).most_common(10):
                    print(f"  {signal}: {count}")

        # Figure
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        # Accuracy by source
        accs = pd.DataFrame({"Source": ["AI", "Human", "Overall"],
                             "Accuracy": [ai_acc, human_acc, overall_acc]})
        bars = axes[0].bar(accs["Source"], accs["Accuracy"], color=["#EF4444", "#22C55E", "#2563EB"])
        axes[0].axhline(y=0.5, color="#999", linestyle="--", label="Chance (50%)")
        axes[0].set_ylim(0, 1); axes[0].yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
        axes[0].set_title("Detection Accuracy by Source", fontweight="bold")
        axes[0].legend()

        # Confidence distribution
        if "confidence" in responses.columns:
            responses.groupby("correct")["confidence"].plot.hist(
                ax=axes[1], alpha=0.6, bins=5, legend=True)
            axes[1].set_title("Confidence: Correct vs Incorrect", fontweight="bold")
            axes[1].set_xlabel("Confidence (1-5)")

        plt.tight_layout(); fig.savefig(f"{OUT}/exp3_detection.png", dpi=200); plt.close()

    print(f"\nFigures saved to {OUT}/exp3_*.png")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT 4: MULTI-CONSTRAINT STRESS TEST
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_experiment_4(filepath):
    print("\n" + "=" * 70)
    print("EXPERIMENT 4: MULTI-CONSTRAINT STRESS TEST")
    print("=" * 70)

    df = pd.read_csv(filepath, low_memory=False)
    if "error" in df.columns:
        df = df[df["error"].isna()].copy()
    df["model_short"] = df["model"].map(MODEL_SHORT).fillna(df["model"])

    print(f"Clean rows: {len(df):,}")
    print(f"Models: {sorted(df['model_short'].unique())}")

    # Expected columns depend on your runner, but likely include:
    # model, num_constraints, constraints_applied, emoji_compliant,
    # bullet_compliant, header_compliant, bold_compliant, word_count_compliant, etc.

    constraint_cols = [c for c in df.columns if c.endswith("_compliant") or c.endswith("_compliance")]
    print(f"Constraint columns found: {constraint_cols}")

    if "num_constraints" in df.columns:
        # Compliance decay curve
        decay = df.groupby(["model_short", "num_constraints"])[constraint_cols].mean()
        print("\nCompliance by number of constraints:")
        print(decay.round(3).to_string())

        # Overall compliance (all constraints met)
        if len(constraint_cols) > 0:
            df["all_compliant"] = df[constraint_cols].all(axis=1)
            full_compliance = df.groupby(["model_short", "num_constraints"])["all_compliant"].mean()
            print("\nFull compliance (ALL constraints met):")
            print(full_compliance.unstack().round(3).to_string())

            # Figure: Decay curve
            fig, ax = plt.subplots(figsize=(11, 6))
            pivot = full_compliance.unstack(0)
            for model in pivot.columns:
                ax.plot(pivot.index, pivot[model], "o-", label=model, linewidth=2.5,
                        markersize=8, color=MODEL_COLORS.get(model, "#888"))
            ax.set_xlabel("Number of Simultaneous Constraints")
            ax.set_ylabel("Full Compliance Rate")
            ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
            ax.set_title("Compliance Decay: More Constraints → Lower Compliance", fontweight="bold")
            ax.legend(); plt.tight_layout()
            fig.savefig(f"{OUT}/exp4_decay_curve.png", dpi=200); plt.close()

        # Which constraint breaks first?
        if len(constraint_cols) >= 2:
            print("\nPer-constraint compliance rate (when all 7 applied):")
            max_constraints = df["num_constraints"].max()
            all7 = df[df["num_constraints"] == max_constraints]
            for col in constraint_cols:
                rate = all7[col].mean()
                print(f"  {col}: {rate:.1%}")

            # Figure: Which breaks first
            fig, ax = plt.subplots(figsize=(10, 5))
            rates = {col.replace("_compliant", "").replace("_compliance", ""): all7[col].mean()
                     for col in constraint_cols}
            rates_sorted = dict(sorted(rates.items(), key=lambda x: x[1]))
            colors = ["#EF4444" if v < 0.5 else "#F97316" if v < 0.8 else "#22C55E"
                      for v in rates_sorted.values()]
            ax.barh(list(rates_sorted.keys()), list(rates_sorted.values()), color=colors)
            ax.set_xlim(0, 1.1); ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0))
            ax.set_xlabel("Compliance Rate"); ax.axvline(x=0.5, color="#999", linestyle="--")
            ax.set_title("Which Constraint Breaks First? (All 7 Applied)", fontweight="bold")
            plt.tight_layout(); fig.savefig(f"{OUT}/exp4_constraint_breakdown.png", dpi=200); plt.close()

    else:
        print("\nWARNING: 'num_constraints' column not found.")
        print("Available columns:", list(df.columns))
        print("You may need to adjust column names in this script.")

    print(f"\nFigures saved to {OUT}/exp4_*.png")


# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-DETECT AND RUN ALL
# ═══════════════════════════════════════════════════════════════════════════════

def run_all():
    """Auto-detect CSV files and run appropriate analyses."""
    print("Auto-detecting experiment data files...\n")

    for f in sorted(glob.glob("*.csv")) + sorted(glob.glob("data/*.csv")):
        fl = f.lower()
        if "exp1" in fl or "emoji" in fl:
            analyze_experiment_1(f)
        elif "exp2" in fl or "color" in fl:
            analyze_experiment_2(f)
        elif "exp3" in fl or "survey" in fl or "ui_detection" in fl:
            key_files = glob.glob("*answer_key*") + glob.glob("*DO_NOT_SHARE*")
            if key_files:
                analyze_experiment_3(f, key_files[0])
            else:
                print(f"Found survey data {f} but no answer key. Skipping Exp 3.")
        elif "exp4" in fl or "constraint" in fl or "stress" in fl:
            analyze_experiment_4(f)
        else:
            print(f"Skipping unrecognized file: {f}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Analyze Aesthetic Anchoring experiments")
    parser.add_argument("--experiment", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--input", type=str, help="Input CSV file")
    parser.add_argument("--answer-key", type=str, help="Answer key JSON (Exp 3 only)")
    parser.add_argument("--all", action="store_true", help="Auto-detect and analyze all CSVs")
    args = parser.parse_args()

    if args.all:
        run_all()
    elif args.experiment and args.input:
        if args.experiment == 1:
            analyze_experiment_1(args.input)
        elif args.experiment == 2:
            analyze_experiment_2(args.input)
        elif args.experiment == 3:
            if not args.answer_key:
                print("Experiment 3 requires --answer-key")
                return
            analyze_experiment_3(args.input, args.answer_key)
        elif args.experiment == 4:
            analyze_experiment_4(args.input)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
