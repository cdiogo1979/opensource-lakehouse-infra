"""RustFS checkpoint keys, bootstrap-checkpoint-keys.py (s3-checkpoints R1 to R10, P1).

RustFS is replaced by an in-memory fake of the admin and S3 calls the script uses.
The live calls run in Build and Test.
"""

import importlib.util
import json
import stat
from pathlib import Path

import pytest
from hypothesis import given, settings

from strategies import bucket_names

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("rustfs_checkpoint_keys", ROOT / "infra/rustfs/bootstrap-checkpoint-keys.py")
ck = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ck)
policies = ck._load("rustfs_bootstrap_policies_test", "bootstrap-policies.py")
BUCKET = "bucket-sales-dev"


class FakeRustFS:
    endpoint = "http://rustfs.test"

    def __init__(self):
        self.users, self.policies, self.attached, self.calls = {}, {}, {}, []

    def request(self, method, path, query=None, body=b""):
        query = query or {}
        self.calls.append((method, path.rsplit("/", 1)[-1]))
        name = path.rsplit("/", 1)[-1]
        if name == "info-canned-policy":
            document = self.policies.get(query["name"])
            return (200, json.dumps({"policy": document}).encode()) if document else (404, b"")
        if name == "add-canned-policy":
            self.policies[query["name"]] = json.loads(body)
            return 200, b""
        if name == "remove-canned-policy":
            return (200, b"") if self.policies.pop(query["name"], None) else (404, b"")
        if name == "user-info":
            return (200, b"{}") if query["accessKey"] in self.users else (404, b"")
        if name == "add-user":
            self.users[query["accessKey"]] = json.loads(body)["secretKey"]
            return 200, b""
        if name == "set-user-or-group-policy":
            self.attached[query["userOrGroup"]] = query["policyName"]
            return 200, b""
        if name == "remove-user":
            self.attached.pop(query["accessKey"], None)
            return (200, b"") if self.users.pop(query["accessKey"], None) else (404, b"")
        raise AssertionError(f"unexpected call {method} {path}")

    def s3_client(self, endpoint, access_key, secret_key):
        fake = self

        class Client:
            def request(self, method, path, query=None, body=b""):
                return (200, b"") if fake.users.get(access_key) == secret_key else (403, b"")

        return Client()


@pytest.fixture
def setup(tmp_path):
    fake = FakeRustFS()
    keys = ck.Keys(fake, policies, fake.s3_client, store=tmp_path / "store", stage=tmp_path / "stage")
    return fake, keys, tmp_path


def stored(tmp_path, folder="store"):
    return json.loads((tmp_path / folder / BUCKET).read_text())


def test_converge_creates_policy_user_attachment_and_both_files(setup):
    fake, keys, tmp_path = setup
    assert keys.ensure(BUCKET) == "created"
    assert fake.policies["checkpoints-bucket-sales-dev"] == ck.checkpoint_policy(BUCKET)
    assert fake.attached == {"ckpt-bucket-sales-dev": "checkpoints-bucket-sales-dev"}
    key = stored(tmp_path)
    assert key["access_key"] == "ckpt-bucket-sales-dev" and fake.users[key["access_key"]] == key["secret_key"]
    assert stored(tmp_path, "stage") == key
    assert stat.S_IMODE((tmp_path / "store" / BUCKET).stat().st_mode) == 0o600
    assert stat.S_IMODE((tmp_path / "store").stat().st_mode) == 0o700
    assert stat.S_IMODE((tmp_path / "stage" / BUCKET).stat().st_mode) == 0o644
    assert stat.S_IMODE((tmp_path / "stage").stat().st_mode) == 0o755


def test_converge_is_idempotent_and_repairs_the_staged_copy(setup):
    fake, keys, tmp_path = setup
    keys.ensure(BUCKET)
    first = stored(tmp_path)
    (tmp_path / "stage" / BUCKET).unlink()
    assert keys.ensure(BUCKET) == "unchanged"
    assert stored(tmp_path) == first == stored(tmp_path, "stage")


def test_a_lost_or_mismatched_stored_key_is_reissued(setup):
    fake, keys, tmp_path = setup
    keys.ensure(BUCKET)
    fake.users["ckpt-bucket-sales-dev"] = "changed-elsewhere"
    assert keys.ensure(BUCKET) == "rotated"
    assert fake.users["ckpt-bucket-sales-dev"] == stored(tmp_path)["secret_key"]
    (tmp_path / "store" / BUCKET).unlink()
    assert keys.ensure(BUCKET) == "rotated"


