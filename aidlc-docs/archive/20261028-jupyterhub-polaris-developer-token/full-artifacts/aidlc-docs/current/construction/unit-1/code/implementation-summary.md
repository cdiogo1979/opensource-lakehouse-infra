# Unit 1 Code Generation Summary — JupyterHub OIDC Foundation

## Generated behavior

- JupyterHub uses a confidential Keycloak Authorization Code client with PKCE S256 and admits only users with the developer or analyst group.
- OAuth auth state is encrypted in persistent Hub-owned SQLite. The Hub-only client secret and crypt key are generated once with restrictive permissions and mounted read-only.
- Each stable Keycloak subject receives one Spark-enabled Jupyter server and a collision-resistant persistent named home. Servers have the approved 1 CPU/2 GiB defaults and two-user capacity limit.
- User servers join `jupyter-user` and `data-access`; the Hub attaches `data-access` before returning from its spawn hook. The Hub alone joins `core` and has Docker socket access.
- The active Jupyter path no longer uses FreeIPA LDAP, user keytabs, Hive settings, or RustFS root credentials. Unit 2 token forwarding and Unit 3 Polaris authorization/credential vending remain outside this unit.
- `scripts/lakehouse.sh stop` removes only project-labelled user-server containers and then stops Compose services without deleting named volumes.

## Modified

- `infra/keycloak/bootstrap-realm.py`, `infra/keycloak/realm-contract.json`
- `infra/jupyter/hub/Dockerfile`, `infra/jupyter/hub/requirements.txt`, `infra/jupyter/hub/jupyterhub_config.py`
- `infra/jupyter/singleuser/Dockerfile`, `infra/jupyter/singleuser/requirements.txt`, `infra/jupyter/singleuser/spark-defaults.conf`, `infra/jupyter/singleuser/start-session.sh`
- `docker-compose.yml`, `docker-compose.deferred.yml`, `.env.example`
- `scripts/prepare-lakehouse-runtime.py`, `scripts/validate-jupyterhub-credentials.py`, `scripts/lakehouse.sh`, `README.md`
- `aidlc-docs/current/aidlc-state.md`, `aidlc-docs/current/audit.md`, and the Unit 1 Code Generation plan

## Created

- `infra/jupyter/hub/lakehouse_policy.py`
- `infra/jupyter/hub/lakehouse_spawner.py`
- `infra/jupyter/hub/requirements-lock.txt` (currently direct dependency constraints; complete transitive resolution remains outstanding)
- `tests/jupyterhub/test_config_contract.py`
- `tests/jupyterhub/test_lakehouse_policy.py`
- `tests/jupyterhub/test_runtime_credentials.py`
- `tests/keycloak/test_jupyterhub_client_contract.py`

## Removed

- `infra/jupyter/hub/lakehouse_ldap.py`
- `infra/jupyter/hub/user-identities.json`

## Verification and remaining limits

- Static checks passed: Python syntax compilation for ten implementation/test files, shell syntax, Keycloak contract JSON parsing, and `docker compose config --quiet`.
- Unit tests were added but not executed in Code Generation. Docker images were not built and no runtime containers were started or changed.
- Package indexes were unavailable from this session. Direct dependencies and architecture-specific immutable base image digests are pinned, but the full transitive lock must be generated and verified before the build can be described as reproducible.
- Eligibility is refreshed before a spawn. Running servers are not monitored for immediate Keycloak group changes; an operator must stop a running server after removing its access group.
- The local endpoints use HTTP on loopback. This does not support external or production exposure.
