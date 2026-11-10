#!/usr/bin/env python3
"""Adapt Ranger 2.9.0's subprocess environment parser to Python 3.14 bytes."""

from pathlib import Path


SOURCE = Path("/opt/ranger/ranger-2.9.0-admin/db_setup.py")
OLD = """\tfor line in proc.stdout:
\t\t(key, _, value) = line.partition(\"=\")
\t\tos.environ[key] = value.rstrip()
"""
NEW = """\tfor line in proc.stdout:
\t\tif isinstance(line, bytes):
\t\t\tline = line.decode(\"utf-8\")
\t\t(key, _, value) = line.partition(\"=\")
\t\tos.environ[key] = value.rstrip()
"""


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    if source.count(OLD) != 1:
        raise SystemExit("Expected one Ranger db_setup.py environment parser block")
    SOURCE.write_text(source.replace(OLD, NEW), encoding="utf-8")


if __name__ == "__main__":
    main()
