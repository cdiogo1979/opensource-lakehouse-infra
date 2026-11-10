# Business Logic Model — workload-python

## Flows
1. **Regenerate the lock** (operator): `lock-workload-python.sh` → a throwaway container of the runtime's base image → venv → wheels-only install of `requirements.in` → `pip freeze` (BR-V2 environment) → header plus sorted lines → BR-L validation → write `requirements.lock`. A lock that fails BR-L is not written.
2. **Build an image**: create the venv → `pip install --no-deps --only-binary=:all: -r requirements.lock` → copy the lock and module → `check-venv` (BR-I1). The Jupyter image also installs Python 3.10, the kernel spec, the server setting, the `.pth` file and the command.
3. **Airflow run**: `create_cluster` → `install_requirements` (BR-R5 shortcut, or BR-E → install with constraint → BR-V with extras allowed) → `validate_environment` → `submit_*` → `stop_cluster` → `verify_workloads_succeeded`.
4. **Product CI**: the workflow rules → when present, BR-E → wheels-only dry-run resolution for the platform tags (BR-R3) → report.
5. **Jupyter**: BR-J1 path → BR-E → stamp check or `--reset` → dry-run resolution → remove changed projects from the folder → install the missing set with `--no-deps` → stamp → BR-V → restart notice.
6. **Parity**: for each image, `check-venv` plus `pip freeze` and the embedded lock → compare (BR-I3).
7. **`generate_tpch`**: arguments → `dbgen` → count → compare with the expected rule → log and exit.

## Failure behavior
| Situation | Result |
|---|---|
| Lock line malformed, duplicate, platform-managed | the generator writes nothing; image builds and checks fail with the line |
| Venv differs from the lock | image build fails; parity fails; `install_requirements` fails if an extras install changed a locked version |
| Extras line refused (BR-E) | CI fails with every problem; `install_requirements` fails before pip runs; the Jupyter command fails without changes |
| Extras conflict with the lock, or no suitable wheel | pip's `ResolutionImpossible` or "No matching distribution" message, exit 1, in all three places |
| PyPI unreachable | CI fails; `install_requirements` retries twice, then fails before workload code runs; cleanup still happens |
| No `requirements.txt` | nothing happens anywhere, and no network access |
| Lock changed since a Jupyter install | the command refuses until `--reset` |
| TPC-H count differs | the task fails, naming the entity, count and expected value |

## Testable properties (PBT-01)
| # | Property | Category | Rule |
|---|---|---|---|
| P1 | Rendering any valid mapping as a lock and parsing it gives the same mapping | round-trip (PBT-02) | BR-L |
| P2 | Name normalization is idempotent, and two names are equal after normalization exactly when they differ only in case and in runs of `-`, `_`, `.` | idempotence and invariant (PBT-03) | entities |
| P3 | `compare(lock, installed)` is empty exactly when the two mappings are equal; with `allow_extra` exactly when the lock is a subset of `installed` with equal versions; each problem names a package from one of the two | invariant, oracle (dictionary comparison) | BR-V3, BR-V4 |
| P4 | Any generated plain requirement line is accepted; adding any option prefix, URL, `@` reference or path makes it refused; the problem's line number is the line's position | invariant | BR-E3 to BR-E5 |
| P5 | Comments and blank lines added anywhere never change the accepted set | invariant | BR-E2 |
| P6 | For every valid scale factor and entity other than `lineitem`, the expected count equals the integer `base × sf` computed from the decimal digits (oracle: integer arithmetic on thousandths) | oracle | BR-T3 |
| P7 | Every scale-factor text outside BR-T2 is refused, and every valid one is accepted | invariant | BR-T2 |

**Not property-tested**: pip's resolution and the image builds (external, verified live); the factory's task graph (example tests: the task order is fixed).

**Generators (PBT-07)**: project names from the BR-L2 alphabet with mixed case and separators; versions as dotted numbers with optional `post`, `rc` and local parts; requirement lines built from names, optional extras, specifier lists and markers; scale factors as thousandths from 1 to 1000, plus invalid ones (0, negative, more than three decimals, above 1, non-numeric).
**Framework (PBT-08, PBT-09)**: Hypothesis, as in the existing suites; shrinking on; the `ci` profile is derandomized, so failures replay with the printed seed. Example-based tests remain for each rule's concrete cases (PBT-10 complements them).
