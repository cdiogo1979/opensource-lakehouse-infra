# Code Quality Assessment

- **Legacy StarRocks code**: carefully written and safe. It uses guarded targets, never prints secrets, and allowlists output. But it is bound to the retired topology: Kerberos, FreeIPA LDAP, Hive Metastore, the `iceberg-poc-*` container names, and the `.runtime/ranger-test` paths. It has no v2 tests.
- **Risks**:
  - StarRocks images are large: 2.8 GB for FE alone, and BE is similar.
  - Memory needs on a laptop. StarRocks BE typically wants several GB.
  - Polaris token lifetime. A long-lived catalog session needs OAuth2 credential renewal, not a static token.
- **Technical debt**: `write-service-account` references remain in `infra/starrocks/ldap-access`.
