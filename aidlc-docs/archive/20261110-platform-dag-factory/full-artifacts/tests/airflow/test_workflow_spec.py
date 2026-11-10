"""Workflow JSON v1, bundle identity, the validator, and the platform wiring (BR-1 to BR-4, BR-10; P1, P3, P4).

The spec, identity, and validator modules use only the standard library, so these
tests run on the host. The Airflow-side factory is tested in the Airflow image
(tests/airflow/test_dag_factory.py, scripts/verify/dag-factory-tests.sh).
"""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workflow_strategies as ws  # noqa: E402

from lakehouse_dags import identity, spec, validate  # noqa: E402

ROOT = ws.ROOT
DATA_PRODUCTS = ROOT / "infra/products/data_products.py"
EXAMPLE = {
    "apiVersion": spec.API_VERSION,
    "name": "test_environment",
    "schedule": None,
    "tasks": [
        {"name": "test_environment_first", "entrypoint": "test_environment.py"},
        {"name": "test_environment_second", "entrypoint": "test_environment.py", "runs_after": ["test_environment_first"]},
        {"name": "count_sample_rows", "entrypoint": "count_sample_rows.py", "runs_after": ["test_environment_first"],
         "args": ["--date", "2026-11-10"], "retries": 2, "retry_delay_seconds": 60, "execution_timeout_seconds": 3600},
    ],
}


def repository(tmp_path, documents=(EXAMPLE,)):
    for entrypoint in ("test_environment.py", "count_sample_rows.py"):
        (tmp_path / "notebooks/workload").mkdir(parents=True, exist_ok=True)
        (tmp_path / "notebooks/workload" / entrypoint).write_text("print('ok')\n")
    (tmp_path / "workflows").mkdir(exist_ok=True)
    for document in documents:
        (tmp_path / "workflows" / f"{document['name']}.json").write_text(json.dumps(document))
    (tmp_path / "dags").mkdir(exist_ok=True)
    (tmp_path / "dags/lakehouse.py").write_text(spec.STUB_TEXT)
    return tmp_path


def problems_for(tmp_path, document):
    _, problems = spec.parse_workflow(json.dumps(document), "workflows/test_environment.json", repository(tmp_path, ()))
    return problems


# --- Examples --------------------------------------------------------------------------


def test_the_example_parses_with_every_task_option(tmp_path):
    workflow, problems = spec.parse_workflow(json.dumps(EXAMPLE), "workflows/test_environment.json", repository(tmp_path))
    assert problems == []
    assert [task.name for task in workflow.tasks] == ["test_environment_first", "test_environment_second", "count_sample_rows"]
    last = workflow.tasks[2]
    assert (last.args, last.retries, last.retry_delay_seconds, last.execution_timeout_seconds) == (("--date", "2026-11-10"), 2, 60, 3600)
    assert spec.to_document(workflow) == EXAMPLE


@pytest.mark.parametrize("mutate, field", [
    (lambda d: d.update(extra=1), "extra"),
    (lambda d: d.update(apiVersion="v2"), "apiVersion"),
    (lambda d: d.update(name="other"), "name"),
    (lambda d: d.update(name=".hidden"), "name"),
    (lambda d: d.pop("schedule"), "schedule"),
    (lambda d: d.update(tags=["spark"]), "tags"),
    (lambda d: d.update(tags=["a b"]), "tags"),
    (lambda d: d.update(tasks=[]), "tasks"),
    (lambda d: d["tasks"][0].update(entrypoint="missing.py"), "tasks[0].entrypoint"),
    (lambda d: d["tasks"][0].update(entrypoint="../x.py"), "tasks[0].entrypoint"),
    (lambda d: d["tasks"][0].update(command="rm"), "tasks[0].command"),
    (lambda d: d["tasks"][1].update(runs_after=["nobody"]), "tasks[1].runs_after"),
    (lambda d: d["tasks"][1].update(runs_after=["test_environment_second"]), "tasks[1].runs_after"),
    (lambda d: d["tasks"][0].update(runs_after=["count_sample_rows"]), "tasks"),  # cycle
    (lambda d: d["tasks"][2].update(retries=True), "tasks[2].retries"),
    (lambda d: d["tasks"][2].update(retries=11), "tasks[2].retries"),
    (lambda d: d["tasks"][0].update(retry_delay_seconds=5), "tasks[0].retry_delay_seconds"),
    (lambda d: d["tasks"][2].update(execution_timeout_seconds=0), "tasks[2].execution_timeout_seconds"),
    (lambda d: d["tasks"][2].update(args="--date"), "tasks[2].args"),
    (lambda d: d["tasks"][2].update(args=["tab\there"]), "tasks[2].args"),
    (lambda d: d["tasks"][1].update(name="test_environment_first"), "tasks"),
])
def test_invalid_fields_are_refused_with_their_field_named(tmp_path, mutate, field):
    document = copy.deepcopy(EXAMPLE)
    mutate(document)
    assert field in {problem.field for problem in problems_for(tmp_path, document)}


