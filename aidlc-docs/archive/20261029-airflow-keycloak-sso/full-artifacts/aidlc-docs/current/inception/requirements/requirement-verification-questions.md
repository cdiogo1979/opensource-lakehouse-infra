# Requirements Clarification — Airflow / Keycloak SSO

The intent is to enable human single sign-on from Keycloak to the Airflow web application. Current Airflow login is local FAB authentication; Keycloak currently has a JupyterHub-specific OIDC client. Please answer all questions. For mappings/URLs, include the concrete values after the selected option.

## Question 1 — SSO scope
Which authentication surface should this intent cover?

A) Human browser login to the Airflow web UI only; preserve existing Airflow API authentication behavior.

B) Human browser login and interactive authentication to the Airflow REST API.

C) Browser login plus a broader API/service authentication redesign.

X) Other (please describe after the [Answer]: tag below)

[Answer]:A

## Question 2 — Keycloak realm
Which Keycloak realm should authenticate Airflow users?

A) Use the existing `lakehouse` realm and add a distinct Airflow OIDC client (recommended; do not reuse the JupyterHub client).

B) Create/use a separate realm for Airflow identities.

X) Other (please describe after the [Answer]: tag below)

[Answer]:A

## Question 3 — Allowed users and Airflow role mapping
How should Keycloak identities become Airflow users and permissions? Airflow roles (`Admin`, `User`, `Viewer`, etc.) are not the same as Polaris data roles.

A) Allow only explicitly named Keycloak groups and map each group to a specified Airflow role; list the exact group-to-role mapping after the answer.

B) Allow all successfully authenticated users but assign a restricted default Airflow role; specify the role.

C) Permit only pre-provisioned Airflow users and use their existing Airflow roles; specify how identity matching should work.

X) Other (please describe after the [Answer]: tag below)

[Answer]:A

## Question 4 — Local Airflow account fallback
What should happen to the current file-backed local Airflow admin login after SSO is enabled?

A) Retain a protected local admin account as a documented break-glass fallback.

B) Disable local password login after SSO is configured; retain only the account bootstrap mechanism if technically required.

C) Keep both local and Keycloak login available for all existing accounts.

X) Other (please describe after the [Answer]: tag below)

[Answer]:A

## Question 5 — Account provisioning
How should a first-time Keycloak user become an Airflow user?

A) Automatically create the Airflow account at first successful SSO login and derive roles from the approved group mapping.

B) Require an operator to pre-provision the Airflow account and role before first login.

X) Other (please describe after the [Answer]: tag below)

[Answer]:A

## Question 6 — Logout and session behavior
What logout behavior is required?

A) End the Airflow application session only; a later login may reuse the Keycloak browser session.

B) End both the Airflow session and the Keycloak browser session (OIDC provider logout).

C) Specify maximum Airflow session duration/idle timeout and logout behavior after selecting this option.

X) Other (please describe after the [Answer]: tag below)

[Answer]:A

## Question 7 — Deployment URL and callback
Which Airflow URL should Keycloak register as the OIDC callback origin?

A) Keep the local loopback-only setup; use a stable local hostname/port and provide the exact URL.

B) Configure an HTTPS hostname for a named deployment environment; provide the hostname, proxy/TLS termination boundary, and environment.

X) Other (please describe after the [Answer]: tag below)

[Answer]:A

## Question 8 — Authentication assurance
What should this intent require for login assurance?

A) Respect the existing Keycloak realm authentication flow; do not change MFA/password policies.

B) Require MFA for Airflow through a dedicated Keycloak authentication flow.

C) Require a different assurance mechanism (for example a separate realm-specific or conditional-access policy); specify it.

X) Other (please describe after the [Answer]: tag below)

[Answer]:A

## Question 9 — Integration verification boundary
What runtime verification is authorized after implementation?

A) Automated tests and local Compose/Keycloak integration only; no interactive login or persistent realm changes.

B) Automated tests plus a local end-to-end browser/login verification using a designated test user; specify cleanup expectations.

C) Code and test artifacts only; defer all service startup and runtime testing.

X) Other (please describe after the [Answer]: tag below)

[Answer]:A

## Question 10 — Security Baseline extension
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications).

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects).

X) Other (please describe after the [Answer]: tag below)

[Answer]:B

## Question 11 — Property-Based Testing extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components).

B) Partial — enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity).

C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic).

X) Other (please describe after the [Answer]: tag below)

[Answer]:C

## Question 12 — Resiliency Baseline extension
Should the resiliency baseline be applied as directional design-time guidance?

A) Yes — apply the resiliency baseline as directional best practices and design-time guidance (recommended for business-critical workloads, as an informed starting point that can be validated and hardened before go-live).

B) No — skip the resiliency baseline (suitable for PoCs, prototypes, and experimental projects where rapid iteration matters more than reliability).

X) Other (please describe after the [Answer]: tag below)

[Answer]:B
