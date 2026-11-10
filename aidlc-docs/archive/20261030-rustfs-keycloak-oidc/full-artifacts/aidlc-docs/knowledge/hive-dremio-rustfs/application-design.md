# Current Application Design — Open Source Lakehouse Infrastructure V2

This canonical file remains under its earlier knowledge namespace for continuity. The current target is the local `opensource-lakehouse-infra-v2` bootstrap described in [`../opensource-lakehouse-infra-v2/application-design.md`](../opensource-lakehouse-infra-v2/application-design.md). The original Hive/FreeIPA implementation is preserved in the intent archives.

## Current scope

The supported local journey uses Keycloak for OIDC identities and groups, Apache Polaris for Iceberg catalogs and authorization, RustFS for S3-compatible storage, and Spark for smoke-table operations. It creates a `default` data product across production, dev, and UAT. FreeIPA, MIT Kerberos, and Hive are retired from the supported Compose runtime. Airflow, JupyterHub, Jenkins, and StarRocks remain deferred and unsupported by this bootstrap.

## Verification boundary

The fresh local bootstrap, U1–U4 checks, and all four role read/write matrices passed as documented in the intent archive and deploy handoff. U2 closed under a user-accepted verification waiver: the actual human PKCE callback and some reconciliation failure-path diagnostics were not verified. The project is a local single-node setup and has not been certified for production, HA, or multi-host operation.
