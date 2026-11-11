# Identity: Keycloak, LDAP, users and groups

Reference for platform admins and anyone who needs the sign-in details. Back to the [README](../../README.md).

## Bootstrap users

The product bootstrap creates five users in the `lakehouse` realm, defined in `infra/keycloak/bootstrap-users.json`. Each has the permanent password `ChangeM3!`, a local-development default documented here on purpose, and belongs to one group.

| User | Group | Purpose |
|---|---|---|
| `joe-developer` | `role-default-developer` | Develops in dev; reads UAT and production |
| `peter-analyst` | `role-default-analyst` | Reads production |
| `maria-owner` | `role-default-owner` | Owns the data product |
| `srv-default-writer` | `role-default-writer` | Service user for Airflow and Spark writes |
| `platform-admin` | `role-platform-admin` | Administers the platform |

**One password everywhere**: users and passwords live in the LDAP directory (`ldap` service), which Keycloak reads and writes. Groups stay in Keycloak. The same username and password sign in to Keycloak (and every web app) and to StarRocks. A password changed in Keycloak (account page or admin console) changes it everywhere.

## What each group can do

For `default`, as set in `data-products/default.yaml`; every other product's groups work the same way unless its file says otherwise:

| Group | Data (Polaris, StarRocks, RustFS) | JupyterHub | Airflow | Jenkins | Keycloak |
|---|---|---|---|---|---|
| `role-default-owner` | manage all environments | — | User | admin of folder `default` | — |
| `role-default-developer` | read prod and UAT; read and write dev; author MVs in dev | user | User | read and build in folder `default` | — |
| `role-default-analyst` | read prod | user | User | read folder `default` | — |
| `role-default-writer` | read and write all environments | — | Viewer | — | — |
| `role-platform-admin` | owner of every product, plus StarRocks system admin | Hub admin | Admin | Administer (all of Jenkins) | admin of the `lakehouse` realm |

## Where to sign in

| To do this | Go to | As |
|---|---|---|
| Use a product | the product URL in the [README](../../README.md#components) | a user whose group the product admits |
| Check your own account | <http://keycloak.localhost:8080/realms/lakehouse/account/> | any bootstrap user |
| Administer the `lakehouse` realm (users, groups, clients) | <http://keycloak.localhost:8080/admin/lakehouse/console/> | `platform-admin` |
| Administer Keycloak itself (the `master` realm, server settings) | <http://127.0.0.1:8080/admin/> | `admin`, with the password in `.runtime/credentials/keycloak-admin-password` |

- **No `master` access**: the bootstrap users exist only in `lakehouse`, so they cannot sign in to `master`. This is intended.
- **Restoring defaults**: later runs of the product bootstrap never change existing users, so password and group changes survive. To put the five users back to their defaults, run:

  ```sh
  ./scripts/bootstrap/bootstrap-users.sh
  python3 infra/polaris/reconcile-keycloak-groups.py
  ```

  It changes only those five users.
- **Writer password**: Airflow and Spark read `srv-default-writer`'s password from `.runtime/credentials/srv-default-writer-password`. If you change it in Keycloak, run `bootstrap-users.sh` to restore it.
- **Group changes**: these reach Polaris and StarRocks through a reconciler that runs every five minutes, or immediately with `python3 infra/polaris/reconcile-keycloak-groups.py` and `./scripts/lakehouse.sh reconcile-starrocks`.

## Keycloak

- **Realm**: the realm `lakehouse` holds every data product's groups, the bootstrap users, and one client per application. The contract is `infra/keycloak/realm-contract.json`, applied idempotently by `infra/keycloak/bootstrap-realm.py` (with the product groups from `data-products/`), which refuses conflicting changes.
- **Users in LDAP**: the realm's user storage is the provider `lakehouse-ldap`. It reads and writes users and passwords in the `ldap` service over LDAPS (`ldaps://ldap:636`, bind `cn=keycloak,ou=services,dc=lakehouse,dc=local`), and Keycloak trusts its CA through `truststore-paths`. Groups stay in Keycloak. Client service accounts (`service-account-*`) and the `master` realm stay local.
- **Hostnames**: browsers use `keycloak.localhost:8080`, the canonical issuer. Containers call `keycloak:8080`, because `.localhost` means loopback inside a container.
- **Writer identity**: workload writes use `srv-default-writer` through the confidential `lakehouse-writer` client (password grant, one-hour tokens).
- **Optional CLI client**: the human CLI client `lakehouse-cli` has no callback until an application needs one: `python3 infra/keycloak/bootstrap-realm.py --redirect-uri 'http://localhost:PORT/EXACT/CALLBACK'`.

## Moving an existing stack to LDAP

For stacks created before the directory existed: users created earlier live in Keycloak's own database and cannot carry their passwords over. Run the one-time migration:

```sh
python3 scripts/operations/migrate-users-to-ldap.py --dry-run   # list users and password sources
python3 scripts/operations/migrate-users-to-ldap.py             # type "migrate" to run
```

- **Passwords**: bootstrap users get `ChangeM3!`, product writer users the password in their file, and anyone else `ChangeM3!` (the report names them).
- **Kept**: groups, names, email, and enabled state.
- **Jupyter homes**: users get a new Keycloak ID, so each Jupyter home is copied to the new ID's volume and verified. Then the old volume and the old Hub user are deleted. Stop users' Jupyter servers first.
- **Safety**: the Keycloak database is backed up to `.runtime/backups/<time>-pre-ldap/`. A user's old record is deleted only after the LDAP password works, and a rerun continues an interrupted migration.
