# Detector Validation: Annotation Guidelines

You will label 300 short model outputs for four features. Your labels are used to measure how accurately our
automatic detectors identify these features. They feed the precision, recall and agreement numbers in the paper.

## Files

- `items.csv`: one output per row (`item_id`, `text`). Open it in a spreadsheet or text editor and read the raw text exactly as written.
- `labels_annotator_A.csv` / `labels_annotator_B.csv`: fill in **your** sheet only, 0 or 1 per feature. The `notes` column is optional.
- `_key/`: **do not open.** It contains the detector outputs and the model names. Seeing them would bias your labels.

## Rules

1. Label independently. Do not discuss items with the other annotator until both sheets are complete.
2. Judge the raw text. Do not render Markdown. `**bold**` counts as bold formatting even though you see asterisks.
3. Every cell must be `0` or `1`. If you are unsure, choose the more likely label and write a note.
4. Expect about 2–3 hours. Take breaks; consistency matters more than speed.

## Features

### `markdown`: Markdown formatting

Label **1** if the text contains Markdown syntax that a Markdown renderer would change:
- headings (lines starting with `#`);
- bullet list lines (starting with `-`, `*` or `+` followed by a space) or numbered list lines (`1.`, `2)`);
- bold or italic markers (`**text**`, `*text*`, `__text__`);
- inline code (`` `text` ``) or code blocks;
- Markdown links (`[text](url)`) or tables (`| a | b |`).

A single list line or a single bold phrase is enough. Label **0** for plain paragraphs, even if they are long or
use line breaks. A hyphen used as a dash inside a sentence ("fast - and free") is not a list.

### `emoji`: emoji characters

Label **1** if the text contains at least one pictographic emoji (for example 😀 🚀 ✨ ❤️ ✅ 🎉 📅). Label **0** if it
contains none. Check marks, arrows, stars and bullets drawn as plain symbols (✓ → ★ •) are **not** emoji; label them
under `decorative`.

### `decorative`: decorative symbols

Label **1** if the text uses non-emoji symbols decoratively: ✓ ✔ ✗ ★ ☆ → ← • ▪ ◆ ■ and similar. Ordinary
punctuation, currency signs and math symbols are not decorative. A symbol used as a list bullet (•) counts.

### `polish`: promotional polish

Label **1** if the text reads as promotional or hype-style copy: enthusiastic exclamation marks ("We're thrilled!"),
or stock marketing language ("seamless", "elevate your experience", "unlock", "next-level", "delightful"). Label
**0** for neutral, informational or instructional text, even if it is well written. A single exclamation mark
used for a warning ("Do not share your password!") is **not** promotional; use your judgement and add a note.

## When you are done

Save your sheet in place. When both sheets are complete, run:

```bash
uv run python score_annotation.py
```

This writes `analysis_output/annotation/detector_validation.csv`: inter-annotator kappa, detector-versus-human
kappa, and weighted precision, recall and F1 for each feature. Then resolve the disagreements together, record the
adjudicated label in both sheets (note "adjudicated"), and rerun the script.
