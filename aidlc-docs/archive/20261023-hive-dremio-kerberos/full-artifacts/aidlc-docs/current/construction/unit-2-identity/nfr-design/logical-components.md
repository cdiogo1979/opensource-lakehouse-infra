# Unit 2 Identity Provisioning — Logical Components

## Component View

This view describes responsibilities, readiness dependencies, and information flow. Concrete Compose service names, image choices, commands/API calls, mounts, policy documents, healthcheck implementation, and credential file paths remain for Infrastructure Design.

| Logical component | Responsibility | Readiness/operation contract |
|---|---|---|
| Compose lifecycle/operator interface | Starts the stack and invokes identity setup explicitly after prerequisites are ready. | Reports service status separately from identity-provisioning status. Does not claim overall setup complete when a required account or permission failed. |
| Kerberos KDC | Owns the disposable realm and Kerberos principals/keytabs. | Realm health and service identity availability precede principal creation. Existing Hive service principal and keytab are preserved. |
| Metastore PostgreSQL | Owns Hive metastore metadata and its native admin role. | Database ready before any account setup; Hive service role remains separate; writer receives no direct metastore database credential. |
| Hive Metastore/Hadoop authorization adapter | Coordinates writer capability and post-ETL database reader grants through the Hive-owned mechanism. | Metastore ready before adapter use. Unsupported authorization behavior is a feasibility failure; successful setup does not prove effective-user enforcement. |
| RustFS account/policy adapter | Creates component-native admin, writer, and test-user credentials/policies where supported. | RustFS and bucket ready before setup. Each policy is component-owned and independently verified; health does not prove access scope. |
| Dremio account adapter | Creates the native Dremio admin and writer local accounts. | Dremio initial setup and API readiness required. Source/query mapping and non-admin Space write validation belong to Unit 4. |
| Spark consumer | Uses the caller's Kerberos identity and RustFS credential for ETL or later queries. | No local Spark user directory is introduced. ETL is gated on writer credentials and permissions being provisioned. |
| JupyterHub consumer (Unit 5) | Maps notebook user labels to isolated Spark sessions and user credentials. | Not provisioned by Unit 2; consumes the per-user identity/credential contract when Unit 5 is implemented. |
| Unit 2 provisioner | Coordinates the component adapters in a fixed sequential workflow and reports per-component outcomes. | Runs once on operator request after required readiness checks; preserves prior successful setup on failure and supports safe rerun. |
| Unit 3 post-ETL grant operation | Applies reader grants after `databaseA` and `databaseB` exist. | Cannot run before ETL creates the databases. Reports grants as configured only after the owning component confirms the operation. |

## Readiness and Provisioning Flow

```text
Compose services ready:
  KDC + PostgreSQL/schema + RustFS/bucket + Hive Metastore + initialized Dremio
                                      |
                                      v
                    Validate protected credential files
                                      |
                                      v
                 Unit 2 one-shot provisioner (sequential)
                   |             |             |
                   v             v             v
               Kerberos       RustFS         Dremio
               principals    accounts/       local admin
               and keytabs    policies       and writer
                   |             |             |
                   +-------------+-------------+
                                 |
                    Hive writer capability setup
                                 |
                     per-component result report
                                 |
                                 v
                    Unit 3 ETL as write-service-account
                                 |
                                 v
                   Post-ETL reader-grant operation
                       user_a: databaseA
                       user_b: databaseA + databaseB
```

The graph is logical. Infrastructure Design may refine independent service startup, but account setup must wait on every service it calls. Reader grants remain a separate post-ETL phase. No component's successful setup implies another component's account or permission is ready.

## Credential and Data Boundaries

- Protected local credential files are inputs/outputs to the one-shot provisioning flow; only owning adapters may consume their component's setup credentials.
- The coordinator handles references and status, not secret values.
- Component state remains in its existing authority: KDC database, Dremio account store, RustFS user/policy store, and PostgreSQL roles.
- Hive metadata and RustFS objects remain separate. The writer receives no PostgreSQL metastore login.
- No centralized identity database, persistent coordinator, or additional policy authority is introduced.

## Failure Boundaries

- Missing service readiness or required credential files stops the run before mutation.
- A component adapter failure stops subsequent required steps and marks overall provisioning failed/incomplete.
- Successful earlier changes remain for diagnosis and safe rerun; automatic rollback or volume reset is prohibited.
- Unsupported account/policy APIs or authorization semantics are surfaced as blockers, not retried indefinitely or bypassed with admin credentials.
- Component health and account-provisioning success do not prove end-user allow/deny outcomes or effective-user propagation.

## Cross-Cutting Constraints

- All published developer ports remain loopback-only; provisioner-to-component calls use the private Compose network.
- Kerberos, Dremio, RustFS, and PostgreSQL credentials are distinct; admin credentials remain distinct from test-user and writer credentials.
- Output reports identity, component, operation, and state while redacting secret material.
- No monitoring, alerting, HA, scaling, UI, or persistent identity-management component is added.
