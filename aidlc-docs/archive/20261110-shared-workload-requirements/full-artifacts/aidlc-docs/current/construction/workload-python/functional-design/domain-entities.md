# Domain Entities — workload-python

| Entity | Form | Rules |
|---|---|---|
| **Project name** | text | Normalized as in PEP 503: lowercase, each run of `-`, `_`, `.` becomes `-`. All comparisons use the normalized name |
| **Lock** | `infra/workload-python/requirements.lock`; in images `/opt/lakehouse/requirements.lock` | A mapping of normalized name → exact version (BR-L1 to BR-L5) |
| **Base set** | `infra/workload-python/requirements.in` | The top-level pins the lock is resolved from (FR-1) |
| **Installed set** | `pip freeze` of an interpreter, with `PYTHONPATH` unset | Normalized name → version; `pip`, `setuptools`, `wheel` are not listed by `pip freeze` |
| **Extras file** | a product's root `requirements.txt` | Lines of plain requirements (BR-E1 to BR-E8) |
| **Requirement** | `name[extras] specifiers ; marker` | One accepted line of an extras file |
| **Problem** | `(line or package, message)` | Reported, never silently ignored; any problem gives exit 1 |
| **Platform tags** | the runtime's pip targets | Python 3.10, `cp`, `cp310`, `manylinux2014_aarch64`, `manylinux_2_17_aarch64` to `manylinux_2_31_aarch64` |
| **User extras folder** | `~/.local/lakehouse/python3.10` (Jupyter) | Holds the user's installed extras and `.lakehouse-lock.sha256`, the SHA-256 of the lock they were installed against |
| **TPC-H entity** | one of `region`, `nation`, `supplier`, `customer`, `part`, `partsupp`, `orders`, `lineitem` | The table `generate_tpch.py` counts |
| **Scale factor** | decimal text | 0.001 to 1, at most three decimal places (BR-T2) |

**Relationships**: the lock is derived from the base set; each venv's installed set must equal the lock (image checks, parity) or contain it unchanged (after extras); an extras file is resolved against the lock as a constraint; the user extras folder belongs to exactly one lock (its stamp).
