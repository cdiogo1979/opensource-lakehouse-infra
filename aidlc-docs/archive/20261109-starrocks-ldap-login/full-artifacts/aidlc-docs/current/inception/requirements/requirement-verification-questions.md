# Requirement Verification Questions — StarRocks LDAP Login

Context: the probe showed one StarRocks user has exactly one login method, and that passwords cannot be copied out of Keycloak.

## Q1 StarRocks login model
A) Password only: every synced StarRocks user logs in with their LDAP password; token login and `starrocks-token.sh` are retired (Recommended)
B) Both, through two StarRocks user names per person (for example `joe-developer` with a password and `joe-developer@token` with a token)
C) Password for service users (`srv-*`), token for people
X) Other

[Answer]: A — Password only

## Q2 How Keycloak uses LDAP
A) Writable federation: Keycloak creates users and sets passwords in LDAP, so the existing user scripts, writer-user creation, resets, and the account console keep working (Recommended)
B) Read-only federation: users and passwords are managed only with LDAP tools; the Keycloak-side user scripts change to LDAP
X) Other

[Answer]: A — Writable federation

## Q3 Existing Keycloak users
A) Recreate them in LDAP with their documented or file-recorded password (bootstrap users `ChangeM3!`, writer users from their password files), then remove the local copies (Recommended)
B) Recreate them with the default password and require a change at next sign-in
X) Other

[Answer]: A — Recreate with the known password

## Q4 LDAP server
A) Own small OpenLDAP image built from pinned Alpine packages (maintained packages, full LDAP write support) (Recommended)
B) lldap (lightweight and maintained; Keycloak write-back must be verified)
C) bitnami legacy OpenLDAP (as in the probe; no longer maintained)
X) Other

[Answer]: A — Own OpenLDAP image from pinned Alpine packages

## Q5 Security Baseline extension
A) Yes
B) No
X) Other

[Answer]: B — No

## Q6 Property-Based Testing extension
A) Yes, full
B) Partial
C) No
X) Other

[Answer]: B — Partial (PBT-02, 03, 07, 08, 09 enforced)

## Q7 Resiliency Baseline extension
A) Yes
B) No
X) Other

[Answer]: B — No
