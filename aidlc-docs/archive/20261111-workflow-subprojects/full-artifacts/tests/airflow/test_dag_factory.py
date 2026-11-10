"""The platform DAG factory inside Airflow (BR-5 to BR-9; P2).

Airflow and the Docker SDK live only in the Airflow image, so these tests skip on
the host; run them with scripts/verify/dag-factory-tests.sh. Docker and the broker
are faked; nothing here starts a container.
"""

import json
import sys
from datetime import timedelta
from pathlib import Path

import pytest

pytest.importorskip("airflow.exceptions")  # not just "airflow": tests/airflow is a namespace package on the host
pytest.importorskip("docker")

from hypothesis import HealthCheck, given, settings  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workflow_strategies as ws  # noqa: E402

import lakehouse_dags  # noqa: E402
from airflow.exceptions import AirflowException  # noqa: E402
from lakehouse_dags import factory, spec  # noqa: E402
from lakehouse_dags.identity import Identity  # noqa: E402

IDENTITY = Identity("default-uat", "default", "uat")
GOLDEN = {
    "apiVersion": spec.API_VERSION,
    "name": "test_environment",
    "schedule": None,
    "tasks": [
        {"name": "test_environment_first", "entrypoint": "test_environment.py"},
        {"name": "test_environment_second", "entrypoint": "test_environment.py", "runs_after": ["test_environment_first"]},
        {"name": "count_sample_rows", "entrypoint": "count_sample_rows.py", "runs_after": ["test_environment_first"]},
    ],
}


@pytest.fixture(autouse=True)
def airflow_settings(monkeypatch, tmp_path):
    ca = tmp_path / "ca.crt"
    ca.write_text("ca")
    monkeypatch.setenv("LAKEHOUSE_SPARK_DOCKER_NETWORK", "lakehouse-local_airflow-spark")
    monkeypatch.setenv("LAKEHOUSE_BROKER_CA_HOST_PATH", str(ca))
    monkeypatch.setenv("LAKEHOUSE_BUNDLE_HOST_ROOT", "/host/bundles")
    monkeypatch.setenv("LAKEHOUSE_BUNDLE_CONTAINER_ROOT", "/opt/airflow/dag_bundles")


def bundle(tmp_path, name="default-uat", documents=(GOLDEN,)):
    """A product bundle checkout at <storage>/<bundle>/tracking_repo with the stub."""
    root = tmp_path / name / "tracking_repo"
    (root / "dags").mkdir(parents=True)
    (root / "dags/lakehouse.py").write_text(spec.STUB_TEXT)
    (root / "notebooks/workload").mkdir(parents=True)
    for entrypoint in ("test_environment.py", "count_sample_rows.py"):
        (root / "notebooks/workload" / entrypoint).write_text("print('ok')\n")
    if documents:
        (root / "workflows").mkdir()
        for document in documents:
            (root / "workflows" / f"{document['name']}.json").write_text(json.dumps(document))
    return root


def load(root):
    namespace = {}
    lakehouse_dags.load_workflows(namespace, str(root / "dags/lakehouse.py"))
    return namespace


def edges(dag):
    return {(task.task_id, downstream) for task in dag.tasks for downstream in sorted(task.downstream_task_ids)}


def test_the_golden_workflow_builds_todays_dag_with_validation_in_the_container(tmp_path):
    namespace = load(bundle(tmp_path))
    dag = namespace["dag_default_uat_test_environment"]
    assert dag.dag_id == "default-uat-test_environment" and set(dag.tags) == {"default-uat", "spark"}  # Airflow 3 keeps tags as a set
    assert dag.schedule is None
    assert dag.catchup is False
    assert sorted(task.task_id for task in dag.tasks) == sorted([
        "create_cluster", "install_requirements", "validate_environment", "submit_test_environment_first", "submit_test_environment_second",
        "submit_count_sample_rows", "stop_cluster", "verify_workloads_succeeded"])
    assert edges(dag) == {
        ("create_cluster", "install_requirements"),
        ("install_requirements", "validate_environment"),
        ("validate_environment", "submit_test_environment_first"),
        ("submit_test_environment_first", "submit_test_environment_second"),
        ("submit_test_environment_first", "submit_count_sample_rows"),
        *{(f"submit_{name}", leaf) for name in ("test_environment_first", "test_environment_second", "count_sample_rows")
          for leaf in ("stop_cluster", "verify_workloads_succeeded")},
        ("stop_cluster", "verify_workloads_succeeded"),
    }
    assert dag.get_task("stop_cluster").trigger_rule == "all_done"
    create = dag.get_task("create_cluster").op_kwargs
    assert (create["environment"], create["product"]) == ("uat", "default")
    assert create["bundle_source"] == str(tmp_path / "default-uat/tracking_repo")


