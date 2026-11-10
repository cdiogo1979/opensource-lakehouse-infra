# Unit 1 Code Generation Plan — Identity Provisioning

## Unit Context

- **Unit:** Unit 1 — Identity Provisioning
- **Story:** US-04 — Provision dedicated StarRocks service identities for Hive Metastore and RustFS access.
- **Requirements:** FR-4, FR-5; identity-related NFR-1/NFR-2; Unit 1 NFR-1 through NFR-5.
- **Workspace:** Brownfield Compose project at `/Users/carlosdiogo/code_repo/hive-dremio-rustfs`.
- **Dependencies:** Existing KDC, Hive Metastore, RustFS, bucket initialization, host credential bootstrap, and all-platform identity-provisioner flow.
- **Completion boundary:** Provision StarRocks Kerberos and RustFS credentials/resources and document their interface for Unit 2. StarRocks runtime mounts/service, SQL accounts, catalog registration, and query/write integration remain in Units 2 and 3.

## Approved Contracts

- Kerberos principal: `starrocks@${KERBEROS_REALM}`; keytab path `.runtime/credentials/keytabs/starrocks.keytab`.
- RustFS account/access-key ID: `starrocks`; secret file `.runtime/credentials/rustfs-starrocks-secret-key`; policy name `lakehouse-starrocks`.
- RustFS policy scope: bucket `lake`, prefixes `warehouse/databaseA.db/` and `warehouse/databaseB.db/`, with only approved scoped list and object actions.
- Invocation: existing `scripts/provision-identities.sh` wrapper and `identity-provisioner` Compose profile.
- Provisioning: attempt Kerberos and RustFS branches independently exactly once; preserve successful resources; return per-provider redacted outcomes and aggregate failure if either fails.
- Credential handling: create absent files only, do not implicitly rotate credentials or principal keys, use `0700` directories and `0600` StarRocks secret/keytab files, and keep `.runtime/credentials/` ignored.
- Infrastructure: reuse current keytab bind mount, add the StarRocks RustFS secret as a file-backed Compose secret, reuse `iceberg_net` and existing service dependencies, preserve the host Hive render/restart sequence after overall success.

## Exact Application Files

1. `scripts/bootstrap-local.sh` — create the StarRocks RustFS secret only if absent and enforce protected file mode without displaying its value.
2. `docker-compose.yml` — declare the file-backed `rustfs-starrocks-secret-key` and grant it to the existing `identity-provisioner`; retain existing profile, dependencies, mounts, network, and shared volumes.
3. `infra/identity-provisioner/provision-kerberos-identities.sh` — provision/reuse `starrocks@${KERBEROS_REALM}`, create the keytab only when absent, enforce mode, validate TGT with cleanup, and capture safe provider outcome without preventing the RustFS branch from running.
4. `infra/identity-provisioner/provision-rustfs-identities.py` — define/reconcile the exact StarRocks scoped policy, create/reuse account `starrocks` using the mounted secret, validate non-mutating list access to both approved prefixes, and expose only allowlisted error categories/statuses.
5. `infra/identity-provisioner/Dockerfile` — modify only if the implementation requires an already installed utility or command not present in the existing image; do not add an orchestration framework.
6. `README.md` and/or the existing identity-provisioning operations documentation — document bootstrap prerequisites, the invocation, generated credential references, provider results, safe reruns, and manual reconciliation.
7. `aidlc-docs/current/construction/unit-1-identity-provisioning/code/` — add a Markdown implementation summary and Unit 2 handoff contract only; no application code belongs under `aidlc-docs/`.

## Generation Steps

- [x] **Step 1 — Local credential bootstrap (US-04, NFR-3.1, NFR-3.2):** Extend `scripts/bootstrap-local.sh` to generate `.runtime/credentials/rustfs-starrocks-secret-key` only when absent, enforce `0600`, preserve existing contents, and keep output value-free. Confirm keytab and parent directories remain `0700`.
- [x] **Step 2 — Compose secret wiring (US-04, NFR-3.2):** Add the file-backed Compose secret and mount it only into the existing identity provisioner for Unit 1. Preserve existing mounts/dependencies/network and avoid environment-variable or command-line secret values.
- [x] **Step 3 — Kerberos identity provisioning (US-04, FR-5, NFR-1.2, NFR-3.1, NFR-3.3, NFR-3.5):** Add the StarRocks principal/keytab create-if-absent path, mode enforcement, TGT verification and ticket-cache cleanup. Do not randomize existing principal keys or overwrite an existing keytab. Convert failures to safe status categories without displaying raw provider command output.
- [x] **Step 4 — RustFS identity and policy (US-04, FR-4, NFR-1.2, NFR-3.3, NFR-3.5, NFR-3.6):** Add the dedicated `lakehouse-starrocks` policy with exact approved resource/prefix scope, create/reuse account `starrocks` using the mounted secret, reject drift without overwriting existing policy/account credentials, and validate both prefixes using non-mutating list requests. Return only allowlisted error categories and safe HTTP status.
- [x] **Step 5 — Independent provider orchestration (US-04, NFR-1.3, NFR-1.4, NFR-4.1–NFR-4.4):** Ensure Kerberos and RustFS are each invoked once even when the other fails, capture separate outcomes, preserve successful state, and return aggregate failure after both attempts. Retain the existing successful full-provisioning Hive render/restart behavior.
- [x] **Step 6 — Operator documentation (US-04, NFR-5.1, NFR-5.3):** Update the existing project operations documentation with prerequisites, `scripts/bootstrap-local.sh`, `scripts/provision-identities.sh`, credential paths/permissions, redacted outcome meanings, rerun behavior, and manual drift reconciliation. Document the read-only credential paths that Unit 2 must consume.
- [x] **Step 7 — Unit implementation summary and handoff (US-04):** Create the Markdown code summary under `aidlc-docs/current/construction/unit-1-identity-provisioning/code/`, including changed paths, provider contract, Compose dependencies, operational behavior, and known limits for Unit 2.
- [x] **Step 8 — Plan conformance review:** Check the implementation against every approved Unit 1 design and requirement, ensure no duplicate files or unrelated service/data changes were introduced, and update each completed checkbox immediately.
- [x] **Approval gate:** User approved Unit 1 Code Generation on 2026-10-24; functional and runtime verification remain deferred to Build and Test.

## Tests and Verification

No tests were added or executed during this code-generation stage. Shell syntax checks, Python syntax parsing, and `docker compose config -q` passed. Functional, provider, authorization, and runtime verification remain for the AI-DLC Build and Test phase.

## Scope Exclusions

- Do not add StarRocks services, runtime mounts, FE/BE configuration, or ticket renewal (Unit 2).
- Do not add SQL users, roles/grants, catalog SQL bootstrap, or sample tables (Unit 3).
- Do not modify Airflow/Jenkins or delete/recreate shared volumes, KDC/Hive/RustFS data, existing identities, or credentials.
- Do not rotate credentials implicitly, enable automatic retries, add monitoring/queues, or introduce a new orchestration framework.
