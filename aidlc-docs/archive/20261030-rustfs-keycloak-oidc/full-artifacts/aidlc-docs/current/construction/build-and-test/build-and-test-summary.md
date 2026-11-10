# Build and Test Summary — rustfs-keycloak-oidc

Run date: 2026-10-30, local Docker Compose stack (`linux/arm64` Docker engine), host Python 3.14.7.

## Build Status
- **Build tool**: Docker Compose V2. There is no compiled artifact; images are pinned upstream images.
- **Build status**: Success.
  - Core and Airflow-overlay Compose configs render.
  - `keycloak` and `rustfs` were recreated with the new configuration and are healthy (about 15 s).
  - Data volumes were preserved.
- **Applied changes**:
  - protected `rustfs-oidc-client-secret` created
  - Keycloak `rustfs` client and `lakehouse-rustfs-groups` mapper created
  - four RustFS policies created
- **Static checks**: `py_compile` (5 Python files), `sh -n` / `bash -n` (2 scripts), and realm-contract JSON validation all pass.

## Test Execution Summary

### Python Code Quality
- **Formatter / Linter**: N/A — none configured in this repository; the CI runs pytest only. Compile and syntax checks were run instead (above).

### Unit Tests
| Run | Result |
|---|---|
| Suites for this intent (`tests/rustfs`, `tests/keycloak`, `tests/polaris`), seed 20261030 | **84 passed** (81 before the change request) |
| New tests alone | 39 passed (29 RustFS + 10 Keycloak `rustfs` client) |
| Full suite, host interpreter, `PYTHONPATH=infra/jupyter/hub`, seed 20261030 | **137 passed, 1 skipped, 2 failed** (+10 subtests passed) |
| Full suite, CI-pinned venv (pytest 9.2.0, Hypothesis 6.170.12), JupyterHub broker module ignored | 124 passed, 1 skipped, 2 failed |

- **The 2 failures are pre-existing and outside this intent.**
  - `tests/airflow/test_keycloak_sso_contract.py` (2 tests) expects `role-default-developer → Admin`.
  - `infra/airflow/airflow_sso_roles.py` and `infra/airflow/webserver_config.py` were changed to `User` today at 14:17–14:18 UTC, before this intent started at 15:03 UTC.
  - No file touched by this intent is involved.
- **Pre-existing CI gap (not caused by this intent).** `tests/jupyterhub/test_unit2_token_broker.py` needs `jupyterhub` and `PYTHONPATH=infra/jupyter/hub`. `tests/requirements-pbt.txt` and the Jenkinsfile provide neither, so CI collection fails on that module.
- **Coverage**: not measured; no coverage tool is configured.

### Integration Tests
| Scenario | Result |
|---|---|
| 1. `scripts/verify-rustfs-oidc.py` (provider, redirects via both hosts, Keycloak accepts both callbacks, policies match, secret not in `docker inspect`) | **7/7 PASS** |
| 2. Bootstrap idempotency (realm + policies rerun) | **PASS** (all four policies `already-present`; also after the one-time upgrade) |
| 3. Polaris STS regression (`scripts/verify-rustfs-sts.py`) | **PASS** |
| 4. Headless login + authorization with temporary users | **19/19 PASS** after the change request (13/13 before); temporary users and probe object deleted each run |
| 5. Interactive browser login (Q10: B) | **PASS (user-confirmed 2026-10-30)** as `joe-developer` via the bucket view. Earlier attempts were stuck: Change Request 1 fixed policy denials; Change Request 2 is the upstream bucket-list loop (documented limitation) |

Scenario 4 details:
- **Analyst** session:
  - allowed: list buckets (200) and read production (200)
  - denied (403): production write, UAT read, and dev read
- **Logout**: redirected via Keycloak end-session back to `/rustfs/console/auth/login` (302).
- **Developer** session via `localhost`:
  - allowed: dev write (200) and UAT read (200)
  - denied: production write (403)
- **No-group user**: refused (HTTP 400, "OIDC policy mapping did not resolve to current policies").

After the run, the other services were still healthy: Airflow UI and JupyterHub returned 200. All RustFS error-level log lines from the run correspond to the expected denials, the refusal, or the first-run absent-policy lookups.

### Performance Tests
- N/A — no performance requirements (see `performance-test-instructions.md`).

### Additional Tests
- **Contract tests**: Pass (Keycloak client, Compose/network, wrapper, legacy retirement).
- **Security tests**: No vulnerability scanning was run; the Security Baseline extension is disabled. Secret non-exposure and the exact-callback/egress controls were verified (Scenarios 1 and 4).
- **E2E tests**: Pass, headless (Scenario 4). The interactive browser check is pending.

