# Code Summary — jenkins-pipelines

| File | Change | Rules |
|---|---|---|
| `infra/jenkins/plugins.txt` | `+ job-dsl:3732.v9a_c49a_61a_313` (105 plugins, sorted by name) | FR-3, NFR-6 |
| `infra/jenkins/Dockerfile` | The parity check compares `name:version` from each plugin's manifest | NFR-6 |
| `infra/jenkins/casc/jenkins.yaml` | `globalMatrix` changed to `projectMatrix`; header comment | FR-4 |
| `infra/jenkins/init.groovy.d/reconcile-data-products.groovy` | New: applies the rendered Job DSL after jobs load, then deletes marked folders and `_ci`/`_cd` jobs that left the state; deletes nothing when the apply fails or the state is missing, empty or invalid | FR-3, FR-5, BR-6, NFR-4 |
| `compose.jenkins.yml` | Read-only mounts: Job DSL at `/run/lakehouse/jenkins-jobs.groovy`, state JSON at `/run/lakehouse/jenkins-products.json`, and the hook; header comment | FR-3, FR-5 |
| `infra/products/data_products.py` | `FOLDER_ADMIN_PERMISSIONS`, `JENKINS_ROLES`, `JENKINS_PERMISSIONS` as the folder set; refuses `apps.jenkins.owner` and `Overall/*`; `GITHUB_URL`, `github_repository()` | FR-4, BR-3, BR-5 |
| `infra/products/render_jenkins.py` | Rewritten: global `Overall/Read` entries (CasC), `job_dsl()` folders and jobs (own file), `groovy_string()`, `desired_items()`, `render_state()`, `plan()`, three outputs, `--jobs-output`, `--state-output`, `--check` plan | FR-1 to FR-5, BR-1, BR-4, BR-7 to BR-10 |
| `data-products/default.yaml`, `infra/products/template.yaml` | `apps.jenkins` without owner and `Overall/*`; comments | FR-4, FR-6 |
| `infra/keycloak/realm-contract.json` | `jenkins.authorized_groups` describes the folder mapping | FR-4 |
| `scripts/operations/lib/data-products.sh`, `create-data-product.sh`, `remove-data-product.sh`, `scripts/setup/prepare-runtime.py` | Messages, step titles and comments; flow unchanged | FR-5 |
| `scripts/verify/jenkins-oidc.py` | Project matrix check; product folders: marker, the owner's full admin set by permission class, exactly the expected jobs, no stale marked folder (replaces the old job check) | FR-6 |
| `README.md` | Jenkins section (job table, scans, GitHub limit, as-code and hook), group table, sample file, per-folder rights, create/change/remove, limitations (old CI job item replaced, Platform-wide now Airflow only, public repositories) | FR-7 |
| `tests/jenkins/test_product_pipelines.py` | New: 11 example and contract tests, plus P1 to P5 (Hypothesis) | FR-7, PBT |
| `tests/products/product_strategies.py` | `github_urls`, `descriptions` generators (PBT-07) | PBT-07 |
| `tests/jenkins/test_casc_contract.py`, `tests/jenkins/test_plugins_contract.py`, `tests/products/test_data_products.py` | Updated to the new model | |

## PBT compliance (partial)
| Rule | Status |
|---|---|
| PBT-02 Round trip | P1 (`groovy_string` parsed back) and P3 (rendered DSL and state JSON parsed back to `desired_items`) |
| PBT-03 Invariants | P2 (folder grants only its own groups; owner holds the admin set; product groups hold only `Overall/Read` globally), P4 (determinism), P5 (GitHub URL mapping) |
| PBT-07 Generators | Domain generators shared in `product_strategies.py`: product sets, repositories, GitHub URLs, descriptions with quotes, `${` and non-ASCII text |
| PBT-08 Shrinking and reproducibility | Default Hypothesis shrinking and `print_blob=True`; part of `python3 -m pytest -q tests` |
| PBT-09 Framework | Hypothesis, already selected |

**Mutation check (scratch copy)**: removing the `'` escape, dropping the roles' global read entries, and creating `_cd` for every host were each caught by the new tests.
