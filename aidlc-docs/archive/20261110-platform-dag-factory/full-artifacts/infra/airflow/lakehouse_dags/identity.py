"""The data product bundle a DAG file was checked out from (BR-4). Standard library only."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# <product>-main tracks the product's prod branch, <product>-uat its UAT branch. The
# product part matches the platform's data product names (and the broker's DAG_ID_PATTERN).
PRODUCT_BUNDLE = re.compile(r"(?P<product>[a-z][a-z0-9]{1,19})-(?P<branch>main|uat)")
ENVIRONMENTS = {"main": "prod", "uat": "uat"}
# Airflow 3 Git bundles check out to <storage>/<bundle>/tracking_repo or <storage>/<bundle>/versions/<commit>.
CHECKOUT_MARKERS = ("tracking_repo", "versions")


@dataclass(frozen=True)
class Identity:
    bundle: str
    product: str
    environment: str


def bundle_name(path: Path) -> str:
    for parent in Path(path).resolve().parents:
        if parent.name in CHECKOUT_MARKERS:
            return parent.parent.name
    raise ValueError(f"lakehouse_dags: {path} is not inside an Airflow bundle checkout")


def identity_for(path: Path) -> Identity:
    """The bundle, product, and environment for a file inside a bundle checkout."""
    name = bundle_name(path)
    match = PRODUCT_BUNDLE.fullmatch(name)
    if match is None:
        raise ValueError(f"lakehouse_dags: bundle {name!r} is not a data product bundle (<product>-main or <product>-uat)")
    return Identity(name, match["product"], ENVIRONMENTS[match["branch"]])
