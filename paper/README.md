# Paper Package Notes

## TIST Journal Package

Primary journal draft:

- `tist2027_presentation_priors.tex`

Journal support files:

- `journal_aesthetic_anchoring_presentation_priors.md`
- `tist2027_journal_package_manifest.md`
- `aesthetic_anchoring_claim_audit.md`

Use these files as the ACM TIST-oriented package. Keep them separate from the ICISS security/compliance framing and the IUI/Exp7 checkpoint framing. The journal spine and package manifest control claim scope; the `.tex` file is the current TIST-style manuscript draft.

Journal package evidence gate:

```bash
uv run python experiment8_collect_text.py --dry-run
uv run python analyze_post_training_priors.py --input experiment_data/exp8_post_training_priors_20260601_022210.csv --expected-runs-per-cell 2
uv run python analyze_text_baselines.py
uv run python analyze_cross_modal_baselines.py
uv run python validate_feature_audit_samples.py
uv run python verify_tist_bibliography.py --write-audit
uv run python generate_tist_artifact_tables.py
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_exp8_task_matrix.py tests/test_exp8_fake_collectors.py tests/test_exp8_analysis.py tests/test_baseline_feature_audit.py tests/test_cross_modal_baselines.py tests/test_tist_artifact_tables.py tests/test_tist_package_verifier.py tests/test_tist_bibliography_verifier.py
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover
uv run python verify_tist_package.py
```

The current Exp8 first-pass evidence is `480/480` clean rows with `0` missing expected rows in `analysis_output/exp8/analysis_manifest.json`. Analysis from the fixed CSV is reproducible; exact live collection reruns are not deterministic because they use current API routes. The analysis manifest records the canonical CSV hash. The manuscript's Exp8 tables are generated from the checked analysis outputs into `analysis_output/tist_package/`; rerun `generate_tist_artifact_tables.py` after changing any source analysis CSV or manifest. The package verifier checks those table hashes and byte-compares them against a temporary regeneration.

Compile target for journal draft:

```bash
tectonic --outdir /tmp/tist2027_build paper/tist2027_presentation_priors.tex
uv run python verify_tist_package.py --pdf /tmp/tist2027_build/tist2027_presentation_priors.pdf
```

This requires ACM's `acmart.cls`. The verifier's default run checks the source package; the `--pdf` form additionally scans the compiled PDF bytes for author metadata, local identifiers, and sensitive-looking tokens.

## ICISS Draft Notes

Primary ICISS draft:

- `iciss2026_aesthetic_anchoring_draft.tex`

Required venue format checked on 2026-05-17:

- ICISS 2026 regular papers must be written in English.
- Maximum length is 20 pages.
- Submission format is PDF.
- Paper format is Springer LNCS.
- Review is double-blind.
- Submission requires declarations for conflicts of interest, IRB/responsible disclosure/privacy, and Gen-AI use.

Compile target:

```bash
pdflatex iciss2026_aesthetic_anchoring_draft.tex
```

The local machine must have a TeX distribution and `llncs.cls` installed. If `llncs.cls` is missing, download the official Springer LNCS author package and place `llncs.cls` where TeX can find it or in this `paper/` directory.

Before submission:

- Replace the placeholder bibliography with verified references.
- Check final page count under LNCS.
- Keep author names, affiliations, acknowledgements, local paths, and identifying repository links out of the double-blind PDF.
- Confirm that the figures referenced from `../analysis_output/` are the regenerated canonical figures.
- Submit the declarations through the venue system rather than adding identifying acknowledgements to the anonymous manuscript.
