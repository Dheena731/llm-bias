# TIST External Review Checklist

This checklist is for a human review pass over the anonymous TIST package. It is
kept outside the exported archive so the archive SHA remains stable.

## Snapshot To Review

- Manuscript: `paper/tist2027_presentation_priors.tex`
- Export directory: `artifact/tist2027_external_review/`
- Export archive: `artifact/tist2027_external_review.zip`
- Archive SHA-256: `24e473d3f4c5e56f58143974e9de97dace0b84f5c4aefff6a7bbba7bca3e2c54`
- Canonical Exp8 CSV: `experiment_data/exp8_post_training_priors_20260601_022210.csv`
- Canonical Exp8 rows: `480`
- Live paid/API collection required for review: no

## Reviewer Priorities

1. Check whether the manuscript thesis is clear:
   presentation priors are measurable surface-form defaults, not a universal
   instruction-following failure and not a one-color trope.
2. Check whether Studies 1-3, Study 4, and Study 5 read as one journal package
   rather than stitched conference drafts.
3. Check whether the Study 4 Exp8 claims stay route-labeled and first-pass,
   without implying base-vs-instruct or RLHF/post-training causality.
4. Check whether Study 5 and the baseline section clearly label UI/image results
   as bounded feature-calibration evidence, not broad homogenization evidence.
5. Check whether the abstract, introduction, limitations, and conclusion all
   use the same claim boundary.

## Must-Preserve Claim Boundaries

Keep:

- Presentation priors are measurable and condition-sensitive.
- Topic, model, intervention condition, and reported route labels matter.
- Explicit plain-output conditions strongly suppress Markdown and emoji in the
  current Exp8 first pass.
- Study 2 is a negative or limited purple/pink finding.
- Study 5 is a bounded cross-modal extension with small reference baselines.

Do not claim:

- RLHF or post-training causes the observed defaults.
- Route labels prove training stage or base-vs-instruct behavior.
- Models broadly prefer purple/pink aesthetics.
- Generated UI or image artifacts are unusually homogeneous relative to human
  or design-system baselines.
- Exp8 is a full-cost repeated run beyond the current 480-row first pass.

## Manuscript Proof Pass

Review these sections in order:

- Abstract: verify that the contribution and limitations are visible without
  relying on later caveats.
- Introduction: verify that "presentation priors" and "aesthetic anchoring" are
  introduced as measurement terms, not moral judgments.
- Study overview tables: verify row counts and boundaries match the package
  manifest.
- Study 1: verify the error-row caveat is prominent enough.
- Study 2: verify the purple/pink result remains negative or bounded.
- Study 3: verify surface-form compliance is not overclaimed against semantic
  instruction-following benchmarks.
- Study 4: verify Exp8 is described as route-labeled first-pass evidence.
- Study 5: verify UI/image claims stay methodological and baseline-limited.
- Limitations: verify all causal, color, cross-modal, and camera-ready limits
  are explicit.
- Artifact availability: verify referenced files exist in the package.

## Reproduction Commands

Run these from the repository root. They should not launch paid/API collection.

```bash
uv run python prepare_tist_review_package.py --verify
uv run python verify_tist_external_review_handoff.py
shasum -a 256 artifact/tist2027_external_review.zip
zipinfo -1 artifact/tist2027_external_review.zip | rg '__pycache__|\\.pyc$|\\.DS_Store'
tectonic --outdir /tmp/tist2027_build paper/tist2027_presentation_priors.tex
uv run python verify_tist_package.py --pdf /tmp/tist2027_build/tist2027_presentation_priors.pdf --mode review
uv run python verify_tist_bibliography.py
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_exp8_task_matrix.py tests/test_exp8_fake_collectors.py tests/test_exp8_analysis.py tests/test_baseline_feature_audit.py tests/test_cross_modal_baselines.py tests/test_tist_artifact_tables.py tests/test_tist_review_package.py tests/test_tist_package_verifier.py tests/test_tist_bibliography_verifier.py tests/test_tist_external_review_handoff.py
```

Expected current results:

- Package verifier status: `ok`
- Bibliography verifier status: `ok`
- Focused TIST test slice: `99 passed`
- Archive SHA-256:
  `24e473d3f4c5e56f58143974e9de97dace0b84f5c4aefff6a7bbba7bca3e2c54`
- Archive hygiene grep: no matches; `rg` exit status `1` is expected when
  there are no matches.

## Known Non-Blockers

- The anonymous review manuscript intentionally uses ACM `review` and
  `anonymous` metadata.
- The ACM reference block is intentionally suppressed in review mode.
- CCS concepts and final ACM metadata are camera-ready tasks.
- The current fixed-rerun Tectonic build has no overfull/underfull box warnings
  and no missing-reference warnings; remaining log noise is ACM review-mode
  metadata notices and font-request messages.
- UI/image baseline evidence is calibration-only at this stage.

## Reviewer Output Requested

Ask reviewers to return:

- Any sentence that appears to overclaim causality, color preference, or
  cross-modal similarity.
- Any place where the paper reads like a stitched conference draft rather than a
  journal synthesis.
- Any table, artifact path, or row count that appears inconsistent.
- Any reproduction command that fails on a clean checkout.
- Any bibliography entry whose metadata should be checked against publisher
  pages before submission.

## Decision After Review

If review finds only wording and proofing issues, patch the manuscript and rerun
the PDF-aware review verifier. If review finds evidence gaps, decide between
keeping the current first-pass package bounded or investing in one of these
larger upgrades:

- More Exp8 repeats.
- Verified base-route or HF/local provenance collection.
- Balanced human text, UI/design-system, or image baselines.
- Camera-ready ACM metadata and final author fields.
