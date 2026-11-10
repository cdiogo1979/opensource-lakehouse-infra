# Open Source Lakehouse Infrastructure

This project is being rebuilt around a fresh local platform-admin journey. The supported Unit 1 runtime is Keycloak, its PostgreSQL database, Apache Polaris with its own PostgreSQL database, and RustFS. FreeIPA, MIT Kerberos/KDC, and Hive Metastore are retired from the supported stack. No data migration is performed.

## Start the platform

Requirements: Docker with Compose V2 and Python 3. Starting takes two steps.

```sh
cp .env.example .env                    # first time only
./scripts/lakehouse.sh start            # 1. providers, JupyterHub, Jenkins, StarRocks
./scripts/bootstrap-default-product.sh  # 2. realm, users, buckets, catalogs, grants, smoke tables, StarRocks catalogs, roles, users
./scripts/lakehouse.sh start-airflow    # optional: Airflow and its writer token broker
```

Step 1 creates missing credentials under `.runtime/credentials/` and starts the containers. It never changes realm, users, buckets, or catalogs. Step 2 reruns `start`, then creates the `lakehouse` realm, product groups, clients, bootstrap users, buckets, policies, catalogs, and grants, and finishes with the writer and Spark smoke checks, then the StarRocks catalogs, roles, and users (see [StarRocks SQL](#starrocks-sql)). Both steps are safe to rerun.

| Service | URL |
|---|---|
| Keycloak | <http://127.0.0.1:8080> |
| Polaris | <http://127.0.0.1:8181> |
| RustFS console | <http://127.0.0.1:9001/rustfs/console/> |
| JupyterHub | <http://jupyterhub.localhost:8000> |
| Jenkins | <http://127.0.0.1:8090> |
| Airflow (optional) | <http://127.0.0.1:8085> |
| StarRocks SQL (MySQL protocol) | `127.0.0.1:9030`, through `scripts/starrocks-login.sh` |

### Bootstrap users

Step 2 creates these users in the `lakehouse` realm. Each has the permanent password `ChangeM3!` and belongs to exactly one group.

| User | Group | Access |
|---|---|---|
| `joe-developer` | `role-default-developer` | Develops in dev; reads UAT and production |
| `peter-analyst` | `role-default-analyst` | Reads production |
| `maria-owner` | `role-default-owner` | Full product access |
| `srv-default-writer` | `role-default-writer` | Service user for Airflow and Spark writes (password grant through the `lakehouse-writer` client) |
| `platform-admin` | `role-platform-admin` | Owner-equivalent in Polaris and RustFS; Admin in Airflow; Administer in Jenkins; JupyterHub admin; administrator of the `lakehouse` realm in Keycloak; StarRocks owner plus system administration |

#### Keycloak sign-in

These users exist only in the `lakehouse` realm. Keycloak lets each realm's users sign in only to that realm, so they cannot sign in to the `master` realm.

| To do this | Sign in at | As |
|---|---|---|
| Use the products (JupyterHub, Airflow, Jenkins, RustFS, StarRocks) | the product URL | a bootstrap user whose group the product admits (see the table above) |
| Check your own account | <http://keycloak.localhost:8080/realms/lakehouse/account/> | any bootstrap user |
| Administer the `lakehouse` realm: users, groups, clients, realm settings | <http://keycloak.localhost:8080/admin/lakehouse/console/> | `platform-admin` |
| Administer Keycloak itself: the `master` realm, other realms, server settings | <http://127.0.0.1:8080/admin/> (`master` realm) | `admin` only |

- **`platform-admin` and `master`**: `platform-admin` cannot sign in to `master`. The `master` sign-in page rejects it as an unknown user. That is intended: it is a `lakehouse` realm administrator, not a Keycloak server administrator.
- **`admin` password**: in `.runtime/credentials/keycloak-admin-password`. A reset generates a new one.
- **Own rights**: realm administration includes `platform-admin`'s own rights, but `bootstrap-users.sh` puts its group back to the default.

The list lives in `infra/keycloak/bootstrap-users.json`. The password is a local-development default and is documented here on purpose. Do not expose this stack beyond the local machine.

The realm bootstrap only creates users that are missing. Password changes and extra group memberships survive later runs of step 2. To put the five users back to their defaults (password `ChangeM3!` and exactly their listed group), run:

```sh
./scripts/bootstrap-users.sh
python3 infra/polaris/reconcile-keycloak-groups.py
```

`bootstrap-users.sh` changes only the five listed users. Other users are left alone. Airflow and Spark read the writer password from `.runtime/credentials/srv-default-writer-password`, so if you change `srv-default-writer`'s password, run `bootstrap-users.sh` to restore it.

Airflow Bundles are mounted from this repository's `.runtime/airflow-dag-bundles`. Nothing outside this repository is mounted.

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
| Volumes for the Keycloak and Polaris databases, RustFS data, JupyterHub state, Jenkins home, Airflow metadata, and StarRocks metadata and storage: the realm, users, groups, catalogs, buckets, objects, build history, and StarRocks users, roles, and MV databases | Other projects' containers, volumes, and networks |
| Jupyter user homes (`lakehouse-jupyter-home-*`) | Tracked files in this repository |
| The `lakehouse-local` networks | `.runtime` entries other than the three on the left |
| `.runtime/credentials`, `.runtime/container-mounts`, `.runtime/airflow-dag-bundles`: all generated secrets, certificates, and Bundles | Anything outside this repository |

**The reset is irreversible.** Before running it, back up anything you want to keep: the Jenkins home (`lakehouse-local_jenkins-home`), bucket data, notebooks in user homes, and `.runtime/credentials/`. See [State and backup](#state-and-backup).

Without a terminal, the command refuses to run unless you pass `--yes`. `--yes` and `--dry-run` cannot be combined. If a step fails, fix the cause and rerun; resources already deleted are skipped. After a reset, start again with the two steps above.

## StarRocks SQL

StarRocks 4.1.7 (one FE, one BE) runs from its own Compose file, `docker-compose.starrocks.yml`, in the same `lakehouse-local` project. `scripts/lakehouse.sh start`, `status`, and `stop` include it. To leave it out, set `STARROCKS_ENABLED=false` in `.env`; start, stop, and the product bootstrap then skip it with a notice. Memory limits are `STARROCKS_FE_MEMORY_LIMIT` (default `2g`) and `STARROCKS_BE_MEMORY_LIMIT` (default `4g`). The SQL port `9030` and HTTP port `8030` bind to loopback only.

### Logging in

People log in with their Keycloak account, the same users as everywhere else:

```sh
./scripts/starrocks-login.sh joe-developer          # asks for the Keycloak password (ChangeM3! by default)
./scripts/starrocks-login.sh maria-owner -e "SHOW CATALOGS"
```

- **How it works**: the helper gets an access token from the Keycloak `starrocks` client and logs in with it, using a MySQL 9.7 client container and its OpenID Connect plugin. StarRocks checks the token's signature, issuer, and audience.
- **TLS**: the plugin only sends tokens over TLS. `lakehouse.sh start` creates a local StarRocks CA and FE certificate (`scripts/prepare-starrocks-certificates.py`), and the helper verifies the server against `.runtime/container-mounts/starrocks-ca.crt`.
- **No secrets shown**: the password and token are never printed or stored.
- **Token lifetime**: an open session outlives its token; a new login needs a fresh token.
- **Break-glass**: the `root` account. Its password is in `.runtime/credentials/starrocks-root-password`.

### DBeaver and other JDBC clients

JDBC clients use the same Keycloak-token login through MySQL Connector/J 9.1 or later, which reads the token from a file. This was verified with Connector/J 9.3.0, both with encryption only and with full certificate verification.

1. **Keep a fresh token in a private file.** Tokens last five minutes, and StarRocks checks them only when a connection opens, so leave this running while you work. It asks for the Keycloak password once and refreshes the file until the Keycloak session ends:

   ```sh
   ./scripts/starrocks-token.sh --watch joe-developer ~/.starrocks/token
   ```

   Without `--watch` it writes one token and exits.

2. **In DBeaver**:
   - Create a **MySQL** connection.
   - In *Edit Driver Settings*, then *Libraries*, use **mysql-connector-j 9.1 or later**. DBeaver's bundled 8.x driver cannot do this.
   - On the **Main** tab: host `127.0.0.1`, port `9030`, your Keycloak username, and an **empty** password.
   - Under **Driver properties**:

     | Property | Value |
     |---|---|
     | `idTokenFile` | absolute path of the token file, for example `/Users/<you>/.starrocks/token` |
     | `defaultAuthenticationPlugin` | `authentication_openid_connect_client` |
     | `sslMode` | `REQUIRED`, or `VERIFY_IDENTITY` with the truststore below |

3. **Optional: verify the server certificate.**
   - Import the StarRocks CA into a truststore:

     ```sh
     keytool -importcert -noprompt -alias starrocks-ca -file .runtime/container-mounts/starrocks-ca.crt \
       -keystore ~/.starrocks/truststore.p12 -storetype PKCS12 -storepass <choose-one>
     ```

   - Set `sslMode=VERIFY_IDENTITY`, `trustCertificateKeyStoreUrl=file:/Users/<you>/.starrocks/truststore.p12`, and `trustCertificateKeyStorePassword=<choose-one>`.
   - The certificate covers `127.0.0.1`, `localhost`, and `starrocks-fe`.
   - After a reset, the CA is new, so import it again.

The connection has exactly that user's StarRocks roles. For example, `peter-analyst` sees production only. Avoid connecting as `root` for normal work, because it bypasses the role model.

### Catalogs and databases

| Environment | StarRocks catalog (Iceberg on Polaris) | Namespace | MV database (`default_catalog`) |
|---|---|---|---|
| Production | `lakehouse` | `default_lh` | `default_lh` |
| UAT | `lakehouse_uat` | `default_lhuat` | `default_lhuat` |
| Dev | `lakehouse_dev` | `default_lhdev` | `default_lhdev` |

`bootstrap-default-product.sh` creates the three Iceberg REST catalogs.
- **Polaris identity**: they reach Polaris as the Keycloak service account `srv-starrocks`, in the writer group, with OAuth2 client credentials that StarRocks renews itself.
- **Storage**: data files are read and written with Polaris-vended, short-lived RustFS credentials. StarRocks holds no storage keys.
- **Conflicts**: an existing catalog with different settings stops the bootstrap.
- **Secret rotation or repair**: after review, run `python3 infra/starrocks/bootstrap-starrocks.py --recreate-catalogs`. This drops and recreates the catalogs without touching data.

### Roles

StarRocks roles carry the Keycloak group names, with underscores, and match Polaris:

| Role | Production | UAT | Dev | MV databases |
|---|---|---|---|---|
| `role_default_owner` | manage | manage | manage | manage all |
| `role_default_developer` | read | read | read, create, insert | read all |
| `role_default_analyst` | read | — | — | read production |
| `role_default_writer` | read, create, insert | read, create, insert | read, create, insert | create, refresh, and drop MVs in all |
| `role_platform_admin` | manage | manage | manage | manage all |

- **Read** is `SELECT`. **Create, insert** adds `CREATE DATABASE`, `CREATE TABLE`, and `INSERT`, with no drop, delete, or alter, as in Polaris.
- **Drop limit**: StarRocks reaches Polaris as the writer-level `srv-starrocks`, so even owners and platform admins cannot drop Iceberg tables through StarRocks; Polaris refuses it. Drop tables through Spark or Polaris as an owner.
- `role-platform-admin` members also get StarRocks' built-in `user_admin`, `db_admin`, and `cluster_admin`.
- The bootstrap enforces the matrix: privileges added to these five roles by hand are revoked and reported. Other roles and users are never changed.

### Users and reconcile

Every Keycloak user in a product group has a StarRocks user with exactly their groups' roles. Service accounts are excluded.

- **When it syncs**: in the product bootstrap; on demand with `./scripts/lakehouse.sh reconcile-starrocks [--dry-run]`; and every cycle of the scheduled `polaris-group-reconciler`.
- **Leaving a group**: removing someone from all product groups drops their StarRocks user.
- **Safety**: if Keycloak cannot be read, or returns no members, nothing is changed.
- **Materialized views**: a materialized view keeps its author. If the author's user is dropped, it may stop refreshing, and an owner or platform admin must re-create it.

## Provider details

Requirements: Docker with Compose V2 and Python 3.

```sh
cp .env.example .env
./scripts/lakehouse.sh start
./scripts/lakehouse.sh status
```

Open the local endpoints:

- Keycloak: <http://127.0.0.1:8080>
- Polaris: <http://127.0.0.1:8181>
- RustFS S3 API: <http://127.0.0.1:9000>
- RustFS console: <http://127.0.0.1:9001/rustfs/console/> (Keycloak sign-in or root keys; see [RustFS console OIDC login](#rustfs-console-oidc-login))
- JupyterHub: <http://jupyterhub.localhost:8000>
- Jenkins: <http://127.0.0.1:8090> (Keycloak sign-in; see [Jenkins CI and Keycloak SSO](#jenkins-ci-and-keycloak-sso))

The first Keycloak start creates the local `admin` bootstrap administrator from a protected runtime file. Unit 2 operator commands create the `lakehouse` realm, product groups, and bootstrap users, bootstrap Polaris's internal operator principal, and apply the product authorization model after the three catalogs exist. These are explicit commands; provider startup does not apply realm, identity, grant, catalog, bucket, or table changes.

The operator command creates only missing provider credentials/configuration under `.runtime/credentials/`, with directory mode `0700` and file mode `0600`. It never prints credential values or replaces existing credentials. It merges only the tracked Keycloak hostname and Polaris OIDC properties into their protected configuration files, preserving unrelated settings such as database credentials. For non-root images, it refreshes read-only container mount copies under `.runtime/container-mounts/`; that directory is also `0700`, with mount files mode `0644` so the container service users can read them. The host-private parent directory protects these copies from other host users. Keep `.runtime/` private and backed up securely. Credential filenames are listed in `scripts/prepare-lakehouse-runtime.py`; names are not values.

The runtime uses a separate PostgreSQL volume for each provider and a new RustFS volume. It does not mount or delete any legacy volume or RustFS object. `stop` preserves all three new volumes:

```sh
./scripts/lakehouse.sh stop
```

Use `STARTUP_TIMEOUT_SECONDS` to change the default 600-second readiness deadline. Host port variables are listed in `.env.example`; all published endpoints bind to loopback. PostgreSQL and Polaris management endpoints are not published.

## Polaris metadata prerequisite

Before Polaris starts, the operator script invokes an idempotent one-shot step that creates only the `polaris_schema` PostgreSQL schema. Polaris 1.8.0 requires this schema before its later Admin Tool bootstrap. The schema step does not initialize a realm or catalog.

## Unit 2 identity and catalog authorization

The tracked Keycloak contract is in `infra/keycloak/realm-contract.json`. The idempotent realm bootstrap creates the product groups (including `role-platform-admin`, which also gets the `lakehouse` realm's `realm-admin` role), the clients, and any missing [bootstrap users](#bootstrap-users). No bootstrap user is a `master` realm administrator:

```sh
python3 infra/keycloak/bootstrap-realm.py
```

The human CLI client remains without a callback until the actual application callback is known. Configure it only when the consuming application supplies its exact local callback URI:

```sh
python3 infra/keycloak/bootstrap-realm.py \
  --redirect-uri 'http://localhost:PORT/EXACT/CALLBACK'
```

The Keycloak bootstrap administrator belongs to the separate `master` realm and does not automatically become a product owner. Writes from Airflow and Spark authenticate as the `srv-default-writer` user through the confidential `lakehouse-writer` client, using the password grant. The user is a member only of the writer group.

Bootstrap Polaris's protected internal operator principal explicitly:

```sh
./scripts/bootstrap-polaris-realm.sh
```

The authorization commands do not create catalogs or object-storage resources. Before catalogs exist, create only the four Polaris product principal roles and reconcile current Keycloak group membership:

```sh
python3 infra/polaris/bootstrap-product-authorization.py --roles-only
python3 infra/polaris/reconcile-keycloak-groups.py
python3 scripts/verify-polaris-keycloak-auth.py
```

The verification command obtains a fresh writer token without printing it, confirms Polaris resolves the writer identity and denies a privileged management read with HTTP 403, then confirms a corrupted-signature token is rejected with HTTP 401.

## Unit 3 RustFS storage

The operator's protected RustFS bootstrap keys are mounted into Polaris for server-side STS calls. Human and Spark clients use Polaris OAuth and request Polaris-vended credentials; they never receive the root access key or secret. The RustFS STS implementation enforces a minimum 15-minute session duration.

Polaris's STS pool is bounded to eight HTTP connections, with one-second connection-acquisition and connect limits and a two-second read limit. These are per-stage limits; they do not guarantee a five-second end-to-end deadline. Polaris management is configured for container loopback and port 8182 is not published. To inspect readiness from inside the service, run `docker compose exec polaris curl --fail --silent http://127.0.0.1:8182/q/health/ready`. The pinned image's effective bind and credential settings still require runtime verification.

Create only missing buckets; existing buckets and their objects are preserved:

```sh
python3 infra/rustfs/bootstrap-buckets.py
python3 scripts/verify-rustfs-sts.py
```

The STS verification creates a unique object under a dev-only probe key, checks that the session can list/write in dev but cannot list/write production, and deletes only that exact probe object. U4 remains responsible for validating Polaris catalog configuration and Spark/Iceberg end-to-end credential vending.

## RustFS console OIDC login

The RustFS console offers **Keycloak** sign-in through the confidential `rustfs` client in the `lakehouse` realm. RustFS uses each value of the ID token's `groups` claim as the name of a RustFS policy, so access follows product-group membership:

| Keycloak group / RustFS policy | `bucket-default` | `bucket-default-uat` | `bucket-default-dev` |
|---|---|---|---|
| `role-default-owner` | all S3 actions | all S3 actions | all S3 actions |
| `role-default-developer` | read | read | read/write |
| `role-default-analyst` | read | — | — |
| `role-default-writer` | read/write | read/write | read/write |

Every policy can also list bucket names. A user without any of these groups is refused a RustFS session. A user in several groups receives the combined access. No OIDC user can administer RustFS users, policies, or server settings.

Setup is part of the normal operator path. `scripts/lakehouse.sh start` creates `.runtime/credentials/rustfs-oidc-client-secret` once and configures the Keycloak client. `scripts/bootstrap-default-product.sh` creates the four policies after the buckets. Both steps are rerunnable and refuse to overwrite a conflicting client, mapper, secret, or policy. To run them separately:

```sh
python3 infra/keycloak/bootstrap-realm.py
python3 infra/rustfs/bootstrap-policies.py
python3 scripts/verify-rustfs-oidc.py
```

The verification command is read-only. It checks that RustFS lists the provider, that console logins from `localhost` and `127.0.0.1` redirect to Keycloak with an exact registered callback, that the policies match their definitions, and that the client secret is absent from `docker inspect`.

- **Start logins on the console port.** Callbacks are registered only for `http://localhost:9001` and `http://127.0.0.1:9001` (or `RUSTFS_CONSOLE_HOST_PORT`). Logins started on the S3 port are rejected by Keycloak. After changing the console port, rerun `infra/keycloak/bootstrap-realm.py`; it moves only the exact previous RustFS URIs to the new port.
- **Sessions and logout.** Console sessions last one hour. Logging out also ends the Keycloak session and returns to the console login page.
- **Keycloak reachability.** RustFS reaches Keycloak through the internal `lakehouse-local_rustfs-identity` network, where Keycloak answers as `keycloak.localhost`; no other service uses that network. If Keycloak is unavailable, new OIDC logins fail, existing sessions run until expiry, and RustFS retries discovery in the background.
- **Known console limitation (RustFS 1.0.4).** For OIDC users, who are all RustFS non-admins, the console's bucket-list page (`/rustfs/console/browser/`) keeps reloading. This is upstream bug [rustfs/console#271](https://github.com/rustfs/console/issues/271), fixed in console v0.1.38, which no RustFS release bundles yet. Open a specific bucket instead, for example <http://127.0.0.1:9001/rustfs/console/browser?bucket=bucket-default-dev>, and switch buckets the same way. Upgrade RustFS once a release bundles console v0.1.38 or later.
- **Root break-glass.** The root access key and secret key in `.runtime/credentials/rustfs-access-key` and `rustfs-secret-key` still sign in to the console. Use them only for recovery and administration; Polaris continues to use them server-side for STS.
- **Secret rotation.** Write a new value to `.runtime/credentials/rustfs-oidc-client-secret`, set the same value on the Keycloak `rustfs` client, rerun `scripts/prepare-lakehouse-runtime.py`, and restart RustFS (`docker compose up -d rustfs`). A small entrypoint wrapper (`infra/rustfs/rustfs-entrypoint.sh`) reads the mounted file at start, because RustFS 1.0.4 accepts the OIDC secret only as an environment variable.

After the catalogs `lakehouse`, `lakehouse_uat`, and `lakehouse_dev` exist, add the catalog-scoped roles/grants and reconcile again:

```sh
python3 infra/polaris/bootstrap-product-authorization.py
python3 infra/polaris/reconcile-keycloak-groups.py
```

The current reconciler uses the protected local Keycloak bootstrap administrator; replacing it with a narrowly scoped Keycloak reader identity remains a hardening item before shared or production use. Polaris keeps the canonical Keycloak issuer but fetches signing keys over the private `keycloak` Compose service DNS name because `.localhost` resolves to loopback inside containers.

## One-time catalog path reset

The catalog layout is `<bucket>/<catalog>/<database>/<table>`:

| Environment | Catalog | Database namespace | Bucket |
|---|---|---|---|
| Production | `lakehouse` | `default_lh` | `bucket-default` |
| UAT | `lakehouse_uat` | `default_lhuat` | `bucket-default-uat` |
| Development | `lakehouse_dev` | `default_lhdev` | `bucket-default-dev` |

For the one-time local reset only, install the pinned boto3 dependency, start the providers, prepare the identity and Polaris operator principal, ensure the three buckets exist, and run the guarded reset. This deletes every object (including object versions) in those three buckets and removes namespaces, table metadata, and catalog metadata only within the known old/new default-product catalogs. It does not delete buckets or named volumes. Review the target mappings before running:

```sh
python3 -m pip install -r infra/bucket-init/requirements.txt
./scripts/lakehouse.sh start
python3 infra/keycloak/bootstrap-realm.py
./scripts/bootstrap-polaris-realm.sh
python3 infra/rustfs/bootstrap-buckets.py
python3 infra/polaris/reset-default-product-once.py --confirm-reset-default-product
```

Then run the normal bootstrap below to recreate the catalogs, namespaces, authorization, and smoke tables. The reset script is separate and is never invoked by normal bootstrap.

The one-command operator path is:

```sh
scripts/bootstrap-default-product.sh
```

It starts the core stack, provisions the identity/catalog/storage resources and grants, reconciles group memberships, verifies writer authentication, then submits the Spark smoke-table job. The approved local single-realm configuration sets `polaris.realm-context.require-header=false`; this makes the configured `lakehouse` realm the default until realm-aware vended-credential refresh is verified. Normal bootstrap is idempotent and safe to rerun; it preserves existing bucket contents.

The default-product bootstrap also starts `polaris-group-reconciler`, which synchronizes Keycloak product-group membership into Polaris immediately and every five minutes. Start it separately with `docker compose --profile scheduled-reconciliation up -d --build polaris-group-reconciler` if the default product was provisioned outside the one-command bootstrap. Set `POLARIS_GROUP_RECONCILE_INTERVAL_SECONDS` in `.env` to change the interval. A group change can take up to one interval to reach Polaris; run `python3 infra/polaris/reconcile-keycloak-groups.py` for immediate synchronization. The reconciler reads the protected Keycloak administrator password and Polaris bootstrap credentials read-only. Keep its Compose profile enabled only after those credentials have been provisioned.

## JupyterHub developer and analyst access

`./scripts/lakehouse.sh start` prepares protected Hub credentials, prepares/validates the broker CA and server certificate, checks the configured Docker subnet against local routes and networks, builds the pinned Hub and Spark-enabled single-user images, starts the providers, reconciles the confidential `jupyterhub` client and group claims in Keycloak, then starts JupyterHub. `./scripts/lakehouse.sh status` includes Hub health and the internal broker TLS readiness check. Hub is published only on loopback at `http://jupyterhub.localhost:8000`; Keycloak login uses the canonical `http://keycloak.localhost:8080/realms/lakehouse` issuer. This local profile uses HTTP for browser login and is not suitable for exposure beyond the local machine.

Only members of `role-default-developer`, `role-default-analyst`, or `role-platform-admin` are admitted. `role-platform-admin` members are also JupyterHub admins: they can see, stop, and open other users' servers, and their notebooks use owner-level data access. Owner/writer-only membership does not allow Hub login. Group admission is refreshed before each server spawn. If access is removed while a server is already running, stop the server in JupyterHub or stop the service with `./scripts/lakehouse.sh stop`; revocation is enforced at the next admission check and is not instantaneous.

Each user receives one Spark-enabled Jupyter server, limited by default to 1 CPU and 2 GiB RAM, with a maximum of two active servers. Override `JUPYTERHUB_SINGLEUSER_CPU_LIMIT`, `JUPYTERHUB_SINGLEUSER_MEMORY_LIMIT`, and `JUPYTERHUB_HOST_PORT` in `.env` after reviewing host capacity. When the port changes, the startup command reconciles the exact Keycloak callback for that port. User servers join only `jupyter-user` and `data-access`; the Hub alone has Docker socket access and joins `core`. User homes are separate named volumes derived from the stable Keycloak subject and survive server stop/recreate. `scripts/lakehouse.sh stop` removes only containers carrying the project’s Jupyter user-server label before stopping services; it does not remove home or Hub state volumes. Permanent user-home deletion requires explicit operator review and removal of that exact named volume; do not use `docker compose down -v` for routine operation.

The token broker listens on `https://jupyterhub:8443` only on the configured `jupyter-user` address. Compose does not publish port 8443. The user container receives the public CA certificate read-only; the Hub server certificate/key are mounted read-only into Hub, and the CA signing key remains on the host. Subnet defaults are `172.30.240.0/24` and Hub address `172.30.240.2`; adjust `JUPYTER_USER_SUBNET` and `JUPYTERHUB_BROKER_BIND_IP` together in `.env` if the preflight reports a conflict. Start the stack through `scripts/lakehouse.sh` so the preflight runs before Compose creates IPAM.

To rotate broker trust deliberately, stop the stack (which removes running user-server containers but preserves named homes), run `python3 scripts/prepare-jupyterhub-broker-certificates.py --rotate`, then run `./scripts/lakehouse.sh start`. The new CA is trusted only after Hub and user servers are recreated. Routine startup validates existing certificates and preserves their identity. Do not copy or mount `jupyterhub-broker-ca-key.pem` into any container.

The protected runtime bootstrap creates `.runtime/credentials/jupyterhub-oidc-client-secret` and `.runtime/credentials/jupyterhub-auth-state-crypt-key` once and stages Hub-only read-only copies. Keep `.runtime/` private. To rotate the confidential client secret, update the Keycloak client and protected file as one coordinated operation, then restart Hub; do not regenerate the auth-state crypt key while Hub auth state must remain readable. The encrypted auth-state key protects OAuth state at rest, and neither it nor the OIDC client secret is mounted into user servers.

The first login requires an existing Keycloak user in one of the two approved groups. Confirm the client and group claim with `python3 infra/keycloak/bootstrap-realm.py`; it refuses client-secret or callback mismatches. To create a user-identity Spark session from a notebook, use `from lakehouse_spark import create_spark_session` followed by `spark = create_spark_session()`. Both Jupyter and Airflow use the same pinned Spark 3.5.5 / Iceberg 1.10.2 runtime and JVM token-provider plugin. Iceberg 1.10 is required because its REST catalog initialization and requests use the custom AuthManager; earlier 1.8.1 runtime ignored it during initial catalog config and returned 401. The provider keeps the active JWT in memory and renews it over verified HTTPS through the identity-specific broker: JupyterHub refreshes the active user's token, while Airflow refreshes only the current run's writer token using its run-scoped capability. The writer client secret never enters Spark. Polaris separately vends and refreshes temporary S3 credentials; that mechanism remains independent of JWT renewal. No static or root RustFS credential is used as fallback. Polaris-vended RustFS credentials are configured for one hour with a 10-minute cache. Live checks verified the returned lifetime, read access within each smoke-table location, and denial of a production credential against a dev object. Other S3 operations and a strict five-second end-to-end latency bound remain unverified; the user accepted these limitations at Build and Test completion. See `aidlc-docs/current/construction/build-and-test/` and `aidlc-docs/current/deploy/deploy-handoff.md`.

Polaris also requires a principal record for each Keycloak username before that user's Spark queries can be authorized. After creating a user or changing product-group membership, reconcile the current Keycloak memberships before the user's first data query:

```sh
python3 infra/polaris/reconcile-keycloak-groups.py
```

This idempotent step creates missing Polaris principals and synchronizes their product principal-role assignments. JupyterHub checks Keycloak group admission when the user logs in and again before spawning a server; it does not create Polaris principals itself. The end-to-end test verified this sequence with a temporary developer and removed the temporary user and Polaris principal afterward.

## Jenkins CI and Keycloak SSO

Jenkins runs the CI for the `opensource-lakehouse` workload repository. It uses a multibranch pipeline (`opensource-lakehouse-dp/opensource-lakehouse-ci`) that scans `https://github.com/cdiogo1979/opensource-lakehouse/` anonymously and runs that repository's `Jenkinsfile` on the built-in node. The Docker socket is not mounted.

`scripts/lakehouse.sh start` starts Jenkins on `http://127.0.0.1:${JENKINS_HOST_PORT:-8090}`, and `status` and `stop` include it. Sign in with **Keycloak** through the confidential `jenkins` client in the `lakehouse` realm. Permissions follow product groups:

| Keycloak group | Jenkins permissions |
|---|---|
| `role-default-owner`, `role-platform-admin` | Administer |
| `role-default-developer` | Read, build, cancel, and view workspaces and logs |
| `role-default-analyst` | Read-only |
| `role-default-writer`, users without a product group, and anonymous users | None |

How it is configured:

- **Image and plugins.** `infra/jenkins/Dockerfile` builds Jenkins 2.580.1 with exactly the plugins in `infra/jenkins/plugins.txt`, and the build fails if the installed set differs. At start the image's plugins replace any copies in the home, and nothing is installed at runtime.
- **Security as code.** `infra/jenkins/casc/jenkins.yaml` sets the security realm, the permission matrix, the break-glass account, executors, and the root URL. It is reapplied at every start, so changes to these in the UI are overwritten. Jobs and build history are not managed there.
- **Reaching Keycloak.** Browser redirects use `keycloak.localhost:8080`. Jenkins calls the token, key, and user-info endpoints at `keycloak:8080`, because `.localhost` is loopback inside containers.
- **Secrets.** The client secret (`.runtime/credentials/jenkins-oidc-client-secret`) and the break-glass password (`.runtime/credentials/jenkins-break-glass-password`) are created once and mounted read-only. They are never written into Compose or the YAML.

Operations:

- **Break-glass.** If Keycloak is unavailable, sign in through the escape-hatch login as `jenkins-break-glass` with the password from the file above. That account has Administer. To rotate the password, replace the file, rerun `scripts/prepare-lakehouse-runtime.py`, and restart Jenkins (`docker compose up -d jenkins`).
- **Client secret rotation.** Update the Keycloak `jenkins` client and the protected file together, then restart Jenkins. `infra/keycloak/bootstrap-realm.py` refuses a mismatch.
- **Migrated home.** The first `start` copies the pre-v2 Jenkins home (volume `iceberg-poc-jenkins-home`, from the sibling `hive-dremio-rustfs` stack) into `lakehouse-local_jenkins-home`. The copy keeps the job and its build history, and runs through `scripts/migrate-jenkins-home.py`.
  - The source is mounted read-only, the copy is verified, and an origin marker is written last.
  - Start-up refuses a non-empty home without a marker, and refuses to copy while the legacy container is running.
  - Without a legacy volume, Jenkins starts with an empty home, prints a notice, and the workload job must be restored or recreated.
- **Legacy removal.** After the v2 Jenkins has been verified, `scripts/lakehouse.sh remove-legacy-jenkins --confirm` removes only the stopped legacy container `hive-dremio-rustfs-jenkins-1` and the volume `iceberg-poc-jenkins-home`. It refuses unless the v2 home is a verified copy and v2 Jenkins is healthy. The unrelated `jenkins_home` volume is never touched.
- **Verification.** `python3 scripts/verify-jenkins-oidc.py` is read-only. It checks health, anonymous denial, login redirects and accepted callbacks for both loopback hosts, that the running plugins match `plugins.txt`, the OIDC realm and permission matrix, the migrated job and origin marker, and that no secret appears in `docker inspect`.

## Deferred integrations

Airflow, Jenkins, and StarRocks were deferred during the v2 rebuild. Airflow now has its own operator path (`scripts/lakehouse.sh start-airflow`), Jenkins is part of the core stack (see above), and StarRocks runs from `docker-compose.starrocks.yml` (see [StarRocks SQL](#starrocks-sql)); its Kerberos, LDAP, and Hive-era assets were retired. JupyterHub and Jenkins are implemented in the main Compose stack; `docker-compose.deferred.yml` retains only inventory entries for them. The retired implementation directories `infra/freeipa`, `infra/hive`, and `infra/kerberos` were removed from this copy. Other legacy or deferred directories remain untouched and are not activated by the supported runtime.

## State and backup

Normal start, status, and stop commands preserve persistent state. Before manual backup or restore, stop the owning services and use Docker volume backup procedures for `lakehouse-local_keycloak-db-data`, `lakehouse-local_polaris-db-data`, and `lakehouse-local_rustfs-data`. Back up `.runtime/credentials/` separately using encrypted storage. Never use `docker compose down -v` unless you intend to destroy the corresponding state. To destroy all local state on purpose, use [Reset the platform](#reset-the-platform).

## Build and Test status

The previous Polaris catalog path correction passed Build and Test on the local Docker Compose stack. Bootstrap and Spark verified table locations as `<bucket>/<catalog>/<database>/<table>` for production, dev, and UAT. Temporary identities verified the developer, analyst, owner, and writer access matrix across all three environments, with probe rows and principals removed afterward. A second bootstrap run preserved an existing bucket object. The approved one-time reset emptied the three default-product buckets before recreating the catalogs and smoke tables. See the [previous Build and Test summary](aidlc-docs/archive/20261028-polaris-database-path-layout/full-artifacts/aidlc-docs/current/construction/build-and-test/build-and-test-summary.md) and archived deploy handoff for the data-loss boundary, operating sequence, evidence, and limitations.

The current JupyterHub intent has generated Units 1–4. Unit 1 passed its focused source tests and image builds; its accepted dependency-lock and live integration/performance/E2E gaps remain documented in `aidlc-docs/current/construction/build-and-test/unit-1-build-and-test-summary.md`. Unit 2 adds the in-process TLS token broker, per-user refresh coordination, certificate/subnet preparation, and Spark session handoff. Its 34 JupyterHub tests, 6 Keycloak contract tests, both image builds, Compose rendering, Python compilation, and shell syntax checks passed. Live integration and performance remain unverified; see `aidlc-docs/current/construction/build-and-test/unit-2-build-and-test-summary.md`.

Unit 3 passed 75 pytest cases plus 5 Hypothesis subtests, both images, Compose rendering, and static checks. The live developer/analyst/owner/writer role matrix passed across production, UAT, and dev; temporary test data and identities were cleaned up, and Polaris management-listener isolation was verified. Follow-up testing verified one-hour Polaris credentials, sampled RustFS table-prefix read scope and cross-environment denial, and fail-closed behavior after JWT expiry. Unit 4 passed 82 pytest cases, 5 Hypothesis subtests, both image builds, Compose validation, Python/Bash compilation, and Keycloak realm-contract JSON validation. The developer end-to-end journey, analyst authorization, server startup, and home persistence passed; the user reports GUI browser testing complete. The user considers Build and Test complete with the documented S3-operation, strict latency, JWT renewal, performance/concurrency, resiliency scheduling, and supply-chain limitations accepted. See `aidlc-docs/current/construction/build-and-test/build-and-test-summary.md` and the [Deploy Handoff](aidlc-docs/current/deploy/deploy-handoff.md).
