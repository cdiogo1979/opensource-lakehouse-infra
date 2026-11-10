"""Build a product workflow's Airflow DAG and run its Spark tasks (BR-5 to BR-8).

Ported from the workload repository's ``dags/dag_factory.py``. Every task callable
is platform code: the scheduler, which holds the Docker socket and the broker
control token, imports no product repository module. Repository code runs only
inside the run's Spark container (the config check and the entry points).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import ssl
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

import docker
from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.providers.standard.operators.python import PythonOperator
from airflow.task.trigger_rule import TriggerRule

from .identity import Identity
from .redact import redact_spark_output
from .spec import Workflow

CONTAINER_BUNDLE_ROOT = Path("/opt/lakehouse-bundle")
LOGGER = logging.getLogger(__name__)
# Runs inside the Spark container with the repository's own loader (BR-6).
VALIDATE_SNIPPET = (
    "import sys; sys.path.insert(0, '/opt/lakehouse-bundle/notebooks/common'); "
    "from config_loader import load_environment_config; "
    "load_environment_config(sys.argv[1], sys.argv[2], sys.argv[3])"
)


class LakehouseOperator(PythonOperator):
    """A PythonOperator that renders no templates.

    Workflow ``args`` are product-authored strings that end up in the Spark
    container's command line. With templating, ``{{ conn.<id>.password }}`` or
    ``{{ var.value.<key> }}`` would be rendered by the scheduler and handed to the
    product's code, so arguments are always passed exactly as written.
    """

    template_fields = ()
    template_ext = ()


def _container_name(dag_id: str, run_id: str) -> str:
    """A stable, Docker-safe container name for one DAG run."""
    safe_dag_id = re.sub(r"[^a-zA-Z0-9_.-]", "-", dag_id)
    run_suffix = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:12]
    return f"lakehouse-{safe_dag_id[:40]}-{run_suffix}"


def _docker_host_bundle_path(bundle_source: str) -> str:
    """Translate an Airflow-container bundle path to its Docker-host path."""
    host_root_value = os.environ.get("LAKEHOUSE_BUNDLE_HOST_ROOT")
    container_root_value = os.environ.get("LAKEHOUSE_BUNDLE_CONTAINER_ROOT")
    if not host_root_value or not container_root_value:
        raise AirflowException("LAKEHOUSE_BUNDLE_HOST_ROOT and LAKEHOUSE_BUNDLE_CONTAINER_ROOT must be configured.")
    host_root = Path(host_root_value)
    container_root = Path(container_root_value)
    if not host_root.is_absolute() or not container_root.is_absolute():
        raise AirflowException("Airflow bundle host and container roots must be absolute paths.")
    try:
        relative_bundle = Path(bundle_source).resolve().relative_to(container_root.resolve())
    except ValueError as error:
        raise AirflowException("The versioned DAG bundle path is outside LAKEHOUSE_BUNDLE_CONTAINER_ROOT.") from error
    return str(host_root / relative_bundle)


def _read_broker_control_token() -> str:
    """Read the scheduler-only broker control credential without logging it."""
    path = Path(os.environ.get("AIRFLOW_BROKER_CONTROL_TOKEN_FILE", "/run/secrets/airflow_broker_control_token"))
    try:
        token = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise AirflowException("The broker control credential is unavailable.") from error
    if len(token) < 32:
        raise AirflowException("The broker control credential is invalid.")
    return token


def _broker_request(method: str, route: str, payload: Mapping[str, Any] | None, credential: str) -> dict[str, Any] | None:
    """Call the private broker over verified TLS; failures never echo response details."""
    base_url = os.environ.get("LAKEHOUSE_BROKER_URL", "https://airflow-token-broker:8443").rstrip("/")
    parsed = urlsplit(base_url)
    if (parsed.scheme, parsed.hostname, parsed.port) != ("https", "airflow-token-broker", 8443) or any(
        (parsed.path, parsed.query, parsed.fragment, parsed.username, parsed.password)
    ):
        raise AirflowException("The token broker endpoint is not the approved private HTTPS service.")
    ca_file = os.environ.get("LAKEHOUSE_BROKER_CA_FILE", "/run/certs/airflow-token-broker-ca.crt")
    try:
        context = ssl.create_default_context(cafile=ca_file)
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{base_url}{route}",
            data=body,
            headers={"Authorization": f"Bearer {credential}", "Accept": "application/json", "Content-Type": "application/json"},
            method=method,
        )
        with urlopen(request, context=context, timeout=5) as response:  # nosec B310 - scheme, host, and CA are pinned above.
            raw = response.read()
        return json.loads(raw) if raw else None
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        raise AirflowException("The token broker request failed; sensitive response details were suppressed.") from None


def _create_spark_container(
    image: str,
    network: str,
    data_network: str,
    docker_url: str,
    bundle_source: str,
    environment: str,
    product: str,
    aws_region: str,
    broker_ca_host_path: str,
    broker_ca_container_path: str,
    **context: object,
) -> dict[str, str]:
    """Register the run with the broker and start its Spark container with the bundle mounted read-only."""
    dag_id = context["dag"].dag_id
    container_name = _container_name(dag_id, str(context["run_id"]))
    docker_bundle_source = _docker_host_bundle_path(bundle_source)
    control_token = _read_broker_control_token()
    registration = _broker_request("POST", "/v1/runs", {"dag_id": dag_id, "run_id": str(context["run_id"])}, control_token)
    if not isinstance(registration, dict):
        raise AirflowException("The token broker returned an invalid registration response.")
    run_handle = registration.get("run_handle")
    capability = registration.get("renewal_capability")
    initial_token = registration.get("access_token")
    if not all(isinstance(value, str) and value for value in (run_handle, capability, initial_token)):
        raise AirflowException("The token broker returned an incomplete registration response.")

    volumes = {
        docker_bundle_source: {"bind": str(CONTAINER_BUNDLE_ROOT), "mode": "ro"},
        broker_ca_host_path: {"bind": broker_ca_container_path, "mode": "ro"},
    }
    client = docker.DockerClient(base_url=docker_url)
    container = None
    try:
        try:
            client.containers.get(container_name).remove(force=True)
        except docker.errors.NotFound:
            pass
        container = client.containers.create(
            image=image,
            command=["sleep infinity"],
            name=container_name,
            network=network,
            entrypoint=["/bin/bash", "-lc"],
            labels={"lakehouse-local.role": "airflow-spark-run", "lakehouse-local.run-handle": run_handle},
            environment={
                "AWS_REGION": aws_region,
                "AWS_DEFAULT_REGION": aws_region,
                "AWS_EC2_METADATA_DISABLED": "true",
                "LAKEHOUSE_TOKEN_PROVIDER": "airflow",  # nosec B105 - provider selector, not a credential.
                "LAKEHOUSE_INITIAL_ACCESS_TOKEN": initial_token,
                "LAKEHOUSE_TOKEN_BROKER_URL": os.environ.get("LAKEHOUSE_BROKER_URL", "https://airflow-token-broker:8443"),
                "LAKEHOUSE_TOKEN_BROKER_CA": broker_ca_container_path,
                "LAKEHOUSE_RUN_HANDLE": run_handle,
                "LAKEHOUSE_RUN_CAPABILITY": capability,
                "SPARK_CONTAINER_ROLE": "driver",
                "SPARK_MASTER_HOST": "spark",
                "LAKEHOUSE_ENVIRONMENT": environment,
                "LAKEHOUSE_PRODUCT": product,
                "PYTHONPATH": str(CONTAINER_BUNDLE_ROOT),
            },
            volumes=volumes,
        )
        client.networks.get(data_network).connect(container)
        container.start()
        LOGGER.info("Started reusable Spark container %s for DAG run %s", container_name, context["run_id"])
        return {"container_name": container.name, "run_handle": run_handle}
    except Exception:
        if container is not None:
            try:
                container.remove(force=True)
            except docker.errors.DockerException:
                LOGGER.warning("Failed Spark container cleanup after startup error.")
        try:
            _broker_request("DELETE", f"/v1/runs/{quote(run_handle, safe='')}", None, control_token)
        except AirflowException:
            LOGGER.warning("Broker run revocation failed after Spark startup error; bounded expiry remains active.")
        raise
    finally:
        client.close()


def _run_in_container(command: list[str], label: str, docker_url: str, **context: object) -> None:
    """Run one command in this DAG run's Spark container; fail the task on a non-zero exit."""
    run_state = context["ti"].xcom_pull(task_ids="create_cluster")
    container_name = run_state.get("container_name") if isinstance(run_state, dict) else None
    if not container_name:
        raise AirflowException("The Spark container was not registered for this DAG run.")
    client = docker.DockerClient(base_url=docker_url)
    try:
        result = client.containers.get(container_name).exec_run(command, workdir=str(CONTAINER_BUNDLE_ROOT), demux=False)
        output = redact_spark_output(result.output or b"")
        if result.exit_code != 0:
            LOGGER.error("%s failed; sanitized output follows:\n%s", label, output)
            raise AirflowException(f"{label} exited with status {result.exit_code}.")
        LOGGER.info("%s succeeded; sanitized output follows:\n%s", label, output)
    finally:
        client.close()


