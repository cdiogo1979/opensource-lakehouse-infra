# Integration Test Instructions — StarRocks Audit Capture (live, run 2026-11-26)

| # | Check | How | Result |
|---|---|---|---|
| 1 | Images and lock | rebuild both images; `workload-python-parity.sh` | PASS (57 packages, one kernel) |
| 2 | Capture installed | runtime bootstrap after recreating the FE | PASS: plugin installed 5.0.0, table ok, user created |
| 3 | Idempotence | runtime bootstrap again | PASS: plugin kept, user ok |
| 4 | Rows arrive | `audit_capture.py --status`; staging query | PASS: rows within a minute; `query` and `connection`; UTC; partition `p20261126` |
| 5 | Loader least privilege | `SHOW GRANTS FOR 'srv-auditloader'@'%'` | PASS: INSERT on the staging table only |
| 6 | No credential in the audit data | search the staging table for `IDENTIFIED BY` and the loader password | PASS: StarRocks masks it (`'***'`); the password appears nowhere |
| 7 | Read grants | full bootstrap; `SHOW GRANTS FOR ROLE` | PASS: SELECT on the staging table for role_audit_owner, _developer, _writer only; recognised as current on the next run |
| 8 | Writer token login from a Spark run | `audit-uat-starrocks_audit` (scheduled 07:20 and manual) | PASS: bronze pulled 704 rows as srv-audit-writer over TLS; silver 704 events, 0 unparsed |
| 9 | Consumer end to end | uat silver and views | PASS: 728 events = 728 distinct keys; 0 unredacted; five views active, last refresh SUCCESS |
| 10 | Jupyter password login | `lakehouse_starrocks.connect()` in a Jupyter server as an audit developer (after rebuilding the Hub image and restarting the server) | PASS (2026-11-26, run by the user): prompted for the password, logged in as the Keycloak username, read the staging table. Found and fixed on the way: the Hub image needed a rebuild; the login first used the Hub's Keycloak ID instead of the username |
