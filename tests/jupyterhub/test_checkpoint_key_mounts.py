"""Jupyter checkpoint key mounts: which dev keys a user's server receives (s3-checkpoints R12, R13, P2)."""

import json
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/products"))
import product_strategies as ps  # noqa: E402

from infra.jupyter.hub.lakehouse_policy import checkpoint_buckets, checkpoint_key_volumes  # noqa: E402

DEFAULT = ps.dp.load_all()


def test_owners_and_developers_get_the_dev_key_and_nobody_gets_uat_or_prod():
    dev = next(p for p in DEFAULT if p.name == "default").environment("dev").bucket
    for role in ("owner", "developer"):
        assert checkpoint_buckets([f"role-default-{role}"], DEFAULT) == (dev,)
    for groups in (["role-default-analyst"], ["role-default-writer"], ["role-platform-admin"], [], "role-default-owner", [1]):
        assert checkpoint_buckets(groups, DEFAULT) == ()


def test_staged_keys_become_read_only_mounts(tmp_path):
    staged = tmp_path / "checkpoint-keys"
    staged.mkdir()
    (staged / "bucket-a-dev").write_text(json.dumps({"access_key": "ckpt-bucket-a-dev", "secret_key": "x"}))
    volumes = checkpoint_key_volumes(("bucket-a-dev",), "/host/runtime/checkpoint-keys", staged)
    assert volumes == {"/host/runtime/checkpoint-keys/bucket-a-dev": {"bind": "/run/secrets/lakehouse-checkpoints/bucket-a-dev", "mode": "ro"}}
    assert checkpoint_key_volumes((), "/host/runtime/checkpoint-keys", staged) == {}


def test_a_missing_or_symlinked_key_or_a_bad_host_folder_fails_the_spawn(tmp_path):
    staged = tmp_path / "checkpoint-keys"
    staged.mkdir()
    with pytest.raises(RuntimeError, match="bucket-a-dev"):
        checkpoint_key_volumes(("bucket-a-dev",), "/host/runtime/checkpoint-keys", staged)
    (staged / "bucket-b-dev").write_text("{}")
    (staged / "bucket-a-dev").symlink_to(staged / "bucket-b-dev")
    with pytest.raises(RuntimeError, match="bucket-a-dev"):
        checkpoint_key_volumes(("bucket-a-dev",), "/host/runtime/checkpoint-keys", staged)
    for host in ("relative/checkpoint-keys", "/host/runtime/other"):
        with pytest.raises(RuntimeError, match="host folder"):
            checkpoint_key_volumes((), host, staged)


def test_the_spawner_wires_the_mounts_into_admission():
    spawner = (ROOT / "infra/jupyter/hub/lakehouse_spawner.py").read_text()
    assert "checkpoint_key_volumes(\n            checkpoint_buckets(oauth_user.get(\"groups\"))" in spawner
    config = (ROOT / "infra/jupyter/hub/jupyterhub_config.py").read_text()
    assert 'checkpoint_keys_host_dir = os.environ["JUPYTERHUB_CHECKPOINT_KEYS_HOST_DIR"]' in config
    compose = (ROOT / "compose.jupyter.yml").read_text()
    assert "./.runtime/container-mounts/checkpoint-keys:/run/secrets/checkpoint-keys:ro" in compose


roles = st.sampled_from(ps.dp.ROLES)


@settings(derandomize=True, print_blob=True, max_examples=200)
@given(ps.product_sets, st.lists(st.tuples(st.integers(0, 4), roles), max_size=6), st.lists(st.sampled_from(["role-platform-admin", "other", ""]), max_size=2))
def test_p2_selected_buckets_are_dev_buckets_of_owner_or_developer_products_only(products, picks, extra):
    groups = [products[i % len(products)].group(role) for i, role in picks] if products else []
    selected = checkpoint_buckets(groups + extra, products)
    expected = {p.environment("dev").bucket for p in products if {p.group("owner"), p.group("developer")} & set(groups)}
    assert set(selected) == expected
    never = {env.bucket for p in products for env in p.environments if env.key != "dev"}
    assert not set(selected) & never


# --- StarRocks CA for lakehouse_starrocks.connect() (AC-22) ------------------------------

from infra.jupyter.hub.lakehouse_policy import starrocks_ca_volume  # noqa: E402


def test_the_starrocks_ca_is_mounted_read_only_when_the_hub_has_it(tmp_path):
    hub_copy = tmp_path / "starrocks-ca.crt"
    assert starrocks_ca_volume("/host/.runtime/container-mounts/starrocks-ca.crt", hub_copy) == {}  # the Hub has no copy: StarRocks off
    hub_copy.write_text("cert")
    assert starrocks_ca_volume("/host/.runtime/container-mounts/starrocks-ca.crt", hub_copy) == {
        "/host/.runtime/container-mounts/starrocks-ca.crt": {"bind": str(hub_copy), "mode": "ro"}}
    for host in ("", "relative/starrocks-ca.crt", "/host/other.crt"):
        assert starrocks_ca_volume(host, hub_copy) == {}


def test_the_spawner_passes_the_starrocks_settings():
    config = (ROOT / "infra/jupyter/hub/jupyterhub_config.py").read_text()
    assert 'starrocks_ca_host_path = os.environ.get("JUPYTERHUB_STARROCKS_CA_HOST_PATH", "")' in config
    assert '"LAKEHOUSE_STARROCKS_CA": "/run/certs/starrocks-ca.crt"' in config and '"LAKEHOUSE_STARROCKS_HOST": "starrocks-fe"' in config
    assert "volumes.update(starrocks_ca_volume(spawner.starrocks_ca_host_path, STARROCKS_CA))" in (ROOT / "infra/jupyter/hub/lakehouse_spawner.py").read_text()
    compose = (ROOT / "compose.jupyter.yml").read_text()
    assert "./.runtime/container-mounts/starrocks-ca.crt:/run/certs/starrocks-ca.crt:ro" in compose
    start = (ROOT / "scripts/lakehouse.sh").read_text()
    assert start.index("prepare-starrocks-certificates.py\n    \"${COMPOSE[@]}\" up -d jupyterhub") > 0  # the CA exists before the Hub mounts it
