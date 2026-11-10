# StarRocks Integration — Requirement Verification Questions

Please select one option for each question by filling in the `[Answer]:` line. Use the final `X) Other` option when needed. Decisions here will define the scope of the StarRocks OSS integration; Ranger is not assumed to be included unless you select it.

## Question 1 — Integration scope
Which project should this intent change?

A) Add StarRocks to `hive-dremio-rustfs` only. Leave `airflow-spark-jenkins` unchanged for now.

B) Add StarRocks to `hive-dremio-rustfs` and migrate the sibling Airflow Spark job from Nessie to Hive Metastore/RustFS.

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2 — StarRocks workload
What should StarRocks do with the existing Iceberg tables?

A) Query-only engine for existing Iceberg tables. Spark remains the writer.

B) Query and write Iceberg tables from StarRocks as well as Spark.

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 3 — Authentication and Kerberos requirement
StarRocks' documented Kerberos integration uses service-process keytabs/TGTs for HMS access; it does not establish per-query end-user Kerberos impersonation through to Hive and RustFS. Which requirement applies?

A) Use a StarRocks service identity for HMS/storage access and StarRocks-native SQL users/roles. Do not require user Kerberos propagation.

B) Per-user Kerberos identity must propagate from the SQL client through StarRocks to HMS and RustFS. If StarRocks cannot provide this, treat that as a blocker.

C) Use a StarRocks service identity for HMS/storage access and LDAP/SSO for SQL login. Do not require user Kerberos propagation.

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4 — Authorization and Ranger
How should StarRocks permissions be managed in this intent?

A) Use StarRocks native users and SQL roles/grants for this PoC; defer Ranger.

B) Include Apache Ranger now for StarRocks policies, including the needed Ranger service/plugin configuration.

C) Use LDAP-backed StarRocks authentication and native StarRocks roles; defer Ranger.

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5 — RustFS access identity
Which RustFS identity should StarRocks use to read Iceberg data?

A) Create a dedicated StarRocks read-only RustFS identity, scoped to the lake data it needs.

B) Reuse the existing Hive service identity for reads.

C) Reuse another existing RustFS identity (name it after `[Answer]:`).

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6 — SQL users and data permissions
Which StarRocks user/role setup should be provisioned for the PoC?

A) Only an administrator initially; define user roles after connectivity and query validation.

B) Administrator plus the existing `user_a`, `user_b`, and `write-service-account` roles/users, with database-level access rules aligned to current requirements.

C) Administrator plus a small set of shared roles (read-only and writer); defer mapping individual users.

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 7 — Local operations
How should StarRocks run in Docker Compose?

A) Single-node PoC (one FE and one BE), persistent named volumes, host ports bound to loopback, and a documented resource requirement.

B) Single-node PoC, started only with an optional Compose profile so normal Hive/Spark startup stays lightweight.

C) Multi-node/distributed deployment design, even if run locally for the first prototype.

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 8 — Initial verification
What is the minimum acceptance check for this integration?

A) StarRocks starts, connects to HMS and RustFS, lists the existing databases/tables, and successfully queries one existing Iceberg sample table.

B) Option A plus negative SQL authorization tests proving a restricted user is denied an ungranted database/table.

C) Option B plus a StarRocks write to Iceberg and a cross-engine readback from Spark.

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 9 — StarRocks release selection
How should the StarRocks OSS image version be selected and maintained?

A) Pin a current stable OSS release after checking compatibility, with an explicit tag/digest in Compose.

B) Use a floating latest tag for this local PoC.

C) I will provide a specific StarRocks version/tag.

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question: Security Baseline Extension
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints.

B) No — skip all SECURITY rules; this is a local PoC.

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question: Property-Based Testing Extension
Should property-based testing rules be enforced?

A) Yes — enforce all PBT rules.

B) Partial — enforce PBT rules only for pure functions and serialization round-trips.

C) No — skip PBT rules; this is a thin infrastructure integration.

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question: Resiliency Baseline Extension
Should the resiliency baseline be applied as directional design-time guidance?

A) Yes — apply it as a starting point for availability, recovery, and observability decisions.

B) No — skip it for this local PoC.

X) Other (please describe after [Answer]: tag below)

[Answer]: B
