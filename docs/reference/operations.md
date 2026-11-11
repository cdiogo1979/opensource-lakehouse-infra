# Operations

Reference for platform admins: status, reset, backup, secrets, and the bootstrap steps. Back to the [README](../../README.md). The task-ordered view: the [platform admin journey](../journeys/platform-admin.md).

## Status and stop

```sh
./scripts/lakehouse.sh status   # health of core, the enabled modules, and the scheduled reconciler
./scripts/lakehouse.sh stop     # stops them; volumes and data are kept
```

`stop` also removes running Jupyter user servers. Their home volumes are kept. Avoid `docker compose ... down -v`: it deletes volumes.

## Reset the platform

The reset deletes all local platform state, so the next start begins from nothing:

```sh
./scripts/lakehouse.sh reset --dry-run   # list what would be deleted
./scripts/lakehouse.sh reset             # list it, then type "reset" to confirm
./scripts/lakehouse.sh reset --yes       # no prompt, for scripts
```

| Deleted | Kept |
|---|---|
| All `lakehouse-local` containers, including Jupyter user servers and Airflow Spark runs | Docker images |
| All platform volumes: realm and users, catalogs, buckets and objects, JupyterHub state and user homes, Jenkins home, Airflow metadata, and StarRocks metadata and storage | Other projects' containers, volumes, and networks |
| The `lakehouse-local` networks | Tracked files in this repository |
| `.runtime/credentials`, `.runtime/container-mounts`, `.runtime/airflow-dag-bundles`, `.runtime/state` (secrets, certificates, bundles, applied product names); the LDAP directory (`ldap-data`) | Other `.runtime` entries, such as `.runtime/backups`, and the product files in `data-products/` |

**The reset cannot be undone.** Back up anything you want to keep first.
- **Prompts**: without a terminal, it refuses unless you pass `--yes`.
- **Failures**: if a step fails, fix the cause and rerun.
- **Afterwards**: start again with the two [Quick start](../../README.md#quick-start) steps. Step 2 recreates every product in `data-products/`, with empty buckets.

## Backup

- **Data**: stop the owning service, then back up its Docker volume with your usual volume backup method. The volumes are named `lakehouse-local_*`, for example `lakehouse-local_jenkins-home`, `lakehouse-local_rustfs-data`, and `lakehouse-local_ldap-data` (the users and password hashes; back it up with `lakehouse-local_keycloak-db-data`).
- **Credentials**: back up `.runtime/credentials/` separately, in encrypted storage.

## Secrets and rotation

- **Where they live**: all secrets are in `.runtime/credentials/` (directory mode `0700`, files `0600`). They are created once by `scripts/setup/prepare-runtime.py`, never printed, and never written into Compose files.
- **Container copies**: containers that cannot read host-private files get read-only copies in `.runtime/container-mounts/`.
- **Rotating a client secret** (RustFS, Jenkins, JupyterHub, Airflow, StarRocks):
  1. Write the new value to the file.
  2. Set the same value on the Keycloak client.
  3. Rerun `python3 scripts/setup/prepare-runtime.py`.
  4. Restart the service, for example `docker compose -f compose.core.yml up -d rustfs`.

  `infra/keycloak/bootstrap-realm.py` refuses to continue while the file and Keycloak disagree.
- **Checkpoint keys**: `./scripts/lakehouse.sh rotate-checkpoint-keys [--product FILE]` (see [Streaming checkpoints](streaming-checkpoints.md)).
- **StarRocks catalog secret**: `python3 infra/starrocks/bootstrap-starrocks.py --recreate-catalogs` (see [StarRocks](starrocks.md#users)).
- **JupyterHub broker trust**: see [JupyterHub](jupyterhub.md). **Auth-state key**: do not regenerate it while Hub sessions must stay readable.
- **LDAP**:
  - **Keycloak's bind password** (`.runtime/credentials/ldap-keycloak-password`): change the file, then restart `ldap` (it re-hashes the bind entry at start) and rerun `python3 infra/keycloak/bootstrap-realm.py`, which updates and tests the provider.
  - **The LDAP admin password** (`ldap-admin-password`) is for recovery only.
  - **Certificates**: `python3 scripts/setup/prepare-ldap-certificates.py --rotate`, then restart `ldap`, Keycloak, and the StarRocks FE.

## Running bootstrap steps individually

`bootstrap-default-product.sh` runs these in order for every product file; each is idempotent, and the product steps also take `--product FILE` and `--dry-run`:

```sh
python3 infra/keycloak/bootstrap-realm.py               # realm, clients, product groups, missing users
./scripts/bootstrap/bootstrap-users.sh                   # reset the five users to their defaults
./scripts/bootstrap/bootstrap-polaris-realm.sh           # Polaris internal operator principal
python3 infra/rustfs/bootstrap-buckets.py                # buckets
python3 infra/rustfs/bootstrap-policies.py               # RustFS group policies
python3 infra/rustfs/bootstrap-checkpoint-keys.py        # checkpoint keys (users, policies, staged files)
python3 infra/polaris/bootstrap-catalogs.py              # catalogs and namespaces
python3 infra/polaris/bootstrap-product-authorization.py # Polaris grants
python3 infra/polaris/reconcile-keycloak-groups.py       # Polaris principals from Keycloak groups
docker compose -f compose.core.yml --profile scheduled-reconciliation up -d --build polaris-group-reconciler  # 5-minute sync
python3 scripts/verify/polaris-keycloak-auth.py          # writer token check
./scripts/bootstrap/smoke-spark.sh                       # Spark smoke tables
python3 infra/starrocks/bootstrap-starrocks.py           # StarRocks catalogs, MV databases, roles
python3 infra/starrocks/reconcile-starrocks-users.py     # StarRocks users from Keycloak groups
python3 infra/products/product-cli.py record --all       # lock the applied product names
```
