#!/usr/bin/env python3
"""Fail closed unless the maintained main and UAT Git Bundles are configured."""

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit


def fail(message: str) -> None:
    raise SystemExit(f"Airflow configuration error: {message}")


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
required = (
    "LAKEHOUSE_BUNDLE_HOST_ROOT",
    "LAKEHOUSE_BUNDLE_CONTAINER_ROOT",
)
missing = [name for name in required if not os.environ.get(name)]
if missing:
    fail("required path or main/UAT Bundle inputs are missing")

bundle_host_root = Path(os.environ["LAKEHOUSE_BUNDLE_HOST_ROOT"])
bundle_container_root = Path(os.environ["LAKEHOUSE_BUNDLE_CONTAINER_ROOT"])
if not all(path.is_absolute() for path in (bundle_host_root, bundle_container_root)):
    fail("Bundle roots must be absolute paths")
# The host root is only meaningful on the host; inside the image this file is not in the repository.
if "--host-paths" in sys.argv[1:] and bundle_host_root != REPOSITORY_ROOT / ".runtime" / "airflow-dag-bundles":
    fail("Bundle host root must be this repository's ignored .runtime/airflow-dag-bundles directory")
try:
    config_text = os.environ.get(
        "LAKEHOUSE_BUNDLE_CONFIG_LIST",
        os.environ.get("AIRFLOW__DAG_PROCESSOR__DAG_BUNDLE_CONFIG_LIST", ""),
    )
    if not config_text:
        fail("the main/UAT Bundle configuration is missing")
    configs = json.loads(config_text)
except (TypeError, json.JSONDecodeError):
    fail("Bundle configuration must be valid JSON")

expected = {
    "lakehouse-main": "main",
    "lakehouse-uat": "uat",
}
if not isinstance(configs, list) or len(configs) != len(expected):
    fail("configure exactly lakehouse-main (main) and lakehouse-uat (uat)")

by_name = {}
for bundle in configs:
    if not isinstance(bundle, dict):
        fail("each Bundle configuration must be an object")
    name = bundle.get("name")
    if not isinstance(name, str):
        fail("each Bundle must have a string name")
    if name in by_name:
        fail(f"duplicate Bundle name: {name}")
    by_name[name] = bundle

if set(by_name) != set(expected):
    fail("Bundle names must be exactly lakehouse-main and lakehouse-uat")

shared_repo_url = None
for name, tracking_ref in expected.items():
    bundle = by_name[name]
    if bundle.get("classpath") != "airflow.providers.git.bundles.git.GitDagBundle":
        fail(f"{name} must use the GitDagBundle provider")
    kwargs = bundle.get("kwargs")
    if not isinstance(kwargs, dict):
        fail(f"{name} requires GitDagBundle kwargs")
    if kwargs.get("tracking_ref") != tracking_ref:
        fail(f"{name} must track {tracking_ref}")
    if kwargs.get("git_conn_id") != "lakehouse_git":
        fail(f"{name} must use the lakehouse_git Airflow connection")
    if kwargs.get("refresh_interval") != 300:
        fail(f"{name} must refresh every 300 seconds")
    if kwargs.get("sparse_dirs") != ["dags", "configs", "notebooks"]:
        fail(f"{name} must sparse-checkout dags, configs, and notebooks")
    repo_url = kwargs.get("repo_url")
    if not isinstance(repo_url, str) or not repo_url.strip():
        fail(f"{name} requires a repo_url")
    parsed_url = urlsplit(repo_url)
    if parsed_url.username or parsed_url.password:
        fail("do not embed Git credentials in the repository URL; use lakehouse_git")
    if shared_repo_url is None:
        shared_repo_url = repo_url
    elif repo_url != shared_repo_url:
        fail("lakehouse-main and lakehouse-uat must use the same repository URL")

print("Airflow paths and the maintained main/UAT Bundle list are valid.")
