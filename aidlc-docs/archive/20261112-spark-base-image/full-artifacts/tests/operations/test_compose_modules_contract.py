"""Contracts for the modular Compose layout and the cleanup of retired files."""

import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULES = ("compose.core.yml", "compose.jupyter.yml", "compose.jenkins.yml", "compose.starrocks.yml", "compose.airflow.yml")
SKIP = {"aidlc-docs", ".agents", ".claude", ".runtime", ".git", ".pytest_cache", ".hypothesis", "__pycache__"}
RETIRED = (
    "docker-compose.yml", "docker-compose.airflow.yml", "docker-compose.starrocks.yml", "docker-compose.deferred.yml",
    "infra/tpch-generator", "infra/tpch-loader", "infra/identity-provisioner", "infra/bucket-init",
    "infra/polaris/reset-default-product-once.py", "scripts/prepare-ranger-test-secrets.sh", "infra/jupyter/examples",
    "Jenkinsfile", "scripts/migrate-jenkins-home.py",
)


def repository_text_files():
    for path in ROOT.rglob("*"):
        if path.is_file() and not SKIP & set(path.relative_to(ROOT).parts) and path.suffix in {".py", ".sh", ".yml", ".yaml", ".md", ".example", ".conf", ".txt", ""}:
            try:
                yield path, path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue


def test_module_files_exist_and_only_core_names_the_project():
    for name in MODULES:
        assert (ROOT / name).is_file(), name
    assert (ROOT / "compose.core.yml").read_text().count("name: lakehouse-local\n") == 1
    for name in MODULES[1:]:
        assert not re.search(r"^name:", (ROOT / name).read_text(), re.M), name


def test_each_module_owns_the_expected_services():
    def services(name):
        text = (ROOT / name).read_text()
        body = text.split("\nservices:\n", 1)[1]
        body = re.split(r"\n(?:networks|volumes|secrets):\n", body, maxsplit=1)[0]
        return set(re.findall(r"^  ([a-z][a-z0-9-]*):$", body, re.M))
    assert services("compose.core.yml") == {"keycloak-db", "keycloak", "polaris-db", "polaris-schema-init", "polaris", "polaris-group-reconciler", "rustfs", "ldap"}
    assert services("compose.jupyter.yml") == {"jupyterhub"}
    assert services("compose.jenkins.yml") == {"jenkins"}
    assert services("compose.starrocks.yml") == {"starrocks-fe", "starrocks-be"}


def test_resource_names_are_unchanged():
    text = "".join((ROOT / name).read_text() for name in MODULES)
    for resource in ("lakehouse-local_core", "lakehouse-local_jupyter-user", "lakehouse-local_data-access", "lakehouse-local_rustfs-identity",
                     "lakehouse-local_keycloak-db-data", "lakehouse-local_polaris-db-data", "lakehouse-local_rustfs-data", "lakehouse-local_ldap-data",
                     "lakehouse-local_jupyterhub-state", "lakehouse-local_jenkins-home", "lakehouse-local_starrocks"):
        assert resource in text, resource


def test_retired_files_are_gone_and_unreferenced():
    for path in RETIRED:
        assert not (ROOT / path).exists(), path
    this_file = Path(__file__).resolve()
    pattern = re.compile(r"docker-compose[.a-z]*\.yml|tpch-(?:generator|loader)|identity-provisioner|bucket-init|reset-default-product-once|prepare-ranger-test-secrets|migrate-jenkins-home|remove-legacy-jenkins|jupyter/examples")
    offenders = [str(path.relative_to(ROOT)) for path, text in repository_text_files()
                 if path.resolve() != this_file and path.name != "test_legacy_retirement.py" and pattern.search(text)]
    assert offenders == []


def test_every_compose_invocation_names_its_files():
    offenders = []
    for path, text in repository_text_files():
        if path.suffix not in {".py", ".sh"}:
            continue
        for line in text.splitlines():
            if re.search(r'docker compose (?!version)|"docker", "compose", "(?!-f)', line) and "compose.core.yml" not in line \
                    and "COMPOSE[@]" not in line and "COMPOSE=(" not in line:
                offenders.append(f"{path.relative_to(ROOT)}: {line.strip()}")
    assert offenders == []


