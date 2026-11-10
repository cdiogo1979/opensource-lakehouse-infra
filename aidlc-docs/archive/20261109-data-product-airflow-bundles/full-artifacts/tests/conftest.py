"""Test-session setup shared by every suite.

Several modules load every data product file when imported. The suites must not
depend on which products exist in this checkout, so the whole session reads a
private directory holding only the default product; tests that need more
products write their own files.
"""

import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PRODUCTS = Path(tempfile.mkdtemp(prefix="lakehouse-test-products-"))
shutil.copy(ROOT / "data-products" / "default.yaml", _PRODUCTS / "default.yaml")
os.environ["LAKEHOUSE_DATA_PRODUCTS_DIR"] = str(_PRODUCTS)
