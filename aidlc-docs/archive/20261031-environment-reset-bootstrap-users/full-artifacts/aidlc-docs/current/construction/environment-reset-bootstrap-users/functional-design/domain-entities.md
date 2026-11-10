# Domain Entities — environment-reset-bootstrap-users

## BootstrapIdentitySet (`infra/keycloak/bootstrap-users.json`, new)
This is the single source of the default identities and the default password.

```json
{"default_password": "ChangeM3!",
 "groups": ["role-default-developer","role-default-analyst","role-default-owner","role-default-writer","role-platform-admin"],
 "users": [
  {"username":"joe-developer","group":"role-default-developer","firstName":"Joe","lastName":"Developer"},
  {"username":"peter-analyst","group":"role-default-analyst","firstName":"Peter","lastName":"Analyst"},
  {"username":"maria-owner","group":"role-default-owner","firstName":"Maria","lastName":"Owner"},
  {"username":"srv-default-writer","group":"role-default-writer","firstName":"Default","lastName":"Writer"},
  {"username":"platform-admin","group":"role-platform-admin","firstName":"Platform","lastName":"Admin"}]}
```

- **Email**: `<username>@lakehouse.local`, with `emailVerified: true`. Users are enabled with no required actions.
- **Password**: permanent (`temporary: false`).

## PlatformAdminGroup `role-platform-admin`
| Service | Mapping (owner-equivalent) |
|---|---|
| Keycloak | Group with the `polaris` client role `role-default-owner` |
| Polaris | Reconciler maps members to the principal role `role-default-owner` |
| RustFS | Policy `role-platform-admin`, identical to the owner policy |
| Airflow | `Admin` |
| Jenkins | `Overall/Administer` |
| JupyterHub | Not admitted (owners are not admitted) |

## WriterClient `lakehouse-writer` (new; replaces `write-service-account`)
- **Client settings**: confidential; `directAccessGrantsEnabled: true`; `standardFlowEnabled: false`; `serviceAccountsEnabled: false`; `access.token.lifespan: 3600`.
- **Polaris role mapper**: the client gets the Polaris client-role mapper.
- **Secret**: `.runtime/credentials/keycloak-writer-client-secret`. The existing file name is kept.
- **Token flow**: `grant_type=password`, `client_id=lakehouse-writer`, the client secret, `username=srv-default-writer`, and the password from `.runtime/credentials/srv-default-writer-password`. That file is written by runtime preparation from `default_password`.
- **Polaris principal**: `srv-default-writer`, which replaces `service-account-write-service-account`.

## ResetInventory (`scripts/reset-lakehouse.py`, new)
| Kind | Selector |
|---|---|
| Containers | label `com.docker.compose.project=lakehouse-local`; label `lakehouse-local.role` ∈ {`jupyter-user-server`, `airflow-spark-run`} |
| Volumes | exact `lakehouse-local_{keycloak-db-data,polaris-db-data,rustfs-data,jupyterhub-state,jenkins-home,airflow-postgres-data}`; prefix `lakehouse-jupyter-home-` |
| Networks | exact `lakehouse-local_{core,jupyter-user,data-access,rustfs-identity,airflow-internal,airflow-spark}` |
| Files | `<repo>/.runtime/{credentials,container-mounts,airflow-dag-bundles}` |
| Kept | images; any other volume, network, or container; `.runtime/aidlc-test-venv`; everything outside `<repo>/.runtime` |

## BundleRoot
`<repo>/.runtime/airflow-dag-bundles` is the only accepted `LAKEHOUSE_BUNDLE_HOST_ROOT`. `LAKEHOUSE_PROJECT_ROOT` is removed.
