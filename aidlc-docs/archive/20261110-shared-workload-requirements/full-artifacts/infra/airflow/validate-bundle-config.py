#!/usr/bin/env python3
"""Fail closed unless the Git Bundle list is the one generated from the data products.

Every product with a `repo` contributes exactly two GitDagBundles, `<name>-main`
and `<name>-uat`, from one credential-free repository. Inside the Airflow image
the shape is checked; with --host-paths (scripts/lakehouse.sh) the list must also
equal the list generated from data-products/*.yaml, and the bundle host root must
be this repository's .runtime/airflow-dag-bundles.
"""

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

CLASSPATH = "airflow.providers.git.bundles.git.GitDagBundle"
NAME = re.compile(r"^(?P<product>[a-z][a-z0-9]{1,19})-(?P<env>main|uat)$")
FIXED_KWARGS = {"git_conn_id": "lakehouse_git", "refresh_interval": 300, "sparse_dirs": ["dags", "workflows", "notebooks", "configs"], "subdir": "dags"}


def fail(message: str) -> None:
    raise SystemExit(f"Airflow configuration error: {message}")


def validate(configs: object, expected: list | None = None) -> None:
    """Shape rules for any product set; equality with `expected` when given."""
    if not isinstance(configs, list):
        fail("the Bundle configuration must be a JSON list")
    seen: dict[str, dict] = {}
    for bundle in configs:
        if not isinstance(bundle, dict) or not isinstance(bundle.get("name"), str):
            fail("each Bundle must be an object with a string name")
        name = bundle["name"]
        match = NAME.fullmatch(name)
        if not match:
            fail(f"Bundle name {name!r} must be <product>-main or <product>-uat")
        if name in seen:
            fail(f"duplicate Bundle name: {name}")
        if bundle.get("classpath") != CLASSPATH:
            fail(f"{name} must use the GitDagBundle provider")
        kwargs = bundle.get("kwargs")
        if not isinstance(kwargs, dict):
            fail(f"{name} requires GitDagBundle kwargs")
        for key, value in FIXED_KWARGS.items():
            if kwargs.get(key) != value:
                fail(f"{name} must set {key} to {value!r}")
        if not isinstance(kwargs.get("tracking_ref"), str) or not kwargs["tracking_ref"]:
            fail(f"{name} requires a tracking_ref branch")
        repo_url = kwargs.get("repo_url")
        if not isinstance(repo_url, str):
            fail(f"{name} requires a repo_url")
        parsed = urlsplit(repo_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            fail("Bundle repositories must be credential-free https URLs")
        seen[name] = bundle
    products = {NAME.fullmatch(name).group("product") for name in seen}
    for product in products:
        main, uat = seen.get(f"{product}-main"), seen.get(f"{product}-uat")
        if main is None or uat is None:
            fail(f"product {product} must have both {product}-main and {product}-uat")
        if main["kwargs"]["repo_url"] != uat["kwargs"]["repo_url"]:
            fail(f"{product}-main and {product}-uat must use the same repository")
    if expected is not None and configs != expected:
        fail("the Bundle list differs from the one generated from data-products/*.yaml; regenerate it")


def main() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    missing = [name for name in ("LAKEHOUSE_BUNDLE_HOST_ROOT", "LAKEHOUSE_BUNDLE_CONTAINER_ROOT") if not os.environ.get(name)]
    if missing:
        fail("required Bundle path inputs are missing")
    host_root = Path(os.environ["LAKEHOUSE_BUNDLE_HOST_ROOT"])
    container_root = Path(os.environ["LAKEHOUSE_BUNDLE_CONTAINER_ROOT"])
    if not (host_root.is_absolute() and container_root.is_absolute()):
        fail("Bundle roots must be absolute paths")
    host_paths = "--host-paths" in sys.argv[1:]
    if host_paths and host_root != repository_root / ".runtime" / "airflow-dag-bundles":
        fail("Bundle host root must be this repository's ignored .runtime/airflow-dag-bundles directory")
    text = os.environ.get("LAKEHOUSE_BUNDLE_CONFIG_LIST", os.environ.get("AIRFLOW__DAG_PROCESSOR__DAG_BUNDLE_CONFIG_LIST", ""))
    if text == "":
        fail("the Bundle configuration is missing")
    try:
        configs = json.loads(text)
    except json.JSONDecodeError:
        fail("Bundle configuration must be valid JSON")
    expected = None
    if host_paths:
        sys.path.insert(0, str(repository_root / "infra" / "products"))
        import data_products

        expected = data_products.bundle_config(data_products.load_all())
    validate(configs, expected)
    print(f"Airflow paths and the {len(configs)} product Bundles are valid.")


if __name__ == "__main__":
    main()
