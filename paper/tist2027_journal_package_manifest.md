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
| UI/image baselines | Small reference layer added | Feature-calibration support only; balanced baselines still required before strong cross-modal similarity claims. |

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
- `analysis_output/exp8/stage_summary.csv`
- `analysis_output/exp8/stage_condition_summary.csv`
- `analysis_output/exp8/condition_summary.csv`
- `analysis_output/exp8/confidence_intervals.csv`
- `analysis_output/exp8/planned_contrasts_fdr.csv`
- `analysis_output/exp8/paired_condition_delta_summary.csv`
- `analysis_output/exp8/cluster_paired_condition_contrasts.csv`
- `analysis_output/exp8/prompt_family_holdout.csv`
- `analysis_output/exp8/length_sensitivity.csv`
- `analysis_output/exp8/missingness_summary.csv`

Generated manuscript table artifacts:

- `analysis_output/tist_package/tist_artifact_manifest.json`
- `analysis_output/tist_package/table_exp8_completeness.tex`
- `analysis_output/tist_package/table_exp8_stage_summary.tex`
- `analysis_output/tist_package/table_exp8_condition_summary.tex`
- `analysis_output/tist_package/table_exp8_ci_contrasts.tex`

Current deterministic package check:

```bash
uv run python verify_tist_package.py --mode review
```

Latest verifier output:

| Field | Value |
| --- | --- |
| status | `ok` |
| python_version | `3.12.11` |
| csv_sha256 | `90c88bd0741d66cad0a3872bcc967f44f1d4926306feabd751a17597ca1779b2` |
| raw_dir_sha256 | `c99c8b318d45e9a004301a050bfd499eae2a58cfa70b4a0b93d48550899bd742` |
| analysis_manifest_sha256 | `c9c25356956b2d034f041922bc4bf2fc9de883ec04b483d05c9c3191135d7ee3` |
| tist_artifact_manifest_sha256 | `e5cc2ed5578090a90adbe09a4c615fa472ea8954f839c883b15d7295e98ff0f7` |
| external_review_scan | review-mode ACM metadata, anonymous manuscript metadata, bibliography metadata, generated table artifacts, generated table inputs, local identifier, stale review metadata, source secret, and compiled-PDF metadata scans `ok` when run with `--pdf /tmp/tist2027_build/tist2027_presentation_priors.pdf --mode review`. |

Latest external-review package export:

| Field | Value |
| --- | --- |
| export_dir | `artifact/tist2027_external_review` |
| archive | `artifact/tist2027_external_review.zip` |
| archive_sha256 | Printed by `prepare_tist_review_package.py --verify`; not embedded here to avoid self-referential archive-hash drift. |
| package_scan | `ok`; 549 text files scanned, no local identifier, source secret, excluded-path, binary-payload, or claim-boundary failures |
| bundle_verifier | `ok` when run from inside the exported package root |

Git note:

The verifier records the current `HEAD` at run time, but the manifest does not pin a repository commit hash because that metadata is process-specific and should not appear in a double-blind review package.

## Tracked Canonical Package Set

Track the TIST package surface, not every generated file in the workspace.

Package docs and manuscript:

- `paper/README.md`
- `paper/tist2027_presentation_priors.tex`
- `paper/tist2027_presentation_priors_refs.bib`
- `paper/haips2026_refs.bib`
- `paper/tist2027_journal_package_manifest.md`
- `paper/tist2027_bibliography_audit.md`
- `paper/journal_aesthetic_anchoring_presentation_priors.md`
- `paper/aesthetic_anchoring_claim_audit.md`
- `EXPERIMENT8_PROTOCOL.md`

Exp8 code, config, and tests:

- `aesthetic_features.py`
- `experiment8_common.py`
- `experiment8_collect_text.py`
- `analyze_post_training_priors.py`
- `analyze_text_baselines.py`
- `analyze_cross_modal_baselines.py`
- `validate_feature_audit_samples.py`
- `generate_tist_artifact_tables.py`
- `prepare_tist_review_package.py`
- `verify_tist_package.py`
- `verify_tist_bibliography.py`
- `configs/exp8_post_training_priors.json`
- `configs/text_baselines.json`
- `configs/ui_image_baselines.json`
- `configs/feature_validity_audit_samples.json`
- `tests/__init__.py`
- `tests/test_exp8_task_matrix.py`
- `tests/test_exp8_fake_collectors.py`
- `tests/test_exp8_analysis.py`
- `tests/test_baseline_feature_audit.py`
- `tests/test_cross_modal_baselines.py`
- `tests/test_tist_artifact_tables.py`
- `tests/test_tist_review_package.py`
- `tests/test_tist_package_verifier.py`
- `tests/test_tist_bibliography_verifier.py`

Canonical outputs:

- `experiment_data/exp8_post_training_priors_20260601_022210.csv`
- `experiment_artifacts/exp8_text/raw/b3dd18b8bb4f/exp8_20260601_022210/`
- `analysis_output/exp8/`
- `analysis_output/tist_package/`
- `analysis_output/baselines/text_baseline_rows.csv`
- `analysis_output/baselines/text_baseline_summary.csv`
- `analysis_output/baselines/ui_baseline_rows.csv`
- `analysis_output/baselines/ui_baseline_summary.csv`
- `analysis_output/baselines/image_baseline_rows.csv`
- `analysis_output/baselines/image_baseline_summary.csv`
- `analysis_output/baselines/cross_modal_homogenization_summary.csv`
- `analysis_output/baselines/generated_images/`

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

