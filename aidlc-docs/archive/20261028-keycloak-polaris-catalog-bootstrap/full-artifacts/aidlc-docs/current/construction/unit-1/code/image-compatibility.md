# Unit 1 Image Compatibility Record

Started during Code Generation and verified during U1 Build and Test on 2026-10-28. Pulled image digests are recorded below; Docker selected `linux/arm64` for the local engine.

| Image | Version | Compose reference | Platform/digest evidence | Status |
|---|---|---|---|---|
| Keycloak | 26.8.1 | `quay.io/keycloak/keycloak:26.8.1@sha256:79c623a22abacf3fe6c00a5fb30f5b7843d717b234033b80995891c06116d244` | Pulled and inspected successfully for `linux/arm64`; resolved repo digest matches the configured immutable reference. | Verified for local platform |
| Apache Polaris | 1.8.0 | `apache/polaris:1.8.0@sha256:347615e736cab2c9be0d8c464552ac930be4755302bb0aeb745216bbae99ba5b` | Pulled and inspected successfully for `linux/arm64`; resolved repo digest matches the configured immutable reference. | Verified for local platform |
| PostgreSQL | 17.11-alpine3.24 | `postgres:17.11-alpine3.24@sha256:1bcc18d81671b02906296aad470ec9778a6b71016ce953092024b680bad007b0` | Pulled and inspected successfully for `linux/arm64`; resolved repo digest matches the configured immutable reference. Same reference used for both provider DBs and the schema helper. | Verified for local platform |
| RustFS | 1.0.4 | `rustfs/rustfs:1.0.4` | User explicitly accepted the version-pinned tag without immutable digest pinning. Pulled successfully; local arm64 image resolved to `sha256:ed9210d6411d77ffceb70d94b964a3cb7d225983368bc25bebe01e995293dcc2`. The previous 1.0.0 digest was not reused. | **Accepted by user: version tag only; pulled and recorded** |

The Docker engine is `linux/arm64`. The pinned Keycloak, Polaris, and PostgreSQL references were pulled and inspected; each resolved repo digest matched the configured reference. RustFS was pulled by its user-approved version tag and resolved to the arm64 digest recorded above. No image builds were needed or performed.

Sources:

- Keycloak [26.8.1 release](https://www.keycloak.org/2026/10/keycloak-2681-released) and [container image docs](https://www.keycloak.org/server/containers).
- Polaris [1.8.0 image tags](https://hub.docker.com/r/apache/polaris/tags) and [relational JDBC documentation](https://polaris.apache.org/releases/1.8.0/metastores/relational-jdbc/).
- PostgreSQL [17.11 image tag metadata](https://hub.docker.com/_/postgres/tags).
- RustFS [1.0.4 release](https://github.com/RustFS/RustFS/releases), [container usage](https://github.com/rustfs/rustfs), and [credential file injection](https://docs.rustfs.com/en/operations/credentials).