def test_non_json_and_non_objects_are_problems_not_exceptions():
    assert spec.parse_workflow("{", "workflows/x.json")[1][0].message.startswith("is not valid JSON")
    assert spec.parse_workflow("[]", "workflows/x.json")[1][0].message == "must be a JSON object"


def test_identity_accepts_product_bundles_in_both_checkout_layouts(tmp_path):
    for layout in ("tracking_repo/dags/lakehouse.py", "versions/0123abc/dags/lakehouse.py"):
        assert identity.identity_for(tmp_path / "default-main" / layout) == identity.Identity("default-main", "default", "prod")
        assert identity.identity_for(tmp_path / "sales-uat" / layout) == identity.Identity("sales-uat", "sales", "uat")
    for bundle in ("lakehouse-main", "dev", "default-dev", "Default-main", "default-main-x"):
        if bundle == "lakehouse-main":
            continue  # a valid product name pattern; the platform reserves 'lakehouse', checked below
        with pytest.raises(ValueError, match="not a data product bundle"):
            identity.identity_for(tmp_path / bundle / "tracking_repo/dags/lakehouse.py")
    with pytest.raises(ValueError, match="not inside an Airflow bundle checkout"):
        identity.identity_for(tmp_path / "somewhere/dags/lakehouse.py")


def test_identity_matches_the_platform_product_and_dag_id_rules():
    sys.path.insert(0, str(ROOT / "infra/products"))
    import data_products

    assert identity.PRODUCT_BUNDLE.pattern.split("-(?P<branch>")[0] == data_products.DAG_ID_PATTERN.pattern.split("-(?P<env>")[0].lstrip("^")
    # 'lakehouse' is a reserved product name, so legacy lakehouse-main bundles never come from a product file.
    assert "lakehouse" in data_products.RESERVED_NAMES


def test_validator_accepts_a_clean_repository_and_lists_every_problem(tmp_path, capsys):
    root = repository(tmp_path)
    assert validate.main([str(root)]) == 0 and capsys.readouterr().out == "OK: 1 workflow(s)\n"
    (root / "dags/lakehouse.py").write_text(spec.STUB_TEXT + "import os\n")
    (root / "dags/extra.py").write_text("from airflow import DAG\n")
    (root / "workflows/notes.txt").write_text("x")
    assert validate.main([str(root)]) == 1
    out = capsys.readouterr().out.splitlines()
    assert out[-1] == "3 problem(s)"
    assert any(line.startswith("dags/extra.py: only the stub belongs") for line in out)
    assert any(line.startswith("dags/lakehouse.py: differs from the platform stub") for line in out)
    assert any(line.startswith("workflows/notes.txt: only *.json") for line in out)


def test_validator_accepts_a_repository_without_workflows_and_crlf_stubs(tmp_path, capsys):
    (tmp_path / "dags").mkdir()
    (tmp_path / "dags/lakehouse.py").write_bytes(spec.STUB_TEXT.replace("\n", "\r\n").encode())
    assert validate.main([str(tmp_path)]) == 0 and "OK: 0 workflow(s)" in capsys.readouterr().out


def test_the_stub_passes_airflow_safe_mode_discovery():
    content = spec.STUB_TEXT.lower()
    assert "airflow" in content and "dag" in content  # might_contain_dag_via_default_heuristic (Airflow 3.3.2)
    compile(spec.STUB_TEXT, "dags/lakehouse.py", "exec")


