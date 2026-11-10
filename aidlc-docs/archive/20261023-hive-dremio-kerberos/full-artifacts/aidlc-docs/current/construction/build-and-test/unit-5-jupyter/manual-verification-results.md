# Manual Verification Results — Unit 5 JupyterHub and Per-User Spark

Run the scenarios in `integration-test-instructions.md` through `http://127.0.0.1:8008`. Keep credential values, keytab contents, ticket caches, and full environment output out of this record. Record only pass/fail and sanitized evidence. Do not rotate credentials or remove volumes.

| Gate | Result | Sanitized evidence / failure category |
|---|---|---|
| Sign in as `user_a`, `user_b`, and `admin`; unknown label rejected | PARTIAL | Local smoke sign-ins/spawns passed for all three configured labels; unknown-label rejection not checked. |
| Each session runs as `10001:10001`; matching read-only mounts only; no Docker socket | PARTIAL | All three containers ran as `10001:10001`; detailed mount flags/group inspection completed for `user_a` only. |
| Non-root reads own keytab and RustFS files; `klist` principal matches the session | PASS | `test -r` succeeded for all three identity files in all three sessions; `klist` showed each corresponding `@LAKEHOUSE.LOCAL` principal. |
| `user_a` reads allowed `databaseA.customer` | PENDING | |
| `user_b` reads allowed `databaseA.customer` | USER-REPORTED PASS | User reported the query returned successfully. |
| `user_a` read of `databaseB.customer` is an authorization denial, not an infrastructure failure | REPORTED; CLASSIFICATION PENDING | User reported access denied in the expected test context; exception category/text not supplied, so Hive authorization vs RustFS/S3 denial is unconfirmed. |
| `user_b` read of `databaseB.customer` succeeds | USER-REPORTED PASS | User reported the query worked and returned successfully. |
| Admin sample query reads `iceberg.databaseA.customer` | PASS | Read-only `LIMIT 5` succeeded after Hadoop UGI keytab login; sanitized sample rows returned. |
| RustFS-backed Iceberg queries succeed for each configured session | PENDING | |
| Per-user workspace is isolated and survives that user's server recreation | PENDING | |
| `user_a`, `user_b`, and `admin` sessions run concurrently | PENDING | |

After filling this table, report any failure with its category (authorization, Kerberos, Hive connectivity, missing table, resource/spawn, RustFS credentials, or other) and sanitized error text. Do not retry failed user cases with another identity.
