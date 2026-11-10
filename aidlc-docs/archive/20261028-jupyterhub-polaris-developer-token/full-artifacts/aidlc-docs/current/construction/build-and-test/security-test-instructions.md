# Security Test Instructions

The Unit 1 source tests verify fail-closed group admission, protected credential creation/staging, secret-free helper output, Hub-only secret mounts, and separation of the Hub Docker socket from user servers. The JupyterHub service is loopback-published, while user servers are isolated from the `core` network.

Run the focused suites using the commands in `unit-test-instructions.md`. Before any non-local exposure, perform a separate TLS, image/dependency vulnerability, secret-rotation, and access-revocation review. This local HTTP profile is not approved for public exposure. No vulnerability scan or penetration test was run for this stage.
