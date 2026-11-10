# Functional Design Plan — Unit 4: Dremio Source and Query Identity

## Scope

Define the Dremio query identity and database authorization behavior for `user_a` and `user_b`, using the existing Hive 3.x source, Kerberos service identity, Hive Metastore, RustFS warehouse, and Dremio 26.0.5 Community deployment. Unit 4 consumes the completed Unit 1–3 configuration and sample data. It does not rotate RustFS credentials, recreate the source, reset volumes, or modify data.

Primary stories: US-ID-03 and US-AUTH-02. Related stories: US-CAT-01, US-CAT-02, US-ID-02, US-JDBC-01, and US-DOC-01.

## Approved scope and constraints

- Preserve the existing Dremio Hive source and its working RustFS credential configuration. The user explicitly requested that the RustFS writer key not be rotated.
- Map Dremio local usernames `user_a` and `user_b` to the matching Hive effective usernames (as-is); do not use an administrator or writer identity for query tests.
- Use the Hive source's **Storage Based with User Impersonation** authorization mode, with **Allow VDS-based Access Delegation** disabled so the querying user is impersonated for virtual dataset queries.
- Keep the proxy-user allowlist restricted to `admin`, `write-service-account`, `user_a`, and `user_b`, and the existing Compose subnet.
- Acceptance matrix: `user_a` can query `databaseA` and is denied on `databaseB`; `user_b` can query both. Record the Dremio username, effective Hive username, target database/table, and observed result.
- Query source tables directly to isolate Hive authorization from Dremio Space permissions. Also check the existing Space views as a secondary path; a Dremio-level Space denial alone does not prove Hive authorization.
- Do not treat successful table reads using the Hive source's static RustFS writer credentials as proof of per-user object-store authorization.
- If the Hive Metastore/RustFS path cannot enforce the matrix, preserve the current system and report the observed boundary plus the smallest architecture adjustment for review. Do not grant broad permissions or weaken the matrix.

## Findings carried into design

- The running Dremio, Hive Metastore, KDC, RustFS, PostgreSQL, and Spark services are available; Hive Metastore reports healthy.
- The Hive source has already been created manually and the user confirmed Dremio queries work.
- Dremio's Hive connector configuration has bounded proxy-user host/user settings and S3 compatibility mode.
- The checked-in Hive Metastore template configures Kerberos, S3A, and `hive.metastore.execute.setugi`, but does not currently declare Hive's storage-based authorization pre-event listener/provider. Therefore the allow/deny matrix is not yet established by the configuration, even though Dremio connectivity and data reads work.
- The local runtime credential directory contains `user_a` and `user_b` Kerberos keytabs and RustFS credentials, but no Dremio passwords for these users. Dremio's supported local-user provisioning path and separate query credentials must be established before testing.

## Functional Design Checklist

- [x] Review Unit 4 stories, requirements, Units 1–3 contracts, current Dremio/Hive configuration, and Unit 3 completion evidence.
- [x] Define explicit Dremio-to-Hive username mapping and the expected effective-user evidence.
- [x] Define the Dremio direct-source and secondary view-query authorization scenarios.
- [x] Define the four allow/deny outcomes, required Dremio local accounts, and credential separation.
- [x] Define the Hive authorization configuration gap and fail-closed feasibility behavior.
- [x] Document the fixed-credential RustFS limitation and avoid claiming user-specific storage authorization without evidence.
- [x] Generate and validate Unit 4 functional design artifacts against approved scope.

## Feasibility Gates

- Confirm `user_a` and `user_b` can authenticate as distinct Dremio local users without platform-admin privileges.
- Confirm Dremio sends each matching username through the Hive source and Hive Metastore evaluates it as the effective user.
- Confirm Hive storage-based authorization is configured and that its filesystem checks on RustFS distinguish the required profiles.
- Execute direct-source queries for all four matrix outcomes; record effective user and the component that allowed or denied each query.
- If the current Hive Metastore/RustFS setup cannot enforce the matrix, stop before changing the authorization architecture and return the smallest proposed adjustment for review.

## Current Status

Functional design artifacts are complete and ready for user review. No runtime configuration, credentials, or data were changed. The per-user Dremio/Hive authorization matrix remains unverified; the missing Hive storage-based authorization configuration and missing local Dremio test-user credentials are explicit implementation/test gates.