def test_lakehouse_builds_the_file_list_from_flags():
    lakehouse = (ROOT / "scripts/lakehouse.sh").read_text()
    for flag, module in (("JUPYTER_ENABLED", "compose.jupyter.yml"), ("JENKINS_ENABLED", "compose.jenkins.yml"), ("STARROCKS_ENABLED", "compose.starrocks.yml")):
        assert f'if [[ "${flag}" == true ]]; then MODULE_FILES+=(-f {module})' in lakehouse
    assert 'COMPOSE=(docker compose -f compose.core.yml ${MODULE_FILES[@]+"${MODULE_FILES[@]}"})' in lakehouse
    assert 'AIRFLOW_COMPOSE=("${COMPOSE[@]}" -f compose.airflow.yml --profile airflow)' in lakehouse
    env = (ROOT / ".env.example").read_text()
    assert "JUPYTER_ENABLED=true" in env and "JENKINS_ENABLED=true" in env and "STARROCKS_ENABLED=true" in env


def test_module_combinations_render(tmp_path):
    env = {"JUPYTERHUB_BROKER_CA_HOST_PATH": "x", "LAKEHOUSE_BROKER_CA_HOST_PATH": "x", "LAKEHOUSE_BUNDLE_HOST_ROOT": "/x",
           "LAKEHOUSE_BUNDLE_CONTAINER_ROOT": "/opt/airflow/dag_bundles", "LAKEHOUSE_BUNDLE_CONFIG_LIST": "x", "AIRFLOW_UID": "50000",
           "DOCKER_GID": "0", "LAKEHOUSE_CHECKPOINT_KEYS_HOST_DIR": "/x/checkpoint-keys"}
    env = {**os.environ, **env}
    for combo in ((), ("compose.jupyter.yml",), ("compose.jenkins.yml",), ("compose.starrocks.yml",), MODULES[1:]):
        args = ["docker", "compose", "-f", "compose.core.yml"] + [part for name in combo for part in ("-f", name)] + ["config", "-q"]
        result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, env=env)
        assert result.returncode == 0, (combo, result.stderr[-300:])


def test_spark_smoke_checks_use_the_current_runtime_image():
    assert 'IMAGE="${SPARK_BOOTSTRAP_IMAGE:-local/lakehouse-spark-runtime:3.5.9_1.10.2}"' in (ROOT / "scripts/bootstrap/smoke-spark.sh").read_text()
    assert 'SPARK_IMAGE = "local/lakehouse-spark-runtime:3.5.9_1.10.2"' in (ROOT / "scripts/verify/role-matrix.py").read_text()
    for job in ("infra/spark-bootstrap/create_smoke_tables.py", "infra/spark-bootstrap/verify_role_matrix.py"):
        assert '".rest.auth.type": "oauth2"' in (ROOT / job).read_text(), job


def test_builds_are_reproducible_so_start_does_not_recreate_containers():
    for script in ("scripts/lakehouse.sh", "scripts/bootstrap-default-product.sh"):
        assert "export BUILDX_NO_DEFAULT_ATTESTATIONS=1" in (ROOT / script).read_text(), script


def test_partial_module_commands_never_suggest_removing_other_modules():
    for script in ("scripts/lakehouse.sh", "scripts/bootstrap-default-product.sh"):
        text = (ROOT / script).read_text()
        assert "export COMPOSE_IGNORE_ORPHANS=true" in text and "--remove-orphans" not in text.replace("suggest --remove-orphans", ""), script


def test_stop_stops_the_scheduled_reconciler_first_and_start_brings_it_back():
    """stop-reconciler: the reconciler stops before the services it reads and starts after them, once it exists."""
    lakehouse = (ROOT / "scripts/lakehouse.sh").read_text()
    stop = lakehouse[lakehouse.index("  stop)\n"):]
    stop = stop[:stop.index(";;")]
    assert 'if reconciler_exists; then "${RECONCILER_COMPOSE[@]}" stop polaris-group-reconciler; fi' in stop
    assert stop.index("stop polaris-group-reconciler") < stop.index("stop starrocks-be") < stop.index("stop keycloak polaris")
    start = lakehouse[lakehouse.index("start_stack() {"):lakehouse.index("prepare_airflow_environment() {")]
    assert start.index('"${RECONCILER_COMPOSE[@]}" up -d polaris-group-reconciler') > start.index('up -d "${STARROCKS_SERVICES[@]}"')
    assert "reconciler_exists()" in lakehouse and "--profile scheduled-reconciliation" in lakehouse


def test_the_reconciler_loop_exits_on_stop_instead_of_being_killed():
    """stop-reconciler: PID 1 sh traps SIGTERM and sleeps interruptibly, so docker stop doesn't wait for the kill."""
    run = (ROOT / "infra/polaris/reconciler/run.sh").read_text()
    assert "trap 'echo \"Reconciler stopping\"; exit 0' TERM INT" in run
    assert 'sleep "$interval" &\n  wait $!' in run
