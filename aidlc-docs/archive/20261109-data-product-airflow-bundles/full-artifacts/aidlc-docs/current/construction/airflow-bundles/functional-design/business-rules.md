# Business Rules — airflow-bundles

## BR-1 Product file
1. **Optional `repo`**: when present, all three fields are required and valid (Domain Entities); otherwise the file is refused, with exit 2.
2. **No credentials**: a repo URL with user, password, query, or fragment is refused.
3. **Writer from the product (CR-1)**: a product's DAGs write as its `writer_user`, and the file has no writer setting.
4. **`default.yaml` and the template**: `default.yaml` gets `repo: {url: https://github.com/cdiogo1979/opensource-lakehouse.git, prod_branch: main, uat_branch: uat}`. The template includes the same block, commented, with an explanation.

## BR-2 Bundle list
1. **Generation**: exactly two bundles per product with a repo, none for others, in the stated order. The same product files always give the same JSON.
2. **Validator**:
   - every entry has the Bundle shape and a name `<product>-(main|uat)`
   - each product has exactly both names, with the same `repo_url`
   - no duplicate names; no credentials in URLs
   - with `--host-paths`, the list must also equal the list generated from the product files
3. **Empty list**: no product with a repo gives an empty list, which Airflow accepts (no bundles). The verifier then expects none.

## BR-3 Broker selection (Q1)
1. **Product from the DAG ID**: a DAG ID not matching `DAG_ID_PATTERN`, or naming a product without a staged writer, is refused (`403 unknown_product`).
2. **Bundle check**: the broker gets the DAG from the Airflow API as `lakehouse-broker`. Its `bundle_name` must equal `<product>-<env>`; otherwise `403 bundle_mismatch`. A DAG Airflow doesn't know gives `403 unknown_dag`. If Airflow can't be reached or returns an error, the answer is `503 service_unavailable`.
3. **Token**:
   - the token comes from a password grant on `lakehouse-writer` as the product writer
   - its `preferred_username` must be the writer, and its Polaris role claim must contain the product's writer group; otherwise `503`, with nothing issued
   - the registration remembers the product, so renewals use the same writer and check it again
4. **Viewer token**: the broker's Airflow token is cached until 60 s before it expires, then fetched again.
5. **Logging**: refusals are logged with reason, DAG ID, and product. No token, password, or capability is ever logged or returned in an error.

## BR-4 Staging and restarts
1. **Staging**: `stage-airflow-writers.py` writes `writers.json` and one password file per product with a repo. It removes files of products that no longer have one. Files are mode 0644 inside the host-private 0700 mount directory, mounted read-only into the broker only.
2. **When Airflow is recreated**: the operator scripts and `start-airflow` compare the fingerprint. Airflow is recreated only when the fingerprint changed, or on an explicit `start-airflow`. With `--no-restart` the command is printed; while Airflow is stopped nothing runs, and the next `start-airflow` applies the change.
3. **Recording**: the fingerprint is recorded only after a successful `start-airflow`.

## BR-5 Broker's Airflow identity
- **User**: `lakehouse-broker`, a local FAB user with role Viewer and the password from `.runtime/credentials/airflow-broker-viewer-password` (created once).
- **Ensuring it**: `airflow-init` creates the user or resets its role and password to match, idempotently, and never prints the password.

## BR-6 Workload patch (delivered, not applied here)
- **`identity_for_bundle`**: `<p>-main` gives (`<p>-main`, `prod`) and `<p>-uat` gives (`<p>-uat`, `uat`). Legacy `lakehouse-main`/`-prod`/`-uat` keep their current mapping; anything else gives (`dev`, `dev`).
- **DAG IDs**: stay `<prefix>-<workload>`, so they become `default-main-test_environment`.
- **Configs**: the environment config is read from `configs/<product>/<env>.yml` when present, otherwise `configs/<env>.yml`.
- **Testing**: the patch must pass the workload repository's own tests on a copy of the local checkout.
