#!/usr/bin/env python3
"""Check the relative links and anchors of Markdown documentation (read-only).

  python3 scripts/verify/docs-links.py README.md docs/

Every `[text](target)` that is not a URL must point to an existing file, and a
`#anchor` must match a heading of that file (GitHub's anchor rules). Code blocks
are skipped. Exit 1 lists every broken link.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
EXTERNAL = ("http://", "https://", "mailto:")


def anchor(heading: str) -> str:
    """GitHub's anchor for a heading: lowercase, punctuation removed, spaces to hyphens."""
    text = re.sub(r"`([^`]*)`", r"\1", heading)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def prose_lines(path: Path):
    """The file's lines outside fenced code blocks, with their numbers."""
    fenced = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            yield number, line


def anchors(path: Path) -> set[str]:
    found, seen = set(), {}
    for _, line in prose_lines(path):
        match = HEADING.match(line)
        if match:
            base = anchor(match.group(2))
            count = seen.get(base, 0)
            found.add(base if count == 0 else f"{base}-{count}")
            seen[base] = count + 1
    return found


def check(files: list[Path]) -> list[str]:
    problems = []
    for path in files:
        for number, line in prose_lines(path):
            for target in LINK.findall(line):
                if target.startswith(EXTERNAL):
                    continue
                file_part, _, fragment = target.partition("#")
                resolved = (path.parent / file_part).resolve() if file_part else path.resolve()
                if not resolved.exists():
                    problems.append(f"{path}:{number}: missing target {target}")
                elif fragment and resolved.suffix == ".md" and fragment not in anchors(resolved):
                    problems.append(f"{path}:{number}: no heading for #{fragment} in {resolved.name}")
    return problems


def main(argv: list[str]) -> int:
    files = []
    for argument in argv or ["README.md", "docs"]:
        path = Path(argument)
        files.extend(sorted(path.rglob("*.md")) if path.is_dir() else [path])
    problems = check(files)
    for problem in problems:
        print(problem)
    print(f"{len(files)} file(s), {'no broken links' if not problems else f'{len(problems)} broken link(s)'}.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
