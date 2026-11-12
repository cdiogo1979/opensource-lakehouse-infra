# Requirements — OS package upgrades in the built images (20261112-built-image-os-upgrades)

Approved by the user ("1 and 2 and b2b intents, proceed with your recommended decisions").

## Intent
106 critical and high findings with a released fix are OS packages in images built here whose Dockerfiles take the base's packages as published: Airflow 63, Jenkins 20, Polaris group reconciler 19, Airflow token broker 4 (and 1 medium in LDAP).

## Functional requirements
- **FR-1** Airflow, Jenkins and the token broker (Debian) run `apt-get update && apt-get upgrade --yes --no-install-recommends` and remove the apt lists, as root, before their own installs.
- **FR-2** The Polaris group reconciler and LDAP (Alpine) run `apk upgrade --no-cache` before their pinned `apk add`.
- **FR-3** A guard test: every image built here (`list-images.py --targets`) upgrades its OS packages (the Spark runtime with `apt-get upgrade`; Jupyter single-user and JupyterHub keep their targeted `--only-upgrade`, since their bases have no fixable OS findings).
- **FR-4** The services still work: images build; Airflow, token broker, Jenkins, LDAP and reconciler restart healthy; a UAT DAG run succeeds; Keycloak login through LDAP and Jenkins OIDC verifiers pass.
- **FR-5** Docs: the vulnerability alerts page states that built images upgrade OS packages at build.

## Decisions (recommended, accepted)
- Upgrades follow the base's distribution release (no new release, no new packages); builds are less reproducible between days, accepted already for Spark and Jupyter, and the weekly scan shows what each build holds.
- Users stay as before (Airflow returns to `airflow`, broker to 65532, Jenkins to `jenkins`).
