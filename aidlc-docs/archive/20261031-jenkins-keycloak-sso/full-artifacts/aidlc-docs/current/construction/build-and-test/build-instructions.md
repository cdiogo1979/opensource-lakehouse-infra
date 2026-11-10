# Build Instructions — jenkins-keycloak-sso

## Prerequisites
- Docker with Compose V2, Python 3, and network access to `updates.jenkins.io` (plugin downloads at image build) and GitHub (CI checkout).
- The core stack running, with Keycloak healthy.

## Steps
```bash
python3 scripts/prepare-lakehouse-runtime.py          # creates the Jenkins client secret and break-glass password once
docker compose -f docker-compose.yml build jenkins     # pinned 2.580.1 image; build fails if plugins differ from plugins.txt
python3 infra/keycloak/bootstrap-realm.py             # adds the jenkins client and groups mapper
python3 scripts/migrate-jenkins-home.py               # one-time verified copy of iceberg-poc-jenkins-home (legacy container must be stopped)
docker compose -f docker-compose.yml up -d jenkins
```
`scripts/lakehouse.sh start` performs all of these steps as part of core start.

## Code analysis
No formatter or linter is configured in this repository. Run `python3 -m py_compile` on the changed Python files and `bash -n scripts/lakehouse.sh`.

## Verify the build
- `docker inspect` reports `lakehouse-local-jenkins-1` as healthy.
- `python3 scripts/verify-jenkins-oidc.py` reports 9 PASS lines.
