# Build and Test — Data Product Jenkins Pipelines (2026-11-10)

## Offline
- `python3 -m pytest -q tests`: **422 passed, 2 skipped**, including P1 to P5.
- **Mutation check** (scratch copy): removing the `'` escape, dropping the roles' global read entries, and creating `_cd` for every host were each caught.

## Build
- `scripts/lakehouse.sh start` rebuilt `local/lakehouse-jenkins:2.580.1`.
  - **Plugins**: the new `name:version` parity check passed with 105 plugins. `cloudbees-folder` stayed at the pinned 6.1106; the bare probe install had bumped it.
  - **Other services**: unchanged.

## Live
| Check | Result |
|---|---|
| `scripts/verify/jenkins-oidc.py` | **10/10 PASS**, including the new project-matrix and product-folder checks. The old "workload CI job" failure is gone. |
| `default/default_ci` | Scan found `main` and `uat`. **`main` #1 and `uat` #1 SUCCESS** with the workload `Jenkinsfile`. |
| `default/default_cd` | Scanned unauthenticated (`api.github.com`, no credentials) in 2 s. `main` and `uat` ignored because no PR is filed for them; 0 open PRs. |
| Permissions (Jenkins ACL evaluated as break-glass for identities carrying each Keycloak group) | See the matrix below. |
| `jptest` create (with `repo`) | Plan printed. Folder and both jobs created; owner admin only there; `default`'s roles see nothing in `jptest`. |
| `jptest`: `repo` removed | Exactly `jptest_ci` and `jptest_cd` deleted (logged by the hook); empty folder kept. |
| `jptest` removed | Folder deleted by the hook; `default` untouched; verifier passes. |
| `jptest` re-created from scratch | Folder and both jobs **in memory after one start** (the fix below). `jptest_ci` `main` #1 and `uat` #1 SUCCESS. |
| Re-apply unchanged | "Jenkins configuration unchanged"; Jenkins not restarted. |
| Removal without `--no-restart` | The script restarted Jenkins itself; folder deleted. |

**Permission matrix**

| Identity | Jenkins | Admin | Folder read | Configure | Create | Build | Folder credentials |
|---|---|---|---|---|---|---|---|
| default owner | yes | no | yes | yes | yes | yes | yes |
| default developer | yes | no | yes | no | no | yes | no |
| default analyst | yes | no | yes | no | no | no | no |
| default writer | no | no | no | no | no | no | no |
| jptest owner, on `default` | yes | no | no | no | no | no | no |
| default roles, on `jptest` | yes or no | no | no | no | no | no | no |
| platform admin | yes | yes | yes | yes | yes | yes | yes |
| no group | no | no | no | no | no | no | no |

## Defect found and fixed during Build and Test
A Job DSL script in CasC runs before Jenkins loads its jobs, so a **new** product's folder was written to disk but missing from Jenkins until the next restart. Updates to existing folders were not affected. The DSL now lives in its own rendered file, which the init hook applies after the jobs load, before it deletes anything; if the apply fails, nothing is deleted. Re-verified with `jptest` created from scratch, and the tests were updated. Details are in the application design ("Change found in Build and Test").

## Side effect (my error)
- **What happened**: the unchanged re-apply of `jptest` ran without `--no-restart`. `jptest` still had a `repo` block whose bundles had never been applied, so `apply_airflow` **recreated Airflow with the `jptest` bundles**, and the removal recreated it again without them.
- **Impact**: no DAG run was in progress or started in that window, so nothing was interrupted. Airflow is healthy with `default`'s bundles, and its recorded fingerprint is back.
- **Residue**: two DAG records, `jptest-main-test_environment` and `jptest-uat-test_environment` (not paused, no schedule, no runs). The broker would refuse them (`unknown_product`). Deleting them is left to the user.

## Not run
- **`reset` and `start`**: deletes every platform volume. The equivalent path, a folder and jobs created on a home that has never had them, was verified with `jptest`.
- **A `_cd` build of a real PR**: there are no open PRs. A test needs the user's approval to push a branch and open a PR on `cdiogo1979/opensource-lakehouse`.
- **Interactive browser OIDC logins per role**: the ACL was evaluated for synthetic identities with the same group authorities. Sign-in itself is unchanged and the verifier checks the login redirect.

## Residue (resolved 2026-11-10, at the user's request)
- **Removal backups**: `.runtime/backups/20261110T093246Z-remove-jptest` and `.runtime/backups/20261110T093611Z-remove-jptest` were deleted.
- **DAG records**: the two `jptest` DAG records were already gone; Airflow removed them after their bundles left. Nothing needed deleting.
- **Other**: test logs remain under the session scratchpad. The probe credentials and the admin password file were deleted.
