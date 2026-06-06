# Experiment 8 Route-Labeled Presentation Priors Report

Clean analyzed rows: 480
Errored rows after dedupe: 0
Input files: experiment_data/exp8_post_training_priors_20260601_022210.csv
Run IDs: exp8_20260601_022210
Config hashes: b3dd18b8bb4f9863836a8905009630f66e786c1aba0efb8dd923387ca173a7dd
Matrix completeness status: complete
Expected matrix rows: 480
Observed expected rows: 480
Missing expected rows: 0
Unexpected artifact IDs: 0

## Stage Summary

| Stage label | n | Format default rate | Polish default rate | Emoji rate | Markdown rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat_or_instruct | 120 | 40.0% | 35.8% | 10.8% | 40.0% |
| instruct_candidate | 360 | 34.7% | 52.2% | 3.1% | 33.3% |

## Condition Summary

| Condition | n | Format default rate | Polish default rate | Emoji rate | Markdown rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| diverse_domain_specific | 96 | 64.6% | 74.0% | 5.2% | 61.5% |
| neutral | 96 | 80.2% | 72.9% | 19.8% | 78.1% |
| no_emoji | 96 | 27.1% | 22.9% | 0.0% | 27.1% |
| plain_no_markdown | 96 | 2.1% | 25.0% | 0.0% | 2.1% |
| polished_but_plain | 96 | 6.2% | 45.8% | 0.0% | 6.2% |

## Claim Boundary

Route labels are provenance metadata, not proof of a training mechanism. Causal claims about RLHF or post-training require verified route provenance.
Clustered condition contrasts pair each condition against neutral within model family, route label, model, prompt family, domain, and run; they resample prompt-family clusters and include route-level consistency diagnostics.

Required companion outputs: `confidence_intervals.csv`, `planned_contrasts_fdr.csv`, `paired_condition_delta_summary.csv`, `cluster_paired_condition_contrasts.csv`, `prompt_family_holdout.csv`, `length_sensitivity.csv`, `missingness_summary.csv`, `matrix_completeness.csv`, and `analysis_manifest.json`.
