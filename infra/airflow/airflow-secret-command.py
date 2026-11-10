#!/usr/bin/env python3
"""Resolve selected Airflow secrets from read-only files without logging them."""

import sys
from pathlib import Path


def read_secret(path: str) -> str:
    value = Path(path).read_text(encoding="utf-8").rstrip("\r\n")
    if not value:
        raise RuntimeError("required secret is empty")
    return value


if len(sys.argv) != 2 or sys.argv[1] != "database-url":
    raise SystemExit("unsupported secret command")

from sqlalchemy.engine import URL  # Imported after argument validation.

password = read_secret("/run/secrets/airflow_postgres_password")
sys.stdout.write(
    URL.create(
        "postgresql+psycopg2",
        username="airflow",
        password=password,
        host="airflow-postgres",
        database="airflow",
    ).render_as_string(hide_password=False)
)
