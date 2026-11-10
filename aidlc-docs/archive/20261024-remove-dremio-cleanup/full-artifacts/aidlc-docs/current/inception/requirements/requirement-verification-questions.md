# Requirements Verification Questions — Remove Dremio and Clean Project

Please answer every question by filling in the `[Answer]:` line. These decisions set the cleanup boundary. Dremio-specific files and local state are identifiable, but the project also contains Hive/RustFS data, Kerberos state, shared credentials, notebook workspaces, and TPCH data that could be lost by broad cleanup.

## Question 1 — What should remain after Dremio is removed?

A) **Recommended:** Keep Hive Metastore, PostgreSQL, Kerberos, RustFS, Spark, JupyterHub, and the TPCH Spark ETL. Remove Dremio and all Dremio-only JDBC/Spaces/views integration and references.

B) Keep only Hive Metastore, PostgreSQL, Kerberos, and RustFS. Also remove Spark, JupyterHub, and the TPCH workload.

C) Keep Hive, PostgreSQL, Kerberos, RustFS, and Spark/TPCH, but remove JupyterHub as well as Dremio.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 2 — What local Dremio runtime state may be deleted?

A) **Recommended:** Remove Dremio-specific local passwords/keytab, the `dremio` principal from the existing KDC, and only the Dremio Docker data volume/container state. Preserve Hive/PostgreSQL metadata, RustFS objects, other Kerberos principals, shared credentials, TPCH data/results, and Jupyter workspaces.

B) Remove Dremio source/configuration files only. Preserve all local credentials, KDC state, and Docker volumes, including Dremio state.

C) Remove Dremio-specific credential files and the Dremio Docker volume, but leave the Dremio Kerberos principal in the KDC and preserve all other state.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 3 — Security Baseline Extension

Should security extension rules be enforced as blocking constraints for this cleanup?

A) Yes — enforce the Security Baseline.

B) **Recommended:** No — skip the extension for this local PoC cleanup; functional secret/data preservation requirements still apply.

C) Other (please describe after `[Answer]:` below)

[Answer]:B

## Question 4 — Property-Based Testing Extension

Should property-based testing rules apply to any pure helper logic changed during cleanup?

A) Yes — enforce all PBT rules.

B) **Recommended:** Partial — apply only to changed pure functions and serialization round-trips.

C) No — skip PBT rules for this infrastructure-focused cleanup.

D) Other (please describe after `[Answer]:` below)

[Answer]:B

## Question 5 — Resiliency Baseline Extension

Should resiliency baseline guidance apply to the retained local stack?

A) Yes — apply the resiliency baseline as design guidance.

B) **Recommended:** No — skip it for this local PoC cleanup.

C) Other (please describe after `[Answer]:` below)

[Answer]:B
