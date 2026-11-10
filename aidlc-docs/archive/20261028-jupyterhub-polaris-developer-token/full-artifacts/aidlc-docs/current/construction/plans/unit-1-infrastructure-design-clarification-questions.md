# Unit 1 Infrastructure Design Clarification

The six Infrastructure Design answers select their recommended options. There is one network-topology conflict to resolve before generating the infrastructure design:

- Q3 selects attaching spawned user servers to the existing Compose network.
- Q6 selects a dedicated user-server network and says provider services should be inaccessible.
- The approved Spark journey requires user servers to reach Polaris REST and RustFS S3, while keeping Keycloak, provider databases, Docker Engine, and administrative credentials outside the user-server boundary.

## Clarification Question 1 — User-server network access

Which network boundary should Infrastructure Design use?

A) Keep user servers off the existing `core` network. Attach Hub to `core` and a dedicated user network; attach user servers to the user network and a separate data-access network that exposes only Polaris REST and RustFS S3. Attach Polaris and RustFS to both `core` and the data-access network. Do not expose Keycloak, PostgreSQL, or administrative credentials to user servers. (Recommended; supports the approved Spark flow with network separation.)

B) Attach user servers to the existing `core` network for simpler connectivity. Keep administrative credentials and Docker Engine access out of user containers, accepting that the containers can reach other services on `core`.

X) Other (please describe).

[Answer]: A

