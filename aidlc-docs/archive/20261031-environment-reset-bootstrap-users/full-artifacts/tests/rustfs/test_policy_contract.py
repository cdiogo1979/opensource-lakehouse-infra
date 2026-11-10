"""Contract and property tests for the RustFS product-group policies."""

import json

import pytest
from hypothesis import given, settings, strategies as st

from strategies import (
    access_maps,
    buckets,
    policies,
    policy_documents,
    product_group_sets,
    product_groups,
    s3_actions,
    shuffled_documents,
)


ALLOWED_RESOURCES = {"arn:aws:s3:::*"} | {
    arn for bucket in policies.BUCKETS for arn in (f"arn:aws:s3:::{bucket}", f"arn:aws:s3:::{bucket}/*")
}
READ = {
    "s3:GetBucketLocation",
    "s3:GetBucketObjectLockConfiguration",
    "s3:GetBucketPolicyStatus",
    "s3:GetBucketTagging",
    "s3:GetBucketVersioning",
    "s3:ListBucket",
    "s3:ListBucketVersions",
    "s3:GetObject",
    "s3:GetObjectLegalHold",
    "s3:GetObjectRetention",
    "s3:GetObjectTagging",
    "s3:GetObjectVersion",
}
CONSOLE_METADATA_READS = {"s3:GetBucketPolicyStatus", "s3:GetBucketVersioning", "s3:GetBucketObjectLockConfiguration"}
WRITE = {
    "s3:ListBucketMultipartUploads",
    "s3:PutObject",
    "s3:DeleteObject",
    "s3:AbortMultipartUpload",
    "s3:ListMultipartUploadParts",
}


def allows(document: dict, action: str, resource: str) -> bool:
    return any(
        statement["Effect"] == "Allow"
        and resource in statement["Resource"]
        and (action in statement["Action"] or "s3:*" in statement["Action"])
        for statement in document["Statement"]
    )


def bucket_actions(document: dict, bucket: str) -> set[str]:
    arns = (f"arn:aws:s3:::{bucket}", f"arn:aws:s3:::{bucket}/*")
    return {
        action
        for statement in document["Statement"]
        if set(statement["Resource"]) & set(arns)
        for action in statement["Action"]
    }


class FakeAdmin:
    def __init__(self, status: int, body: bytes):
        self.status = status
        self.body = body
        self.created = None

    def request(self, method, path, query=None, body=b""):
        if method == "GET" and path.endswith("/info-canned-policy"):
            return self.status, self.body
        if method == "PUT" and path.endswith("/add-canned-policy"):
            self.created = (query["name"], json.loads(body))
            self.status, self.body = 200, json.dumps({"policy": json.loads(body)}).encode()
            return 200, b""
        raise AssertionError(f"Unexpected request: {method} {path}")


# ---- Example-based contract tests ----


def test_policy_names_are_exactly_the_product_groups():
    assert sorted(policies.policy_documents()) == [
        "role-default-analyst",
        "role-default-developer",
        "role-default-owner",
        "role-default-writer",
        "role-platform-admin",
    ]


def test_platform_admin_policy_equals_the_owner_policy():
    assert policies.policy_document("role-platform-admin") == policies.policy_document("role-default-owner")


def test_access_matrix_matches_the_approved_design():
    documents = policies.policy_documents()
    owner, developer = documents["role-default-owner"], documents["role-default-developer"]
    analyst, writer = documents["role-default-analyst"], documents["role-default-writer"]
    for bucket in policies.BUCKETS:
        assert bucket_actions(owner, bucket) == {"s3:*"}
        assert bucket_actions(writer, bucket) == READ | WRITE
    assert bucket_actions(developer, "bucket-default") == READ
    assert bucket_actions(developer, "bucket-default-uat") == READ
    assert bucket_actions(developer, "bucket-default-dev") == READ | WRITE
    assert bucket_actions(analyst, "bucket-default") == READ
    assert bucket_actions(analyst, "bucket-default-uat") == set()
    assert bucket_actions(analyst, "bucket-default-dev") == set()


def test_every_policy_lists_bucket_names_and_grants_no_administration():
    for document in policies.policy_documents().values():
        assert document["Version"] == "2012-10-17"
        assert policies.LIST_BUCKETS_STATEMENT in document["Statement"]
        actions = {action for statement in document["Statement"] for action in statement["Action"]}
        assert not any(action.startswith("admin:") for action in actions)


@pytest.mark.parametrize(
    ("status", "body", "missing"),
    [
        (404, b"", True),
        (400, b"<Error><Code>NoSuchCannedPolicy</Code></Error>", True),
        (500, b"<Error><Code>InternalError</Code><Message>policy does not exist</Message></Error>", True),
        (500, b"<Error><Code>InternalError</Code><Message>disk failure</Message></Error>", False),
        (403, b"<Error><Code>AccessDenied</Code></Error>", False),
    ],
)
def test_absent_policy_detection_is_specific(status, body, missing):
    assert policies.missing_canned_policy(status, body) is missing


