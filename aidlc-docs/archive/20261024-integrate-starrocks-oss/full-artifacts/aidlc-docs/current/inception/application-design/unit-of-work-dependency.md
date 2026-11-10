# Unit of Work Dependency Matrix — StarRocks OSS Integration

## Dependency Table

| Unit/activity | Depends on | Consumes | Produces |
|---|---|---|---|
| Unit 1 — Identity Provisioning | Existing KDC, RustFS, and current identity-provisioning mechanisms | Approved StarRocks principal/policy settings and protected credential location | Dedicated HMS keytab/config reference and scoped RustFS credential/policy references; redacted provisioning status |
| Unit 2 — StarRocks Runtime | Unit 1 credential/configuration contract; existing Compose network and shared platform services | StarRocks image/configuration decisions, mounted credentials, service endpoints | Ready single-FE/single-BE runtime, SQL/UI loopback endpoints, persistent FE/BE state |
| Unit 3 — SQL Bootstrap and Catalog Access | Unit 1 identity contract and Unit 2 FE readiness | HMS/RustFS catalog config, bootstrap admin credential reference, database/access matrix | Reconciled Iceberg catalog, native accounts/roles/grants, redacted bootstrap status |
| Integrated verification | Units 1, 2, and 3 complete | Running stack, designated disposable/reversible write test data, test identities | Evidence for query/write/access matrix/persistence/preservation or explicit list of unverified criteria |

## Required Order

Required execution order:

1. Confirm the existing KDC and RustFS are ready.
2. Complete Unit 1 — Identity Provisioning.
3. Complete Unit 2 — StarRocks Runtime (FE and BE together).
4. Complete Unit 3 — SQL Bootstrap and Catalog Access.
5. Run integrated verification.

The sequence is acyclic. Unit 2 needs the Unit 1 credential mount contract; Unit 3 needs both the service credentials and a ready FE; integrated verification requires all three units. Shared services remain external dependencies and are not recreated or migrated by these units.

## Coordination Contracts

- Unit 1 publishes credential/configuration references and policy scope; it never prints secret values.
- Unit 2 consumes those references through mounted files/environment contracts and exposes readiness, not a control-plane API.
- Unit 3 starts only after readiness and uses StarRocks SQL for catalog and grant setup; it is an explicit repeatable operator action.
- Unit 3's storage service credential does not replace StarRocks SQL authorization. Per-user access is verified at the SQL layer.
- Unit 2 owns runtime-specific operations documentation; Units 1 and 3 document their own provisioning/bootstrap operations. Integrated verification evidence is recorded after all units.
