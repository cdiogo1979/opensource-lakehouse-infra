# Component Methods — Shared Workload Requirements

Signatures and purpose only; the rules are defined in Functional Design.

## C1 `workload_python.py` (standard library; Python 3.10)
| Function | Input → output | Purpose |
|---|---|---|
| `parse_lock(text)` | `str` → `dict[str, str]` (normalized name → version) | Reads the lock (`name==version` lines, comments) and refuses anything else |
| `parse_freeze(text)` | `str` → `dict[str, str]` | Reads `pip freeze` output with the same normalization |
| `compare(lock, installed, allow_extra=False)` | → `list[str]` problems | Missing, different and (unless allowed) extra packages |
| `check_extras_lines(text)` | `str` → `list[Problem]` (line number, message) | The line rules for a product `requirements.txt`: plain requirements only; no options, URLs, paths, or `pyspark` |
| `platform_args()` | → `list[str]` | pip target arguments for the runtime: `--python-version 3.10 --implementation cp --abi cp310`, `--platform manylinux2014_aarch64` and `manylinux_2_17` to `manylinux_2_31` aarch64 |

| CLI command | Purpose | Exit |
|---|---|---|
| `check-venv PYTHON --lock LOCK [--allow-extra]` | `pip freeze` of that interpreter (with `PYTHONPATH` unset) equals the lock, and Python is 3.10 | 0 equal; 1 problems |
| `check-extras FILE --lock LOCK` | the line rules, then a wheels-only dry-run resolution for the runtime platform with the lock as constraint | 0 ok; 1 problems |
| `install-extras FILE --lock LOCK [--target DIR]` | absent file: nothing to do; otherwise the line rules, then a wheels-only install constrained by the lock, into the running venv or into `DIR`, then `check-venv --allow-extra` | 0 ok or nothing to do; 1 problems |

## C2 `lock-workload-python.sh`
`scripts/setup/lock-workload-python.sh` → rewrites `infra/workload-python/requirements.lock`. Runs a throwaway container of the runtime's base image, creates a venv, installs `requirements.in` with wheels only, and writes the header plus `pip freeze`.

## C5 DAG factory
| Callable | Purpose |
|---|---|
| `install_command() -> list[str]` | `["/opt/lakehouse/venv/bin/python", "/opt/lakehouse/workload_python.py", "install-extras", "/opt/lakehouse-bundle/requirements.txt", "--lock", "/opt/lakehouse/requirements.lock"]` |
| `_install_requirements(docker_url, **context)` | `_run_in_container(install_command(), "Product requirements install", ...)`, with output redacted |
| `validate_command(...)` | unchanged arguments; the interpreter becomes `/opt/lakehouse/venv/bin/python` |

## C4 Jupyter command
`lakehouse-install-requirements [PATH]` (default `./requirements.txt`) → `install-extras PATH --lock /opt/lakehouse/requirements.lock --target ~/.local/lakehouse/python3.10`. Prints that a kernel restart is needed.

## C6 Validator wrapper
`lakehouse-validate-workflows [ROOT]`: `python3 -m lakehouse_dags.validate ROOT`, then, when `ROOT/requirements.txt` exists, `python3 /opt/lakehouse/workload-python/workload_python.py check-extras ...`. Exit 1 if either fails.

## C8 `generate_tpch.py`
`main(argv) -> int`; `parse_task_args(args) -> (entity, scale_factor)`; `expected_count(entity, scale_factor, orders_count) -> range | int` (rule detail in Functional Design).
