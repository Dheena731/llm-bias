# Presentation Priors in Generative Models

## Journal Identity

This is the journal synthesis package for the aesthetic anchoring work. It should remain distinct from:

- `iciss2026_aesthetic_anchoring_v2.tex`, which is the security/compliance-oriented empirical source for the older text experiments.
- `iui2027_aesthetic_default_bias.tex`, which is the Exp7 cross-modal checkpoint manuscript.

The journal claim is not that models prefer a single visual trope. The claim is that generative systems exhibit measurable presentation priors: surface-form choices that appear under underspecified prompts, vary by topic/model/route label, and respond differently to suppression or polish instructions.

## Relationship To Prior Versions

| Artifact | Role in journal package | Boundary |
| --- | --- | --- |
| ICISS aesthetic anchoring draft | Source for journal Studies 1-3 | Security/compliance is an application domain, not the journal's central identity. |
| IUI Exp7 aesthetic defaults draft | Source for Study 5 cross-modal feasibility evidence | Keep as checkpoint extension until repeated cells and UI/image baselines are stronger. |
| Exp8 OpenRouter route-labeled probe | Journal-only technical extension | Current matrix is route-labeled instruction/chat evidence, not base-vs-instruct causal proof. |

Repository experiment numbering maps to the journal as follows:

| Repository handle | Journal study |
| --- | --- |
| Exp1 emoji persistence | Study 1: topic-conditioned emoji defaults and suppression |
| Exp2 color/gradient suggestions | Study 2: text palette myth correction and gradient persistence |
| Exp4 multi-constraint formatting | Study 3: measured surface-form compliance |
| Exp8 route-labeled text probe | Study 4: current route-labeled presentation-prior probe |
| Exp7 cross-modal defaults | Study 5: bounded cross-modal feasibility extension |

Canonical term: use **presentation priors** for the general phenomenon. Use **aesthetic anchoring** as a memorable shorthand after defining it. Avoid "post-training" in the title or thesis until base-model evidence exists.

## Abstract Draft

Generative models do more than answer prompts; they also choose presentation forms when users leave style underspecified. We call this behavior aesthetic anchoring: topic-conditioned presentation priors across text, UI code, and image artifacts, plus route-labeled text priors in Experiment 8. This paper synthesizes controlled text experiments with a new route-labeled probe and a bounded cross-modal extension. In older text experiments, emoji use is strongly topic-conditioned and mostly suppressed by the first explicit no-emoji instruction; text color-suggestion tasks show negative or blue-dominant results rather than broad color-preference evidence centered on purple/pink; and measured surface-format constraints behave differently from semantic instruction-following benchmarks. Experiment 8 extends the analysis by measuring Markdown, emoji, decorative symbols, stock-polish phrases, and length inflation across current OpenRouter instruction/chat route labels. Exp7 provides checkpoint evidence that similar measurement can be applied to generated UI and image artifacts, but those claims remain bounded until balanced baselines are added. We argue that presentation priors are a distinct evaluation target: not always harmful, not reducible to instruction failure, and not causally attributable to post-training without verified base-model evidence.

## Paper Spine

1. Introduction: define aesthetic anchoring as presentation-prior bias, not a color-trope paper or universal instruction failure.
2. Definitions: presentation prior, aesthetic anchoring, surface-form compliance, and prior-plus-override curve.
3. Related work: instruction following, output-format bias, post-training side effects, generated UI, text-to-image bias, and creative-output convergence.
4. Study 1: old Exp1 emoji anchoring across topics and suppression levels.
5. Study 2: old Exp2 color/gradient results, with purple framed as a negative or limited finding.
6. Study 3: old Exp4 measured multi-constraint surface-form compliance.
7. Study 4: Exp8 route-labeled presentation-prior probe.
8. Study 5: Exp7 cross-modal extension, explicitly checkpoint-bounded.
9. Baselines and validity: hand-authored text baselines now; do not make stronger cross-modal similarity claims until balanced baselines are added.
10. Discussion and limitations: defaults can be useful conventions, route labels are not causal proof, and feature extractors require validation.

For an ACM TIST-style journal draft, expand this spine into: Abstract; Introduction; Definitions and Problem Formulation; Related Work; Study Overview and Common Method; Studies 1-5; Baselines, Measurement Validity, and Reviewer-Robustness; Discussion; Limitations, Ethics, Artifact Availability, and AI Disclosure; Conclusion.

## Study Mapping

| Study | Source | Paper role | Claim boundary |
| --- | --- | --- | --- |
| Exp1 emoji persistence | ICISS anchoring draft and `analyze_results.py` outputs | Main empirical backbone | Topic-conditioned default activation; first suppression signal carries most override effect. |
| Exp2 color/gradient | ICISS anchoring draft and corrected outputs | Negative myth correction | Text palette prompts do not support broad purple/pink preference; gradient persistence is model-specific. |
| Exp4 multi-constraint | ICISS anchoring draft and measured-only scorer | Surface-form compliance evidence | Do not claim contradiction of semantic instruction-following benchmarks. |
| Exp8 route-labeled probe | `EXPERIMENT8_PROTOCOL.md`, collector, and new analysis outputs | New technical contribution | Current OpenRouter matrix does not include base candidates; use `route_stage_label`. |
| Exp7 cross-modal defaults | IUI draft and `analysis_output/exp7` | Bounded extension | Checkpoint evidence only until repeated cells and baselines are stronger. |

## Required Result Slots

Exp8 must provide:

- `stage_condition_summary.csv`
- `confidence_intervals.csv`
- `planned_contrasts_fdr.csv`
- `paired_condition_delta_summary.csv`
- `cluster_paired_condition_contrasts.csv`
- `prompt_family_holdout.csv`
- `length_sensitivity.csv`
- `missingness_summary.csv`
- `matrix_completeness.csv`
- `analysis_manifest.json`
- `post_training_priors_report.md`

Text baselines must provide:

- `analysis_output/baselines/text_baseline_rows.csv`
- `analysis_output/baselines/text_baseline_summary.csv`

## Claims To Keep

- Presentation priors are measurable and vary by prompt family, model, route label, and intervention condition.
- Aesthetic anchoring is default activation plus an override curve, not necessarily instruction-following failure.
- The current color evidence is blue-dominant or negative for purple, depending on modality and task.
- Exp7 is useful as a cross-modal measurement demonstration, not yet the journal-grade core.

## Claims To Avoid

- Do not make RLHF/post-training causal attributions unless base-model evidence and route provenance are verified.
- Keep color findings negative, blue-dominant, or task-bounded rather than using broad color-bias framing.
- Keep cross-modal similarity language bounded until human or design-system baselines are analyzed.
- Do not merge this journal synthesis with the ICISS or IUI paper identities.

## Current Implementation Hooks

Run these before promoting Exp8 into the manuscript:

```bash
uv run python experiment8_collect_text.py --dry-run
uv run python experiment8_collect_text.py --smoke --max-workers 1
uv run python analyze_post_training_priors.py --input experiment_data/exp8_post_training_priors_TIMESTAMP.csv --expected-runs-per-cell 2
uv run python analyze_text_baselines.py
uv run python validate_feature_audit_samples.py
```

For a cost-controlled OpenRouter route-labeled pass, run:

```bash
uv run python experiment8_collect_text.py --full --confirm-full --runs-per-cell 2 --max-workers 4
```

For base-vs-instruct claims, add a separate HF/local collector for base routes before strengthening any route-provenance account.
