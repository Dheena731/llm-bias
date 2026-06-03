# TIST External Review Worksheet

Use this worksheet for one independent human review pass over the anonymous
TIST package. Return one filled copy per reviewer. Keep this file outside the
exported archive so the archive SHA remains stable.

## Reviewer Metadata

- Reviewer ID:
- Review date:
- Package archive SHA checked against handoff: yes/no
- Reproduction commands attempted: yes/no
- Reproduction environment notes:

## Summary Judgment

Choose one:

- Accept current bounded review package after minor wording/proofing edits.
- Hold external review until listed evidence or reproducibility gaps are fixed.
- Escalate to a larger evidence upgrade before journal review.

One-paragraph rationale:

## Claim-Boundary Review

Mark each item pass/fail and cite exact page, section, or sentence for failures.

| Check | Pass/Fail | Evidence or requested edit |
| --- | --- | --- |
| Exp8 is route-labeled first-pass evidence, not causal route-provenance proof. |  |  |
| RLHF/post-training causality is not claimed. |  |  |
| Purple/pink results remain negative or limited. |  |  |
| Study 5 UI/image claims remain calibration-limited. |  |  |
| No broad generated-artifact homogenization claim appears without stronger baselines. |  |  |
| The abstract, introduction, limitations, and conclusion use consistent boundaries. |  |  |

## Journal Spine Review

| Check | Pass/Fail | Evidence or requested edit |
| --- | --- | --- |
| Studies 1-3 read as empirical foundations, not a pasted conference draft. |  |  |
| Study 4 Exp8 is clearly the route-labeled probe. |  |  |
| Study 5 is framed as bounded cross-modal extension evidence. |  |  |
| Baselines are described as calibration evidence, not definitive population comparisons. |  |  |
| Limitations are concrete enough for a journal reviewer. |  |  |

## Reproducibility Review

| Check | Pass/Fail | Evidence or requested edit |
| --- | --- | --- |
| `prepare_tist_review_package.py --verify --source-commit 494d4e3` reproduces the handoff SHA. |  |  |
| `verify_tist_external_review_handoff.py` reports `ok`. |  |  |
| `verify_tist_package.py --mode review` reports `ok`. |  |  |
| `verify_tist_bibliography.py` reports `ok`. |  |  |
| Focused tests pass. |  |  |
| Archive hygiene grep returns no matches. |  |  |

## Required Findings

List any issue that must be fixed before external submission.

| Severity | Location | Finding | Required resolution |
| --- | --- | --- | --- |
| blocker/major/minor |  |  |  |

## Non-Blocking Suggestions

List optional wording, formatting, or presentation improvements.

| Location | Suggestion |
| --- | --- |
|  |  |

## Final Recommendation

- Reviewer recommendation:
- Conditions for approval:
