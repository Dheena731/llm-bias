# TIST 2027 Journal Package Manifest

## Package Identity

Working title:

> Presentation Priors in Generative Models: A Computational Audit of Surface-Form Defaults

Primary manuscript:

- `paper/tist2027_presentation_priors.tex`

Bibliography sources:

- `paper/haips2026_refs.bib`
- `paper/tist2027_presentation_priors_refs.bib`

Control notes:

- `paper/journal_aesthetic_anchoring_presentation_priors.md`
- `paper/aesthetic_anchoring_claim_audit.md`
- `EXPERIMENT8_PROTOCOL.md`

Source manuscripts:

- `paper/iciss2026_aesthetic_anchoring_v2.tex` for Studies 1-3.
- `paper/iui2027_aesthetic_default_bias.tex` for bounded Study 5.

The journal identity is separate from the ICISS security/compliance draft and the IUI Exp7 checkpoint draft.

## Evidence State

| Evidence block | Current state | Use in paper |
| --- | --- | --- |
| Study 1: Exp1 emoji anchoring | Corrected older text evidence | Main empirical backbone. |
| Study 2: Exp2 color/gradient | Corrected older text evidence | Negative purple/pink result; model-specific gradient persistence. |
| Study 3: Exp4 multi-constraint | Corrected measured-only scoring | Surface-form compliance distinction. |
| Study 4: Exp8 route-labeled text probe | First-pass model-run evidence complete: 480/480 rows | Journal technical extension, route-labeled only. |
| Study 5: Exp7 cross-modal extension | Checkpoint evidence | Secondary feasibility extension only. |
| Text baselines | Small hand-authored baseline layer | Validity support, not final human-vs-model contrast. |
| UI/image baselines | Not complete | Required before strong homogenization claims. |

## Exp8 First-Pass Evidence

Primary data:

- `experiment_data/exp8_post_training_priors_20260601_022210.csv`

Run metadata:

- `run_id`: `exp8_20260601_022210`
- `config_hash`: `b3dd18b8bb4f9863836a8905009630f66e786c1aba0efb8dd923387ca173a7dd`
- Expected rows: `480`
- Observed expected rows: `480`
- Missing expected rows: `0`
- Errored rows after dedupe: `0`

Analysis outputs:

- `analysis_output/exp8/post_training_priors_report.md`
- `analysis_output/exp8/analysis_manifest.json`
- `analysis_output/exp8/matrix_completeness.csv`
- `analysis_output/exp8/stage_condition_summary.csv`
- `analysis_output/exp8/confidence_intervals.csv`
- `analysis_output/exp8/planned_contrasts_fdr.csv`
- `analysis_output/exp8/paired_condition_delta_summary.csv`
- `analysis_output/exp8/cluster_paired_condition_contrasts.csv`
- `analysis_output/exp8/prompt_family_holdout.csv`
- `analysis_output/exp8/length_sensitivity.csv`
- `analysis_output/exp8/missingness_summary.csv`

Current deterministic package check:

```bash
uv run python verify_tist_package.py
```

Latest verifier output:

| Field | Value |
| --- | --- |
| status | `ok` |
| python_version | `3.12.11` |
| git_commit | `6af72bf6bee493c40190f56d1b44617bce3f2f58` |
| csv_sha256 | `90c88bd0741d66cad0a3872bcc967f44f1d4926306feabd751a17597ca1779b2` |
| raw_dir_sha256 | `c99c8b318d45e9a004301a050bfd499eae2a58cfa70b4a0b93d48550899bd742` |
| analysis_manifest_sha256 | `1cc0b61b868d23cc1a8b43070e4080b686063e948a61e57ebabba0719774670a` |

Git note:

The current package files must be added to a commit before an external reviewer can recover this exact package from Git. The verifier records the current `HEAD`, but many package files are still untracked in the working tree.

## Tracked Canonical Package Set

Track the TIST package surface, not every generated file in the workspace.

Package docs and manuscript:

- `paper/README.md`
- `paper/tist2027_presentation_priors.tex`
- `paper/tist2027_presentation_priors_refs.bib`
- `paper/haips2026_refs.bib`
- `paper/tist2027_journal_package_manifest.md`
- `paper/journal_aesthetic_anchoring_presentation_priors.md`
- `paper/aesthetic_anchoring_claim_audit.md`
- `EXPERIMENT8_PROTOCOL.md`

Exp8 code, config, and tests:

- `aesthetic_features.py`
- `experiment8_common.py`
- `experiment8_collect_text.py`
- `analyze_post_training_priors.py`
- `analyze_text_baselines.py`
- `validate_feature_audit_samples.py`
- `verify_tist_package.py`
- `configs/exp8_post_training_priors.json`
- `configs/text_baselines.json`
- `configs/feature_validity_audit_samples.json`
- `tests/__init__.py`
- `tests/test_exp8_task_matrix.py`
- `tests/test_exp8_fake_collectors.py`
- `tests/test_exp8_analysis.py`
- `tests/test_baseline_feature_audit.py`

