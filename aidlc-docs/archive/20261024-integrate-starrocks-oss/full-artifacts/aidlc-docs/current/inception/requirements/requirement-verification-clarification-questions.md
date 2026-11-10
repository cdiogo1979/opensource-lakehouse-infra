# StarRocks Integration — Requirement Clarifications

Two requirements need clarification before the requirements baseline can be finalized.

## Clarification 1 — RustFS credentials for StarRocks writes
You selected StarRocks query and write support for Iceberg tables, and also selected a read-only RustFS identity. How should StarRocks receive the object-store permissions needed to write?

A) Use one dedicated StarRocks RustFS identity with read/write access limited to the Iceberg warehouse prefix.

B) Configure separate read-only and read/write StarRocks catalog identities, if supported by the selected setup; keep query access read-only and use the write catalog only for explicit writes.

C) Change StarRocks to query-only and keep the dedicated RustFS identity read-only; Spark remains the only writer.

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Clarification 2 — StarRocks database access matrix
Question 8 requires a restricted-user denial test, but the intended database grants were not specified. Which StarRocks SQL access policy should be implemented?

A) `user_a` reads `databaseA` only; `user_b` reads `databaseB` only; `write-service-account` can read/write both; `admin` has full access.

B) `user_a` and `user_b` can read both databases; only `write-service-account` can write; `admin` has full access.

C) All listed users can read both databases; `write-service-account` and `admin` can write; no per-database read restriction is required.

X) Other (please describe the grants for each user after [Answer]: tag below)

[Answer]: X , it should be the same as we have defined for spark / jupyter