def validate_command(environment: str, product: str) -> list[str]:
    return ["python3", "-c", VALIDATE_SNIPPET, environment, str(CONTAINER_BUNDLE_ROOT / "configs"), product]


def submit_command(entrypoint: str, environment: str, spark_master: str, args: tuple[str, ...] = ()) -> list[str]:
    """``spark-submit`` for one task; ``args`` follow ``--`` and are never shell-interpreted (BR-7)."""
    command = [
        "/opt/spark/bin/spark-submit",
        "--master",
        spark_master,
        str(CONTAINER_BUNDLE_ROOT / "notebooks" / "workload" / entrypoint),
        "--environment",
        environment,
        "--config-dir",
        str(CONTAINER_BUNDLE_ROOT / "configs"),
    ]
    return command + ["--", *args] if args else command


def _validate_environment(environment: str, product: str, docker_url: str, **context: object) -> None:
    _run_in_container(validate_command(environment, product), "Environment config check", docker_url, **context)


def _submit_spark_job(entrypoint: str, environment: str, spark_master: str, args: list[str], docker_url: str, **context: object) -> None:
    _run_in_container(submit_command(entrypoint, environment, spark_master, tuple(args)), f"Spark workload {entrypoint}", docker_url, **context)


def _stop_spark_container(docker_url: str, **context: object) -> None:
    """Remove this DAG run's Spark container and revoke its broker run, also after failures."""
    container_name = _container_name(context["dag"].dag_id, str(context["run_id"]))
    run_state = context["ti"].xcom_pull(task_ids="create_cluster") or {}
    run_handle = run_state.get("run_handle") if isinstance(run_state, dict) else None
    cleanup_errors = []
    client = docker.DockerClient(base_url=docker_url)
    try:
        try:
            container = client.containers.get(container_name)
        except docker.errors.NotFound:
            LOGGER.info("Spark container %s is already absent.", container_name)
        else:
            try:
                container.remove(force=True)
                LOGGER.info("Stopped and removed Spark container %s.", container_name)
            except docker.errors.DockerException:
                cleanup_errors.append("container")
    finally:
        client.close()
    if isinstance(run_handle, str) and run_handle:
        try:
            _broker_request("DELETE", f"/v1/runs/{quote(run_handle, safe='')}", None, _read_broker_control_token())
        except AirflowException:
            cleanup_errors.append("broker")
    if cleanup_errors:
        raise AirflowException("Airflow writer-run cleanup was incomplete; broker expiry remains the fallback.")