> In a complete 480-row first pass, route-labeled presentation-prior features are measurable and condition-sensitive. Neutral prompts produce high format-default and Markdown rates; explicit plain-output instructions strongly suppress Markdown and emoji. These are route-labeled OpenRouter results, not causal evidence about training provenance.

Unsafe Exp8 claim:

> Unsupported causal attribution to RLHF/post-training.

## Baseline and Validity Layer

Current text baseline outputs:

- `analysis_output/baselines/text_baseline_rows.csv`
- `analysis_output/baselines/text_baseline_summary.csv`

Current cross-modal reference baseline outputs:

- `analysis_output/baselines/ui_baseline_rows.csv`
- `analysis_output/baselines/ui_baseline_summary.csv`
- `analysis_output/baselines/image_baseline_rows.csv`
- `analysis_output/baselines/image_baseline_summary.csv`
- `analysis_output/baselines/cross_modal_homogenization_summary.csv`
- `analysis_output/baselines/generated_images/`

Current feature-audit command:

```bash
uv run python validate_feature_audit_samples.py
```

Current limitation:

The hand-authored text baseline layer and the UI/image reference baseline layer are small and should be described as validity checks. They are not yet strong enough for broad human-vs-model or design-system-vs-model baseline claims.

## Reproduction Commands

Core verification:

```bash
uv run python experiment8_collect_text.py --dry-run
uv run python analyze_post_training_priors.py --input experiment_data/exp8_post_training_priors_20260601_022210.csv --expected-runs-per-cell 2
uv run python analyze_text_baselines.py
uv run python analyze_cross_modal_baselines.py
uv run python validate_feature_audit_samples.py
uv run python verify_tist_bibliography.py --write-audit
uv run python generate_tist_artifact_tables.py
uv run python prepare_tist_review_package.py --verify
tectonic --outdir /tmp/tist2027_build paper/tist2027_presentation_priors.tex
uv run python verify_tist_package.py --pdf /tmp/tist2027_build/tist2027_presentation_priors.pdf --mode review
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_exp8_task_matrix.py tests/test_exp8_fake_collectors.py tests/test_exp8_analysis.py tests/test_baseline_feature_audit.py tests/test_cross_modal_baselines.py tests/test_tist_artifact_tables.py tests/test_tist_review_package.py tests/test_tist_package_verifier.py tests/test_tist_bibliography_verifier.py
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover
uv run python verify_tist_package.py --mode review
```

Regenerate `analysis_output/tist_package/` after any change to the Exp8 analysis manifest, stage summary, condition summary, confidence intervals, or planned-contrasts outputs. The package verifier checks the generated table manifest hashes, byte-compares against a temporary regeneration, and fails on stale, incomplete, or manually edited table artifacts. The Exp8 analysis manifest records the canonical CSV hash, and the package verifier checks that hash before accepting the analysis outputs.

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

- Causal attribution to RLHF/post-training without verified base-model routes.
- Broad color-bias framing from the bounded purple/pink result.
- Claims about cross-modal artifact similarity without balanced baselines.
- Merging ICISS, IUI, and TIST identities.

## Submission Readiness Gates

Ready now:

- Separate TIST-style manuscript draft exists.
- Exp8 first pass is complete and self-auditing.
- Required Exp8 analysis files exist, including prompt-family-clustered paired condition contrasts.
- Generated TIST table fragments are built from the checked Exp8 analysis outputs and verified by source/artifact hashes.
- Text, UI reference, image reference, and manual audit scripts run.
- Manual TIST bibliography has been converted to ACM BibTeX sources, first-pass metadata fixes are applied, and cited entries pass the local bibliography metadata audit.
- Tectonic compiles the ACM draft to an 11-page PDF; the current fixed-rerun log has no overfull/underfull box warnings and no missing-reference warnings. Remaining warnings are font-request messages and review-mode ACM metadata notices.
- The package verifier now includes external-review gates for anonymous manuscript metadata, bibliography metadata, local identifiers, stale review metadata, source secret scans, and compiled-PDF metadata scanning; the current compiled PDF passes the `--pdf` scan.
- The external-review exporter writes a self-contained anonymous bundle, records deterministic source provenance in `PACKAGE_PROVENANCE.json`, scans the export tree, writes `MANIFEST.sha256` and `PACKAGE_SCAN.json`, creates a zip archive, and verifies the package from inside the exported root.
- Claim boundaries are explicit.

Camera-ready: not ready:

- Remove the `review` and `anonymous` document-class options.
- Replace anonymous author, affiliation, country, and email placeholders with final submission metadata.
- Add final ACM DOI, copyright/rights statement, volume, number, article, page, year/month, and any venue-required metadata.
- Re-run a future `uv run python verify_tist_package.py --mode camera-ready`; it should fail until those fields are intentionally replaced.

Still required before a journal submission:

- Recheck the TeX warning log during final venue formatting review.
- Recheck bibliography metadata against publisher pages after any reference changes and during final copyediting.
- Do not make broad cross-modal similarity claims until baselines are expanded beyond the current small reference layer.
- Do not strengthen route-label provenance claims until model-based route/provenance analysis is added; current clustered contrasts support condition-level robustness screening, not causal route evidence.
- Increase Exp8 repeats or clearly label the current result as first-pass evidence.
- Re-run the external-review verifier, including `--pdf`, after any final manuscript or PDF-generation change.
