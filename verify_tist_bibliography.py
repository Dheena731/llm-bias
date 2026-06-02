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

EXPECTED_CITED_METADATA: dict[str, dict[str, str]] = {
    "bianchi2022t2i": {
        "entry_type": "inproceedings",
        "doi": "10.1145/3593013.3594095",
        "url": "https://doi.org/10.1145/3593013.3594095",
        "source": "ACM Digital Library",
    },
    "friedrich2024fairness": {
        "entry_type": "article",
        "doi": "10.1007/s43681-024-00531-5",
        "url": "https://link.springer.com/article/10.1007/s43681-024-00531-5",
        "source": "Springer Nature",
    },
    "jiang2024followbench": {
        "entry_type": "inproceedings",
        "doi": "10.18653/v1/2024.acl-long.257",
        "url": "https://aclanthology.org/2024.acl-long.257/",
        "source": "ACL Anthology",
    },
    "kong2026macaron": {
        "entry_type": "misc",
        "eprint": "2605.24830",
        "url": "https://arxiv.org/abs/2605.24830",
        "source": "arXiv",
    },
    "long2025format": {
        "entry_type": "inproceedings",
        "doi": "10.18653/v1/2025.naacl-long.15",
        "url": "https://aclanthology.org/2025.naacl-long.15/",
        "source": "ACL Anthology",
    },
    "ouyang2022training": {
        "entry_type": "inproceedings",
        "url": "https://proceedings.neurips.cc/paper_files/paper/2022/hash/b1efde53be364a73914f58805a001731-Abstract-Conference.html",
        "source": "NeurIPS Proceedings",
    },
    "wu2024uicoder": {
        "entry_type": "inproceedings",
        "doi": "10.18653/v1/2024.naacl-long.417",
        "url": "https://aclanthology.org/2024.naacl-long.417/",
        "source": "ACL Anthology",
    },
    "zhou2023ifeval": {
        "entry_type": "misc",
        "doi": "10.48550/arXiv.2311.07911",
        "eprint": "2311.07911",
        "url": "https://arxiv.org/abs/2311.07911",
        "source": "arXiv",
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
    for field in _required_fields(entry.entry_type):
        if not fields.get(field):
            failures.append(f"{key} missing required field {field}")
    if not (fields.get("doi") or fields.get("url")):
        failures.append(f"{key} missing DOI or URL")
    expected_type = expected.get("entry_type")
    if expected_type and entry.entry_type != expected_type:
        failures.append(f"{key} expected entry type {expected_type}, found {entry.entry_type}")
    for field in ["doi", "url", "eprint"]:
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
    failures = parsed.duplicate_keys + missing_entries + metadata_failures + expected_missing + expected_unreferenced
    return {
        "status": "ok" if not failures else "fail",
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


def write_audit_markdown(result: dict[str, Any], output_path: Path = AUDIT_MARKDOWN) -> None:
    lines = [
        "# TIST Bibliography Metadata Audit",
        "",
        "Scope: cited entries in `paper/tist2027_presentation_priors.tex`.",
        "",
        "Source check date: 2026-06-02.",
        "",
        f"Status: `{result['status']}`",
        "",
        "| Key | Source | DOI | URL |",
        "| --- | --- | --- | --- |",
    ]
    for key in result["cited_keys"]:
        expected = EXPECTED_CITED_METADATA[key]
        lines.append(
            f"| `{key}` | {expected['source']} | {expected.get('doi', '')} | {expected.get('url', '')} |"
        )
    lines.extend(
        [
            "",
            "Notes:",
            "",
            "- The audit is a local metadata gate over cited entries, not a replacement for final publisher-side proofing.",
            "- Unused entries in shared bibliography files are reported by the script but are not package blockers.",
            "",
            "Primary source pages checked:",
            "",
        ]
    )
    for key in result["cited_keys"]:
        expected = EXPECTED_CITED_METADATA[key]
        lines.append(f"- `{key}`: {expected.get('url', '')}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify TIST cited bibliography metadata")
    parser.add_argument("--write-audit", action="store_true", help=f"Write {AUDIT_MARKDOWN}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = audit_bibliography()
    if args.write_audit:
        write_audit_markdown(result)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