def test_rotation_changes_rustfs_first_and_keeps_the_files_when_it_fails(setup):
    fake, keys, tmp_path = setup
    keys.ensure(BUCKET)
    before = stored(tmp_path)
    original = fake.request

    def failing(method, path, query=None, body=b""):
        return (500, b"") if path.endswith("add-user") else original(method, path, query, body)

    fake.request = failing
    with pytest.raises(ck.CheckpointKeyError, match="add-user failed"):
        keys.ensure(BUCKET, rotate=True)
    assert stored(tmp_path) == before == stored(tmp_path, "stage")
    fake.request = original
    assert keys.ensure(BUCKET, rotate=True) == "rotated" and stored(tmp_path) != before


def test_dry_run_writes_nothing(setup):
    fake, keys, tmp_path = setup
    assert keys.ensure(BUCKET, dry_run=True) == "created"
    assert not fake.users and not fake.policies and not (tmp_path / "store").exists()


def test_removal_deletes_user_then_policy_then_files_and_tolerates_absent_items(setup):
    fake, keys, tmp_path = setup
    keys.ensure(BUCKET)
    fake.calls.clear()
    assert keys.remove(BUCKET) == "removed"
    order = [name for _, name in fake.calls if name in ("remove-user", "remove-canned-policy")]
    assert order == ["remove-user", "remove-canned-policy"]
    assert not fake.users and not fake.policies and not (tmp_path / "store" / BUCKET).exists() and not (tmp_path / "stage" / BUCKET).exists()
    assert keys.remove(BUCKET) == "removed"


def test_stale_staged_keys_are_pruned(setup):
    fake, keys, tmp_path = setup
    keys.ensure(BUCKET)
    keys.ensure("bucket-old-dev")
    assert keys.prune_stage([BUCKET]) == ["bucket-old-dev"]
    assert sorted(p.name for p in (tmp_path / "stage").iterdir()) == [BUCKET]
    assert ck.missing_staged([BUCKET, "bucket-old-dev"], tmp_path / "stage") == ["bucket-old-dev"]


def test_invalid_bucket_names_are_refused():
    for bucket in ("", "UPPER", "a", "has_underscore", "-dash"):
        with pytest.raises(ck.CheckpointKeyError):
            ck.checkpoint_policy(bucket)


def test_the_output_never_contains_a_secret(setup, capsys):
    fake, keys, tmp_path = setup
    keys.ensure(BUCKET)
    keys.ensure(BUCKET, rotate=True)
    secret = stored(tmp_path)["secret_key"]
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err


def test_every_product_bucket_of_the_model_is_covered():
    products = ck.data_products.load_all()
    assert ck.product_buckets(products) == [env.bucket for product in products for env in product.environments]


@settings(derandomize=True, print_blob=True, max_examples=200)
@given(bucket_names)
def test_p1_the_policy_reaches_only_its_bucket_and_its_checkpoints_prefix(bucket):
    document = ck.checkpoint_policy(bucket)
    assert set(document) == {"Version", "Statement"} and len(document["Statement"]) == 2
    listing, objects = document["Statement"]
    assert all(statement["Effect"] == "Allow" for statement in document["Statement"])
    assert listing["Action"] == ["s3:ListBucket"] and listing["Resource"] == [f"arn:aws:s3:::{bucket}"]
    assert listing["Condition"] == {"StringLike": {"s3:prefix": ["checkpoints", "checkpoints/*"]}}
    assert sorted(objects["Action"]) == ["s3:DeleteObject", "s3:GetObject", "s3:PutObject"]
    assert objects["Resource"] == [f"arn:aws:s3:::{bucket}/checkpoints/*"] and "Condition" not in objects
    text = json.dumps(document)
    assert "admin:" not in text and "ListAllMyBuckets" not in text and "arn:aws:s3:::*" not in text


def test_the_index_maps_every_product_environment_to_its_bucket_without_secrets(tmp_path):
    products = ck.data_products.load_all()
    ck.write_index(products, tmp_path)
    index = json.loads((tmp_path / ck.INDEX).read_text())
    assert index == {p.name: {env.key: env.bucket for env in p.environments} for p in products}
    assert stat.S_IMODE((tmp_path / ck.INDEX).stat().st_mode) == 0o644
    # The index is not a key: pruning and the key check ignore it.
    keys = ck.Keys(FakeRustFS(), policies, None, store=tmp_path / "store", stage=tmp_path)
    assert keys.prune_stage([]) == []


def test_a_policy_returned_with_reordered_condition_values_compares_equal():
    document = ck.checkpoint_policy(BUCKET)
    returned = json.loads(json.dumps(document))
    returned["Statement"][0]["Condition"]["StringLike"]["s3:prefix"].reverse()
    assert policies.canonical_policy(returned) == policies.canonical_policy(document)
    returned["Statement"][0]["Condition"]["StringLike"]["s3:prefix"] = ["checkpoints/*", "other"]
    assert policies.canonical_policy(returned) != policies.canonical_policy(document)
