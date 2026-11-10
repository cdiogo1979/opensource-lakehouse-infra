# Business Rules — environment-reset-bootstrap-users

## Identity
- **RB-1 Create-only on start**: `bootstrap-realm.py` (run by `lakehouse.sh start`) creates missing groups (including `role-platform-admin`) and missing bootstrap users with the default password and default group. It never changes an existing user's password or groups.
- **RB-2 Enforce on demand**: `scripts/bootstrap-users.sh` (run by `bootstrap-default-product.sh`, or manually) does the following for each bootstrap user:
  - creates the user if missing
  - resets the password to `default_password` (permanent)
  - sets the user enabled, with no required actions and the profile fields
  - removes the user from every realm group other than its default group, and adds it to the default group

  Rerunning it is safe and yields the same state. It never touches users outside the set.
- **RB-3 Single default source**: the default password and the user/group table live only in `bootstrap-users.json`. `platform-admin-password` is no longer created or read.
- **RB-4 Platform admin is owner-equivalent**: in every service listed in `domain-entities.md`, `role-platform-admin` gets exactly the owner rights. `platform-admin` is only in `role-platform-admin`.

## Writer identity
- **RB-5 Writer is `srv-default-writer`**: all writer tokens come from the password grant on `lakehouse-writer` for `srv-default-writer`.
- **RB-6 Broker checks**: the broker rejects tokens unless `azp == lakehouse-writer`, `preferred_username == srv-default-writer`, the `role-default-writer` Polaris role is present, and the lifetime is at most 3605 s.
- **RB-7 Secret files**: the writer password reaches the broker and the Spark smoke job only as a mounted read-only file. It is never passed in the environment or written to logs.
- **RB-8 Retired client**: `write-service-account` is no longer created or used. After a reset it does not exist.

## Reset
- **RB-9 Exact inventory**: the reset removes only resources matching the selectors in `domain-entities.md`. It prints the discovered inventory before acting.
- **RB-10 Confirmation**: with no flag, the operator must type `reset` exactly; anything else aborts with no changes. `--yes` skips the prompt. `--dry-run` prints the inventory and changes nothing. The two flags are mutually exclusive.
- **RB-11 Order**: containers first, then volumes, then networks, then files. A failure stops the reset with a clear message. Rerunning it continues safely.
- **RB-12 Repository boundary**: the reset deletes files only under `<repo>/.runtime/{credentials,container-mounts,airflow-dag-bundles}`. It refuses any path that resolves outside `<repo>/.runtime`.

## Bundles
- **RB-13 Bundle root**: `validate-bundle-config.py` accepts only `<repo>/.runtime/airflow-dag-bundles`. The sibling repository is never referenced.
- **RB-14 One-time sibling cleanup**: `../opensource-lakehouse/.runtime` is removed once, as an operator step after Airflow uses the new root. It is not part of the reset.