def test_every_callable_is_platform_code():
    """No task callable comes from a product repository module (NFR-1)."""
    workflow, _ = spec.parse_workflow(json.dumps(GOLDEN), "workflows/test_environment.json")
    dag = factory.build_dag(workflow, Path("/opt/airflow/dag_bundles/default-uat/tracking_repo"), IDENTITY)
    assert {task.python_callable.__module__ for task in dag.tasks} == {"lakehouse_dags.factory"}


def test_task_options_and_args_reach_only_their_submit_task(tmp_path):
    document = json.loads(json.dumps(GOLDEN))
    document["tasks"][2].update(args=["--date", "2026-11-10"], retries=3, retry_delay_seconds=30, execution_timeout_seconds=600)
    dag = load(bundle(tmp_path, documents=(document,)))["dag_default_uat_test_environment"]
    task = dag.get_task("submit_count_sample_rows")
    assert (task.retries, task.retry_delay, task.execution_timeout) == (3, timedelta(seconds=30), timedelta(seconds=600))
    assert task.op_kwargs["args"] == ["--date", "2026-11-10"]
    assert dag.get_task("submit_test_environment_first").op_kwargs["args"] == []


def test_no_task_renders_templates_so_args_cannot_read_connections_or_variables(tmp_path):
    document = json.loads(json.dumps(GOLDEN))
    document["tasks"][0]["args"] = ["{{ conn.lakehouse_git.password }}", "{{ var.value.secret }}"]
    dag = load(bundle(tmp_path, documents=(document,)))["dag_default_uat_test_environment"]
    for task in dag.tasks:
        assert isinstance(task, factory.LakehouseOperator) and task.template_fields == () and task.template_ext == ()
    submit = dag.get_task("submit_test_environment_first")
    submit.render_template_fields({"conn": None, "var": None})
    assert submit.op_kwargs["args"] == ["{{ conn.lakehouse_git.password }}", "{{ var.value.secret }}"]


def test_commands_pass_args_after_double_dash_as_a_list():
    base = ["/opt/spark/bin/spark-submit", "--master", "local[*]", "/opt/lakehouse-bundle/notebooks/workload/job.py",
            "--environment", "uat", "--config-dir", "/opt/lakehouse-bundle/configs"]
    assert factory.submit_command("job.py", "uat", "local[*]") == base
    assert factory.submit_command("job.py", "uat", "local[*]", ("--x", "a b; rm -rf /")) == base + ["--", "--x", "a b; rm -rf /"]
    assert factory.validate_command("uat", "default") == ["/opt/lakehouse/venv/bin/python", "-c", factory.VALIDATE_SNIPPET, "uat", "/opt/lakehouse-bundle/configs", "default"]
    assert "config_loader" in factory.VALIDATE_SNIPPET and "/opt/lakehouse-bundle/notebooks/common" in factory.VALIDATE_SNIPPET


def test_install_requirements_runs_the_platform_tool_with_retries_and_no_workflow_options(tmp_path):
    """BR-A1 to BR-A4: the product's root requirements.txt, constrained by the image's lock; 2 retries, 30 s."""
    document = json.loads(json.dumps(GOLDEN))
    document["tasks"][0].update(retries=7, retry_delay_seconds=5)
    dag = load(bundle(tmp_path, documents=(document,)))["dag_default_uat_test_environment"]
    install = dag.get_task("install_requirements")
    assert (install.retries, install.retry_delay) == (2, timedelta(seconds=30))
    assert install.downstream_task_ids == {"validate_environment"}
    assert factory.install_command() == [
        "/opt/lakehouse/venv/bin/python", "/opt/lakehouse/workload_python.py", "install-extras",
        "/opt/lakehouse-bundle/requirements.txt", "--lock", "/opt/lakehouse/requirements.lock"]


def test_install_requirements_runs_in_the_registered_container_and_failures_are_redacted(monkeypatch, caplog):
    container = FakeContainer(exit_code=1, output=b"ERROR: ResolutionImpossible token=abc")
    monkeypatch.setattr(factory.docker, "DockerClient", lambda base_url: FakeDocker(container))
    with pytest.raises(AirflowException, match="Product requirements install exited with status 1"):
        factory._install_requirements("unix://x", **context({"container_name": "existing"}))
    assert container.commands[0] == (factory.install_command(), "/opt/lakehouse-bundle")
    assert "token=abc" not in caplog.text


def test_load_workflows_reports_every_problem_and_builds_nothing(tmp_path):
    bad = dict(GOLDEN, name="broken", tasks=[{"name": "a", "entrypoint": "nope.py"}])
    root = bundle(tmp_path, documents=(GOLDEN, bad))
    namespace = {}
    with pytest.raises(spec.WorkflowError) as error:
        lakehouse_dags.load_workflows(namespace, str(root / "dags/lakehouse.py"))
    assert "workflows/broken.json: tasks[0].entrypoint" in str(error.value) and namespace == {}


