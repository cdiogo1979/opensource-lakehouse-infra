"""Hypothesis range invariants for Polaris's generated credential settings."""

import importlib.util
from pathlib import Path

from hypothesis import given, strategies as st


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "prepare_lakehouse_runtime", ROOT / "scripts/prepare-lakehouse-runtime.py"
)
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


@given(
    duration=st.integers(min_value=2, max_value=86_400),
    cache=st.integers(min_value=1, max_value=86_399),
)
def test_valid_positive_cache_is_shorter_than_duration(duration, cache):
    if cache < duration:
        runtime.validate_credential_timing(duration, cache)


@given(duration=st.integers(min_value=1, max_value=86_400))
def test_cache_equal_to_or_longer_than_duration_is_rejected(duration):
    import pytest

    with pytest.raises(ValueError):
        runtime.validate_credential_timing(duration, duration)
    with pytest.raises(ValueError):
        runtime.validate_credential_timing(duration, duration + 1)
