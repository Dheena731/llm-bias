"""Markdown split into markup syntax (changes when rendered) and list structure (plain-text lists).

Reviewers showed that a single "has Markdown" flag mixes the two: plain hyphen or numbered lists are ordinary
plain-text structure, while headings, emphasis, code, links and tables are markup that only makes sense rendered.
"""

from __future__ import annotations

import re

MARKUP_PATTERNS = {
    "heading": re.compile(r"^\s{0,3}#{1,6}\s+\S", re.MULTILINE),
    "bold": re.compile(r"\*\*[^*\n]*[^*\s][^*\n]*\*\*|__[^_\n]*[^_\s][^_\n]*__"),  # "____" fill-in blanks do not match
    "italic": re.compile(r"(?<![*\w])\*(?![\s*])[^*\n]+(?<!\s)\*(?![*\w])"),
    "code": re.compile(r"`[^`\n]+`|^```", re.MULTILINE),
    "link": re.compile(r"\[[^\]\n]+\]\([^)\s]+\)"),
    "table": re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE),
    "rule": re.compile(r"^\s*(?:-{3,}|\*{3,})\s*$", re.MULTILINE),
}
LIST_LINE = re.compile(r"^\s*(?:[-*+•]|\d{1,2}[.)])\s+\S", re.MULTILINE)


def markdown_kinds(text: str) -> dict[str, bool]:
    text = text or ""
    tables = len(MARKUP_PATTERNS["table"].findall(text)) >= 2  # one pipe line is not a table
    markup = tables or any(p.search(text) for name, p in MARKUP_PATTERNS.items() if name != "table")
    return {"has_markup": bool(markup), "has_list": bool(LIST_LINE.search(text))}


if __name__ == "__main__":
    cases = {
        "**Subject:** Update": (True, False),
        "Effective date: ____________": (False, False),
        "- check the form\n- send it": (False, True),
        "1. First\n2. Second": (False, True),
        "## Heading\nBody": (True, False),
        "Use *care* here": (True, False),
        "| a | b |\n|---|---|": (True, False),
        "plain prose, fast - and free": (False, False),
    }
    for text, expected in cases.items():
        got = markdown_kinds(text)
        assert (got["has_markup"], got["has_list"]) == expected, (text, got)
    print("ok")
