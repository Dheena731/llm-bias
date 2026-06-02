import tempfile
import unittest
from pathlib import Path

from verify_tist_bibliography import (
    EXPECTED_CITED_METADATA,
    audit_bibliography,
    parse_bib_entries,
    parse_citation_keys,
)


class TistBibliographyVerifierTests(unittest.TestCase):
    def test_parse_citation_keys_handles_multiple_cite_forms(self):
        text = r"""
        Prior work \cite{alpha,beta} and \citep[see][]{gamma} plus \citet{alpha}.
        """

        self.assertEqual(parse_citation_keys(text), ["alpha", "beta", "gamma"])

    def test_parse_bib_entries_reports_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "a.bib"
            second = Path(tmp) / "b.bib"
            first.write_text("@misc{same,\n  title={A},\n  year={2024}\n}\n", encoding="utf-8")
            second.write_text("@misc{same,\n  title={B},\n  year={2025}\n}\n", encoding="utf-8")

            result = parse_bib_entries([first, second])

        self.assertEqual(result.duplicate_keys, ["same"])

    def test_audit_rejects_cited_entry_missing_required_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            tex = Path(tmp) / "paper.tex"
            bib = Path(tmp) / "refs.bib"
            tex.write_text(r"\cite{alpha}", encoding="utf-8")
            bib.write_text("@inproceedings{alpha,\n  title={A},\n  year={2024}\n}\n", encoding="utf-8")

            result = audit_bibliography(tex, [bib], expected_metadata={})

        self.assertEqual(result["status"], "fail")
        self.assertIn("alpha missing required field author", result["metadata_failures"])
        self.assertIn("alpha missing required field booktitle", result["metadata_failures"])

    def test_real_tist_bibliography_matches_curated_metadata(self):
        result = audit_bibliography()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["cited_keys"], sorted(EXPECTED_CITED_METADATA))
        self.assertEqual(result["metadata_failures"], [])

    def test_audit_rejects_stale_audit_markdown_when_sync_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tex = root / "paper.tex"
            bib = root / "refs.bib"
            audit = root / "audit.md"
            tex.write_text(r"\cite{alpha}", encoding="utf-8")
            bib.write_text(
                "@misc{alpha,\n"
                "  author={Unit Author},\n"
                "  title={Unit Title},\n"
                "  year={2026},\n"
                "  url={https://example.com/unit}\n"
                "}\n",
                encoding="utf-8",
            )
            audit.write_text("stale\n", encoding="utf-8")

            result = audit_bibliography(
                tex,
                [bib],
                expected_metadata={
                    "alpha": {
                        "entry_type": "misc",
                        "url": "https://example.com/unit",
                        "source": "Unit Source",
                    }
                },
                audit_markdown_path=audit,
                require_audit_sync=True,
            )

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["audit_markdown_failures"], ["bibliography audit markdown out of sync"])


if __name__ == "__main__":
    unittest.main()
