"""Opt-in local Spark/Polaris role-matrix acceptance check."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
ROLE_MATRIX_COMMAND = ROOT / "scripts/verify-role-matrix.py"
LIVE_ENABLED = os.environ.get("LAKEHOUSE_LIVE_ROLE_MATRIX") == "1"


@pytest.mark.integration
@pytest.mark.live
@pytest.mark.skipif(
    not LIVE_ENABLED,
    reason="Set LAKEHOUSE_LIVE_ROLE_MATRIX=1 to run the provider-mutating role matrix.",
)
def test_live_spark_polaris_vended_access_role_matrix_and_cleanup():
    """Run the approved temporary-identity verifier and require confirmed cleanup."""
    result = subprocess.run(
        [sys.executable, str(ROLE_MATRIX_COMMAND)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=900,
        shell=False,
    )
    safe_output = result.stdout + "\n" + result.stderr

    assert result.returncode == 0, (
        "Live role-matrix verification failed; inspect its redacted status output."
    )
    assert "ROLE_MATRIX_RESULT:" in safe_output
    assert "ROLE_MATRIX_CLEANUP:" in safe_output
    assert "Temporary identity cleanup completed." in safe_output
    assert not re.search(r"\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.", safe_output)
    assert not re.search(
        r"(?i)(client_secret|access_token|refresh_token|secret_access_key)\s*[=:]",
        safe_output,
    )
