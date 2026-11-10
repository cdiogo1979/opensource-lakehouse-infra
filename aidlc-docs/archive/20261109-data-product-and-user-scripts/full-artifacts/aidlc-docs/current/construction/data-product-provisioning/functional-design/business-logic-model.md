# Business Logic Model — data-product-provisioning

## Flow A: `--init <name>`
1. Validate the name (BR-1.1). Refuse if `data-products/<name>.yaml` exists, or if the derived names collide with an existing file (BR-1.2).
2. Render the template: the conventions and matrix of `default.yaml`, with `default` replaced by `<name>`.
3. Write the file and print its path and next step. No other system changes.

## Flow B: apply `<file>`
```text
take lock
validate file + collisions + locked names            (BR-1)    -> exit 2 on failure
for each component in [Keycloak, RustFS buckets, RustFS policies,
                       Polaris catalogs+namespaces, Polaris roles+grants,
                       Polaris reconcile, StarRocks roles+grants+MV dbs,
                       StarRocks reconcile, Jenkins render]:
    plan  = desired(file, all files) - actual(system)
    apply additions                                   (BR-7)
    apply revocations of extras                       (BR-7)
    report created / granted / revoked names
if Jenkins render changed and Jenkins is running and not --no-restart: restart Jenkins
write AppliedState
release lock
```
- **Polaris catalog step**:
  - The allowed locations of each shared catalog become the catalog's own base location plus `s3://<bucket>/<catalog>/` for every product file, in file order. Locations of buckets with no file left are removed only by Flow C.
  - The namespace is created with `location = s3://<bucket>/<catalog>/<namespace>/`. An existing namespace with another location is a conflict: refused and reported.
- **`--dry-run`** runs every `plan` and prints them. No `apply` runs, and no state is written.

## Flow C: remove `<name>`
```text
take lock
refuse default; load file or AppliedState                 (BR-8.1-2)
inventory data; refuse without --purge-data if any        (BR-8.3)
confirm (typed name or --yes), listing data and members   (BR-8.4)
back up file + state to .runtime/backups/<ts>-remove-<name>/
Jenkins render without the product (restart unless --no-restart)
StarRocks: drop MV dbs (purge) -> revoke + drop product roles
Polaris:   drop views, tables (purge) -> drop namespaces -> delete catalog roles
           -> delete principal roles -> remove allowed locations
RustFS:    delete objects (purge) -> delete buckets -> delete group policies
           -> rewrite role-platform-admin policy
Keycloak:  delete writer user + password file -> remove owner client roles from
           role-platform-admin -> delete groups -> delete client roles
reconcile Polaris and StarRocks
delete file and AppliedState
release lock
```
A failure stops the run and reports the step. The backup, file, and state remain, so the same command resumes.

## Flow D: the product bootstrap after a reset
Flow B for `default.yaml`, then for every other file in name order, inside `bootstrap-default-product.sh`. The steps around it stay as today: realm and clients, users, the Polaris realm, smoke checks, and the scheduled reconciler.

## Flow E: scheduled reconcile (every 300 s)
Load every file. If any is invalid, log it and skip the cycle with nothing changed. Otherwise:
1. Desired Polaris principal roles: the union of each user's product groups, plus every owner role for `role-platform-admin` members.
2. StarRocks users: the existing rules, with the managed roles drawn from all files.

## Flow F: create user
Validate (BR-9), check that the username is free, create the user, and set the password from stdin. Then print the next steps: assign groups in the Keycloak admin console, and access follows on the next reconcile.

## One-time migration in this intent (Code Generation, then Build and Test)
1. Record each `default` role's effective access with `role-matrix.py` (the baseline).
2. Add the namespace-location flag and the filter pattern to Polaris, regenerate the runtime properties, and restart Polaris.
3. Apply `default.yaml` (Flow B): the namespace grants are added, then the catalog-wide grants revoked.
4. Run `role-matrix.py` again and compare with the baseline. Any difference fails Build and Test.
5. Recreate JupyterHub and Airflow with the product mount, and move Jenkins to the rendered CasC file.
