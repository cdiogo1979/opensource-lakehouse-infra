# Integration Test Instructions — Unit 5 JupyterHub and Per-User Spark

## Scope and safeguards

These scenarios validate the JupyterHub, DockerSpawner, per-user Spark, Kerberos, Hive, and RustFS path. Run only after completing `build-instructions.md`. Preserve all existing platform volumes, Hive/Dremio objects, RustFS objects, credential values, and per-user workspace volumes. Do not run ETL, rotate credentials, use admin/writer as a fallback, or probe RustFS directly as an authorization test.

## Scenario 1 — Compose and image build

Follow `build-instructions.md`.

**Expected:** Compose parses; both pinned images build; the existing platform services remain available; JupyterHub's published UI port is loopback-only.

## Scenario 2 — Hub access boundary

1. Open `http://127.0.0.1:8008` and sign in using a configured label. DummyAuthenticator accepts arbitrary password text and does not establish a real human identity.
2. Confirm the allowed labels are `user_a`, `user_b`, and `admin`; try an unconfigured label only to confirm it is rejected. Do not enter any real password.
3. Confirm the Hub landing page opens the user's single-user server.

**Expected:** Hub UI is available only on localhost. Unknown labels receive no server or credential mapping. `admin` is a Hub administrator but its Spark session remains the `admin` data identity.

## Scenario 3 — Session identity, mounts, and non-root file access

For each configured identity, start one server and inspect the corresponding container without printing its environment or file contents:

```bash
docker ps --filter label=hub.jupyter.org/username=user_a
docker inspect --format '{{.Config.User}} {{json .HostConfig.GroupAdd}}' <container-id>
docker inspect --format '{{range .Mounts}}{{println .Destination .RW}}{{end}}' <container-id>
```

Repeat for `user_b` and `admin`. In that user's terminal, verify identity files are readable as `jovyan` using `test -r` on `/run/credentials/identity.keytab`, `/run/credentials/rustfs-access-key`, and `/run/credentials/rustfs-secret-key`; do not `cat`, `env`, `printenv`, or display tickets. Run `klist` to record the principal and ticket validity only.

**Expected:** container user is `10001:10001`; its supplemental groups include only the configured host primary GID; each user receives exactly its own three read-only identity files, the read-only example mount, and its own writable named volume. No Docker socket or other identity files are mounted. `klist` shows the matching username principal.

## Scenario 4 — Spark/Hive/RustFS allow and deny matrix

Open `/opt/jupyter-examples/spark-authz.py` and run it separately in `user_a` and `user_b` sessions. Record username, principal, database, expected/actual result, and failure category only.

| Session | `databaseA.customer` | `databaseB.customer` |
|---|---|---|
| `user_a` | Allow | Authorization deny |
| `user_b` | Allow | Allow |

**Expected:** both allowed reads succeed. The `user_a` restricted read must fail with a recognizable authorization decision while the matching principal is established. Kerberos, Hive connectivity, missing-table, resource, and RustFS credential errors are failures, not authorization denials. Do not rerun a failed case as `admin` or `write-service-account`.

## Scenario 5 — Per-user workspace persistence and isolation

1. In each user's notebook workspace, create a harmless marker file with a distinct username-only value.
2. Stop and recreate that user's server from the Hub UI.
3. Confirm the matching marker remains and the other user's marker is absent.
4. Remove only the marker files created for this scenario.

**Expected:** the user's own named volume persists across server recreation; users do not share writable workspaces. Leave the named volumes intact.

## Scenario 6 — Three-session capacity

Start `user_a`, `user_b`, and `admin` servers concurrently. Confirm each reaches its own Jupyter page and has its own configured volume and identity mapping. Stop each server from the Hub UI after inspection.

**Expected:** all three sessions can be active together on the available host. Record a resource or spawn failure as an operational failure, not an authorization result. No performance SLA is defined.

## Evidence and cleanup

Use local Docker status/logs and the redacted notebook output. Never capture credential values, keytab contents, ticket-cache files, full container environment, or RustFS secret material. Do not run `docker compose down -v`, `scripts/clean.sh`, or volume-prune commands. Stopping a user server must preserve its named workspace.
