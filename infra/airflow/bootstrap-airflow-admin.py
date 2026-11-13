#!/usr/bin/env python3
"""Idempotently create the Airflow admin without OS arguments or log leakage."""

import contextlib
import io
import json
import logging
import os
import sys
import warnings

logging.disable(logging.CRITICAL)
# A library warning printed on stdout would break the JSON user listing below.
warnings.filterwarnings("ignore")

from airflow.__main__ import main as airflow_main


def invoke_cli(arguments: list[str]) -> tuple[int, str]:
    original_argv = sys.argv
    captured_out = io.StringIO()
    captured_err = io.StringIO()
    sys.argv = ["airflow", *arguments]
    try:
        with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(captured_err):
            try:
                airflow_main()
            except SystemExit as error:
                code = error.code if isinstance(error.code, int) else 1
                if code:
                    return code, captured_out.getvalue()
            except Exception:
                return 1, ""
        return 0, captured_out.getvalue()
    finally:
        sys.argv = original_argv


def rows_from_json(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for candidate in value.values():
            if isinstance(candidate, list):
                return candidate
    return []


username = os.environ.get("AIRFLOW_ADMIN_USERNAME", "admin")
try:
    with open("/run/secrets/airflow_admin_password", encoding="utf-8") as secret_file:
        password = secret_file.read().rstrip("\r\n")
except OSError:
    raise SystemExit("Airflow administrator bootstrap failed; the password file is unavailable.") from None
if not username or not password:
    raise SystemExit("Airflow administrator bootstrap failed; required account data is unavailable.")

status, listing = invoke_cli(["users", "list", "--output", "json"])
if status != 0:
    raise SystemExit("Airflow administrator bootstrap failed; sanitized CLI failure.")
try:
    existing_users = rows_from_json(json.loads(listing))
except json.JSONDecodeError:
    raise SystemExit("Airflow administrator bootstrap failed; user listing format was unexpected.") from None

if any(isinstance(row, dict) and row.get("username") == username for row in existing_users):
    print("Airflow administrator already exists; bootstrap is complete.")
    raise SystemExit(0)

status, _ = invoke_cli(
    [
        "users",
        "create",
        "--username",
        username,
        "--password",
        password,
        "--firstname",
        "Lakehouse",
        "--lastname",
        "Administrator",
        "--role",
        "Admin",
        "--email",
        "admin@localhost",
    ]
)
if status != 0:
    raise SystemExit("Airflow administrator bootstrap failed; sanitized CLI failure.")
print("Airflow administrator was created.")
