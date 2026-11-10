# Business Logic Model — airflow-bundles

## Flow A: generate and validate the bundle list
`load_all() → for product (default first, then by name) with repo: [prod bundle, uat bundle] → JSON (compact, deterministic)`. The validator checks the shape and, on the host, equality with the regenerated list.

## Flow B: `start-airflow`
```text
prepare runtime and Airflow secrets (incl. lakehouse-broker password)
stage writers (BR-4.1); generate the bundle list; validate --host-paths
compose up --build (airflow-init runs ensure-broker-viewer.py; services get the list)
verify bundles per product (airflow-dags.sh)
record fingerprint
```

## Flow C: product apply or remove (added step)
```text
if Airflow is running and fingerprint(new) != recorded:
    --dry-run    -> print bundle and writer changes
    --no-restart -> print "scripts/lakehouse.sh start-airflow"
    else         -> scripts/lakehouse.sh start-airflow
```

## Flow D: run registration (broker)
```text
ref = parse(dag_id)                      -> 403 unknown_product
writer = writers[ref.product]            -> 403 unknown_product
dag = airflow.get_dag(dag_id) (Viewer)   -> 403 unknown_dag | 503
dag.bundle_name == ref.product-ref.env   -> 403 bundle_mismatch
token = keycloak.password_grant(writer)  -> check username and group, else 503
registration(product=ref.product, ...)   -> 201 {run_handle, capability, token}
```

## Properties (PBT-01; partial mode enforces PBT-02, 03, 07, 08, 09)
| ID | Property | Category | Rule |
|---|---|---|---|
| P1 | For generated product sets, `validate(bundle_config(p), expected=bundle_config(p))` passes, and the JSON parses back to the same list | Round trip | PBT-02 |
| P2 | Every product with a repo has exactly `<name>-main` (prod branch) and `<name>-uat` (UAT branch); products without a repo have none; names are unique | Invariant | PBT-03 |
| P3 | `product_for_dag_id(f"{name}-{env}-{workload}") == (name, env)` for every valid name, env, and workload; IDs without a valid prefix give `None` | Invariant / round trip | PBT-03 |
| P4 | The broker's selection never returns a writer of a product other than the bundle's: for generated (DAG ID, bundle) pairs, selection succeeds only when the bundle equals the DAG's `<product>-<env>` and that product has a writer | Invariant | PBT-03 |
| P5 (advisory) | Generating twice from the same files gives an identical list and fingerprint | Idempotency | PBT-04 |

- **Generators** (PBT-07): `tests/products/product_strategies.py` builds valid product names, repo URLs, branch names, workload names, and product sets.
- **Shrinking and seeds** (PBT-08): shrinking stays on, and failures print their reproduction blob (`print_blob=True`).