def test_missing_policy_is_created_with_the_approved_document():
    admin = FakeAdmin(404, b"")
    assert policies.ensure_policy(admin, "role-default-analyst", policies.policy_document("role-default-analyst")) == "created"
    assert admin.created == ("role-default-analyst", policies.policy_document("role-default-analyst"))


def test_existing_policy_in_string_form_is_accepted_when_equal():
    document = policies.policy_document("role-default-writer")
    admin = FakeAdmin(200, json.dumps({"policy": json.dumps(document)}).encode())
    assert policies.ensure_policy(admin, "role-default-writer", document) == "already-present"
    assert admin.created is None


def test_conflicting_policy_is_refused_without_revealing_documents():
    existing = policies.policy_document("role-default-owner")
    admin = FakeAdmin(200, json.dumps({"policy": existing}).encode())
    with pytest.raises(policies.PolicyBootstrapError) as error:
        policies.ensure_policy(admin, "role-default-analyst", policies.policy_document("role-default-analyst"))
    assert "role-default-analyst" in str(error.value)
    assert "arn:aws" not in str(error.value)
    assert admin.created is None


def test_read_levels_include_console_metadata_but_no_configuration_writes():
    for group in ("role-default-developer", "role-default-analyst", "role-default-writer"):
        actions = {a for s in policies.policy_document(group)["Statement"] for a in s["Action"]}
        assert CONSOLE_METADATA_READS <= actions
        assert not any(a.startswith(("s3:Put", "s3:DeleteBucket")) and a != "s3:PutObject" for a in actions)


def test_exact_previous_definition_is_upgraded_and_verified():
    group = "role-default-developer"
    admin = FakeAdmin(200, json.dumps({"policy": policies.previous_policy_document(group)}).encode())
    outcome = policies.ensure_policy(admin, group, policies.policy_document(group), policies.previous_policy_document(group))
    assert outcome == "updated"
    assert admin.created == (group, policies.policy_document(group))


def test_previous_definition_differs_only_by_console_metadata():
    for group in ("role-default-developer", "role-default-analyst", "role-default-writer"):
        previous = {a for s in policies.previous_policy_document(group)["Statement"] for a in s["Action"]}
        current = {a for s in policies.policy_document(group)["Statement"] for a in s["Action"]}
        assert previous < current
        assert not (current - previous) & {"s3:PutObject", "s3:DeleteObject"}
    owner = "role-default-owner"
    assert policies.previous_policy_document(owner) == policies.policy_document(owner)


def test_unreadable_existing_policy_is_refused():
    admin = FakeAdmin(200, b"not json")
    with pytest.raises(policies.PolicyBootstrapError):
        policies.ensure_policy(admin, "role-default-owner", policies.policy_document("role-default-owner"))


# ---- Property-based tests (PBT-02, PBT-03) ----


@settings(print_blob=True)
@given(policy_documents)
def test_p1_policy_json_round_trip_preserves_canonical_form(document):
    assert policies.canonical_policy(json.loads(json.dumps(document))) == policies.canonical_policy(document)


@settings(print_blob=True)
@given(shuffled_documents())
def test_p2_canonical_form_ignores_ordering(pair):
    document, shuffled = pair
    assert policies.canonical_policy(shuffled) == policies.canonical_policy(document)


@settings(print_blob=True)
@given(policy_documents)
def test_p3_policies_are_allow_only_and_bucket_scoped(document):
    for statement in document["Statement"]:
        assert statement["Effect"] == "Allow"
        assert set(statement["Resource"]) <= ALLOWED_RESOURCES
        assert statement["Action"]
        if "arn:aws:s3:::*" in statement["Resource"]:
            assert statement["Action"] == ["s3:ListAllMyBuckets"]


@settings(print_blob=True)
@given(product_group_sets, buckets, s3_actions)
def test_p4_group_union_equals_per_bucket_highest_access(groups, bucket, action):
    combined = policies.access_document(policies.effective_access(groups))
    for resource in (f"arn:aws:s3:::{bucket}", f"arn:aws:s3:::{bucket}/*"):
        any_member = any(allows(policies.policy_document(group), action, resource) for group in groups)
        assert any_member == allows(combined, action, resource)


@settings(print_blob=True)
@given(product_groups, access_maps, st.booleans())
def test_p5_existing_policy_is_accepted_iff_canonically_equal(group, other_access, previous_actions):
    desired = policies.policy_document(group)
    previous = policies.previous_policy_document(group)
    level_actions = policies.PREVIOUS_ACCESS_LEVEL_ACTIONS if previous_actions else policies.ACCESS_LEVEL_ACTIONS
    existing = policies.access_document(other_access, level_actions)
    admin = FakeAdmin(200, json.dumps({"policy": existing}).encode())
    canonical = policies.canonical_policy(existing)
    if canonical == policies.canonical_policy(desired):
        assert policies.ensure_policy(admin, group, desired, previous) == "already-present"
        assert admin.created is None
    elif canonical == policies.canonical_policy(previous):
        assert policies.ensure_policy(admin, group, desired, previous) == "updated"
    else:
        with pytest.raises(policies.PolicyBootstrapError):
            policies.ensure_policy(admin, group, desired, previous)
        assert admin.created is None
