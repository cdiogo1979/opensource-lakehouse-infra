# Unit 4 Code Generation — Clarifications and Recommendations

## Decisions recorded

The user approved all three recommended choices on 2026-10-27:

1. FreeIPA `administrator` maps deliberately to the existing JupyterHub platform admin identity, MIT `admin@LAKEHOUSE.LOCAL`, existing RustFS admin pair, and preserved `iceberg-poc-jupyter-admin-work` workspace.
2. `user_a` and `user_b` are removed from interactive JupyterHub access; their credentials and volumes remain untouched.
3. Use LDAPAuthenticator 2.0.2 after package/image compatibility checks; exact FreeIPA behavior remains for Build and Test.

## Current gate status

- Unit 3 Build and Test is complete with documented limits; its verification gate is satisfied for starting Unit 4 Code Generation.
- The distinct FreeIPA human administrator login has been selected as `administrator`.
- The administrator mapping decision is resolved as above. The administrator account itself must be provisioned in FreeIPA before login is possible.
- The running Hub image reports Python 3.10.12 and JupyterHub 5.3.0, meeting LDAPAuthenticator 2.0.2's declared Python >=3.9 and JupyterHub >=4.1.6 minimums. Dependencies are pinned in the Hub requirements. Actual FreeIPA TLS/schema/group/lock behavior remains a Unit 4 Build and Test gate.

## Decisions needed

### 1. Map the FreeIPA administrator login

**Question (resolved A):** Should FreeIPA user `administrator` be explicitly authorized as the JupyterHub platform administrator and map to the existing `admin` MIT principal/keytab, RustFS admin credential pair, and `iceberg-poc-jupyter-admin-work` volume?

- **A — Explicitly map to the existing admin identity (Recommended).** Add `administrator` to the Hub administrator allowlist. Use the existing admin MIT and RustFS credentials and preserve the existing admin volume. Record this as a deliberate cross-system identity mapping; never use FreeIPA's built-in directory-superuser credential. Do not copy or rename credentials or move workspace data.
- **B — Create a separate platform-admin data identity.** Provision a new MIT principal/keytab, RustFS identity/credential pair, and a new persistent workspace for `administrator`. Keep the existing `admin` volume and identity unchanged. This has clearer identity separation but requires additional provisioning and validation.

**Decision:** A was explicitly approved. The mapping is represented in the provisioning-owned identity registry. This does not create or modify any FreeIPA user, keytab, RustFS credential, or workspace.

### 2. Treatment of legacy JupyterHub logins

**Question (resolved A):** When FreeIPA authentication is enabled, should `user_a` and `user_b` stop being able to sign in while their keytabs, RustFS credentials, and named workspaces remain intact?

- **A — Remove from the interactive allowlist; preserve all files and volumes (Recommended).** New access comes only from the approved FreeIPA role mapping. Do not delete, migrate, rename, or reassign the legacy assets.
- **B — Keep the legacy logins available during a time-limited parallel period.** Specify the end date and require a separate rollback path. This temporarily retains the local/dummy authentication surface and needs a carefully controlled transition design.

**Decision:** A was approved. The FreeIPA-backed JupyterHub allow path omits both legacy logins; their existing files and named volumes remain unchanged.

### 3. Authenticator implementation choice

**Question (resolved A):** Proceed with the reviewed `LDAPAuthenticator==2.0.2` candidate, subject to compatibility checks, or use a project-maintained custom authenticator?

- **A — Use the reviewed LDAPAuthenticator candidate (Recommended).** First identify the Python version in the exact Hub base image, pin the full resolved dependency set, and verify the candidate can express the required group checks. Do not add it to the image until these checks pass. Keep fresh spawn-time authorization in the Hub-side hook as designed.
- **B — Implement a custom `ldap3` authenticator.** This offers direct control over FreeIPA attributes but adds project-owned authentication code and ongoing security/compatibility maintenance.

**Decision:** A was approved. The live Hub image reports Python 3.10.12 and JupyterHub 5.3.0; both satisfy the candidate's published minimums. The candidate and LDAP dependency pins are in `infra/jupyter/hub/requirements.txt`. The package documents OpenLDAP testing, not FreeIPA acceptance, so local FreeIPA Build and Test remains mandatory before declaring authentication ready.

## Compatibility facts to verify (not preference questions)

1. Inspect the built Hub image's exact Python/JupyterHub versions and resolve a reproducible dependency lock for `jupyterhub-ldapauthenticator==2.0.2`. The current requirements pin JupyterHub 5.3.0 and DockerSpawner 14.0.0; the Hub Dockerfile uses the `quay.io/jupyterhub/jupyterhub:5.3.0` tag.
2. From the Hub's intended Compose network, validate `ipa.lakehouse.local` certificate SAN and CA chain for LDAPS. Keep hostname verification enabled; do not publish LDAP/LDAPS ports.
3. Validate the actual FreeIPA user/group attributes and the read-only lookup account's exact search rights. Check both required role groups, no role, conflicting roles, and disabled/locked accounts.
4. Confirm the Hub-only LDAP reader secret and stable Hub auth-state crypt-key are provisioned as protected files before deployment. The Hub code must fail closed when they or FreeIPA are unavailable.
5. Verify real login and spawn-time recheck against isolated FreeIPA before accepting the dependency. No live-user policy change, notebook spawn, or service restart occurs during Code Generation.

## Existing identity assets observed

The credentials directory already contains `admin.keytab`, `developer-user.keytab`, and `analyst-user.keytab`, plus matching admin/developer/analyst RustFS credential files. The existing Hub config still uses `DummyAuthenticator` and hard-coded `user_a`, `user_b`, and `admin` mappings. Keep all legacy files and volumes untouched while replacing the Hub authentication/configuration path according to the approved contracts.

## Recommended answers summary

1. Administrator: **A**, explicitly map FreeIPA `administrator` to the existing platform `admin` identity and preserved workspace.
2. Legacy logins: **A**, remove `user_a`/`user_b` from interactive access while preserving their files and volumes.
3. Authenticator: **A**, use LDAPAuthenticator 2.0.2 only after the pinned Hub/Python/dependency and FreeIPA checks pass.

These decisions authorized Code Generation only. No identity was provisioned; no credential value, service, workspace, or bucket was changed, and no tests or deployment were run.
