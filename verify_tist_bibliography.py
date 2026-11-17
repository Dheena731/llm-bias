"""Verify cited TIST bibliography metadata against a curated source table."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TIST_TEX = Path("paper/tist2027_presentation_priors.tex")
TIST_BIB_FILES = [Path("paper/haips2026_refs.bib"), Path("paper/tist2027_presentation_priors_refs.bib")]
AUDIT_MARKDOWN = Path("paper/tist2027_bibliography_audit.md")
SOURCE_CHECK_DATE = "2026-06-03"

EXPECTED_CITED_METADATA: dict[str, dict[str, str]] = {
    "bianchi2022t2i": {
        "entry_type": "inproceedings",
        "booktitle": "Proceedings of the 2023 ACM Conference on Fairness, Accountability, and Transparency",
        "pages": "1493--1504",
        "year": "2023",
        "doi": "10.1145/3593013.3594095",
        "url": "https://doi.org/10.1145/3593013.3594095",
        "source": "ACM Digital Library",
    },
    "friedrich2024fairness": {
        "entry_type": "article",
        "journal": "AI and Ethics",
        "volume": "5",
        "pages": "2103--2123",
        "year": "2025",
        "doi": "10.1007/s43681-024-00531-5",
        "url": "https://link.springer.com/article/10.1007/s43681-024-00531-5",
        "source": "Springer Nature",
    },
    "jiang2024followbench": {
        "entry_type": "inproceedings",
        "booktitle": "Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)",
        "month": "August",
        "pages": "4667--4688",
        "year": "2024",
        "doi": "10.18653/v1/2024.acl-long.257",
        "url": "https://aclanthology.org/2024.acl-long.257/",
        "source": "ACL Anthology",
    },
    "kong2026macaron": {
        "entry_type": "misc",
        "year": "2026",
        "doi": "10.48550/arXiv.2605.24830",
        "eprint": "2605.24830",
        "url": "https://arxiv.org/abs/2605.24830",
        "source": "arXiv",
    },
    "long2025format": {
        "entry_type": "inproceedings",
        "author": "Long, Do Xuan and Nguyen, Ngoc-Hai and Sim, Tiviatis and Dao, Hieu and Joty, Shafiq and Kawaguchi, Kenji and Chen, Nancy F. and Kan, Min-Yen",
        "booktitle": "Proceedings of the 2025 Conference of the Nations of the Americas Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)",
        "month": "April",
        "pages": "299--330",
        "year": "2025",
        "doi": "10.18653/v1/2025.naacl-long.15",
        "url": "https://aclanthology.org/2025.naacl-long.15/",
        "source": "ACL Anthology",
    },
    "ouyang2022training": {
        "entry_type": "inproceedings",
        "author": "Ouyang, Long and Wu, Jeffrey and Jiang, Xu and Almeida, Diogo and Wainwright, Carroll and Mishkin, Pamela and Zhang, Chong and Agarwal, Sandhini and Slama, Katarina and Ray, Alex and Schulman, John and Hilton, Jacob and Kelton, Fraser and Miller, Luke and Simens, Maddie and Askell, Amanda and Welinder, Peter and Christiano, Paul F. and Leike, Jan and Lowe, Ryan",
        "booktitle": "Advances in Neural Information Processing Systems",
        "volume": "35",
        "pages": "27730--27744",
        "year": "2022",
        "url": "https://proceedings.neurips.cc/paper_files/paper/2022/hash/b1efde53be364a73914f58805a001731-Abstract-Conference.html",
        "source": "NeurIPS Proceedings",
    },
    "wu2024uicoder": {
        "entry_type": "inproceedings",
        "booktitle": "Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)",
        "month": "June",
        "pages": "7511--7525",
        "year": "2024",
        "doi": "10.18653/v1/2024.naacl-long.417",
        "url": "https://aclanthology.org/2024.naacl-long.417/",
        "source": "ACL Anthology",
    },
    "zhou2023ifeval": {
        "entry_type": "misc",
        "year": "2023",
        "doi": "10.48550/arXiv.2311.07911",
        "eprint": "2311.07911",
        "url": "https://arxiv.org/abs/2311.07911",
        "source": "arXiv",
    },
    "zhang2025lists": {
        "entry_type": "inproceedings",
        "year": "2025",
        "doi": "10.18653/v1/2025.acl-long.1308",
        "url": "https://aclanthology.org/2025.acl-long.1308/",
        "source": "ACL Anthology",
    },
    "singhal2024length": {
        "entry_type": "inproceedings",
        "year": "2024",
        "url": "https://openreview.net/forum?id=G8LaO1P0xv",
        "source": "OpenReview",
    },
    "dubois2024length": {
        "entry_type": "misc",
        "year": "2024",
        "url": "https://arxiv.org/abs/2404.04475",
        "eprint": "2404.04475",
        "source": "arXiv",
    },
    "feuer2025style": {
        "entry_type": "inproceedings",
        "year": "2025",
        "url": "https://openreview.net/forum?id=MzHNftnAM1",
        "source": "OpenReview",
    },
    "zhou2023lima": {
        "entry_type": "inproceedings",
        "year": "2023",
        "doi": "10.52202/075280-2400",
        "url": "https://proceedings.neurips.cc/paper_files/paper/2023/hash/ac662d74829e4407ce1d126477f4a03a-Abstract-Conference.html",
        "source": "NeurIPS Proceedings",
    },
    "lin2024unlocking": {
        "entry_type": "inproceedings",
        "year": "2024",
        "url": "https://openreview.net/forum?id=wxJ0eXwwda",
        "source": "OpenReview",
    },
    "sun2025idiosyncrasies": {
        "entry_type": "inproceedings",
        "year": "2025",
        "url": "https://proceedings.mlr.press/v267/sun25z.html",
        "source": "PMLR",
    },
    "tam2024speak": {
        "entry_type": "inproceedings",
        "year": "2024",
        "doi": "10.18653/v1/2024.emnlp-industry.91",
        "url": "https://aclanthology.org/2024.emnlp-industry.91/",
        "source": "ACL Anthology",
    },
    "sclar2024quantifying": {
        "entry_type": "inproceedings",
        "year": "2024",
        "url": "https://openreview.net/forum?id=RIu5lyNXjT",
        "source": "OpenReview",
    },
    "padmakumar2024writing": {
        "entry_type": "inproceedings",
        "year": "2024",
        "url": "https://openreview.net/forum?id=Feiz5HtCD0",
        "source": "OpenReview",
    },
    "doshi2024generative": {
        "entry_type": "article",
        "year": "2024",
        "doi": "10.1126/sciadv.adn5290",
        "url": "https://www.science.org/doi/10.1126/sciadv.adn5290",
        "source": "Science Advances (Crossref)",
    },
    "anderson2024homogenization": {
        "entry_type": "inproceedings",
        "year": "2024",
        "doi": "10.1145/3635636.3656204",
        "url": "https://doi.org/10.1145/3635636.3656204",
        "source": "ACM Digital Library",
    },
    "kirk2024understanding": {
        "entry_type": "inproceedings",
        "year": "2024",
        "url": "https://openreview.net/forum?id=PXD3FAVHJT",
        "source": "OpenReview",
    },
    "bommasani2022picking": {
        "entry_type": "inproceedings",
        "year": "2022",
        "doi": "10.52202/068431-0265",
        "url": "https://proceedings.neurips.cc/paper_files/paper/2022/hash/17a234c91f746d9625a75cf8a8731ee2-Abstract-Conference.html",
        "source": "NeurIPS Proceedings",
    },
    "chiang2024chatbot": {
        "entry_type": "inproceedings",
        "year": "2024",
        "url": "https://proceedings.mlr.press/v235/chiang24b.html",
        "source": "PMLR",
    },
    "li2024style": {
        "entry_type": "misc",
        "year": "2024",
        "url": "https://lmsys.org/blog/2024-08-28-style-control/",
        "source": "LMSYS blog",
    },
    "zheng2023judging": {
        "entry_type": "inproceedings",
        "year": "2023",
        "doi": "10.52202/075280-2020",
        "url": "https://proceedings.neurips.cc/paper_files/paper/2023/hash/91f18a1287b398d378ef22505bf41832-Abstract-Datasets_and_Benchmarks.html",
        "source": "NeurIPS Proceedings",
    },
    "saito2023verbosity": {
        "entry_type": "misc",
        "year": "2023",
        "url": "https://arxiv.org/abs/2310.10076",
        "eprint": "2310.10076",
        "source": "arXiv",
    },
    "park2024disentangling": {
        "entry_type": "inproceedings",
        "year": "2024",
        "doi": "10.18653/v1/2024.findings-acl.297",
        "url": "https://aclanthology.org/2024.findings-acl.297/",
        "source": "ACL Anthology",
    },
    "rafailov2023direct": {
        "entry_type": "inproceedings",
        "year": "2023",
        "doi": "10.52202/075280-2338",
        "url": "https://proceedings.neurips.cc/paper_files/paper/2023/hash/a85b405ed65c6477a4fe8302b5e06ce7-Abstract-Conference.html",
        "source": "NeurIPS Proceedings",
    },
    "lambert2024tulu": {
        "entry_type": "misc",
        "year": "2024",
        "url": "https://arxiv.org/abs/2411.15124",
        "eprint": "2411.15124",
        "source": "arXiv",
    },
    "olmo2025furious": {
        "entry_type": "misc",
        "year": "2025",
        "url": "https://arxiv.org/abs/2501.00656",
        "eprint": "2501.00656",
        "source": "arXiv",
    },
    "wallace2024instruction": {
        "entry_type": "misc",
        "year": "2024",
        "url": "https://arxiv.org/abs/2404.13208",
        "eprint": "2404.13208",
        "source": "arXiv",
    },
    "harada2025instructions": {
        "entry_type": "inproceedings",
        "year": "2025",
        "doi": "10.18653/v1/2025.findings-emnlp.896",
        "url": "https://aclanthology.org/2025.findings-emnlp.896/",
        "source": "ACL Anthology",
    },
    "liang2024monitoring": {
        "entry_type": "inproceedings",
        "year": "2024",
        "url": "https://proceedings.mlr.press/v235/liang24b.html",
        "source": "PMLR",
    },
    "kobak2025delving": {
        "entry_type": "article",
        "year": "2025",
        "doi": "10.1126/sciadv.adt3813",
        "url": "https://www.science.org/doi/10.1126/sciadv.adt3813",
        "source": "Science Advances (Crossref)",
    },
    "deka2017rico": {
        "entry_type": "inproceedings",
        "year": "2017",
        "doi": "10.1145/3126594.3126651",
        "url": "https://doi.org/10.1145/3126594.3126651",
        "source": "ACM Digital Library",
    },
    "wu2023webui": {
        "entry_type": "inproceedings",
        "year": "2023",
        "doi": "10.1145/3544548.3581158",
        "url": "https://doi.org/10.1145/3544548.3581158",
        "source": "ACM Digital Library",
    },
    "li2016diversity": {
        "entry_type": "inproceedings",
        "year": "2016",
        "doi": "10.18653/v1/N16-1014",
        "url": "https://aclanthology.org/N16-1014/",
        "source": "ACL Anthology",
    },
}


@dataclass(frozen=True)
class BibEntry:
    key: str
    entry_type: str
    fields: dict[str, str]
    path: Path


@dataclass(frozen=True)
class BibParseResult:
    entries: dict[str, BibEntry]
    duplicate_keys: list[str]


def parse_citation_keys(text: str) -> list[str]:
    keys = set()
    cite_pattern = re.compile(r"\\cite[a-zA-Z*]*(?:\[[^\]]*\])*\{([^}]+)\}")
    for group in cite_pattern.findall(text):
        keys.update(key.strip() for key in group.split(",") if key.strip())
    return sorted(keys)


def _strip_value(value: str) -> str:
    value = value.strip().rstrip(",").strip()
    if (value.startswith("{") and value.endswith("}")) or (value.startswith('"') and value.endswith('"')):
        value = value[1:-1]
    return value.strip()


def _parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in body.splitlines():
        match = re.match(r"\s*([A-Za-z][A-Za-z0-9_-]*)\s*=\s*(.+?)\s*,?\s*$", line)
        if not match:
            continue
        fields[match.group(1).lower()] = _strip_value(match.group(2))
    return fields


def parse_bib_entries(paths: list[Path] = TIST_BIB_FILES) -> BibParseResult:
    entries: dict[str, BibEntry] = {}
    duplicates: set[str] = set()
    entry_pattern = re.compile(r"@(?P<type>\w+)\s*\{\s*(?P<key>[^,\s]+)\s*,(?P<body>.*?)(?=^@\w+\s*\{|\Z)", re.S | re.M)
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for match in entry_pattern.finditer(text):
            key = match.group("key").strip()
            if key in entries:
                duplicates.add(key)
                continue
            entries[key] = BibEntry(
                key=key,
                entry_type=match.group("type").lower(),
                fields=_parse_fields(match.group("body")),
                path=path,
            )
    return BibParseResult(entries=entries, duplicate_keys=sorted(duplicates))


def _required_fields(entry_type: str) -> list[str]:
    base = ["author", "title", "year"]
    if entry_type == "inproceedings":
        return base + ["booktitle", "pages", "publisher"]
    if entry_type == "article":
        return base + ["journal", "volume", "pages"]
    if entry_type == "techreport":
        return base + ["institution"]
    return base


def _metadata_failures_for_entry(key: str, entry: BibEntry, expected: dict[str, str]) -> list[str]:
    failures = []
    fields = entry.fields
    # ICLR/COLM papers are published on OpenReview without page numbers or a separate publisher.
    unpaginated = "openreview.net" in fields.get("url", "")
    for field in _required_fields(entry.entry_type):
        if unpaginated and field in ("pages", "publisher"):
            continue
        if not fields.get(field):
            failures.append(f"{key} missing required field {field}")
    if not (fields.get("doi") or fields.get("url")):
        failures.append(f"{key} missing DOI or URL")
    expected_type = expected.get("entry_type")
    if expected_type and entry.entry_type != expected_type:
        failures.append(f"{key} expected entry type {expected_type}, found {entry.entry_type}")
    for field in ["author", "booktitle", "journal", "volume", "pages", "year", "month", "doi", "url", "eprint"]:
        expected_value = expected.get(field)
        if expected_value and fields.get(field) != expected_value:
            failures.append(f"{key} expected {field} {expected_value}, found {fields.get(field, '<missing>')}")
    if fields.get("eprint") and fields.get("archiveprefix", "").lower() != "arxiv":
        failures.append(f"{key} has eprint but missing archivePrefix=arXiv")
    return failures


def audit_bibliography(
    tex_path: Path = TIST_TEX,
    bib_paths: list[Path] = TIST_BIB_FILES,
    expected_metadata: dict[str, dict[str, str]] = EXPECTED_CITED_METADATA,
    audit_markdown_path: Path = AUDIT_MARKDOWN,
    require_audit_sync: bool = False,
) -> dict[str, Any]:
    cited_keys = parse_citation_keys(tex_path.read_text(encoding="utf-8"))
    parsed = parse_bib_entries(bib_paths)
    missing_entries = sorted(key for key in cited_keys if key not in parsed.entries)
    metadata_failures = []
    for key in cited_keys:
        entry = parsed.entries.get(key)
        if not entry:
            continue
        metadata_failures.extend(_metadata_failures_for_entry(key, entry, expected_metadata.get(key, {})))
    expected_missing = sorted(set(cited_keys) - set(expected_metadata))
    expected_unreferenced = sorted(set(expected_metadata) - set(cited_keys))
    unused_entries = sorted(set(parsed.entries) - set(cited_keys))
    audit_markdown_failures = []
    result = {
        "bib_entry_count": len(parsed.entries),
        "cited_entry_count": len(cited_keys),
        "cited_keys": cited_keys,
        "duplicate_keys": parsed.duplicate_keys,
        "missing_entries": missing_entries,
        "metadata_failures": metadata_failures,
        "expected_metadata_missing": expected_missing,
        "expected_metadata_unreferenced": expected_unreferenced,
        "unused_entries": unused_entries,
    }
    if require_audit_sync:
        expected_audit = render_audit_markdown({**result, "status": "ok"}, expected_metadata)
        if not audit_markdown_path.exists() or audit_markdown_path.read_text(encoding="utf-8") != expected_audit:
            audit_markdown_failures.append("bibliography audit markdown out of sync")
    failures = (
        parsed.duplicate_keys
        + missing_entries
        + metadata_failures
        + expected_missing
        + expected_unreferenced
        + audit_markdown_failures
    )
    result["status"] = "ok" if not failures else "fail"
    result["audit_markdown_failures"] = audit_markdown_failures
    return result


def render_audit_markdown(
    result: dict[str, Any],
    expected_metadata: dict[str, dict[str, str]] = EXPECTED_CITED_METADATA,
) -> str:
    lines = [
        "# TIST Bibliography Metadata Audit",
        "",
        "Scope: cited entries in `paper/tist2027_presentation_priors.tex`.",
        "",
        f"Source check date: {SOURCE_CHECK_DATE}.",
        "",
        f"Status: `{result['status']}`",
        "",
        "| Key | Source | DOI | URL |",
        "| --- | --- | --- | --- |",
    ]
    for key in result["cited_keys"]:
        expected = expected_metadata[key]
        lines.append(
            f"| `{key}` | {expected['source']} | {expected.get('doi', '')} | {expected.get('url', '')} |"
        )
    lines.extend(
        [
            "",
            "Notes:",
            "",
            "- Publisher/registry source pages were checked for the cited entries on the date above.",
            "- The audit is a local metadata gate over cited entries; recheck source pages after any reference changes.",
            "- The Friedrich et al. entry intentionally uses the AI and Ethics volume citation year, while the article page also reports a 2024 online publication date.",
            "- Unused entries in shared bibliography files are reported by the script but are not package blockers.",
            "",
            "Primary publisher/registry pages checked:",
            "",
        ]
    )
    for key in result["cited_keys"]:
        expected = expected_metadata[key]
        lines.append(f"- `{key}`: {expected.get('url', '')}")
    return "\n".join(lines) + "\n"


def write_audit_markdown(result: dict[str, Any], output_path: Path = AUDIT_MARKDOWN) -> None:
    output_path.write_text(render_audit_markdown(result), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify TIST cited bibliography metadata")
    parser.add_argument("--write-audit", action="store_true", help=f"Write {AUDIT_MARKDOWN}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = audit_bibliography(require_audit_sync=not args.write_audit)
    if args.write_audit:
        write_audit_markdown(result)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
