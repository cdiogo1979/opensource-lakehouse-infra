# Requirements Clarification — Token Refresh in the Single-Container Journey (Resolved)

Your answers select (1) a per-user container that hosts both Jupyter single-user server and Spark driver/client, with no Docker socket, and (2) encrypted Hub auth state plus refreshed tokens for newly spawned Spark execution. In this topology, a JWT copied to the container environment at spawn cannot be replaced when the Hub later refreshes it. Also, Spark sessions launched inside the already-running container are not newly spawned containers.

Which behavior should the requirements specify?

## Question 9: Renewed JWT delivery after user-container startup

A) Add a Hub-side token broker/refresh endpoint. The user's refresh token remains encrypted in Hub auth state; a Spark launcher in the user's container requests a fresh access JWT from the Hub before starting each Spark session. The Hub verifies the user session and returns only that user's JWT. The container does not receive the refresh token. (Recommended for least privilege, but adds a small Hub integration and API.)

B) Keep the simpler spawn-time-only handoff. JupyterHub refreshes the access token before spawning the per-user container and passes that exact JWT. Once it expires, Polaris rejects later catalog requests; the user restarts the Jupyter server to obtain a new JWT. No in-session refresh is promised. (Simplest implementation; work requiring later Polaris calls may need restart.)

C) Change to separate per-job Spark containers so each execution receives a fresh token at container spawn. This changes the Q1 container boundary and requires a trusted job launcher without exposing the Docker socket to user code.

X) Other (describe after `[Answer]`).

[Answer]:A

**Resolution**: Add a Hub-side token broker. The refresh token remains in encrypted Hub auth state; the user's Spark launcher requests a fresh access token for each Spark session. The user container receives only the JWT for its own user. A Spark session does not silently switch identity after start.

## Interpretation of previous answers

- Include both developer and analyst journeys. Developer permissions remain read all environments/write dev only; analyst remains read production only/no writes.
- Do not add the broader Security Baseline as an extra control set. The explicit token, OIDC, least-privilege, isolation, and short-lived storage credential safeguards in the requirements still apply because they are part of the requested flow.
- Build and Test is authorized to use the local stack, create temporary test identities/data, perform browser OIDC login and Spark access tests, then clean up those temporary resources.
