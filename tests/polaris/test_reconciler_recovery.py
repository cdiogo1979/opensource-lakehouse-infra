"""The scheduled reconciler runs current code, restores the StarRocks bind pattern first, and reports its health."""

import re
import subprocess
import sys
import time
from pathlib import Path

from hypothesis import given, settings, strategies as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/starrocks"))
from starrocks_strategies import reconcile, sr  # noqa: E402

COMPOSE = (ROOT / "compose.core.yml").read_text()
SERVICE = COMPOSE[COMPOSE.index("  polaris-group-reconciler:"):COMPOSE.index("  rustfs:")]
RUN = (ROOT / "infra/polaris/reconciler/run.sh").read_text()


def test_every_script_the_cycle_runs_is_mounted_read_only_from_the_repository():
    for script in re.findall(r"python (/opt/lakehouse/\S+\.py)", RUN):
        name = Path(script).name
        assert re.search(rf"- \./infra/\S*{re.escape(name)}:{re.escape(script)}:ro", SERVICE), script
    assert "- ./infra/products/data_products.py:/opt/lakehouse/products/data_products.py:ro" in SERVICE
    assert "- ./infra/starrocks/starrocks_common.py:/opt/lakehouse/starrocks/starrocks_common.py:ro" in SERVICE
    assert "- ./infra/polaris/reconciler/run.sh:/opt/lakehouse/run.sh:ro" in SERVICE
    assert 'ENTRYPOINT ["/bin/sh", "/opt/lakehouse/run.sh"]' in (ROOT / "infra/polaris/reconciler/Dockerfile").read_text()


def test_the_bind_pattern_step_runs_first_and_success_needs_every_step():
    assert RUN.index("--bind-pattern-only") < RUN.index("reconcile-keycloak-groups.py") < RUN.rindex("reconcile-starrocks-users.py")
    assert RUN.count("ok=false") == 3 and 'if [ "$ok" = true ]; then\n    date +%s > "$success_file"' in RUN


def test_bind_pattern_only_needs_neither_keycloak_nor_valid_product_files(monkeypatch, capsys):
    calls = []

    class Runner:
        def query(self, sql, operation):
            return []

    monkeypatch.setattr(reconcile.sr, "require_products", lambda: (_ for _ in ()).throw(AssertionError("product files must not be checked")))
    monkeypatch.setattr(reconcile, "read_keycloak_memberships", lambda *a: (_ for _ in ()).throw(AssertionError("Keycloak must not be read")))
    monkeypatch.setattr(reconcile.sr, "root_runner", lambda transport, path: Runner())
    monkeypatch.setattr(reconcile.sr, "ensure_ldap_login", lambda runner: calls.append(runner) or "set")
    monkeypatch.setattr(reconcile.sr, "starrocks_enabled", lambda: True)
    assert reconcile.main(["--bind-pattern-only", "--transport", "network"]) == 0
    assert len(calls) == 1 and "set again" in capsys.readouterr().out


def test_bind_pattern_only_fails_without_a_root_login(monkeypatch, capsys):
    monkeypatch.setattr(reconcile.sr, "starrocks_enabled", lambda: True)
    monkeypatch.setattr(reconcile.sr, "root_runner", lambda transport, path: (_ for _ in ()).throw(sr.StarRocksError("StarRocks root login failed")))
    assert reconcile.main(["--bind-pattern-only"]) == 1
    assert "bind pattern check failed" in capsys.readouterr().err


def test_status_lists_the_reconciler():
    launcher = (ROOT / "scripts/lakehouse.sh").read_text()
    assert "lakehouse-local-polaris-group-reconciler-1" in launcher[launcher.index("show_status() {"):]


HEALTHCHECK = re.search(r'test: \["CMD", "sh", "-c", "(.+)"\]', SERVICE).group(1).replace("$$", "$")


@settings(max_examples=40, deadline=None, print_blob=True)
@given(st.integers(0, 1500), st.sampled_from([60, 300, 600]))
def test_p1_the_healthcheck_is_healthy_exactly_within_two_intervals_and_a_minute(tmp_path_factory, age, interval):
    folder = tmp_path_factory.mktemp("health")
    stamp = folder / "reconcile-last-success"
    stamp.write_text(f"{int(time.time()) - age}\n")
    command = HEALTHCHECK.replace("/tmp/reconcile-last-success", str(stamp))
    result = subprocess.run(["sh", "-c", command], env={"RECONCILE_INTERVAL_SECONDS": str(interval), "PATH": "/usr/bin:/bin"}, capture_output=True)
    limit = 2 * interval + 60
    if age <= limit - 2:
        assert result.returncode == 0
    elif age > limit + 2:
        assert result.returncode != 0


def test_no_success_file_is_unhealthy(tmp_path):
    command = HEALTHCHECK.replace("/tmp/reconcile-last-success", str(tmp_path / "missing"))
    assert subprocess.run(["sh", "-c", command], env={"PATH": "/usr/bin:/bin"}).returncode != 0
