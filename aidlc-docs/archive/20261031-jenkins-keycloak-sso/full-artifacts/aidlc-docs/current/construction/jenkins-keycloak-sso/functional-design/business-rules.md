# Business Rules — jenkins-keycloak-sso

## Authentication and authorization
- **JB-1 OIDC only for people**: browser sign-in goes through Keycloak. The legacy local user database is retained in the copied home but is not a login path; the security realm is OIDC.
- **JB-2 Group permissions**: Jenkins authorities are the plain names in the `groups` claim. Permissions are exactly the authorization matrix in `domain-entities.md`.
- **JB-3 Least privilege**:
  - Users with no matrix group, `role-default-writer`, and anonymous users have no permissions.
  - Developers cannot configure or delete jobs, manage credentials, or administer Jenkins.
- **JB-4 Union**: a user in several groups receives the union of their groups' permissions.
- **JB-5 Exact URIs**: the `jenkins` client has exactly the two callbacks and two post-logout URIs for `localhost` and `127.0.0.1` on the Jenkins port. There are no wildcards. Rerunning the bootstrap refuses conflicts, except an exact console-port move of both URI pairs.
- **JB-6 Back-channel via the internal name**: token, JWKS, and userinfo calls use `keycloak:8080`. Browser redirects use `keycloak.localhost:8080`. The issuer is validated against the canonical value.

## Configuration authority
- **JB-7 Plugins come from the image**: `plugins.txt` is the source of truth (104 exact versions). `PLUGINS_FORCE_UPGRADE=true` overwrites migrated plugin copies at start. No runtime plugin installs or updates.
- **JB-8 Security comes from configuration as code**:
  - The YAML is reapplied at every start.
  - It owns the security realm, authorization strategy, executors, mode, crumb issuer, and root URL. Manual UI changes to these are overwritten on restart.
  - Jobs and build history are not managed by configuration as code.
- **JB-9 No inline secrets**: the client secret and the break-glass password are read from mounted files. Nothing secret appears in YAML, Compose, logs, or `docker inspect`.

## Migration
- **JB-10 Copy once, never overwrite**:
  - If the target home holds an origin marker, the helper does nothing.
  - If the target is non-empty without a marker, the helper refuses and changes nothing; the operator must investigate.
- **JB-11 Consistent source**: the copy runs only while the legacy container is stopped. It refuses if `hive-dremio-rustfs-jenkins-1` is running.
- **JB-12 Verified copy**: after copying, the helper compares file counts and a content digest of the source and target, excluding the marker. It writes the marker last. If verification fails, the target is not marked and the next start refuses.
- **JB-13 Read-only source**: the legacy volume is always mounted read-only during the copy.
- **JB-14 Fresh start** (FD Q1: A): if the target is empty and no legacy volume exists, Jenkins starts with an empty home. The helper writes the `fresh` marker and prints a notice that the workload job is absent.

## Legacy removal (FD Q2: A)
- **JB-15 Guarded command**: `scripts/lakehouse.sh remove-legacy-jenkins --confirm` refuses unless all of these hold:
  - the v2 home marker is `migrated:iceberg-poc-jenkins-home`
  - v2 Jenkins is healthy
  - the legacy container is not running
  - `--confirm` is given
- **JB-16 Exact targets**: the command removes only container `hive-dremio-rustfs-jenkins-1` and volume `iceberg-poc-jenkins-home`, and never `jenkins_home` or any image. It is never run automatically. It runs only after you approve the verified Build and Test results.

## Break-glass and availability
- **JB-17 Escape hatch**: user `jenkins-break-glass`, with its password from the protected file and group `jenkins-break-glass` (Administer). It is available at the plugin's escape-hatch login. The password is rotated by replacing the file and restarting Jenkins.
- **JB-18 Keycloak outage**: SSO logins fail and the escape hatch keeps working. Running and scheduled builds are unaffected.
- **JB-19 No regression**: other services' Keycloak clients and the Compose services are unchanged, apart from Jenkins being added to core start, status, and stop.
