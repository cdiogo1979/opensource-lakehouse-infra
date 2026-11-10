#!/usr/bin/env python3
"""Render the Airflow Git Bundle list from the data product files.

Every product with a `repo` block gets `<name>-main` (its prod branch) and
`<name>-uat` (its UAT branch); repositories are read anonymously.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "infra" / "products"))
import data_products  # noqa: E402

try:
    print(json.dumps(data_products.bundle_config(data_products.load_all()), separators=(",", ":")))
except data_products.ProductError as error:
    raise SystemExit(f"Bundle list not rendered: {error}") from None
