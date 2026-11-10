# Isolated Ranger Authorization Test Stack

This stack is opt-in and separate from the default Compose project. Its containers,
networks, volumes, and synthetic identities use the `ranger-test-` prefix. It has
no published host ports. Never attach its services to the production FreeIPA,
MIT KDC, RustFS, Hive Metastore, StarRocks, Airflow, or JupyterHub networks.

## Prepare local test credentials

Run `scripts/prepare-ranger-test-secrets.sh`. It creates generated test credentials
under `.runtime/ranger-test/secrets`, with a private directory and mode-0600 files.
The command does not display secret values. Do not commit that directory.

## Current service sequence

Validate configuration with:

```sh
docker compose -p ranger-test -f docker-compose.ranger-test.yml \
  --profile ranger-authorization-test config --quiet
```

Build only isolated service images before starting anything:

```sh
docker compose -p ranger-test -f docker-compose.ranger-test.yml \
  --profile ranger-authorization-test build
```

The current host build verified Ranger Admin, Ranger DB, FreeIPA, and UserSync
images. Ranger Admin and DB are healthy. FreeIPA test installation currently exits
with status 123 and remains stopped; this prevents the UserSync and authorization
tests from starting. Do not use the current validation FreeIPA service as a
substitute. Diagnose the test-only FreeIPA startup with a review of the test image
and launch configuration before retrying. Preserve its dedicated test volume until
the failure is understood.

After FreeIPA is fixed, start only the test IPA service, wait for its health check,
and run `/usr/local/sbin/bootstrap-ipa-identities` inside `ranger-test-ipa`. Export
only `/etc/ipa/ca.crt` from that container to
`.runtime/ranger-test/secrets/freeipa-test-ca.crt`, preserving mode 0600. Then start
Ranger UserSync. The UserSync LDAP filter is intentionally restricted to the three
synthetic test principals and the `lakehouse-*` role groups.

No Ranger service definitions or policies have been installed yet. Do not treat
Ranger Admin health or UserSync image build as evidence of StarRocks authorization.