def test_no_workflows_means_no_dags_and_non_product_bundles_are_refused(tmp_path):
    assert load(bundle(tmp_path, documents=())) == {}
    with pytest.raises(ValueError, match="not a data product bundle"):
        load(bundle(tmp_path, name="lakehouse-dev"))


# --- Ported container, broker, and cleanup behavior (BR-8) ----------------------------


class FakeContainer:
    def __init__(self, exit_code=0, output=b"ok"):
        self.name = "c"
        self.exit_code, self.output = exit_code, output
        self.commands, self.removed, self.started = [], False, False

    def exec_run(self, command, workdir, demux):
        self.commands.append((command, workdir))
        return type("Result", (), {"exit_code": self.exit_code, "output": self.output})()

    def remove(self, force):
        self.removed = True

    def start(self):
        self.started = True


class FakeDocker:
    def __init__(self, container):
        self.container, self.created, self.connected = container, None, []
        outer = self

        class Containers:
            def get(self, name):
                if outer.created is None and name != "existing":
                    import docker
                    raise docker.errors.NotFound("absent")
                return outer.container

            def create(self, **kwargs):
                outer.created = kwargs
                return outer.container

        class Networks:
            def get(self, name):
                return type("Network", (), {"connect": lambda _, c: outer.connected.append(name)})()

        self.containers, self.networks = Containers(), Networks()

    def close(self):
        pass


class Ti:
    def __init__(self, state):
        self.state = state

    def xcom_pull(self, task_ids):
        return self.state


def context(state=None):
    return {"dag": type("Dag", (), {"dag_id": "default-uat-test_environment"})(), "run_id": "manual__1", "ti": Ti(state)}


def test_container_names_are_stable_and_docker_safe():
    name = factory._container_name("default-uat-test environment/x", "run-1")
    assert name == factory._container_name("default-uat-test environment/x", "run-1")
    assert name.startswith("lakehouse-default-uat-test-environment-x-") and len(name.rsplit("-", 1)[1]) == 12


def test_bundle_paths_translate_to_the_host_and_refuse_outsiders():
    assert factory._docker_host_bundle_path("/opt/airflow/dag_bundles/default-uat/versions/abc") == "/host/bundles/default-uat/versions/abc"
    with pytest.raises(AirflowException):
        factory._docker_host_bundle_path("/etc")


def test_the_broker_endpoint_is_pinned(monkeypatch):
    monkeypatch.setenv("LAKEHOUSE_BROKER_URL", "https://evil.example:8443")
    with pytest.raises(AirflowException, match="not the approved private HTTPS service"):
        factory._broker_request("POST", "/v1/runs", {}, "x" * 40)


def test_create_cluster_mounts_the_bundle_read_only_and_passes_only_run_scoped_values(monkeypatch):
    container = FakeContainer()
    fake = FakeDocker(container)
    monkeypatch.setattr(factory.docker, "DockerClient", lambda base_url: fake)
    monkeypatch.setattr(factory, "_read_broker_control_token", lambda: "t" * 40)
    monkeypatch.setattr(factory, "_broker_request", lambda *a: {"run_handle": "h", "renewal_capability": "cap", "access_token": "tok"})
    state = factory._create_spark_container(
        image="img", network="net", data_network="data", docker_url="unix://x", bundle_source="/opt/airflow/dag_bundles/default-uat/versions/abc",
        environment="uat", product="default", aws_region="us-east-1", broker_ca_host_path="/ca", broker_ca_container_path="/run/ca", **context())
    assert state == {"container_name": "c", "run_handle": "h"} and container.started and fake.connected == ["data"]
    assert fake.created["volumes"]["/host/bundles/default-uat/versions/abc"] == {"bind": "/opt/lakehouse-bundle", "mode": "ro"}
    environment = fake.created["environment"]
    assert (environment["LAKEHOUSE_ENVIRONMENT"], environment["LAKEHOUSE_PRODUCT"], environment["PYTHONPATH"]) == ("uat", "default", "/opt/lakehouse-bundle")
    assert "t" * 40 not in json.dumps(environment)  # the control token never reaches the container


def test_create_cluster_failure_removes_the_container_and_revokes_the_run(monkeypatch):
    container = FakeContainer()
    fake = FakeDocker(container)
    fake.networks.get = lambda name: (_ for _ in ()).throw(RuntimeError("network down"))
    calls = []
    monkeypatch.setattr(factory.docker, "DockerClient", lambda base_url: fake)
    monkeypatch.setattr(factory, "_read_broker_control_token", lambda: "t" * 40)
    monkeypatch.setattr(factory, "_broker_request", lambda method, *a: calls.append(method) or {"run_handle": "h", "renewal_capability": "c", "access_token": "a"})
    with pytest.raises(RuntimeError):
        factory._create_spark_container("img", "net", "data", "unix://x", "/opt/airflow/dag_bundles/default-uat/versions/abc",
                                        "uat", "default", "us-east-1", "/ca", "/run/ca", **context())
    assert container.removed and calls == ["POST", "DELETE"]


