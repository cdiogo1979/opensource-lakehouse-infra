#!/usr/bin/env python3
"""List the container images the platform runs or builds from, for vulnerability scanning.

Reads ``image:`` lines of the ``compose.*.yml`` files and ``FROM`` lines of the current
Dockerfiles (never ``aidlc-docs/``). Images built here (``local/...``) and build-stage
aliases are skipped: their bases and the workload lock are scanned instead.

  python3 scripts/verify/list-images.py          # JSON: [{"image", "sources", "pinned"}]
  python3 scripts/verify/list-images.py --check  # also exit 1 if an image isn't pinned by digest

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_IMAGE_LINE = re.compile(r"^\s*image:\s*(\S+)\s*$")
_FROM_LINE = re.compile(r"^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+(\S+))?\s*$", re.IGNORECASE)


def _skip(image: str, stages: set[str]) -> bool:
    return image.startswith("local/") or image.lower() in stages or image == "scratch" or "$" in image


def images(root: Path = ROOT) -> list[dict]:
    """Every external image with the file:line references that use it, in first-seen order."""
    found: dict[str, list[str]] = {}
    for compose in sorted(root.glob("compose.*.yml")):
        for number, line in enumerate(compose.read_text().splitlines(), 1):
            match = _IMAGE_LINE.match(line)
            if match and not _skip(match[1], set()):
                found.setdefault(match[1], []).append(f"{compose.name}:{number}")
    for dockerfile in sorted(root.rglob("Dockerfile")):
        relative = dockerfile.relative_to(root)
        if relative.parts[0] in ("aidlc-docs", ".git"):
            continue
        stages: set[str] = set()
        for number, line in enumerate(dockerfile.read_text().splitlines(), 1):
            match = _FROM_LINE.match(line)
            if not match:
                continue
            if not _skip(match[1], stages):
                found.setdefault(match[1], []).append(f"{relative.as_posix()}:{number}")
            if match[2]:
                stages.add(match[2].lower())
    return [{"image": image, "sources": sources, "pinned": "digest" if "@sha256:" in image else "tag"} for image, sources in found.items()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 when an image is not pinned by digest")
    args = parser.parse_args(argv)
    listed = images()
    print(json.dumps(listed, indent=2))
    unpinned = [entry["image"] for entry in listed if entry["pinned"] != "digest"]
    if unpinned:
        print("Not pinned by digest: " + ", ".join(unpinned), file=sys.stderr)
    return 1 if args.check and unpinned else 0


if __name__ == "__main__":
    raise SystemExit(main())
