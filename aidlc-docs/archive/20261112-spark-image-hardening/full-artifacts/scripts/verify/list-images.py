#!/usr/bin/env python3
"""List the container images the platform runs or builds from, for pinning checks and vulnerability scanning.

``images()`` reads ``image:`` lines of the ``compose.*.yml`` files and ``FROM`` lines of the
current Dockerfiles (never ``aidlc-docs/``), skipping images built here (``local/...``) and
build-stage aliases: every external image, checked for a digest pin.

``targets()`` is what runs, for scanning: the external images of the Compose files and the
images built here, each with how to build it (its Compose ``build:`` block, or its
``docker build`` line in ``scripts/lakehouse.sh``) and, as its source, its Dockerfile's last
``FROM`` line. Base images and build-only stages aren't scanned on their own.

  python3 scripts/verify/list-images.py            # JSON: [{"image", "sources", "pinned"}]
  python3 scripts/verify/list-images.py --check    # also exit 1 if an image isn't pinned by digest
  python3 scripts/verify/list-images.py --targets  # JSON: what the vulnerability scan covers

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
_BUILD_KEY = re.compile(r"^\s+(context|dockerfile):\s*(\S+)\s*$")
_SCRIPT_BUILD = re.compile(r"docker build -t (local/\S+)\s+-f (\S+) (\S+)")


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


def _last_from(root: Path, dockerfile: str) -> str:
    """``path:line`` of a Dockerfile's last ``FROM``: the base of the image it builds."""
    lines = (root / dockerfile).read_text().splitlines()
    number = max(n for n, line in enumerate(lines, 1) if _FROM_LINE.match(line))
    return f"{dockerfile}:{number}"


def _built(root: Path) -> dict[str, dict]:
    """Images built here: reference -> {"context", "dockerfile"}, the script's builds first (others build from them)."""
    built: dict[str, dict] = {}
    script = root / "scripts/lakehouse.sh"
    if script.is_file():
        for match in _SCRIPT_BUILD.finditer(re.sub(r"\\\n\s*", "", script.read_text())):
            built.setdefault(match[1], {"context": match[3], "dockerfile": match[2]})
    for compose in sorted(root.glob("compose.*.yml")):
        image, build = None, None
        for line in compose.read_text().splitlines():
            match = _IMAGE_LINE.match(line)
            if match:
                image, build = match[1], None
            elif re.match(r"^\s+build:\s*$", line) and image and image.startswith("local/"):
                build = built.setdefault(image, {"context": ".", "dockerfile": "Dockerfile", "compose": True})
            elif build is not None and (key := _BUILD_KEY.match(line)):
                build[key[1]] = key[2]
    for build in built.values():
        context = Path(build["context"].removeprefix("./"))
        build["context"] = context.as_posix()
        if build.pop("compose", False):  # Compose resolves dockerfile against the context
            build["dockerfile"] = (context / build["dockerfile"]).as_posix()
    return built


def targets(root: Path = ROOT) -> list[dict]:
    """What runs: the Compose files' external images, then the images built here with their build."""
    external = []
    for compose in sorted(root.glob("compose.*.yml")):
        for number, line in enumerate(compose.read_text().splitlines(), 1):
            match = _IMAGE_LINE.match(line)
            if match and not _skip(match[1], set()):
                external.append((match[1], f"{compose.name}:{number}"))
    found: dict[str, list[str]] = {}
    for image, source in external:
        found.setdefault(image, []).append(source)
    listed = [{"image": image, "sources": sources, "pinned": "digest" if "@sha256:" in image else "tag"} for image, sources in found.items()]
    for image, build in _built(root).items():
        listed.append({"image": image, "sources": [_last_from(root, build["dockerfile"])], "pinned": "built", "build": build})
    return listed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 when an image is not pinned by digest")
    parser.add_argument("--targets", action="store_true", help="list what the vulnerability scan covers instead")
    args = parser.parse_args(argv)
    if args.targets:
        print(json.dumps(targets(), indent=2))
        return 0
    listed = images()
    print(json.dumps(listed, indent=2))
    unpinned = [entry["image"] for entry in listed if entry["pinned"] != "digest"]
    if unpinned:
        print("Not pinned by digest: " + ", ".join(unpinned), file=sys.stderr)
    return 1 if args.check and unpinned else 0


if __name__ == "__main__":
    raise SystemExit(main())
