# Experiment 8 Protocol: Route-Labeled Presentation Priors

## Purpose

Experiment 8 is the technical bridge between the older Aesthetic Anchoring study and the newer cross-modal Exp7 work. In the current OpenRouter-only configuration, it measures route-labeled presentation priors across current instruction/chat routes. Base-model comparisons require a separate HF/local collector because the originally planned base route IDs are not available through the current OpenRouter chat-completions path.

The target claim is deliberately narrow:

> Generative models exhibit measurable presentation priors under underspecified prompts. These priors can be compared across model family, route label, prompt family, and intervention condition.

This experiment must not claim that RLHF caused a behavior unless the compared routes have verified base/instruct/chat provenance. The current OpenRouter matrix should be reported as `route_stage_label`, not causal training stage.

## Why This Exists

The older Aesthetic Anchoring paper has stronger text evidence than Exp7: repeated trials, cleaner suppression results, and a useful surface-form-versus-semantic distinction. Exp7 adds cross-modal scope, but its current evidence is a checkpoint. Experiment 8 makes the journal version more technical by directly testing route-labeled presentation priors in text first. It should be treated as causal-adjacent evidence until verified base-model routes exist.

## Research Questions

1. Do current instruction/chat routes produce Markdown, emoji, headings, bullets, stock-polish phrases, and length inflation under underspecified prompts?
2. Are these defaults topic-conditioned, as in the older emoji experiment?
3. Do anti-default and plain-output conditions suppress defaults equally across route stages?
4. Are diversity or "polished" prompts confounded with formatting defaults?
5. Which feature classes are stage-sensitive versus prompt-family-sensitive?

## Planned Matrix

Default OpenRouter full matrix:

```text
4 routes x 12 prompt families x 5 conditions x 10 repeats = 2,400 outputs
```

Smoke matrix:

```text
1 route x 1 prompt family x 5 conditions x 1 repeat = 5 outputs
```

The route list is intentionally configurable because OpenRouter availability changes. The 2026-06-01 OpenRouter route audit removed unavailable base-candidate routes and records exact-ID provenance in `configs/exp8_post_training_priors.json`.

## Conditions

1. `neutral`: no style instruction.
2. `no_emoji`: asks for no emoji only.
3. `plain_no_markdown`: asks for plain prose with no Markdown, bullets, headings, or emoji.
4. `diverse_domain_specific`: asks for non-generic, domain-specific output.
5. `polished_but_plain`: asks for polished writing while forbidding Markdown, bullets, headings, and emoji. This intentionally tests conflict between polish and plainness.

## Primary Features

Text features use `aesthetic_features.extract_text_features`:

- `has_emoji`
- `has_markdown`
- `heading_lines`
- `bullet_lines`
- `numbered_lines`
- `has_stock_phrase`
- `word_count`
- `exclamation_count`
- `decorative_symbol_count`

Derived indicators:

- `format_default`: emoji OR Markdown OR decorative symbols.
- `polish_default`: stock phrase OR exclamation OR word count above neutral-family median.

## Required Analysis Before Journal Use

1. Wilson confidence intervals for binary feature rates.
2. Stage-condition tables by model family.
3. Prompt-family-held-out robustness.
4. Sensitivity analysis excluding length-derived features.
5. FDR correction across feature tests.
6. If base routes are added through HF/local collection, base-vs-instruct route contrasts.
7. If statsmodels is added later: mixed-effects logistic regression with prompt family as a random effect.

## Commands

Dry run:

```bash
uv run python experiment8_collect_text.py --dry-run
```

Smoke run:

```bash
uv run python experiment8_collect_text.py --smoke
```

Cost-controlled first pass:

```bash
uv run python experiment8_collect_text.py --full --confirm-full --runs-per-cell 2 --max-workers 4
```

Full run:

```bash
uv run python experiment8_collect_text.py --full --confirm-full --max-workers 6
```

If any route still has `stage_provenance=verify_before_full_run`, full collection exits before API calls. Either verify and update route provenance in the config, or pass `--allow-unverified-routes` and keep all paper language bounded to `route_stage_label`.

Base-model extension:

```text
The OpenRouter chat-completions runner does not currently provide valid base routes for
meta-llama/Llama-3.1-8B or Qwen/Qwen2.5-7B. Add a separate HF/local collector before
making base-vs-instruct or post-training mechanism claims.
```

Analysis:

```bash
uv run python analyze_post_training_priors.py --input experiment_data/exp8_post_training_priors_TIMESTAMP.csv --expected-runs-per-cell 2
```

Use exact input CSVs for journal-package outputs. `--exp8-all` is for exploratory local checks only because it can mix smoke, partial, and full-run CSVs.

## Output Locations

```text
experiment_data/exp8_post_training_priors_TIMESTAMP.csv
experiment_artifacts/exp8_text/raw/
analysis_output/exp8/
```

Required analysis files:

```text
analysis_output/exp8/stage_condition_summary.csv
analysis_output/exp8/confidence_intervals.csv
analysis_output/exp8/planned_contrasts_fdr.csv
analysis_output/exp8/paired_condition_delta_summary.csv
analysis_output/exp8/prompt_family_holdout.csv
analysis_output/exp8/length_sensitivity.csv
analysis_output/exp8/missingness_summary.csv
analysis_output/exp8/matrix_completeness.csv
analysis_output/exp8/analysis_manifest.json
analysis_output/exp8/post_training_priors_report.md
```

`analysis_manifest.json` and `matrix_completeness.csv` are acceptance-gate artifacts. A cost-controlled first pass should report `480/480 observed, 0 missing`; a full 10-repeat run should report `2,400/2,400 observed, 0 missing`.

Text baseline outputs:

```bash
uv run python analyze_text_baselines.py
uv run python analyze_cross_modal_baselines.py
uv run python validate_feature_audit_samples.py
```

## Publication Boundary

For the journal paper, Exp8 should be the causal-adjacent technical experiment. The older Aesthetic Anchoring data remains the robust empirical backbone. Exp7 should be described as cross-modal extension evidence until it is scaled with repeated cells and balanced image routes.
