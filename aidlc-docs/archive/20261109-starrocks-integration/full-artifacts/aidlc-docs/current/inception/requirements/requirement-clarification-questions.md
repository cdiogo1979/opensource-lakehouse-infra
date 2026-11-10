# Requirement Clarification Questions — StarRocks Integration

These follow from the combined answers to Q2 (Keycloak JWT login), Q3 (`srv-starrocks`), Q5 (group-named roles), and Q8 (core start).

## Clarification 1 — Keeping StarRocks users and roles in sync with Keycloak
With JWT login, StarRocks does not read groups from the token (to be confirmed in design), so roles must be granted to StarRocks users by the bootstrap. Which users should exist in StarRocks?

A) Every Keycloak user in a product group. The bootstrap creates a JWT-authenticated StarRocks user per Keycloak user and grants exactly the role of their groups, and a reconcile step, run by the bootstrap and on demand, keeps it in sync, like the Polaris reconciler (Recommended)

B) Only the five bootstrap users, created and granted by the bootstrap

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Clarification 2 — What `srv-starrocks` is in Keycloak
The StarRocks Iceberg OAuth2 client authenticates with client credentials. How should `srv-starrocks` be set up?

A) A confidential Keycloak client `srv-starrocks` with a service account in `role-default-writer`, with its secret in `.runtime/credentials`. Polaris sees it as principal `service-account-srv-starrocks` (Recommended)

B) A Keycloak user `srv-starrocks` with a password, if the chosen StarRocks version supports a password grant or a fixed token for the catalog (may need a token refresher)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Clarification 3 — How people get a token to log in
Users present a Keycloak access token as their StarRocks password. How should they get one?

A) A new Keycloak client `starrocks` (password grant, token audience for StarRocks) and a helper `scripts/starrocks-login.sh <user>` that asks for the Keycloak password and opens a MySQL session with the token. Tokens stay short-lived, and an open session outlives its token (Recommended)

B) A token from an existing client (for example `lakehouse-cli`); users fetch it themselves

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Clarification 4 — StarRocks in the core start
StarRocks FE and BE add several GB of images and memory and minutes of start time to every `lakehouse.sh start`. How should this be handled?

A) In the core start by default, using the separate Compose file, with an opt-out `STARROCKS_ENABLED=false` in `.env` for lighter runs (Recommended)

B) Always in the core start, no opt-out

X) Other (please describe after [Answer]: tag below)

[Answer]: A
