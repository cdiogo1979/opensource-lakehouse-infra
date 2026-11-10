# Performance Test Instructions — Unit 4

## Profile and target

Use the approved local profile of one Hub and at most two distinct active user servers. Each user server defaults to 1 CPU and 2 GiB memory. The STS credential acquisition target is five seconds end-to-end; the configured per-stage connection and read timeouts do not prove that total deadline.

## Measurement procedure

1. Record machine architecture, CPU/memory availability, Docker resource limits, image digests, and the two test roles. Do not record identity tokens or credentials.
2. Warm the services, then measure repeated independent credential-vending operations from request start until Polaris returns a successful result to the Iceberg client. Separate Spark startup and table query time from the STS interval.
3. Record sample count, p50/p95/max, timeout/failure count, and whether every sample was measured at the same operation boundary. Keep only timestamps, status, and durations.
4. Repeat with two users active concurrently and confirm one user's authorization outcome does not change the other user's role or result.
5. Compare the measured p95 to five seconds. If the pinned client/service does not expose a safe measurement boundary, report the target as unverified rather than substituting end-to-end query duration.

No dedicated STS latency instrumentation or reproducible performance harness is currently implemented. A local two-user result does not establish production capacity or an SLA. No performance run has yet been recorded for Unit 4.

## Deferred resiliency validation

The following remain a separate validation activity: Keycloak/JWKS outage, Polaris outage, RustFS STS timeout or pool saturation, expired vended credential, refresh denial, and ambiguous mutation outcome. **Owner:** platform operator. **Scheduled date:** unset. Record a date and scope before claiming this activity complete.
