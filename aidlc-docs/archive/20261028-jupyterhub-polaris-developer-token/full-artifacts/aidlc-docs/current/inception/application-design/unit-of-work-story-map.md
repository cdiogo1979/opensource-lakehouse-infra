# Unit of Work Story Map

## Stories to owning units

| Story | Primary implementation owner | Verification owner | Coverage |
|---|---|---|---|
| US-01 — Sign in with an approved Keycloak role | Unit 1 | Unit 4 | Browser Authorization Code flow, correct developer/analyst association, denial for unapproved groups, no password grant. |
| US-02 — Work in an isolated personal environment | Unit 1 | Unit 4 | Per-user Jupyter/Spark server and named home; no Docker socket; no cross-user volume/token access; encrypted Hub state and secret non-persistence. |
| US-03 — Start Spark with my current identity | Unit 2 | Unit 4 | Own-server Hub-token binding, same-user refresh, access JWT only, exact Bearer token, cross-user/invalid-token denial, fail-closed renewal and expiry behavior. |
| US-04 — Develop across environments with dev-only writes | Unit 3 | Unit 4 | Developer reads production/UAT/dev, writes dev, denied writes elsewhere, scoped vended storage access. |
| US-05 — Analyze production data without write access | Unit 3 | Unit 4 | Analyst reads production, denied reads in UAT/dev, denied writes, scoped production credentials. |
| US-06 — Operate access without exposing credentials | Unit 1 (configuration and admission); Unit 2 (broker identity/errors); Unit 4 (diagnostics and runbook) | Unit 4 | OIDC and group configuration, binding and fail-closed behavior, token-free logs, distinguishable failure classes and operations. |

Each story has one primary owner; cross-cutting parts of US-06 are explicitly split by responsibility. Unit 4 verifies user-visible outcomes across the integrated stack and does not replace focused unit verification.

## Requirement ownership

| Requirement | Primary owner | Integration verification |
|---|---|---|
| FR-1 — Keycloak sign-in | Unit 1 | Unit 4 |
| FR-2 — Role-based admission | Unit 1 | Unit 4 |
| FR-3 — User token inheritance and refresh | Unit 2 | Unit 4 |
| FR-4 — Spark-to-Polaris authentication | Unit 2 (client handoff); Unit 3 (Polaris token validation/mapping) | Unit 4 |
| FR-5 — Scoped storage credential vending | Unit 3 | Unit 4 |
| FR-6 — Developer and analyst permissions | Unit 3 | Unit 4 |
| FR-7 — Per-user isolation and token handling | Unit 1 (runtime boundary); Unit 2 (token handling); Unit 4 (integrated checks) | Unit 4 |

## NFR ownership and validation

| NFR concern | Primary owner | Integration verification |
|---|---|---|
| OIDC state/nonce, encrypted auth state, least-privilege admission, secret separation | Unit 1 | Unit 4 |
| JWT issuer/audience/signature/expiry validation and fail-closed renewal | Units 2 and 3 | Unit 4 |
| Token lifecycle and Keycloak availability behavior | Unit 2 | Unit 4 |
| Scoped temporary storage credentials and no root-key fallback | Unit 3 | Unit 4 |
| Token-free audit logging and diagnosable failure categories | Units 1, 2, and 4 | Unit 4 |
| Local profile and production TLS distinction | Unit 1 | Unit 4 / deploy handoff |

## Coverage check

- Every approved story US-01 through US-06 has a primary implementation owner and an integration-verification owner.
- Every functional requirement FR-1 through FR-7 has an implementation owner and Unit 4 verification.
- All token, authorization, isolation, availability, and auditability constraints have explicit unit ownership; detailed test cases are produced in the relevant construction plans.