def test_the_jenkins_wrapper_runs_the_validator(tmp_path):
    wrapper = ROOT / "infra/jenkins/bin/lakehouse-validate-workflows"
    assert "PYTHONPATH=/opt/lakehouse/python exec python3 -m lakehouse_dags.validate" in wrapper.read_text()
    result = subprocess.run([sys.executable, "-m", "lakehouse_dags.validate", str(repository(tmp_path))],
                            env={"PYTHONPATH": str(ROOT / "infra/airflow")}, capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout == "OK: 1 workflow(s)\n"


def test_platform_wiring_mounts_the_package_read_only_where_it_is_used():
    airflow = (ROOT / "compose.airflow.yml").read_text()
    mount = "./infra/airflow/lakehouse_dags:/opt/lakehouse/python/lakehouse_dags:ro"
    for service in ("  airflow-scheduler:\n", "  airflow-dag-processor:\n"):
        block = airflow.split(service, 1)[1].split("\n  airflow-", 1)[0]
        assert mount in block and "PYTHONPATH: /opt/lakehouse/python" in block
    assert airflow.count(mount) == 2  # not in the API server, the triggerer, or the broker
    jenkins = (ROOT / "compose.jenkins.yml").read_text()
    assert mount in jenkins
    assert "./infra/jenkins/bin/lakehouse-validate-workflows:/usr/local/bin/lakehouse-validate-workflows:ro" in jenkins
    for path in (DATA_PRODUCTS, ROOT / "infra/airflow/validate-bundle-config.py"):
        assert '"sparse_dirs": ["dags", "workflows", "notebooks", "configs"]' in path.read_text()


def test_the_package_imports_without_airflow():
    result = subprocess.run([sys.executable, "-c", "import lakehouse_dags, lakehouse_dags.spec, lakehouse_dags.identity, lakehouse_dags.validate, sys; "
                             "print('airflow' in sys.modules)"], env={"PYTHONPATH": str(ROOT / "infra/airflow")}, capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout.strip() == "False"


# --- Properties ------------------------------------------------------------------------


@settings(print_blob=True, max_examples=150, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(workflow=ws.workflows())
def test_p1_valid_workflows_round_trip_through_json(tmp_path_factory, workflow):
    root = ws.write_repository(tmp_path_factory.mktemp("repo"), [workflow])
    parsed, problems = spec.parse_workflow(json.dumps(spec.to_document(workflow)), workflow.source, root)
    assert problems == [] and parsed == workflow


MUTATIONS = {
    "unknown key": (lambda d: d.update(surprise=1), "surprise"),
    "bad name": (lambda d: d.update(name="has space"), "name"),
    "boolean retries": (lambda d: d["tasks"][0].update(retries=True), "tasks[0].retries"),
    "out of range timeout": (lambda d: d["tasks"][0].update(execution_timeout_seconds=86401), "tasks[0].execution_timeout_seconds"),
    "missing entrypoint": (lambda d: d["tasks"][0].update(entrypoint="not_there_zz.py"), "tasks[0].entrypoint"),
    "self dependency": (lambda d: d["tasks"][0].update(runs_after=[d["tasks"][0]["name"]]), "tasks[0].runs_after"),
    "unknown task key": (lambda d: d["tasks"][0].update(shell="x"), "tasks[0].shell"),
}


@settings(print_blob=True, max_examples=150, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(workflow=ws.workflows(), mutation=st.sampled_from(sorted(MUTATIONS)))
def test_p3_any_single_invalid_field_is_reported_and_never_raises(tmp_path_factory, workflow, mutation):
    root = ws.write_repository(tmp_path_factory.mktemp("repo"), [workflow])
    document = spec.to_document(workflow)
    mutate, field = MUTATIONS[mutation]
    mutate(document)
    _, problems = spec.parse_workflow(json.dumps(document), workflow.source, root)
    assert field in {problem.field for problem in problems}


@settings(print_blob=True, max_examples=150)
@given(product=st.from_regex(r"[a-z][a-z0-9]{1,19}", fullmatch=True), branch=st.sampled_from(["main", "uat"]),
       layout=st.sampled_from(["tracking_repo", "versions/abc123"]),
       other=st.from_regex(r"[a-z0-9-]{1,30}", fullmatch=True).filter(lambda n: not identity.PRODUCT_BUNDLE.fullmatch(n)))
def test_p4_product_bundles_map_and_everything_else_is_refused(product, branch, layout, other):
    base = Path("/opt/airflow/dag_bundles")
    found = identity.identity_for(base / f"{product}-{branch}" / layout / "dags/lakehouse.py")
    assert found == identity.Identity(f"{product}-{branch}", product, {"main": "prod", "uat": "uat"}[branch])
    with pytest.raises(ValueError):
        identity.identity_for(base / other / layout / "dags/lakehouse.py")
