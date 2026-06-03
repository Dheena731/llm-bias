# TIST External Review Package Handoff

This note tracks the local handoff state for the anonymous TIST review package.
It is intentionally outside the exported package, because embedding the archive
hash inside exported files would make the archive hash self-referential.

## Current Snapshot

- Exported package source commit: `4c8dec8 Refresh TIST proof metadata`
- Handoff note commit: tracked separately after export; this file is not in the archive
- Export directory: `artifact/tist2027_external_review/`
- Export archive: `artifact/tist2027_external_review.zip`
- Archive SHA-256: `45ac8ff059821c6ce6724910d1faccecb303681710c6610924bb147b116d61cc`
- Package scan status: `ok`
- Package scan text files: `548`
- Canonical Exp8 rows: `480`
- Paid/API collection after this snapshot: none
- Human review checklist: `TIST_EXTERNAL_REVIEW_CHECKLIST.md`

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

The current fixed-rerun Tectonic build writes the PDF successfully with no
overfull or underfull box warnings and no missing-reference warnings. Remaining
log noise is limited to ACM review-mode metadata notices and font-request
messages; the PDF-aware package verifier remains the review gate.

## Claim Boundary

Use the package as a bounded review artifact:

- Exp8 is route-labeled first-pass evidence, not causal route-provenance proof.
- RLHF/post-training causal claims remain out of scope.
- Purple/pink results remain negative or limited, not a broad color-bias claim.
- Cross-modal similarity claims remain bounded until balanced baselines expand.
- Camera-ready ACM metadata is intentionally not ready in the anonymous package.
