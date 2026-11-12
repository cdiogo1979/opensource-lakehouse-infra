# Build and Test Summary — 20261112-built-image-os-upgrades

- Tests: 664 passed, 3 skipped (new: every image built here upgrades its OS packages).
- Builds and scans (`--build`): fixable critical+high OS findings 0 in Airflow (was 63), Jenkins (20), reconciler (19), token broker (4), LDAP (0; its 1 medium gone). Critical: Airflow 23 -> 10, Jenkins 2 -> 1, broker 2 -> 2, reconciler 0, LDAP 0.
- Live: `lakehouse.sh start` and `start-airflow` recreated LDAP, Jenkins, reconciler, token broker and Airflow on the new images, all healthy; `jenkins-oidc.py` passed; `role-matrix.py` passed (Keycloak through LDAP); `default-uat-test_environment` run manual__2026-11-12T19:54:46 succeeded; reconciler cycles succeed.
- Workflow run: checked after the push.
