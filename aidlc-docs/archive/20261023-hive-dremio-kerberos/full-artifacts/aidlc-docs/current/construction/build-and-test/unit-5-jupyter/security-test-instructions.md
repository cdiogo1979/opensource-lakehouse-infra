# Security Test Instructions — Unit 5 JupyterHub and Per-User Spark

The Security Baseline extension is disabled. These checks validate the approved Unit 5 boundaries; they are not a vulnerability scan or production security certification.

- Confirm `docker compose port jupyterhub 8000` reports `127.0.0.1:8008`.
- Inspect container user, supplementary GID, and mount destinations using the redacted commands in `integration-test-instructions.md`; do not print container environment variables or mount source contents.
- Confirm each container mounts only its matching keytab and two RustFS files as read-only, its named work volume as writable, and the examples directory as read-only.
- Confirm Hub has the Docker socket and spawned user containers do not.
- Confirm `.runtime`, `.runtime/credentials`, and `.runtime/credentials/keytabs` remain owner-only (`0700`); only the three user/admin keytabs and six matching RustFS files are group-readable (`0640`). Writer, root RustFS, Hive service, and unrelated service credentials remain `0600`; the existing Dremio keytab retains its pre-existing `0640` mode.
- Confirm a non-configured Hub label is rejected and DummyAuthenticator limitations are documented.
- Keep authorization, impersonation, and RustFS compatibility outcomes separate; no direct RustFS probe is an acceptance test.

Do not copy secrets or ticket material into reports. A passing image build or service startup does not establish per-user authorization.