Canonical outputs:

- `experiment_data/exp8_post_training_priors_20260601_022210.csv`
- `experiment_artifacts/exp8_text/raw/b3dd18b8bb4f/exp8_20260601_022210/`
- `analysis_output/exp8/`
- `analysis_output/baselines/text_baseline_rows.csv`
- `analysis_output/baselines/text_baseline_summary.csv`

Dependency and package support:

- `.env.example`
- `.gitignore`
- `pyproject.toml`
- `requirements.txt`
- `uv.lock`

Exclude stale or non-TIST generated material unless a separate package intentionally needs it:

- `experiment_data/exp8_post_training_priors_20260601_001606.csv`
- `experiment_data/exp8_post_training_priors_20260601_002652.csv`
- `experiment_artifacts/exp8_text/raw/6e5e2e0fa956/`
- `experiment_artifacts/exp8_text/raw/b3dd18b8bb4f/exp8_20260601_002652/`
- `experiment_artifacts/exp8_text/raw/d1a27ec3ad12/`
- `experiment_artifacts/exp7_images/`
- `experiment_artifacts/exp7_text/`
- `experiment_artifacts/exp7_ui/`
- `artifact/aisec2026_anonymous/`

Safe Exp8 claim:

> In a complete 480-row first pass, route-labeled presentation-prior features are measurable and condition-sensitive. Neutral prompts produce high format-default and Markdown rates; explicit plain-output instructions strongly suppress Markdown and emoji. These are route-labeled OpenRouter results, not causal training-stage evidence.

Unsafe Exp8 claim:

> RLHF or post-training causes the observed defaults.

## Baseline and Validity Layer

Current text baseline outputs:

- `analysis_output/baselines/text_baseline_rows.csv`
- `analysis_output/baselines/text_baseline_summary.csv`

Current feature-audit command:

```bash
uv run python validate_feature_audit_samples.py
```

Current limitation:

The hand-authored text baseline layer is small and should be described as a validity check. It is not yet strong enough for broad human-vs-model baseline claims.

## Reproduction Commands

Core verification:

```bash
uv run python experiment8_collect_text.py --dry-run
uv run python analyze_post_training_priors.py --input experiment_data/exp8_post_training_priors_20260601_022210.csv --expected-runs-per-cell 2
uv run python analyze_text_baselines.py
uv run python validate_feature_audit_samples.py
tectonic --outdir /tmp/tist2027_build paper/tist2027_presentation_priors.tex
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_exp8_task_matrix.py tests/test_exp8_fake_collectors.py tests/test_exp8_analysis.py tests/test_baseline_feature_audit.py
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover
uv run python verify_tist_package.py
```

Cost-controlled rerun:

```bash
uv run python experiment8_collect_text.py --full --confirm-full --runs-per-cell 2 --max-workers 4
```

Full Exp8 run:

```bash
uv run python experiment8_collect_text.py --full --confirm-full --max-workers 6
```

Use exact input CSVs for paper outputs. Do not use `--exp8-all` for package artifacts unless stale smoke and partial CSVs are isolated.

## Manuscript Claims

Keep:

- Presentation priors are measurable surface-form tendencies.
- Aesthetic anchoring is default activation plus an override curve.
- Topic, model, and intervention condition matter; route labels are reported as provenance metadata, not causal stage evidence.
- Suppression is partial but often strong for explicit plain-output conditions.
- Current color evidence is negative or blue-dominant, not purple-centered.
- Exp7 is a bounded cross-modal feasibility extension.

Avoid:

- RLHF/post-training causality without verified base-model routes.
- Broad purple-bias framing.
- Generated UI/image homogenization claims without balanced baselines.
- Merging ICISS, IUI, and TIST identities.

## Submission Readiness Gates

Ready now:

- Separate TIST-style manuscript draft exists.
- Exp8 first pass is complete and self-auditing.
- Required Exp8 analysis files exist, including prompt-family-clustered paired condition contrasts.
- Text baseline and manual audit scripts run.
- Manual TIST bibliography has been converted to ACM BibTeX sources.
- Tectonic compiles the ACM draft to a 10-page PDF; remaining warnings are one underfull page-break box and a Tectonic BibTeX rerun notice, not missing references.
- Claim boundaries are explicit.

Still required before a journal submission:

- Polish the remaining underfull page-break warning for the final PDF, if venue formatting review requires it.
- Verify final bibliography metadata against publisher pages before external submission.
- Add or cite final figures/tables generated from the artifact pipeline.
- Expand UI/design-system and image baselines before homogenization claims.
- Add model-based route-stage inference if route-stage claims are strengthened; current clustered contrasts support condition-level robustness screening, not route-stage causality.
- Increase Exp8 repeats or clearly label the current result as first-pass evidence.
- Run a final anonymity and local-path check before external review.
