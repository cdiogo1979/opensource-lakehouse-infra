# Unit 1 Technology Stack Decisions

## Decisions

| Area | Decision | Rationale / constraint |
|---|---|---|
| Hub | JupyterHub 6.1.1 for the initial new local installation | User selected the recommended version direction. It includes the current maintenance/security fixes noted in the official changelog as of 2026-10-28. Pin the exact image digest. |
| Hub Python runtime | Python 3.10 or later | JupyterHub 6 requires Python 3.10 or later. Pin a compatible Python minor version in the Hub image. |
| OIDC integration | OAuthenticator OIDC-capable authenticator, extended only where needed for approved-group admission and the planned Hub handler | Reuse supported OIDC code flow and auth-state behavior. Construction must pin a release compatible with JupyterHub 6.1.1 and verify auth-state/group claim handling before use. |
| Spawner | DockerSpawner | Matches the approved local model of one single-user container per user. The Hub alone receives Docker Engine access. Pin an exact version compatible with the selected Hub release. |
| Single-user image | Custom Spark-enabled image based on the matching JupyterHub single-user release | User selected a custom image for Spark. Its JupyterHub package version must match the Hub. Pin the upstream base digest and every added dependency. |
| Configuration | Existing Python Hub config and Compose layout under `infra/jupyter/` and root Compose | Replaces the deferred LDAP/FreeIPA path; no parallel legacy authenticator. Keep credentials outside source and image layers. |
| Hub persistent state | Persistent Hub state storage plus protected crypt key | Required for encrypted auth state across normal restarts. Backup is operator-managed and outside this unit. |
| User home | Separate named volume per stable Hub identity | Preserves notebooks across normal server/service restarts and isolates each user. The volume is not a token or secret store. |

## Version pinning and compatibility checks

- Pin the Hub image by version and immutable digest.
- Pin `jupyterhub`, OAuthenticator, DockerSpawner, and all Python dependencies to exact compatible versions using a lock/constraints file.
- Use a single-user base image with exactly the Hub's JupyterHub version; add Spark and Iceberg dependencies without changing that version.
- Confirm extension compatibility for the Authenticator handler registration and Hub API token/server identity contract before selecting exact OAuthenticator/DockerSpawner releases.
- Record resolved package versions and image digests in the infrastructure design and generated lock/config files. Do not use floating `latest` tags.

## Deferred choices

- Exact OAuthenticator and DockerSpawner patch versions, Python minor version, and image digests are selected during Infrastructure Design after compatibility resolution and image validation.
- Resource limits are selected for the local machine based on the two-server target; this NFR does not prescribe host-wide CPU/memory settings.
- TLS termination is not added to the local loopback profile. Any non-local exposure requires a separate design and approval.

## References

- [JupyterHub changelog](https://jupyterhub.readthedocs.io/en/stable/reference/changelog.html)
- [JupyterHub Python prerequisites](https://jupyterhub.readthedocs.io/en/stable/tutorial/quickstart.html)
- [DockerSpawner single-user image compatibility](https://jupyterhub-dockerspawner.readthedocs.io/en/latest/docker-image.html)
- [OAuthenticator OIDC and group configuration](https://oauthenticator.readthedocs.io/en/latest/reference/api/gen/oauthenticator.generic.html)