def _verify_workloads_succeeded() -> None:
    """An all-success leaf after every workload and the cleanup task."""


def dag_kwargs(workflow: Workflow, identity: Identity) -> dict[str, Any]:
    names = ", ".join(task.name for task in workflow.tasks)
    return {
        "dag_id": f"{identity.bundle}-{workflow.name}",
        "description": workflow.description or f"Run {workflow.name} ({names}) in one Spark container for {identity.bundle}.",
        "start_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "schedule": workflow.schedule,
        "catchup": False,
        "tags": [identity.bundle, "spark", *workflow.tags],
        "rerun_with_latest_version": False,
    }


def _task_options(task) -> dict[str, Any]:
    options: dict[str, Any] = {}
    if task.retries is not None:
        options["retries"] = task.retries
    if task.retry_delay_seconds is not None:
        options["retry_delay"] = timedelta(seconds=task.retry_delay_seconds)
    if task.execution_timeout_seconds is not None:
        options["execution_timeout"] = timedelta(seconds=task.execution_timeout_seconds)
    return options


def build_dag(workflow: Workflow, bundle_root: Path, identity: Identity) -> DAG:
    """The DAG for one validated workflow of a product bundle checkout."""
    docker_url = os.environ.get("LAKEHOUSE_DOCKER_URL", "unix://var/run/docker.sock")
    docker_network = os.environ.get("LAKEHOUSE_SPARK_DOCKER_NETWORK")
    broker_ca_host_path = os.environ.get("LAKEHOUSE_BROKER_CA_HOST_PATH", "")
    if not docker_network or not Path(broker_ca_host_path).is_absolute():
        raise AirflowException("The Spark networks and broker CA mount must be configured.")
    spark_master = os.environ.get("LAKEHOUSE_SPARK_MASTER", "local[*]")

    dag = DAG(**dag_kwargs(workflow, identity))
    create_cluster = LakehouseOperator(
        task_id="create_cluster",
        python_callable=_create_spark_container,
        op_kwargs={
            "image": os.environ.get("LAKEHOUSE_SPARK_IMAGE", "local/lakehouse-spark-runtime:3.5.5_1.10.2"),
            "network": docker_network,
            "data_network": os.environ.get("LAKEHOUSE_SPARK_DATA_NETWORK", "lakehouse-local_data-access"),
            "docker_url": docker_url,
            "bundle_source": str(bundle_root),
            "environment": identity.environment,
            "product": identity.product,
            "aws_region": os.environ.get("AWS_REGION", "us-east-1"),
            "broker_ca_host_path": broker_ca_host_path,
            "broker_ca_container_path": os.environ.get("LAKEHOUSE_BROKER_CA_CONTAINER_PATH", "/run/certs/airflow-token-broker-ca.crt"),
        },
        dag=dag,
    )
    validate_environment = LakehouseOperator(
        task_id="validate_environment",
        python_callable=_validate_environment,
        op_kwargs={"environment": identity.environment, "product": identity.product, "docker_url": docker_url},
        dag=dag,
    )
    submits = {
        task.name: LakehouseOperator(
            task_id=f"submit_{task.name}",
            python_callable=_submit_spark_job,
            op_kwargs={
                "entrypoint": task.entrypoint,
                "environment": identity.environment,
                "spark_master": spark_master,
                "args": list(task.args),
                "docker_url": docker_url,
            },
            dag=dag,
            **_task_options(task),
        )
        for task in workflow.tasks
    }
    stop_cluster = LakehouseOperator(
        task_id="stop_cluster",
        python_callable=_stop_spark_container,
        op_kwargs={"docker_url": docker_url},
        trigger_rule=TriggerRule.ALL_DONE,
        dag=dag,
    )
    verify = LakehouseOperator(task_id="verify_workloads_succeeded", python_callable=_verify_workloads_succeeded, dag=dag)

    create_cluster >> validate_environment
    for task in workflow.tasks:
        submit = submits[task.name]
        for predecessor in task.runs_after or ():
            submits[predecessor] >> submit
        if not task.runs_after:
            validate_environment >> submit
        submit >> stop_cluster
        submit >> verify
    stop_cluster >> verify
    return dag
