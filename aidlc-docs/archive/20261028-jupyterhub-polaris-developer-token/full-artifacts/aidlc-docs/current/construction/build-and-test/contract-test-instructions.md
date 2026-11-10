# Contract Test Instructions

Unit 1 contract checks are implemented as source tests rather than live provider tests. Run the Keycloak contract suite:

```bash
python3 -m unittest discover -s tests/keycloak -p 'test_*.py' -v
```

It verifies the confidential OIDC client, callback, PKCE, group mapper claims, idempotent reconciliation, and conflict refusal. Polaris token validation and Spark token handoff are outside Unit 1 and have no contract-test result here.
