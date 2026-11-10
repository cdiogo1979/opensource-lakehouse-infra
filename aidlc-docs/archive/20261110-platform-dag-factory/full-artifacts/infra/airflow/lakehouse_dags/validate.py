"""Check a product repository's workflows and stub (BR-10).

  python3 -m lakehouse_dags.validate [REPOSITORY_ROOT]

Exit 0 when valid, 1 with one line per problem otherwise. Standard library only.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .spec import check_repository


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1 or (args and args[0] in ("-h", "--help")):
        print(__doc__.strip())
        return 0 if args and args[0] in ("-h", "--help") else 2
    root = Path(args[0] if args else ".")
    if not root.is_dir():
        print(f"{root}: not a directory")
        return 2
    workflows, problems = check_repository(root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"{len(problems)} problem(s)")
        return 1
    print(f"OK: {len(workflows)} workflow(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
