# Business Logic Model — ldap-password-login

## Flow A: LDAP container start
1. Read the secrets.
2. Render `slapd.conf`, with the hashed admin password.
3. If the MDB is empty, seed it: base, `ou=people`, `ou=services`, and `cn=keycloak` (hashed).
4. Start slapd on LDAPS and ldapi.
5. Health check: an `ldapi` root DSE read.

## Flow B: realm bootstrap (start and the product bootstrap)
`ensure realm → clients → ensure_ldap_federation (create, drift update, or conflict) → test connection → product groups → missing bootstrap users (now written to LDAP) → memberships`.

## Flow C: StarRocks user sync
```text
desired = members of product groups (unchanged)
current = SHOW ALL AUTHENTICATION
for user in desired:
    absent            -> CREATE ... IDENTIFIED WITH authentication_ldap_simple
    plugin JWT        -> ALTER USER ... IDENTIFIED WITH authentication_ldap_simple   (switch)
    plugin LDAP       -> roles converge
    native password   -> conflict, unchanged
grants and revokes, default roles, drops as today
```

## Flow D: migration
```text
preflight (health, provider test, running servers, confirmation)  -> exit 2 on refusal
backup Keycloak DB and inventory
plan = [steps per local user]                                       (pure; --dry-run prints it)
for user in plan:
    write_entry (if absent) -> set_password -> verify_bind          (stop on failure; local copy untouched)
    delete_local -> import (lookup) -> check federationLink
    restore groups, flags, profile
    if old home volume: copy -> verify (count, bytes) -> delete old volume -> delete old Hub user
remove the starrocks client; run the Polaris and StarRocks syncs; report
```

## Properties (PBT-01 identification; partial mode enforces PBT-02, 03, 07, 08, 09)
| ID | Property | Category | Rule |
|---|---|---|---|
| P1 | `parse_ldif(render_entry(person)) == person.attributes` for generated people (usernames in the `uid` pattern; names and emails with Unicode, spaces, colons, and leading or trailing characters) | Round trip | PBT-02 |
| P2 | Every migration plan has, for each user, `verify_bind` before `delete_local`, and `verify_home` before `delete_old_home` | Invariant | PBT-03 |
| P3 | A migration plan covers each local, valid, non-service-account user exactly once, and never a federated or `service-account-*` user | Invariant | PBT-03 |
| P4 | After applying a user-sync plan, every desired user has the LDAP plugin and exactly its group roles; native-password users and `root` are unchanged | Invariant | PBT-03 |
| P5 | The password source always follows the precedence: bootstrap, then writer file, then default | Invariant | PBT-03 |
| P6 (advisory) | Planning the migration again after it completes gives an empty plan | Idempotency | PBT-04 (advisory) |

- **Generators** (PBT-07): shared Hypothesis strategies in `tests/ldap/ldap_strategies.py` for usernames, names, emails, local users, group sets, and StarRocks user states.
- **Framework** (PBT-09): Hypothesis, already pinned in `tests/requirements-pbt.txt`.
- **Shrinking and seeds** (PBT-08): shrinking is never disabled. Failures print the reproduction blob (`print_blob=True`), and the Build and Test instructions document `--hypothesis-seed` for replay.
