# Technology Stack — Jenkins / Keycloak

## Programming Languages
- Groovy (declarative Jenkinsfile), Python 3 (bootstrap scripts and tests), Bash.

## Frameworks
- Jenkins LTS — `lts-jdk21` digest-pinned in `infra/jenkins/Dockerfile` (the legacy instance ran 2.580.1).
- Keycloak — 26.8.1.

## Infrastructure
- Docker Compose — local single-host runtime, loopback-only published ports in v2.

## Build Tools
- Docker image build for `infra/jenkins/`.

## Testing Tools
- pytest and Hypothesis (`tests/requirements-pbt.txt`).
