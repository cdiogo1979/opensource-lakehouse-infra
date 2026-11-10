# Component Methods and Interfaces — Central Identity and Environment Access

These are logical contracts, not implementation signatures. Detailed APIs, retry rules, and formats are assigned to construction units.

## FreeIPA directory

- `authenticate_user(username, password) -> authentication_result`: validate JupyterHub LDAP login over TLS.
- `list_role_memberships(username) -> groups`: return authoritative role groups for the principal.
- `issue_user_kerberos_credential(username) -> protected_credential_reference`: use FreeIPA-managed per-user Kerberos credentials; no password persistence.
- `provision_service_principal(name) -> protected_keytab_reference`: provision service identities through the approved protected workflow.

## Identity and policy provisioner

- `load_role_policy_document() -> validated_policy_model`: validate role, bucket, prefix, and actions; reject unknown scopes and overlapping/broader policy drift.
- `read_directory_assignments() -> identity_group_snapshot`: read approved users, groups, and memberships from FreeIPA using a protected bind identity.
- `reconcile_rustfs_identities(snapshot, policy_model) -> reconciliation_report`: ensure RustFS per-user/service identities, role groups, policy attachments, and least-privilege S3 policies.
- `verify_rustfs_effective_access(identity, expected_scope) -> verification_report`: run allow and deny probes for representative object paths without exposing credentials.
- `reconcile_cutover(old_users, new_users) -> cutover_report`: retire `user_a`/`user_b` only after acceptance checks pass; preserve data and the writer's RustFS S3 key. Service Kerberos keytabs are replaced during FreeIPA cutover.

## RustFS IAM

- `create_or_update_policy(name, policy_document) -> policy_state`: apply a reviewed role policy idempotently.
- `add_or_remove_user_from_group(user, role_group) -> membership_state`: mirror FreeIPA role membership.
- `activate_or_deactivate_user_key(user, key_reference) -> key_state`: manage individual RustFS credentials, including revocation.
- `authorize_s3_request(identity, action, bucket, key) -> allow_or_deny`: enforce every S3 request against current IAM policy.

## JupyterHub and notebook runtime

- `authenticate(username, password) -> hub_identity`: delegate authentication to FreeIPA LDAP over TLS.
- `authorize_spawn(username, groups) -> spawn_decision`: allow approved human groups; deny service identities and unauthorized users.
- `prepare_user_runtime(username) -> isolated_identity_mounts`: mount only that user’s protected Kerberos and RustFS identity files into the user container.
- `terminate_user_sessions(username) -> cleanup_report`: stop notebook/Spark session processes during an explicit access revocation and remove their private ticket caches.

## Spark and Hive Metastore

- `connect_metastore(principal, database, operation) -> metadata_result`: authenticate with the user’s Kerberos identity and apply configured metastore authorization.
- `read_or_write_objects(principal, bucket, key, operation) -> result`: use the caller-specific RustFS credentials; RustFS makes the final object authorization decision.
- `submit_etl_job(bundle_revision, writer_identity) -> job_result`: use only the existing `write-service-account` identity for non-interactive Airflow workloads.

## StarRocks LDAP groups and native RBAC

- `authenticate_ldap_user(username, password) -> authentication_result`: validate a registered StarRocks user against FreeIPA LDAP over TLS.
- `resolve_ldap_groups(user_dn) -> group_set`: StarRocks LDAP Group Provider reads the approved role-group membership using a read-only bind.
- `map_external_group_to_role(group_name) -> role_set`: assign the native StarRocks role granted to that external LDAP group.
- `authorize_starrocks_query(user, catalog, database, object, operation) -> allow_or_deny`: native StarRocks grants check the explicit resource and action scope.
- `read_external_iceberg_data(starrocks_service_identity, location) -> query_data`: after native SQL authorization, StarRocks uses its separate service credential for HMS and RustFS.

## Security contract

Credential material is passed by protected file references or secret mounts, never as policy data, command-line arguments, ordinary environment values, logs, or bundle contents. A principal must not receive another principal’s keytab, S3 key, or ticket cache.
