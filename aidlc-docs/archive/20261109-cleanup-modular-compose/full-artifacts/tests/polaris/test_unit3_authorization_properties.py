"""Hypothesis checks for the approved environment role matrix."""

import importlib.util
from pathlib import Path

from hypothesis import given, strategies as st
import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "verify_role_matrix", ROOT / "infra/spark-bootstrap/verify_role_matrix.py"
)
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)

REFERENCE_READ = {
    "developer": {"prod", "uat", "dev"},
    "analyst": {"prod"},
    "owner": {"prod", "uat", "dev"},
    "writer": {"prod", "uat", "dev"},
}
REFERENCE_WRITE = {
    "developer": {"dev"},
    "analyst": set(),
    "owner": {"prod", "uat", "dev"},
    "writer": {"prod", "uat", "dev"},
}
ROLE = st.sampled_from([*REFERENCE_READ, "unknown", "", "role-default-writer"])
ROLE_SETS = st.sets(ROLE, max_size=5)
ENV = st.sampled_from(["prod", "uat", "dev", "staging", ""])
MUTATIONS = {"write", "create", "alter", "drop", "append", "overwrite", "delete"}
OPERATION = st.sampled_from(["read", *MUTATIONS, "unknown", ""])


def reference(roles, environment, operation):
    matrix = (
        REFERENCE_READ
        if operation == "read"
        else REFERENCE_WRITE
        if operation in MUTATIONS
        else {}
    )
    return any(environment in matrix.get(role, set()) for role in roles)


@given(ROLE_SETS, ENV, OPERATION)
def test_authorization_matches_independent_reference_oracle(roles, environment, operation):
    assert verifier.role_can_access(roles, environment, operation) == reference(
        roles, environment, operation
    )


@given(ROLE_SETS, ENV)
def test_combined_membership_is_union_of_individual_grants(roles, environment):
    for operation in ("read", "write"):
        combined = verifier.role_can_access(roles, environment, operation)
        individual = any(
            verifier.role_can_access({role}, environment, operation) for role in roles
        )
        assert combined == individual


@given(st.sampled_from(["prod", "uat", "dev"]))
def test_analyst_never_mutates(environment):
    for mutation in MUTATIONS:
        assert not verifier.role_can_access({"analyst"}, environment, mutation)


@pytest.mark.parametrize("environment", ["prod", "uat", "dev"])
def test_developer_can_read_every_environment(environment):
    assert verifier.role_can_access({"developer"}, environment, "read")


@pytest.mark.parametrize("environment", ["prod", "uat"])
def test_developer_mutations_are_denied_outside_dev(environment):
    for mutation in MUTATIONS:
        assert not verifier.role_can_access({"developer"}, environment, mutation)


def test_developer_mutations_are_allowed_in_dev():
    for mutation in MUTATIONS:
        assert verifier.role_can_access({"developer"}, "dev", mutation)


@given(ENV, OPERATION)
def test_empty_or_unrecognized_roles_deny_by_default(environment, operation):
    assert not verifier.role_can_access(set(), environment, operation)
    assert not verifier.role_can_access({"unknown", "role-default-owner"}, environment, operation)
    assert not verifier.role_can_access(["developer"], environment, operation)
