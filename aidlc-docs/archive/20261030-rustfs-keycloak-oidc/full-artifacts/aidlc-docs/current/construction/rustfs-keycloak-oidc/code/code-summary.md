# Code Summary — rustfs-keycloak-oidc

Generated per `aidlc-docs/current/construction/plans/rustfs-keycloak-oidc-code-generation-plan.md` (Steps 1–10).

## Modified
| File | Change | Traceability |
|---|---|---|
| `scripts/prepare-lakehouse-runtime.py` | Creates `rustfs-oidc-client-secret` once; stages its read-only mount copy (0644 under the 0700 mounts directory). | FR-7, BR-13 |
| `docker-compose.yml` | RustFS: entrypoint wrapper, OIDC environment (no secret), exact egress allowlist, secret and wrapper mounts, joins `rustfs-identity`. Keycloak: map-form networks with alias `keycloak.localhost` on `rustfs-identity` only. New internal network `lakehouse-local_rustfs-identity`. | FR-1, FR-7, FR-8, BR-14–BR-16 |
| `infra/keycloak/bootstrap-realm.py` | `rustfs` confidential client (exact callbacks and post-logout URIs, PKCE S256), `lakehouse-rustfs-groups` mapper (`groups` in the ID token), console-port resolution (env → `.env` → 9001), exact-pair port-change reconciliation, `--rustfs-secret-file`; always configured. | FR-5, BR-7–BR-9 |
| `infra/keycloak/realm-contract.json` | Declares the `rustfs` client. | FR-5 |
| `infra/rustfs/bootstrap-buckets.py` | `S3Client.request` accepts an optional query and body; bucket behavior unchanged. | FR-4, FR-9 |
| `scripts/bootstrap-default-product.sh` | Runs policy bootstrap after bucket bootstrap. | FR-4, BR-11 |
| `infra/identity-provisioner/Dockerfile` | Removed `COPY`/`chmod` references to the retired files. | FR-10 |
| `README.md` | Console endpoint note and the "RustFS console OIDC login" section, including the upstream console limitation and the bucket deep-link workaround. | FR-6, FR-11 |

## Created
| File | Purpose | Traceability |
|---|---|---|
| `infra/rustfs/rustfs-entrypoint.sh` | Exports the client secret from the mounted file, refuses a missing/empty file, then `exec /entrypoint.sh "$@"`. | FR-7, BR-14 |
| `infra/rustfs/bootstrap-policies.py` | Four group-named policies (read levels include console metadata reads); canonical comparison; create-or-verify, upgrades only the exact previous definition, refuses other conflicts. | FR-3, FR-4, BR-1–BR-5, BR-10, BR-10a, BR-11, BR-12 |
| `scripts/verify-rustfs-oidc.py` | Read-only live checks: provider listed, authorize redirects (both hosts), Keycloak accepts callbacks, policies match, secret absent from `docker inspect`. | Build and Test hooks |
| `tests/rustfs/strategies.py` | Shared Hypothesis generators (PBT-07). | PBT-07 |
| `tests/rustfs/test_policy_contract.py` | Matrix/example tests plus properties P1–P5. | BR-1–BR-5, BR-10; PBT-02, PBT-03 |
| `tests/keycloak/test_rustfs_client_contract.py` | Client, mapper, port resolution, reconciliation, and refusal tests. | BR-7–BR-9 |
| `tests/rustfs/test_compose_oidc_contract.py` | Compose and network contracts; behavioral wrapper tests. | BR-14–BR-16, BR-19 |
| `tests/rustfs/test_legacy_retirement.py` | Retired files absent and unreferenced. | FR-10 |

## Deleted
- `infra/identity-provisioner/reconcile-rustfs-roles.py`
- `infra/identity-provisioner/provision-rustfs-identities.py`
- `infra/identity-provisioner/rustfs-role-policy.json`

## Generation-time checks
- Both Compose files render (`docker compose config`, with the Airflow overlay).
- Python compiles; `sh -n`/`bash -n` pass.
- New tests: 26 RustFS tests and 10 Keycloak `rustfs` client tests passed on the host interpreter at generation time; 39 after the Build and Test change request (Step 11).

Full-suite, live, and regression verification belong to Build and Test.

## Notes
- No live service, realm, credential, or policy was changed during generation.
- PBT: Hypothesis (existing `tests/requirements-pbt.txt`). Shrinking stays enabled, `print_blob=True` is set on property tests, and CI passes `--hypothesis-seed` (PBT-08, PBT-09).
