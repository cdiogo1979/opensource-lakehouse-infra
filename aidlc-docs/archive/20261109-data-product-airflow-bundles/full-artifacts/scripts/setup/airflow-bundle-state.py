#!/usr/bin/env python3
"""Read or record the bundle/writer fingerprint of the last successful start-airflow.

`read` prints the recorded fingerprint (nothing when none is recorded);
`record FINGERPRINT` stores it in .runtime/state/airflow-bundles.json.
"""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

STATE = Path(__file__).resolve().parents[2] / ".runtime" / "state" / "airflow-bundles.json"


def main(argv: list[str]) -> int:
    if argv == ["read"]:
        try:
            print(json.loads(STATE.read_text(encoding="utf-8")).get("fingerprint", ""))
        except (OSError, ValueError, AttributeError):
            print("")
        return 0
    if len(argv) == 2 and argv[0] == "record" and re.fullmatch(r"[0-9a-f]{64}", argv[1]):
        STATE.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".airflow-bundles.", dir=STATE.parent)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump({"fingerprint": argv[1]}, stream)
        os.replace(temporary, STATE)
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
