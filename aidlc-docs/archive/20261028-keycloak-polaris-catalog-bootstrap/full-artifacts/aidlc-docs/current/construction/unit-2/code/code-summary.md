# Unit 2 Code Generation Summary — Keycloak and Polaris Authorization

## Generated source

- `infra/keycloak/realm-contract.json` records the secret-free realm/client/claim contract.
- `infra/keycloak/bootstrap-realm.py` explicitly creates the realm, four groups, Polaris client roles, public PKCE client, confidential writer client, mappers, owner membership, and writer service-account membership. It reads credentials from protected files, verifies an existing writer secret against its protected source, and never logs tokens or response bodies.
- `infra/keycloak/keycloak-entrypoint.sh` reads the first-admin password from its mounted file and starts the pinned Keycloak image without placing the password in command arguments.
- `infra/polaris/oidc.properties` contains the Polaris 1.8.0 mixed/internal and Keycloak OIDC claim mapping. Polaris validates the unchanged `keycloak.localhost` issuer and fetches JWKS through Docker service DNS with discovery disabled.
- `infra/polaris/bootstrap-product-authorization.py` preflights all three catalogs, then creates product principal roles, catalog roles, and approved catalog grants. It does not create catalogs or storage resources.
- `infra/polaris/reconcile-keycloak-groups.py` reads current group membership, creates matching Polaris principals by stable username, and converges only managed product-role assignments while preserving unrelated roles. Polaris does not expose metastore principal IDs through the Management API, so no guessed ID claim or Keycloak user attribute is used.
- `infra/polaris/bootstrap-product-authorization.py --roles-only` creates and verifies the four product principal roles before catalogs exist. The normal mode still requires all three catalogs before applying catalog roles and grants.
- `scripts/bootstrap-polaris-realm.sh` invokes the version-matched Polaris Admin Tool with file-mounted configuration/credentials.
- `scripts/prepare-lakehouse-runtime.py` generated protected Keycloak admin, writer-client, Polaris bootstrap, and provider configuration files and staged their container mounts. It removes obsolete Polaris principal-ID and malformed realm-auth properties while preserving database settings.
- `scripts/verify-polaris-keycloak-auth.py` obtains a fresh writer token and confirms Polaris recognizes the configured principal and writer role, while denying the intentionally privileged management read. It never displays tokens or response bodies.
- `docker-compose.yml` retains the file-backed Keycloak bootstrap entrypoint; the `keycloak.localhost` private-network alias was removed because `.localhost` resolves to loopback inside Polaris.
- `README.md` documents the explicit U2 operator order and U3/U4 boundary.

## Authorization mapping

| Product role | `lakehouse` | `lakehouse-dev` | `lakehouse-uat` |
|---|---|---|---|
| Developer | Read | Read/write | Read |
| Analyst | Read | None | None |
| Owner | Content management + access management | Content management + access management | Content management + access management |
| Writer | Read/write | Read/write | Read/write |

## Scope and handoff

- A fresh local bootstrap reset only the Keycloak and Polaris database volumes. RustFS data and its volume were preserved. Runtime credentials/configuration were generated, Keycloak and Polaris were bootstrapped, and all core containers are healthy.
- Polaris's four product principal roles exist. Keycloak realm/groups/clients/mappers and the writer group membership were verified. Reconciliation created the writer Polaris principal by username and assigned `role-default-writer`.
- Polaris 1.8.0 requires per-realm auth mode using `polaris.authentication."lakehouse".type`. The previous `polaris.authentication.realm-lakehouse.type` property did not configure the realm and left it in global internal-only mode. The tracked template and runtime generator now use/remove the correct properties.
- Live verification now confirms a fresh Keycloak writer token reaches Polaris and resolves as `service-account-write-service-account` with `role-default-writer`. Polaris returns HTTP 403 for the intentionally privileged `GET_PRINCIPAL` operation; this is the expected authorization denial for the writer and confirms authentication is working. The same smoke check confirms a corrupted-signature token is rejected with HTTP 401. `scripts/verify-polaris-keycloak-auth.py` performs these checks without printing credentials, tokens, or response bodies.
- The realm bootstrap requires the operator to supply an exact callback URL and an existing owner username. It does not create human users.
- The U2 reconciliation currently authenticates to Keycloak with the protected local bootstrap administrator to read group membership. Replacing this with a narrowly scoped read-only Keycloak reader identity remains a hardening item before shared/production use.
- Build and Test discovered `.localhost` loopback resolution inside Polaris. The approved design retains the canonical issuer and uses Docker service DNS for JWKS. Discovery is disabled, the correct issuer is validated, and the configured JWKS URL is routed privately through `keycloak:8080`.
- Keycloak client token lifespan, Polaris 1.8.0 claim mapping, management request/response shapes, catalog privilege completeness, grant convergence, least privilege, and safe reruns require Build and Test verification against the pinned services.
- The Polaris setup helper is intentionally separate from U4 catalog creation; it refuses to proceed until all three catalog names exist.
