# Unit 4 Infrastructure Design — Clarification Gate

## Platform administrator identity conflict

The requirements preserve an existing JupyterHub platform identity named `admin` and require the authorized administrator to authenticate against FreeIPA. FreeIPA reserves `admin` for its directory-administrator identity. A second FreeIPA human account cannot use the same username. Exposing the FreeIPA superuser credential to JupyterHub would expand its attack surface and violates the least-privilege boundary in the approved infrastructure plan.

Before Unit 4 implementation, choose a distinct, nonprivileged FreeIPA human login for the platform administrator. Record how that account receives JupyterHub administrator permission and how its identity maps to an active MIT principal, RustFS credentials, and the preserved `iceberg-poc-jupyter-admin-work` volume. Do not silently map a different user's FreeIPA password to the existing `admin` Kerberos/S3 identity. No account or mapping is changed by this document.

## Compatibility checks carried forward

1. Select and pin a concrete LDAPAuthenticator release compatible with Hub 5.3.0 and its Python runtime; official documentation supports group DNs and TLS configuration but notes compatibility has been tested against OpenLDAP, so FreeIPA acceptance must be demonstrated.
2. Confirm the FreeIPA certificate SAN contains `ipa.lakehouse.local`, and that the exported CA validates LDAPS from the Hub on the proposed isolated network.
3. Verify the dedicated `jupyterhub-ldap-reader` can read only required role group/user status attributes and cannot modify any FreeIPA object.
4. Verify the exact FreeIPA group `member`/user lock attributes and the login + pre-spawn lookup behavior with real directory entries.
5. Verify JupyterHub crypt-key secrecy, auth-state encryption, profile-gated startup, credential mount isolation, tmpfs TGT deletion, and workspace preservation.

## Primary references

- JupyterHub [LDAPAuthenticator documentation](https://github.com/jupyterhub/ldapauthenticator) and [changelog](https://github.com/jupyterhub/ldapauthenticator/blob/main/CHANGELOG.md).
- JupyterHub [authenticator and auth-state documentation](https://jupyterhub.readthedocs.io/en/stable/reference/authenticators.html).
- FreeIPA [LDAP documentation](https://www.freeipa.org/page/HowTo/LDAP.html).
