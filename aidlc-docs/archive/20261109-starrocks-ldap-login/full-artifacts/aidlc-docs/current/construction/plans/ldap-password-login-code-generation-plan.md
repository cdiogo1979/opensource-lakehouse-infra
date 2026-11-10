# Code Generation Plan — ldap-password-login

This plan is the single source of truth for Code Generation. Brownfield: files are changed in place. Code Generation changes **files only**; the live migration runs in Build and Test, after a backup.

## Unit context
- **Requirements**: FR-1..FR-7.
- **Design**:
  - Application Design C1–C7, S1–S4, AD-Q1
  - Functional Design BR-1..BR-6, flows A–D, properties P1–P6
- **PBT (partial)**: PBT-02, 03, 07, 08, 09 enforced; Hypothesis.
- **Unchanged**:
  - groups, the data product scripts, the Polaris sync
  - every OIDC client except `starrocks`
  - the Airflow broker
  - `create-user.py`, `keycloak_products.py`, `bootstrap-users.py` (they call Keycloak, which writes to LDAP)

## Steps

### Step 1 — LDAP directory (C1; FR-1, BR-1)
- [x] Create `infra/ldap/Dockerfile`: Alpine 3.22 pinned by digest; `openldap`, `openldap-back-mdb`, `openldap-clients`, `openldap-passwd-argon2` pinned at `2.6.8-r0`.
- [x] Create `infra/ldap/ldap-entrypoint.sh` (POSIX sh): render the config, seed only an empty volume, run slapd on `ldaps:/// ldapi:///`. No secrets in arguments or logs.
- [x] Create `infra/ldap/slapd.conf.template`: schemas, modules, `password-hash {ARGON2}`, TLS paths, MDB, ACLs per BR-1.
- [x] Change `compose.core.yml`:
  - the service `ldap`: networks `core` and `starrocks`; volume `ldap-data`; read-only secrets and certificates; `ldapi` healthcheck; no ports
  - the Keycloak LDAP CA mount
  - the StarRocks CA mount for the scheduled sync
- [x] Change `scripts/lakehouse.sh`: start `ldap` with the first core group and wait for it to be healthy; include it in `status` and `stop`.

### Step 2 — Certificates and secrets (C2)
- [x] Create `scripts/setup/prepare-ldap-certificates.py [--rotate]`: a local CA and a server certificate (SAN `ldap`), following `prepare-starrocks-certificates.py`.
- [x] Change `scripts/setup/prepare-runtime.py`:
  - create `ldap-admin-password`, `ldap-keycloak-password`, and `jupyterhub-maintenance-token` once
  - run the certificate script
  - stage `ldap-ca.crt` and the mounts
  - merge `truststore-paths=/run/certs/ldap-ca.crt` into `keycloak.conf`
- [x] Change `scripts/operations/reset-lakehouse.py`: add the `ldap-data` volume.

### Step 3 — Keycloak federation (C3; FR-2, BR-2)
- [x] Create `infra/keycloak/ldap_federation.py`: `desired_component`, `ensure_ldap_federation` (create, drift, conflict), `test_connection`.
- [x] Change `infra/keycloak/bootstrap-realm.py`: ensure the federation before the product groups and bootstrap users. Read the bind password from its file.

### Step 4 — StarRocks (C4; FR-3, BR-3)
- [x] Change `infra/starrocks/conf/fe.conf`: `ssl_force_secure_transport` and the LDAP settings.
- [x] Change `compose.starrocks.yml`: mount the LDAP CA into the FE.
- [x] Change `infra/starrocks/reconcile-starrocks-users.py`: the LDAP identity, the `switch` plan for JWT users, `ALTER USER` rendering.
- [x] Change `infra/starrocks/starrocks_common.py`: TLS with CA verification in `NetworkRunner`.
- [x] Change the reconciler image (`Dockerfile`, `run.sh`): use the mounted StarRocks CA.

### Step 5 — Clients and token-client removal (C5; FR-4, BR-5)
- [x] Change `scripts/clients/starrocks-login.sh`: password over verified TLS with the cleartext plugin.
- [x] Delete `scripts/clients/starrocks-token.sh`.
- [x] Change `infra/keycloak/bootstrap-realm.py` and `realm-contract.json`: stop creating the `starrocks` client and its audience mapper (the migration deletes it on existing stacks).

### Step 6 — JupyterHub maintenance service (FD-Q2)
- [x] Change `infra/jupyter/hub/jupyterhub_config.py`: the service `lakehouse-maintenance`, with its API token from a mounted secret file and a role limited to `admin:users`.
- [x] Change `compose.jupyter.yml`: mount the token file read-only.

### Step 7 — Migration (C6; FR-5, BR-4)
- [x] Create `infra/keycloak/ldap_people.py` (pure): `LdapPerson`, `render_entry`/`parse_ldif`, `password_source`, `plan_migration`.
- [x] Create `scripts/operations/migrate-users-to-ldap.py`:
  - preflight, backup (`pg_dump`), plan and dry run
  - per user: the steps through `docker exec ldap` (LDAPS as `cn=keycloak`; passwords through temporary files in the container, never arguments)
  - Keycloak replace and restore, the home copy and verify, deleting the old volume and the old Hub user
  - removing the `starrocks` client, the syncs, the report
- [x] Change `scripts/bootstrap-default-product.sh` only if the order needs it (fresh installs need no migration).

### Step 8 — Tests (FR-7; PBT partial)
- [x] Create `tests/ldap/ldap_strategies.py`: shared Hypothesis generators for usernames, names with Unicode and LDIF-special characters, emails, local users, groups, StarRocks user states (PBT-07).
- [x] Create `tests/ldap/test_ldap_people_properties.py`: P1 round trip (PBT-02); P2, P3, P5 invariants (PBT-03); P6 idempotency (advisory). Shrinking on, `print_blob=True` (PBT-08).
- [x] Create `tests/ldap/test_ldap_contract.py`: image pins, ACLs, LDAPS-only listener, no ports, secrets by file, federation settings, bootstrap order, migration safety (no deletion before verification, no password arguments).
- [x] Update the StarRocks tests:
  - P4 for the LDAP plan (PBT-03)
  - `starrocks-login.sh` contracts
  - TLS on the network runner
  - removal of the JWT identity, the token script, and the client
- [x] Update the Keycloak, JupyterHub, and reset tests for the changes above.

### Step 9 — Documentation and summary
- [x] Update `README.md`:
  - components (LDAP)
  - users and sign-in (passwords live in LDAP; same password everywhere)
  - StarRocks login with username and password for DBeaver, JDBC, BI, and the CLI; TLS required
  - migration instructions; reset; backup (`ldap-data`)
  - limitations (LDAP outage)
- [x] Run the full suite and record the results; write `aidlc-docs/current/construction/ldap-password-login/code/code-summary.md`.

## Traceability
| Requirement | Steps |
|---|---|
| FR-1 LDAP | 1, 2 |
| FR-2 Federation | 2, 3 |
| FR-3 StarRocks | 4 |
| FR-4 Clients | 5 |
| FR-5 Migration | 6, 7 |
| FR-6 Fresh install | 1, 3 |
| FR-7 Tests | 8 |
| Docs | 9 |
