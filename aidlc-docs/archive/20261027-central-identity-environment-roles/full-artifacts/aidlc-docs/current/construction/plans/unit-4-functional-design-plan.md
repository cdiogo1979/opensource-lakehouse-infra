# Unit 4 Functional Design Plan — FreeIPA JupyterHub Authentication and Per-User Spark Identity

## Unit Context

Unit 4 connects the approved human role identities to JupyterHub and ensures each notebook Spark session uses only that user's Kerberos principal and RustFS identity. The desired behavior is already proven at the direct Spark/Iceberg boundary for the tested role matrix: `analyst-user` reads production only and cannot write; `developer-user` reads all environments and writes only dev; `write-service-account` is ETL-only and reads/writes all three buckets. Cross-environment database/table metadata visibility is accepted. RustFS denies unauthorized object reads and writes.

Current source inspection shows that `infra/jupyter/hub/jupyterhub_config.py` uses `DummyAuthenticator` and a static `user_a`/`user_b`/`admin` map. The DockerSpawner binds named per-user workspace volumes and read-only keytab/access-key/secret-key files, then sets `KERBEROS_PRINCIPAL` from the Jupyter username. `infra/jupyter/singleuser/start-session.sh` refuses missing credential files and performs `kinit` before launching the notebook command. The active MIT KDC remains authoritative pending the separately approved cutover; FreeIPA must not be silently substituted for the active HMS KDC during this design.

## Functional Design Checklist

- [x] Trace US-08/US-09 and Unit 4 requirements to authentication, group authorization, spawn/stop, session identity, workspace persistence, and revocation acceptance tests.
- [x] Inspect the current Hub/single-user image versions, authenticator dependencies, TLS trust mounts, DockerSpawner configuration, credentials, FreeIPA group/user state, and service networking without changing runtime state.
- [x] Select and document a FreeIPA LDAPS authenticator flow, group lookup, certificate trust, timeout, and fail-closed behavior. Actual pinned FreeIPA compatibility remains a Build and Test proof obligation.
- [x] Define role groups and the separate explicit administrator mapping; exclude `lakehouse-writers` and reject ambiguous group memberships.
- [x] Resolve the transitional human ticket flow: FreeIPA authenticates; the active MIT KDC remains the sole ticket authority until Unit 6; each user uses their own keytab and ticket cache.
- [x] Define an explicit provisioning-owned username-to-credentials/workspace registry; reject unknown/disabled/incomplete entries before spawn.
- [x] Require per-user read-only keytab and RustFS mounts, no service fallback, private tmpfs ticket cache, and no credential persistence.
- [x] Define login/spawn revalidation and an explicit active-server revocation action that stops the container and destroys its ticket cache; measure completion during Build and Test.
- [x] Preserve the admin workspace and existing workspaces; do not automatically transfer or delete legacy workspaces.
- [x] Generate Unit 4 functional design artifacts and record implementation verification points before NFR and infrastructure design.

## Design Questions to Resolve

1. **FreeIPA connectivity and trust:** What stable internal LDAPS endpoint and CA bundle should the Hub use while FreeIPA is isolated? The design must not depend on a browser-only hosts-file workaround or disable certificate validation.
2. **Role membership:** Are users allowed to belong to exactly one notebook role group, or can developers also be analysts? Define conflict handling and administrator authorization explicitly.
3. **Kerberos ticket delivery:** Choose a flow that gives the notebook a ticket for the authenticated user without persisting the user's password, mounting a shared service keytab, or exposing credentials to other containers. Prove it works with the active KDC until cutover and define how the principal realm changes at Unit 6.
4. **RustFS credential lifecycle:** Define how per-user S3 credentials are provisioned/rotated/revoked and associated with FreeIPA users or role groups. Existing named role credentials may be used only for the corresponding test identities; do not introduce a shared human role credential unless the access model explicitly accepts the resulting audit/attribution tradeoff.
5. **Username-to-secret mapping:** Determine whether the Hub reads a strict, allowlisted per-user credential directory, a secret store, or another already-approved mechanism. Unknown users must not be able to influence filesystem paths or mount arbitrary host files.
6. **Workspace retention:** Preserve existing named volumes and define behavior when usernames are renamed, disabled, or deleted. Do not delete workspaces during auth migration.
7. **User-visible outcomes:** Define denial and spawn-failure messages that do not reveal LDAP bind details, passwords, S3 keys, keytabs, or internal topology.
8. **Acceptance matrix:** Define UI login, group membership, spawn, per-container mounts, `klist`, Spark reads/writes against disposable tables, cross-user isolation, stop/revoke, and workspace persistence checks for developer, analyst, admin, and excluded writer identities.

## Expected Functional Design Artifacts

- `construction/unit-4/functional-design/business-logic-model.md`
- `construction/unit-4/functional-design/business-rules.md`
- `construction/unit-4/functional-design/domain-entities.md`
- Update `construction/unit-4/functional-design-clarification.md` only if a material authentication/credential lifecycle decision cannot be resolved from the approved requirements and runtime evidence.

## Safety and Scope Boundaries

- This plan is for design only. Do not install an authenticator, rebuild images, alter Compose, edit FreeIPA users/groups, change keytabs or S3 credentials, change JupyterHub authentication, start/stop services, or delete/rename workspaces.
- Do not make FreeIPA the active MIT KDC replacement or change KDC aliases, realm routing, HMS principal, or service keytabs. Unit 6 owns staged authority cutover.
- Do not mount `write-service-account`, HMS, RustFS admin, or another user's credential into notebook containers.
- Preserve the existing `admin` identity and workspace. Do not grant platform administrator privileges to developer or analyst roles.
- Unit 3 Build and Test has passed the direct role matrix, append/overwrite/delete cases for the tested operations, and core location checks, but still has secondary verification gaps. Unit 4 design may proceed; Unit 4 runtime implementation and integrated acceptance remain gated on an explicit Unit 3 completion/waiver decision.

## Approval Gate

The user approved this plan and requested continuation. Functional Design artifacts are generated at `construction/unit-4/functional-design/`. This approval authorizes design work only; it does not authorize runtime changes, credential provisioning, identity cutover, or workspace changes. Unit 3's remaining test gaps must be closed or explicitly waived before Unit 4 implementation/Build and Test.

## Design outcome

FreeIPA authenticates interactive users over LDAPS and supplies role membership. JupyterHub permits the developer and analyst groups plus the separately configured `admin` account; it denies writer/service identities and conflicting roles. A strict provisioning-owned registry maps each admitted username to that user's own keytab, RustFS credential pair, and named workspace. The notebook obtains its user ticket into a private tmpfs cache; it receives no shared writer/admin identity. During the transition, MIT remains the only active KDC. Existing admin and legacy workspace state is preserved. Active-session revocation requires an explicit server-stop action and measured completion.

The following are verification/design inputs for the next stages, not runtime claims: exact FreeIPA LDAPS hostname and CA mount/network path; the pinned LDAPAuthenticator behavior against this FreeIPA instance; encrypted JupyterHub auth-state key handling; provisioning registry format and onboarding updates for future group members; explicit FreeIPA `admin` account availability; and the operational revocation trigger and completion target. See `construction/unit-4/functional-design-clarification.md`.