def test_commands_run_in_the_registered_container_and_failures_are_redacted(monkeypatch, caplog):
    container = FakeContainer(exit_code=3, output=b"boom password=hunter2 Bearer abc.def")
    monkeypatch.setattr(factory.docker, "DockerClient", lambda base_url: FakeDocker(container))
    with pytest.raises(AirflowException, match="exited with status 3"):
        factory._validate_environment("uat", "default", "unix://x", **context({"container_name": "existing"}))
    assert container.commands[0] == (factory.validate_command("uat", "default"), "/opt/lakehouse-bundle")
    assert "hunter2" not in caplog.text and "<redacted>" in caplog.text
    with pytest.raises(AirflowException, match="not registered"):
        factory._submit_spark_job("job.py", "uat", "local[*]", [], "unix://x", **context(None))


def test_stop_cluster_removes_the_container_and_revokes(monkeypatch):
    container = FakeContainer()
    fake = FakeDocker(container)
    fake.created = {}  # the container exists
    calls = []
    monkeypatch.setattr(factory.docker, "DockerClient", lambda base_url: fake)
    monkeypatch.setattr(factory, "_read_broker_control_token", lambda: "t" * 40)
    monkeypatch.setattr(factory, "_broker_request", lambda method, route, *a: calls.append((method, route)))
    factory._stop_spark_container("unix://x", **context({"container_name": "c", "run_handle": "h/1"}))
    assert container.removed and calls == [("DELETE", "/v1/runs/h%2F1")]


# --- Property ------------------------------------------------------------------------


@settings(print_blob=True, max_examples=60, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
@given(workflow=ws.workflows())
def test_p2_the_task_graph_follows_runs_after_and_cleanup_comes_last(tmp_path_factory, workflow):
    root = tmp_path_factory.mktemp("bundles") / "sales-main" / "tracking_repo"
    ws.write_repository(root, [workflow])
    dag = load(root)[next(iter(load(root)))]
    assert dag.dag_id == f"sales-main-{workflow.name}" and set(dag.tags) == {"sales-main", "spark", *workflow.tags}
    for task in workflow.tasks:
        submit = dag.get_task(f"submit_{task.name}")
        expected = {f"submit_{name}" for name in task.runs_after} or {"validate_environment"}
        assert submit.upstream_task_ids == expected
        assert {"stop_cluster", "verify_workloads_succeeded"} <= submit.downstream_task_ids
        assert submit.op_kwargs["args"] == list(task.args)
    assert dag.get_task("validate_environment").upstream_task_ids == {"install_requirements"}
    assert dag.get_task("install_requirements").upstream_task_ids == {"create_cluster"}


def test_a_subproject_task_runs_its_entrypoint_from_the_subproject_folder():
    """workflow-subprojects FR-2, FR-3: the DAG ID stays <bundle>-<name>; the code comes from notebooks/workload/<project>/."""
    workflow, problems = spec.parse_workflow(json.dumps(GOLDEN), "workflows/sample/test_environment.json", project="sample")
    assert problems == []
    dag = factory.build_dag(workflow, Path("/opt/airflow/dag_bundles/default-uat/tracking_repo"), IDENTITY)
    assert dag.dag_id == "default-uat-test_environment"
    submit = dag.get_task("submit_count_sample_rows")
    assert submit.op_kwargs["entrypoint"] == "sample/count_sample_rows.py"
    command = factory.submit_command(submit.op_kwargs["entrypoint"], "uat", "local[*]")
    assert command[3] == "/opt/lakehouse-bundle/notebooks/workload/sample/count_sample_rows.py"


def test_a_layer_entrypoint_runs_from_the_subproject_layer_folder():
    """CR-1: entrypoint "<layer>/<file>.py" runs notebooks/workload/<project>/<layer>/<file>.py."""
    document = json.loads(json.dumps(GOLDEN))
    for task in document["tasks"]:
        task["entrypoint"] = "ops/" + task["entrypoint"]
    workflow, problems = spec.parse_workflow(json.dumps(document), "workflows/sample/test_environment.json", project="sample")
    assert problems == []
    submit = factory.build_dag(workflow, Path("/opt/airflow/dag_bundles/default-uat/tracking_repo"), IDENTITY).get_task("submit_count_sample_rows")
    command = factory.submit_command(submit.op_kwargs["entrypoint"], "uat", "local[*]")
    assert command[3] == "/opt/lakehouse-bundle/notebooks/workload/sample/ops/count_sample_rows.py"
