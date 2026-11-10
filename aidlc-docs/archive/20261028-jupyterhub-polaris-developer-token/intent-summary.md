# Intent Summary: JupyterHub Developer and Analyst Access

## Objective

Authenticate developers and analysts to JupyterHub through Keycloak OIDC, pass each user's access JWT to that user's isolated Spark session, and enforce Polaris authorization with temporary RustFS storage credentials.

## Outcome

- Developer login and Spark access through Keycloak → JupyterHub → isolated Spark → Polaris/RustFS passed. Developer read access worked across production/UAT/dev, dev writes succeeded, and production/UAT writes were denied.
- Analyst login and production-only read access passed; reads from UAT/dev and all writes were denied.
- Concurrent developer/analyst server startup and per-user home persistence across server stop/restart passed. The user confirmed GUI browser testing completed.
- The user confirmed an expired five-minute Keycloak JWT fails closed and requires a new Spark session. Automatic JWT renewal within an existing session is not implemented.
- Polaris storage credential duration was changed from 900 seconds to 3600 seconds with the 600-second cache unchanged. Live checks confirmed approximately 3599 seconds remaining in all three catalogs.
- Read-only object checks succeeded within each smoke-table location. A production-vended credential was denied access to a known-existing dev metadata object (HTTP 403). Three observed credential/resource requests were below five seconds, but do not prove a p95 or hard total deadline.
- The full automated suite passed 82 tests plus 5 Hypothesis subtests (1 opt-in live wrapper skipped); the final JupyterHub regression suite passed 38 tests. The focused runtime configuration suite passed 4 tests.
- Temporary users, principals, probe data, user servers, home volumes, and Hub test state were cleaned up. No production rollout or public exposure occurred.

## Accepted limitations

Other S3 operations and broader credential scopes were not individually tested. Strict five-second end-to-end STS latency/p95 is not proven. Concurrent Spark workload/performance testing was deferred. Resiliency validation has no scheduled date. Full transitive dependency locking and vulnerability scanning remain open. The Hub's local browser profile uses HTTP and is not suitable for network exposure. The group reconciler uses a protected local Keycloak bootstrap administrator credential; replace it with a narrowly scoped reader before shared/production use.

These items are accepted limitations, not successful test results.

## Handoff and archive contents

The user approved `aidlc-docs/current/deploy/deploy-handoff.md` on 2026-10-29. The final AI-DLC current artifacts and relevant source/config/test files are preserved under `full-artifacts/`. Secrets, `.env`, and `.runtime/` are excluded.
