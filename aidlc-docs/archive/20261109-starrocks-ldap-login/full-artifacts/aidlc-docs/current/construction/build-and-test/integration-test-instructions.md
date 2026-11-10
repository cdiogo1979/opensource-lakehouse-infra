# Integration Test Instructions (live)

1. **Baseline**: `python3 scripts/verify/role-matrix.py` passes; StarRocks users are `AUTHENTICATION_JWT`.
2. **Start**: see the build instructions. The realm bootstrap reports `ldap-federation=created`, StarRocks reports `LDAP password login: set`, and everything is healthy.
3. **Migration**:
   - The dry run lists the users and their password sources.
   - The run backs up the Keycloak database, then migrates each user (entry, password, verify, delete local, import, restore, home), removes the `starrocks` client, and runs the syncs (JWT users switched).
   - A second dry run reports nothing to migrate.
4. **Keycloak**: every migrated user is federated with the same groups, names, and enabled state, and signs in with the known password.
5. **StarRocks** (`scripts/clients/starrocks-login.sh --password-file …`):
   - people and `srv-default-writer` log in with their roles; platform admin also gets the built-ins
   - a wrong password is refused (LDAP 49)
   - plain text is refused ("insecure transport")
6. **Password change**: an admin reset in Keycloak; StarRocks accepts the new password and refuses the old; `bootstrap-users.sh` restores the default.
7. **New users**:
   - `create-user.sh` and a product writer (`create-data-product.sh`) are created in LDAP (federated).
   - After the group assignment and sync, each logs in to StarRocks with its own password or password file.
8. **JDBC**: Connector/J 9.3.0 with username and password connects with `sslMode=REQUIRED` and `VERIFY_IDENTITY`, and is refused with `DISABLED`.
9. **Other checks**:
   - `polaris-keycloak-auth.py` passes (writer token through the federated `srv-default-writer`).
   - `role-matrix.py` matches the baseline.
   - `rustfs-oidc.py` passes; `jenkins-oidc.py` passes all checks except the known missing CI job.
   - The scheduled sync succeeds over TLS.
10. **Self-heal**: clear the FE bind pattern; the next user reconcile sets it again, and logins work.
11. **Cleanup**: remove the temporary product with `--purge-data`, and delete the test user. Their LDAP entries are deleted too.
