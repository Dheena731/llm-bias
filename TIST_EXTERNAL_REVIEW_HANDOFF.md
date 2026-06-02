# TIST External Review Package Handoff

This note tracks the local handoff state for the anonymous TIST review package.
It is intentionally outside the exported package, because embedding the archive
hash inside exported files would make the archive hash self-referential.

## Current Snapshot

- Exported package source commit: `acb2dbb Update TIST package scan count`
- Handoff note commit: tracked separately after export; this file is not in the archive
- Export directory: `artifact/tist2027_external_review/`
- Export archive: `artifact/tist2027_external_review.zip`
- Archive SHA-256: `8d89c04e8d07690050239e446cee6a6e9014f84b6c7648376aa48d0be8604d51`
- Package scan status: `ok`
- Package scan text files: `548`
- Canonical Exp8 rows: `480`
- Paid/API collection after this snapshot: none

The export directory and zip are generated artifacts and are ignored by git.
Do not force-add them unless the repository policy changes.

## Regenerate

```bash
uv run python prepare_tist_review_package.py --verify
shasum -a 256 artifact/tist2027_external_review.zip
zipinfo -1 artifact/tist2027_external_review.zip | rg '__pycache__|\\.pyc$|\\.DS_Store'
```

The final `zipinfo` command should return no matches. Because `rg` exits with
status `1` when there are no matches, that empty result is the expected clean
archive-hygiene outcome.

## PDF Gate

```bash
tectonic --outdir /tmp/tist2027_build paper/tist2027_presentation_priors.tex
uv run python verify_tist_package.py --pdf /tmp/tist2027_build/tist2027_presentation_priors.pdf --mode review
```

The current Tectonic build writes the PDF successfully but still emits the known
BibTeX rerun notice. Treat that as a formatting-review item, not a package
verification failure, while the verifier remains `ok`.

## Claim Boundary

Use the package as a bounded review artifact:

- Exp8 is route-labeled first-pass evidence, not causal route-provenance proof.
- RLHF/post-training causal claims remain out of scope.
- Purple/pink results remain negative or limited, not a broad color-bias claim.
- Cross-modal similarity claims remain bounded until balanced baselines expand.
- Camera-ready ACM metadata is intentionally not ready in the anonymous package.
