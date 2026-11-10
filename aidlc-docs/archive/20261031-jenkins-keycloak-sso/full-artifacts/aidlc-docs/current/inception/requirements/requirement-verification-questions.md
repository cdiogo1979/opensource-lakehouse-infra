# Requirements Verification Questions — Jenkins Onboarding and Keycloak SSO

Intent: onboard Jenkins into the v2 lakehouse Compose stack and integrate Keycloak SSO.
Context: `aidlc-docs/current/inception/reverse-engineering/`.

## Question 1 — Onboarding approach
How should Jenkins be onboarded into v2?

A) A fresh v2 Jenkins defined entirely as code (pinned plugins, configuration as code, jobs as code) with a new home volume; the legacy instance is untouched (Recommended)

B) Migrate the legacy `iceberg-poc-jenkins-home` volume into the v2 stack and add SSO to it

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 2 — Jobs to provision
Which jobs should the v2 Jenkins have?

A) Only the workload CI: a multibranch pipeline for `github.com/cdiogo1979/opensource-lakehouse` running its `Jenkinsfile`, as in the legacy instance (Recommended)

B) The workload CI plus a job for this infrastructure repository's root `Jenkinsfile` (this workspace has no Git remote today)

C) No jobs; SSO-enabled Jenkins only

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3 — Build execution
Where should pipeline steps run?

A) Executors on the built-in node inside the Jenkins container, with no Docker socket mounted; the image already provides Python 3.10, bash, and git (Recommended)

B) Mount the Docker socket so pipelines can use Docker agents

C) A separate inbound agent container

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4 — Keycloak group to Jenkins permission mapping
How should product groups map to Jenkins permissions?

A) Owner: Administer. Developer: read, build, cancel, and view jobs and logs. Analyst: read-only. Writer (service role): no Jenkins access (Recommended)

B) Owner and developer: Administer. Analyst: read-only. Writer: no access

C) Owner: Administer. Developer, analyst, and writer: read-only

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5 — Break-glass access
How should Jenkins be recoverable if Keycloak is unavailable or misconfigured?

A) Built-in OIDC "escape hatch" local admin, with credentials in a protected runtime secret file, documented like the Airflow and RustFS break-glass paths (Recommended)

B) No local login; recover only by editing configuration as code and restarting

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6 — Host port
Which loopback port should Jenkins use?

A) `127.0.0.1:8090` (`JENKINS_HOST_PORT`), avoiding the legacy `8098` (Recommended)

B) `127.0.0.1:8098`, the legacy port (the legacy container must then stay stopped)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7 — Plugin management
How should plugins be installed?

A) An exact-version `plugins.txt` installed at image build; no runtime plugin installs or updates (Recommended)

B) The latest compatible versions resolved at image build

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 8 — GitHub access and triggering
How should Jenkins reach GitHub and discover changes?

A) Anonymous HTTPS with a periodic multibranch scan (polling); no webhooks, since Jenkins is loopback-only (Recommended)

B) A GitHub token credential from a protected file (higher API limits), with a periodic scan

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 9 — Legacy Jenkins container and volumes
What should happen to the legacy `hive-dremio-rustfs-jenkins-1` container and the `iceberg-poc-jenkins-home` / `jenkins_home` volumes?

A) Leave them untouched; out of scope (Recommended)

B) Remove the legacy container and `iceberg-poc-jenkins-home` after the v2 Jenkins is verified

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 10 — When Jenkins runs
How should Jenkins be started?

A) An optional operator command, like Airflow: `scripts/lakehouse.sh start-jenkins`, `jenkins-status`, `stop-jenkins` (Recommended)

B) Always in the core `scripts/lakehouse.sh start`

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 11 — Verification scope
What verification is required before Build and Test can pass?

A) Automated contract tests, local runtime checks, a headless OIDC login and permission check with temporary users, a successful workload CI build, and an interactive login confirmed by you (Recommended)

B) Automated contract tests, local runtime checks, and an interactive login confirmed by you

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 12 — Security Baseline extension
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 13 — Property-Based Testing extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)

B) Partial — enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity)

C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)

X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 14 — Resiliency Baseline extension
Should the resiliency baseline be applied to this project?

Enabling it applies directional, design-time best practices derived from the AWS Well-Architected Framework (Reliability Pillar). It does not make the workload production-ready or certify any availability, RTO, or RPO target.

A) Yes — apply the resiliency baseline as directional best practices and design-time guidance (recommended for business-critical workloads, as an informed starting point that you can validate and harden before go-live)

B) No — skip the resiliency baseline (suitable for PoCs, prototypes, and experimental projects where rapid iteration matters more than reliability)

X) Other (please describe after [Answer]: tag below)

[Answer]: B
