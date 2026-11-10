# Requirements Clarification Questions

Two answers need clarification before the requirements can be finalized.

## Clarification 1 — Dremio authentication and Hive impersonation
Your answer to Question 4 selected Kerberos authentication for users at Dremio, followed by per-user Hive impersonation. The current target image is Dremio Community 26.0.5. Dremio's current edition documentation describes Community local identities, while Kerberos/SASL for the Hive source is a separate service-to-metastore connection setting. Which behavior should this PoC require?

A) Keep Dremio Community local username/password login. Dremio uses its Kerberos service principal/keytab to connect to the Hive Metastore, and the Hive source impersonates the logged-in Dremio query username under explicit Hive proxy-user rules.

B) User Kerberos authentication at Dremio is mandatory. Change to an edition/product and version that supports the required client authentication and per-user identity propagation, even if this changes the current Dremio Community constraint.

C) Use Kerberos only for Dremio's service connection to Hive; do not require per-user Hive impersonation from Dremio. Keep user-level impersonation and its positive/negative checks in Spark/Hive instead.

X) Other (please describe after `[Answer]:` below)

[Answer]: A

## Clarification 2 — RustFS identity-based access
Your answer to Question 5 selected identity-based authentication for Dremio, Spark, and RustFS. RustFS exposes an S3-compatible API whose authenticated requests use S3 Signature Version 4 access/secret credentials; this is a separate mechanism from Kerberos. Which object-store behavior should the PoC require?

A) Keep RustFS on S3 credentials, supplied as local ignored secrets. Kerberos and user impersonation apply to the Hive/Hadoop access path only.

B) Keep RustFS on the S3 protocol but use distinct S3 identities/credentials and policies for Dremio, Spark, and test users. Kerberos still applies only to Hive/Hadoop access.

C) Kerberos must authenticate object-store requests too. Replace RustFS or add a gateway/storage layer that supports the required Kerberos-authenticated access, and treat that as part of the PoC scope.

X) Other (please describe after `[Answer]:` below)

[Answer]:X , the final objective is to implement some level of RBAC, so a given user should only be able to access the same files independently if its coming from dremio , jupyter or directly in rustfs

## Reference notes

- [Dremio editions](https://docs.dremio.com/editions/) lists Hive Metastore as a Community source and lists local identities for Community; external LDAP/OIDC identity providers are Enterprise features.
- [Dremio Hive source configuration](https://docs.dremio.com/current/data-sources/lakehouse-catalogs/hive/) documents Hive Kerberos/SASL and storage-based user impersonation as Hive source settings.
- [RustFS S3 protocol documentation](https://docs.rustfs.com/content/en/administration/protocols/s3.md) describes authenticated S3 clients signing requests with access and secret keys.
