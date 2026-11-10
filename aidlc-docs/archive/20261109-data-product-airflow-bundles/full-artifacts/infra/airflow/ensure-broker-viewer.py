#!/usr/bin/env python3
"""Create or refresh the token broker's read-only Airflow user (Viewer).

The broker asks the Airflow API which bundle a DAG comes from before it issues
a product writer's token. This local FAB user may only read (role Viewer). It is
recreated when present so its role and password always match the protected file.
The CLI runs in-process, so the password never becomes an OS argument or a log line.
"""

import contextlib
import io
import json
import logging
import os
import sys

logging.disable(logging.CRITICAL)

from airflow.__main__ import main as airflow_main

USERNAME = os.environ.get("AIRFLOW_BROKER_VIEWER_USERNAME", "lakehouse-broker")
PASSWORD_FILE = os.environ.get("AIRFLOW_BROKER_VIEWER_PASSWORD_FILE", "/run/secrets/airflow_broker_viewer_password")


def invoke_cli(arguments: list[str]) -> tuple[int, str]:
    original_argv = sys.argv
    captured = io.StringIO()
    sys.argv = ["airflow", *arguments]
    try:
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(io.StringIO()):
            try:
                airflow_main()
            except SystemExit as error:
                code = error.code if isinstance(error.code, int) else 1
                if code:
                    return code, captured.getvalue()
            except Exception:
                return 1, ""
        return 0, captured.getvalue()
    finally:
        sys.argv = original_argv


try:
    with open(PASSWORD_FILE, encoding="utf-8") as stream:
        password = stream.read().rstrip("\r\n")
except OSError:
    raise SystemExit("Broker Viewer bootstrap failed; the password file is unavailable.") from None
if not password:
    raise SystemExit("Broker Viewer bootstrap failed; the password file is empty.")

status, listing = invoke_cli(["users", "list", "--output", "json"])
if status != 0:
    raise SystemExit("Broker Viewer bootstrap failed; sanitized CLI failure.")
try:
    rows = json.loads(listing)
except json.JSONDecodeError:
    raise SystemExit("Broker Viewer bootstrap failed; user listing format was unexpected.") from None
if any(isinstance(row, dict) and row.get("username") == USERNAME for row in rows if isinstance(rows, list)):
    status, _ = invoke_cli(["users", "delete", "--username", USERNAME])
    if status != 0:
        raise SystemExit("Broker Viewer bootstrap failed; could not refresh the existing user.")
status, _ = invoke_cli(["users", "create", "--username", USERNAME, "--password", password, "--firstname", "Lakehouse",
                        "--lastname", "Broker", "--role", "Viewer", "--email", "lakehouse-broker@localhost"])
if status != 0:
    raise SystemExit("Broker Viewer bootstrap failed; sanitized CLI failure.")
print(f"Airflow user {USERNAME} (Viewer) is ready for the token broker.")
