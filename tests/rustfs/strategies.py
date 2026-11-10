"""Reusable Hypothesis generators for RustFS product-group policy tests."""

import importlib.util
from pathlib import Path

from hypothesis import strategies as st


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "rustfs_bootstrap_policies", ROOT / "infra/rustfs/bootstrap-policies.py"
)
policies = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policies)

product_groups = st.sampled_from(sorted(policies.ACCESS_MATRIX))
product_group_sets = st.sets(product_groups, min_size=1)
buckets = st.sampled_from(policies.BUCKETS)
access_levels = st.sampled_from(policies.LEVELS)
access_maps = st.dictionaries(buckets, access_levels)
policy_documents = st.one_of(
    product_groups.map(policies.policy_document),
    access_maps.map(policies.access_document),
)
S3_ACTIONS = sorted(
    {
        "s3:ListAllMyBuckets",
        *policies.READ_BUCKET_ACTIONS,
        *policies.READ_OBJECT_ACTIONS,
        *policies.WRITE_BUCKET_ACTIONS,
        *policies.WRITE_OBJECT_ACTIONS,
        "s3:PutBucketPolicy",
        "s3:DeleteBucket",
        "s3:PutLifecycleConfiguration",
    }
)
s3_actions = st.sampled_from(S3_ACTIONS)


@st.composite
def shuffled_documents(draw, documents=policy_documents):
    """A generated document plus an equivalent copy with every list reordered."""
    document = draw(documents)
    statements = [
        {
            **statement,
            "Action": draw(st.permutations(statement["Action"])),
            "Resource": draw(st.permutations(statement["Resource"])),
        }
        for statement in document["Statement"]
    ]
    return document, {**document, "Statement": draw(st.permutations(statements))}

# Bucket names as the product model allows them (checkpoint keys).
bucket_names = st.from_regex(r"\A[a-z0-9][a-z0-9-]{1,30}[a-z0-9]\Z")
