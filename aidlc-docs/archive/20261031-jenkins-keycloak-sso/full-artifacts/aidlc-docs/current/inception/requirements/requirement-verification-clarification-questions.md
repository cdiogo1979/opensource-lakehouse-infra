# Requirements Clarification Questions — Jenkins Onboarding and Keycloak SSO

Your answers to `requirement-verification-questions.md` contain three ambiguities, all caused by migrating the legacy home (Q1: B).

## Ambiguity 1: Migrated volume vs. legacy removal (Q1: B, Q9: B)
You chose to migrate the legacy `iceberg-poc-jenkins-home` and also to remove that volume after verification. If v2 uses the legacy volume in place, removing it would delete the migrated Jenkins.

### Clarification Question 1
How should the legacy home be migrated?

A) Copy it into a new v2 volume `lakehouse-local_jenkins-home`. The legacy volume stays as an untouched backup until the approved removal after verification (Recommended)

B) Adopt `iceberg-poc-jenkins-home` in place as the v2 home. Only the legacy container is removed after verification, and the volume is kept

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Ambiguity 2: Which plugin set is authoritative (Q1: B, Q7: A)
The legacy home holds 102 hand-installed plugins. You also chose an exact-version `plugins.txt` installed at image build, with no runtime installs.

### Clarification Question 2
Which plugin set should the v2 Jenkins run?

A) `plugins.txt` pins exactly the legacy plugin versions plus the OIDC plugin and its required dependencies. The image is authoritative and overrides the plugin copies in the migrated home at start (Recommended)

B) Keep the legacy home's plugins as installed; `plugins.txt` adds only the OIDC plugin and its dependencies

C) `plugins.txt` pins current up-to-date versions of the needed plugins (an upgrade during migration)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Ambiguity 3: How SSO is configured on a migrated home (Q1: B)
A migrated home is not defined as code. The SSO and authorization settings need a reproducible source.

### Clarification Question 3
How should the security settings be applied?

A) Configuration as code (`configuration-as-code`, already installed) manages the security realm, authorization matrix, escape-hatch admin, and root URL. Migrated jobs, build history, and other settings stay as migrated (Recommended)

B) Configuration as code manages security and also redefines the workload job as code; migrated build history is kept

X) Other (please describe after [Answer]: tag below)

[Answer]: A
