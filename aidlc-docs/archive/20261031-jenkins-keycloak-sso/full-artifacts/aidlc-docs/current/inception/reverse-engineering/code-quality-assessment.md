# Code Quality Assessment — Jenkins / Keycloak

## Test Coverage
- **Overall**: None for Jenkins in v2. Keycloak client contract tests exist for other clients.

## Code Quality Indicators
- **Linting**: Not configured in this workspace (the sibling repository has `scripts/code_quality.sh`).
- **Documentation**: README marks Jenkins as deferred.

## Technical Debt
- The legacy Jenkins was configured by hand (102 plugins, UI-created jobs). Fresh-home reproducibility was never verified.
- The legacy instance published `8098` on all interfaces and mounted the Docker socket.
- The legacy authorization is "logged-in users can do anything", with one shared local admin.

## Patterns and Anti-patterns
- **Good**: pinned base image; runtime tool validation in the image build.
- **Anti-patterns (legacy)**: manual plugin and job state; non-loopback exposure; broad Docker socket access.
