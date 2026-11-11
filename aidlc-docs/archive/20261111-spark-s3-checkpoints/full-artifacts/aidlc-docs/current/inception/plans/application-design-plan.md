# Application Design Plan — Spark S3 Checkpoints

## Steps
- [x] Probe the unknowns from requirements.md (STS audiences, policy mapping, Iceberg offsets, credential options); evidence in `audit.md` (probes 1 to 6)
- [x] Settle the credential model and the Jupyter checkpoint path with the user (questions below)
- [x] Amend the requirements (CR-1)
- [x] Generate components.md
- [x] Generate component-methods.md
- [x] Generate services.md
- [x] Generate component-dependency.md
- [x] Generate application-design.md (consolidated)
- [x] Validate completeness and consistency against requirements.md and the canonical knowledge

## Questions
Asked interactively (AskUserQuestion and chat); answers recorded verbatim in `audit.md`.

### Q1 — Token path to RustFS STS
A) Keycloak token exchange to a `rustfs`-only token (Recommended at the time)
B) Dedicated STS client per role
C) Static S3 keys

[Answer]: A, for probing; superseded by Q4.

### Q2 — Fix for Iceberg-source streams
A) Routing FileIO
B) Upstream fix only
C) Platform incremental helper

[Answer]: The user asked for a general answer for every future streaming job; probing showed Iceberg's `ResolvingFileIO` with a dedicated checkpoint scheme replaces a custom FileIO ("go ahead and check").

### Q3 — Jupyter checkpoint path
A) Same path as the product config (simple; dev is a sandbox)
B) Per-user subpath in Jupyter
C) Separate Jupyter key and prefix

[Answer]: A — "Same path: simple; acceptable if dev is a sandbox."

### Q4 — Credential model
A) Static checkpoint key per product environment bucket
B) STS with token exchange, broker endpoints and a JVM credential provider

[Answer]: A — "lets proceed with static keys". Several products in one Jupyter server are handled by per-bucket S3A keys.

## Answer analysis
No ambiguity remains: each answer selects one option. Q1 is superseded by Q4 (recorded as CR-1 in requirements.md).
