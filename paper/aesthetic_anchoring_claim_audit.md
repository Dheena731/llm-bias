# Aesthetic Anchoring Claim Audit

## Bottom Line

The older Aesthetic Anchoring experiments are useful and should not be discarded. They are the strongest empirical backbone currently in the repo because they contain repeated runs, corrected row accounting, and a clearer surface-form compliance task than Exp7.

The journal paper should use the older experiments as the main text evidence, then use Exp7 as a cross-modal extension and Exp8 as a route-labeled presentation-prior probe. Exp8 should not be framed as mechanism evidence without verified base-route comparisons.

## Claims To Keep

### Topic-conditioned emoji activation is real in the current data

Keep:

> Social-media prompts activate emoji defaults far more than legal, technical, academic, or recipe prompts.

Why keep:

- Based on thousands of rows.
- Repeated runs by topic and model.
- Mechanically detectable feature.
- Strong practical interpretation.

### First suppression instruction carries most of the effect

Keep:

> A single no-emoji instruction removes most emoji behavior; stronger wording adds little after the first suppression signal.

Why keep:

- This is more honest and more interesting than saying defaults are impossible to override.
- It clarifies that the phenomenon is default activation, not universal instruction-following failure.

### Purple/pink text-palette bias is unsupported

Keep, but scope tightly:

> In text-based color-suggestion tasks, broad purple/pink preference is not supported.

Do not generalize to generated UI code or image generation.

### Surface-form constraints differ from semantic constraints

Keep:

> Surface-form instruction following should be evaluated separately from factuality, reasoning, semantic adequacy, and utility.

This is the best conceptual bridge to an AI/LLM evaluation journal.

## Claims To Drop Or Demote

### Strong formality-compliance correlation

Drop as a headline result.

Reason:

- It is based on six topic aggregates.
- Scores are researcher-assigned and ordinal.
- Spearman-only exploratory association is acceptable as appendix/diagnostic evidence.

Replacement:

> Topic family is a strong descriptive factor; a researcher-assigned formality ordering shows an exploratory association but is not treated as a primary result.

### Contradicting He et al. / Curse of Instructions

Drop the contradiction framing.

Replacement:

> Our results suggest that surface-form constraints and semantic constraints should not be pooled. They may show different scaling behavior as constraints accumulate.

### Pink-elephant mechanism

Demote to motivation only.

Reason:

- The data shows output behavior, not cognitive mechanism.
- Small gradient differences should not be used to infer thought-suppression dynamics.

Replacement:

> Prohibitive wording can make forbidden features salient, but our experiments measure only observable output behavior.

### Cross-pipeline causal attribution

Drop causal claims about Western/Chinese alignment, RLHF annotator demographics, or training pipelines unless a new experiment directly tests them.

Replacement:

> Model-specific differences are observed, but capability, routing, generation, and provider differences remain confounds.

## Claims To Fix With Additional Analysis

### Error-rate handling

Required:

- Report Exp1 error rate by model.
- Report Exp1 error rate by model/topic/intensity.
- State whether errors are plausibly random or concentrated.

Implemented in `analyze_results.py`:

- `analysis_output/exp1_error_by_model.csv`
- `analysis_output/exp1_error_by_model_topic_intensity.csv`

### Multi-constraint scoring

Required:

- Never report negative or above-100 compliance.
- Score only measured active constraints.
- Report unmeasured constraints as excluded, not as satisfied.

Current code already uses measured-only scoring through `prepare_experiment_4_dataframe`.

### Purple scope

Required:

- Text color-suggestion task: purple/pink mostly absent.
- UI code task: current Exp7 has occasional purple, but color signal is blue-dominant.
- Image task: current Exp7 has no purple-specific hits under threshold.

## Recommended Paper Architecture

1. Introduction: presentation priors.
2. Definitions: aesthetic anchoring, surface-form compliance, presentation priors.
3. Study 1: old Exp1 emoji topic and suppression evidence.
4. Study 2: old Exp2 color/gradient negative and model-specific result.
5. Study 3: old Exp4 measured multi-constraint surface-form compliance.
6. Study 4: Exp8 route-labeled presentation-prior probe.
7. Study 5: Exp7 cross-modal extension, explicitly labeled as checkpoint evidence unless scaled.
8. Discussion: why surface-form priors are not the same as semantic bias, but still matter for generated artifacts.

## Reviewer-Robust Abstract Claim

Use:

> We show that generative models exhibit measurable presentation priors: topic-conditioned surface forms that appear under underspecified prompts and vary by model, route, and intervention condition. These priors are not always harmful and are often easy to suppress, but they should be measured separately from semantic instruction following.

Avoid:

> Broad color-bias framing from the bounded color result.

Avoid:

> Causal attribution to RLHF/post-training for emoji, color, or style defaults.

Avoid:

> We contradict prior instruction-following benchmarks.
