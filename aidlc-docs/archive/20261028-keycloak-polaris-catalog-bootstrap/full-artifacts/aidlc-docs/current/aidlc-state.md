# AI-DLC State Tracking

## Project Information
- **Project Type**: Brownfield
- **Start Date**: 2026-10-28
- **Current Stage**: CLOSED — verification waiver recorded; full intent archive retained
- **Intent**: Replace FreeIPA with Keycloak and Hive Metastore with Apache Polaris; remove FreeIPA, Hive, and MIT Kerberos from the target Compose setup while deferring Airflow, JupyterHub, and StarRocks integrations. Define a platform-admin journey to create the initial `default` data product across production, dev, and UAT, including catalogs/namespaces, buckets, role groups, and a smoke-test table in each namespace.
- **Intent ID**: `20261028-keycloak-polaris-catalog-bootstrap`
- **Previous Intent**: Closed and archived at `aidlc-docs/archive/20261027-central-identity-environment-roles/`.

## Workspace State
- **Existing Code**: Yes
- **Programming Languages / Configuration**: Python, Bash, SQL, YAML, Dockerfiles, Spark/Hadoop configuration
- **Build System**: Docker Compose, Docker image builds, Python tooling, shell scripts
- **Project Structure**: Brownfield local lakehouse infrastructure stack with service-specific images and Compose overlays
- **Workspace Root**: `/Users/carlosdiogo/code_repo/opensource-lakehouse-infra-v2`
- **Previous intent closure**: The previous intent is CLOSED with a verification waiver. Its full evidence remains archived. `.runtime` was removed from this v2 copy; the original project directory is retained separately as a reference.

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "archive": null,
  "current_stage": "CLOSED",
  "intent_id": "20261028-keycloak-polaris-catalog-bootstrap",
  "previous_intent": "aidlc-docs/archive/20261027-central-identity-environment-roles",
  "status": "COMPACTION",
  "summary": "U1 passed. U2 negative-token and Keycloak outage/reconciliation checks passed. The user accepted a verification waiver for the unverified human PKCE callback and some reconciliation failure-path diagnostics. U3 buckets and RustFS scoped STS session tests pass. U4 end-to-end bootstrap passed: identity/groups, three buckets/catalogs/namespaces, grants, writer auth, Spark smoke-table create/write/read plus vended-credential access across prod/dev/UAT, and temporary-identity live read/write matrix for all four roles. The user approved require-header=false for the configured single lakehouse realm to accommodate Iceberg 1.8.1 header propagation; revisit before adding another realm. The documented bootstrap rerun passed without duplicate rows or bucket data deletion. This waiver is not production approval.",
  "verification_outcome": "waived",
  "verification_waiver": {
    "accepted_by_user": true,
    "accepted_on": "2026-10-28",
    "details": "The user said to accept the remaining gaps and proceed. The human PKCE callback browser flow (no actual callback URI or owner username supplied) and some duplicate/missing-user, unsupported-group, and incomplete-Polaris-update reconciler diagnostics remain unverified. Negative-token checks and Keycloak outage/reconciliation behavior passed. This waiver records incomplete verification; it is not a production pass or deployment authorization."
  }
}
```
<!-- intent-lifecycle:end -->

## Stage Progress
- [x] Workspace detection: Brownfield project; previous intent was CLOSED and archived.
- [x] Reverse engineering of the existing Compose, service images, storage, catalog, identity, and workload integration.
- [x] Requirements analysis and approval.
  - [x] Clarifying questions and extension opt-ins answered.
- [x] Workflow planning and user approval.
- [x] User stories generation approval.
- [x] Application Design question answers reviewed.
- [x] Resolve Question 7 and complete Application Design plan review.
- [x] Approve the Application Design plan.
- [x] Application Design artifact review and approval.
- [x] Units Generation planning answers reviewed.
- [x] Approve the Unit of Work plan.
- [x] Units Generation artifacts and approval.
- [x] Unit 1 Functional Design plan answers reviewed.
- [x] Resolve legacy-volume cleanup trigger.
- [x] Approve the U1 Functional Design plan.
- [x] Generate and validate U1 Functional Design artifacts.
- [x] Approve U1 Functional Design artifacts.
- [x] Unit 1 NFR requirements plan answers reviewed.
- [x] Approve the U1 NFR Requirements plan.
- [x] Generate and validate U1 NFR Requirements artifacts.
- [x] Approve U1 NFR Requirements artifacts.
- [x] Unit 1 NFR Design plan answers reviewed.
- [x] Approve the U1 NFR Design plan.
- [x] Generate and validate U1 NFR Design artifacts.
- [x] Approve U1 NFR Design artifacts.
- [x] Unit 1 Infrastructure Design plan answers reviewed; all ten questions are resolved.
- [x] Approve the U1 Infrastructure Design plan.
- [x] Generate U1 Infrastructure Design and Deployment Architecture artifacts.
- [x] Review and approve U1 Infrastructure Design artifacts.
- [x] Approve the U1 Code Generation plan.
- [x] Generate U1 core Compose runtime, deferred boundary, operator scripts, and documentation; U1 Build and Test subsequently verified the runtime.
- [x] Prepare and approve the U1 Build and Test plan.
- [x] Build and Test U1 runtime; see `construction/unit-1/build-test-report.md`.
- [x] Approve U2 Functional Design plan at `construction/plans/unit-2-functional-design-plan.md`.
- [x] Generate U2 Functional Design artifacts; see `construction/unit-2/functional-design/`.
- [x] Review and approve U2 Functional Design artifacts.
- [x] Complete and approve the U2 NFR Requirements plan at `construction/plans/unit-2-nfr-requirements-plan.md`.
- [x] Generate U2 NFR Requirements artifacts; see `construction/unit-2/nfr-requirements/`.
- [x] Review and approve U2 NFR Requirements artifacts.
- [x] Answer and approve the U2 NFR Design plan at `construction/plans/unit-2-nfr-design-plan.md`.
- [x] Generate U2 NFR Design artifacts; see `construction/unit-2/nfr-design/`.
- [x] Review and approve U2 NFR Design artifacts.
- [x] Answer and approve the U2 Infrastructure Design plan at `construction/plans/unit-2-infrastructure-design-plan.md`.
- [x] Generate U2 Infrastructure Design artifacts; see `construction/unit-2/infrastructure-design/`.
- [x] Review and approve U2 Infrastructure Design artifacts.
- [x] Prepare the U2 Code Generation plan at `construction/plans/unit-2-code-generation-plan.md`.
- [x] Review and approve the U2 Code Generation plan; user authorized generation.
- [x] Generate U2 tracked Keycloak/Polaris configuration and explicit operator helpers; see `construction/unit-2/code/code-summary.md`.
- [x] Review and approve U2 generated source; see `construction/unit-2/code/code-summary.md`.
- [x] Prepare the U2 Build and Test plan at `construction/plans/unit-2-build-and-test-plan.md`.
- [x] Approve the U2 Build and Test plan and begin verification.
- [x] Close U2 Build and Test with a user-accepted verification waiver. The human PKCE callback and some reconciliation failure-path diagnostics remain unverified; negative-token and Keycloak-outage checks passed. Catalog grants and the identity role matrix are verified in U4.
- [x] U3 RustFS bucket and STS primitives implemented and verified; see `construction/unit-3/build-test-report.md`.
- [x] U4 product bootstrap resources and role grants; see `construction/plans/unit-4-build-and-test-plan.md`.
- [x] U4 Spark smoke tables created and read back in all three environments; vended-credential access verified. End-to-end bootstrap and rerun passed.
- [x] U4 temporary-identity positive/negative read/write matrix passed for developer, analyst, owner, and writer across prod/dev/UAT; temporary identities and probe rows were removed. See `construction/unit-4/build-test-report.md`.
- [x] Record the accepted waiver for the U2 human owner/callback and remaining reconciliation diagnostic/failure-path checks.
- [x] Prepare deploy handoff with local startup/bootstrap instructions, test evidence, limitations, and PR draft; no deployment or PR was executed.
- [x] User accepted closure with a verification waiver; U2 callback and reconciliation diagnostic limitations are recorded.

## Current Gate
The default-product bootstrap and Spark checks have passed: identity/groups, three buckets/catalogs/namespaces, grants, writer authentication, Spark smoke-table create/write/read plus scoped vended-credential access in prod/dev/UAT, and the temporary-identity positive/negative read/write matrix for all four roles across all environments. Temporary identities and uniquely tagged probe rows were removed and the original smoke-table rows verified. The user approved `polaris.realm-context.require-header=false` for the configured single `lakehouse` realm because Iceberg 1.8.1 omits `Polaris-Realm` during vended-credential refresh. The documented full bootstrap rerun passed without duplicate rows; bucket contents were preserved. U2 wrong-audience/expiry rejection and Keycloak outage behavior are verified. The deploy handoff is preserved at `aidlc-docs/archive/20261028-keycloak-polaris-catalog-bootstrap/full-artifacts/aidlc-docs/current/deploy/deploy-handoff.md`. The intent is CLOSED with a user-accepted verification waiver for the human PKCE callback and some reconciliation failure-path diagnostics; this is not production approval. Before adding another Polaris realm, restore strict realm-header enforcement or upgrade/fix the client.


## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis |
| Property-Based Testing | Partial (pure functions and serialization round-trips) | Requirements Analysis |
| Resiliency Baseline | No | Requirements Analysis |
