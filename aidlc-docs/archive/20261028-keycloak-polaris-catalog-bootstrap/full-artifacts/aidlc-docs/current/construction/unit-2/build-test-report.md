# Unit 2 Build and Test Report — Keycloak and Polaris

**Status: PARTIALLY VERIFIED.** The live writer authentication issue is resolved. The callback-dependent PKCE browser flow and some reconciliation failure-path diagnostics remain incomplete, so this report does not mark all of U2 Build and Test complete.

## Runtime and checks

- The project Keycloak, Keycloak PostgreSQL, Polaris, Polaris PostgreSQL, and RustFS containers report healthy.
- `docker compose config --quiet` passed.
- Python compilation passed for the runtime preparation helper, Keycloak bootstrap, Polaris authorization/reconciliation helpers, and the new authentication verification helper.
- `scripts/prepare-lakehouse-runtime.py` completed and refreshed the protected Polaris config and read-only mount without exposing credential values.
- Polaris 1.8.0 now uses the documented realm override `polaris.authentication."lakehouse".type=mixed`. The previous `polaris.authentication.realm-lakehouse.type=mixed` did not select the `lakehouse` realm and left the global internal-only mode in effect.
- `infra/keycloak/bootstrap-realm.py` reran successfully; it reports four groups and leaves owner/callback explicitly unconfigured.
- `infra/polaris/bootstrap-product-authorization.py --roles-only` verified all four product principal roles.
- `infra/polaris/reconcile-keycloak-groups.py` reran successfully and reconciled the current writer membership. It was run twice during this verification and remained successful.
- `scripts/verify-polaris-keycloak-auth.py` passed. It obtained a Keycloak writer token without printing it, then Polaris recognized `service-account-write-service-account` with `role-default-writer`. Polaris returned the expected HTTP 403 for privileged `GET_PRINCIPAL` and rejected a deliberately corrupted-signature token with HTTP 401.
- `scripts/verify-polaris-oidc-negative-cases.py` passed. A disposable Keycloak client issued a validly signed token without the Polaris audience; Polaris rejected it with HTTP 401. The same client used a one-second token lifetime; Polaris rejected the genuinely expired token with HTTP 401. The exact temporary client was removed after the test.
- `scripts/verify-keycloak-outage.py` passed. With only this Compose project's Keycloak service stopped, an explicit new writer-token request failed, Polaris continued validating a previously issued writer token (the privileged management request returned its expected HTTP 403), and the membership reconciler failed closed. The script restarted Keycloak in its cleanup path; all five project services then reported healthy, and the normal writer authentication/signature smoke test passed again.
- Both new verifier scripts passed Python bytecode compilation. No credentials, tokens, users, role assignments, catalog state, buckets, or stored data were added or removed by the checks; only the disposable OIDC client was created and deleted.
- The documented project stop/start completed successfully and preserved provider state. After restart, all five containers were healthy; the Polaris schema initializer reported the existing schema and skipped creation; Keycloak realm bootstrap, Polaris roles-only bootstrap, group reconciliation, and the writer/invalid-signature smoke check all passed again.
- The Polaris service was recreated to load the corrected config. No images were rebuilt, volumes were removed, or RustFS data was changed.

## Remaining verification

- Supply an existing human username and the exact application callback URI, then verify owner membership and the PKCE browser flow. No user or callback was invented.
- U4 must create the three catalogs before the catalog-role/grant helper and allowed/denied role matrix can be verified.
- Live negative-token checks include wrong issuer, corrupted signature, wrong audience, and expired token; all were rejected with HTTP 401.
- Read-only Keycloak Admin API checks confirmed the human client is public with standard PKCE flow and direct grants disabled, human access tokens are limited to five minutes, and the writer is a confidential client-credentials service account. Repeated realm bootstrap remained convergent.
- A disposable analyst identity was added to the analyst group, reconciled to the expected Polaris analyst role, removed from the group, and reconciled again; the role was removed. The exact temporary Keycloak user and Polaris principal were cleaned up. No existing memberships were changed.
- The Keycloak outage check passed: token issuance became unavailable, the reconciler returned failure without reporting a current membership snapshot, and Polaris continued to accept the already-issued signed writer token. This documents the intended availability behavior: new logins and reconciliation stop during the outage, while unexpired tokens may continue until their expiry.
- Human owner/callback browser flow remains open because no existing owner username or exact application callback URI was supplied. No callback URL or user was invented.
- Replacing the local Keycloak bootstrap administrator used by reconciliation with a least-privilege reader identity remains a hardening requirement before shared or production deployment.
- U3 RustFS policy and U4 Spark/table end-to-end checks remain with their owning units.

## Conclusion

The fresh local provider bootstrap and writer OIDC authentication now work. The original HTTP 401 was caused by the malformed per-realm Polaris auth property. Writer authentication, expected administrative denial, corrupted-signature/wrong-issuer/wrong-audience/expired-token rejection, Keycloak client settings, analyst membership convergence/revocation, Keycloak outage behavior, and normal stop/start persistence have passed. U2 remains partially verified because the human owner/callback browser flow and some reconciliation failure-path diagnostics remain open. U4 catalog and Spark authorization checks are recorded in the U4 report and are not counted as U2 tests.
