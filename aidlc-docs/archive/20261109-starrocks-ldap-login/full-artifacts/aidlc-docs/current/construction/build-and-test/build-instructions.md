# Build Instructions

1. **Start**: `scripts/lakehouse.sh start` runs `prepare-runtime.py`, which creates the LDAP secrets, the LDAP and StarRocks certificates, the Hub maintenance token, and Keycloak `truststore-paths`. It then builds and starts `ldap` with the core services, recreates Keycloak (new mount; the realm bootstrap creates the `lakehouse-ldap` provider and tests it), and recreates JupyterHub and the StarRocks FE (forced TLS; the runtime bootstrap sets the LDAP bind pattern).
2. **Sync job**: `docker compose -f compose.core.yml --profile scheduled-reconciliation up -d --build polaris-group-reconciler` (TLS client with the StarRocks CA).
3. **Existing stacks only**:
   1. Stop users' Jupyter servers.
   2. `python3 scripts/operations/migrate-users-to-ldap.py --dry-run`
   3. `python3 scripts/operations/migrate-users-to-ldap.py --yes`