## Change Request 1 — Console stuck for read-level users
- **Report**: you logged in as `joe-developer` and the console appeared stuck.
- **Cause**: login succeeded. The console bucket list then called `GetBucketPolicyStatus` on all three buckets, got AccessDenied, and retried in a tight loop: 5,282 denials per bucket in about 80 s, and it was the only denied action. The approved `read` / `read_write` sets lacked console metadata reads. Owners were unaffected (`s3:*`). The headless E2E had not exercised console metadata calls.
- **Decision**: `console-access-clarification-questions.md`, Q1: A and Q2: A.
- **Fix**:
  - `read` (and so `read_write`) now includes read-only console metadata: `s3:GetBucketPolicyStatus`, `s3:GetBucketVersioning`, `s3:GetBucketObjectLockConfiguration`, `s3:GetBucketTagging`, `s3:ListBucketVersions`, `s3:GetObjectTagging`, `s3:GetObjectVersion`, `s3:GetObjectRetention`, `s3:GetObjectLegalHold`.
  - The bootstrap upgrades a policy only when it exactly equals the previous definition (BR-10a), and re-reads it to verify.
- **Applied**: developer, analyst, and writer reported `updated`; owner reported `already-present`. The rerun was idempotent, and `verify-rustfs-oidc.py` passed 7/7.
- **Re-verified**: E2E 19/19, including console metadata allowed in scope (`policyStatus` and `versioning` return 200) and denied out of scope (analyst UAT `policyStatus` returns 403).
- **Residual risk**: other console pages, such as the object browser, may call further actions. If they do, the denials show up in RustFS logs as `s3_authorization_denied`.

## Change Request 2 — Console loops on `account/info` (upstream bug)
- **Report**: after the policy fix, the console still looked stuck and "keeps asking" for `/rustfs/admin/v3/account/info`.
- **Reproduction**: headless Edge, instrumented over the DevTools protocol, with temporary users that were deleted afterwards.
  - The bucket-list page loops for **every** OIDC session: developer about 17 cycles/s, owner (`s3:*`) about 50 cycles/s.
  - Each cycle repeats `account/info`, `accountinfo`, `ListBuckets`, and a listing of each bucket, all returning 200.
- **Root cause**: upstream [rustfs/console#271](https://github.com/rustfs/console/issues/271). The non-admin Browser page remounts during its own permission refresh, and every OIDC user is a RustFS non-admin. The fix, [#272](https://github.com/rustfs/console/pull/272), shipped in console v0.1.38 (2026-10-28). RustFS 1.0.4 (2026-10-25) embeds console v0.1.37 at build time and has no runtime override; no newer RustFS release exists.
- **Workaround (verified)**: `/rustfs/console/browser?bucket=<name>` does not loop. It makes one `account/info` call and one listing.
- **Decision**: `console-access-clarification-questions.md` Q3: A. The limitation is documented in the README, with a follow-up to adopt the first RustFS release that bundles console v0.1.38 or later.
- **Diagnostic restart**: RustFS was restarted once with temporary info logging, then reverted to the repository configuration; `verify-rustfs-oidc.py` passes.

## Extension Compliance (PBT Partial)
| Rule | Status | Note |
|---|---|---|
| PBT-02 Round-trip | Compliant | P1 |
| PBT-03 Invariants | Compliant | P2–P5 |
| PBT-07 Generators | Compliant | Shared domain strategies in `tests/rustfs/strategies.py` |
| PBT-08 Shrinking/reproducibility | Compliant | Shrinking on, `print_blob=True`, seeded runs; CI logs the seed |
| PBT-09 Framework | Compliant | Hypothesis (pinned in `tests/requirements-pbt.txt`) |
| PBT-01, -04, -05, -06, -10 | Advisory (Partial mode) | P1–P5 identified in Functional Design; example tests complement the properties |

## Overall Status
- **Build**: Success.
- **Tests for this intent**: Pass (unit, contract, property, and live integration including the headless E2E).
- **Full suite**: 2 pre-existing failures, unrelated to this intent and in Airflow role-mapping drift; plus the pre-existing CI collection gap for the JupyterHub broker test.
- **Ready for Deploy handoff**: Yes. Interactive login was confirmed by the user through a bucket view (Scenario 5). Known upstream limitation: the bucket-list page loops for OIDC users until RustFS bundles console v0.1.38 or later. The pre-existing Airflow test drift is reported for your decision and is not changed by this intent.

## Next Steps
Once you confirm the interactive login and approve these results, prepare the Deploy handoff. Approving the handoff does not authorize any deployment.
