# Unit 2 Functional Design — Credential Clarification

Question 2 in `unit-2-functional-design-plan.md` selects **B**: reuse one generated password across components. This conflicts with the already-approved `FR-20` and `US-ID-02` requirements to keep component-native administrator credentials separate. The approved scope also requires credentials for `write-service-account` and test users to remain distinct from admin credentials. The design must preserve separate Kerberos, Dremio, RustFS, and PostgreSQL credentials unless the user explicitly amends the component credential separation requirement.

Please choose how to resolve the conflict:

- **A — Preserve the approved separation requirement.** Generate separate native credentials for Dremio, RustFS, and PostgreSQL, as well as separate Kerberos credentials. This replaces answer 2/B.
- **B — Amend the requirement.** Use one shared password across the non-Kerberos component administrator accounts (Dremio, RustFS, and PostgreSQL), while retaining separate Kerberos credentials. This requires amending `FR-20` and `US-ID-02`; it does not allow using Kerberos credentials as web or S3 credentials, or sharing admin credentials with test users or `write-service-account`.
- **X — Other.** Specify which component credentials may share a password.

`write-service-account` credentials remain distinct from all administrator credentials under every option. No application configuration has changed.

**Answer:** A
