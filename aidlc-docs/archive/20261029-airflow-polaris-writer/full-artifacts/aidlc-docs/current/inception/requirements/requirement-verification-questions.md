# Airflow Writer Identity Requirements Questions

Please answer each question by entering the option letter after the [Answer]: tag. These questions preserve the existing Git Bundle definitions and focus end-to-end testing on the main/production job, as requested.

## Question 1
Where should the Airflow control plane run for this intent?

A) Re-enable the Airflow services in opensource-lakehouse-infra-v2 Docker Compose and connect them to the existing Keycloak, Polaris, RustFS, and Spark runtime (recommended; makes the flow testable in the selected workspace).

B) Keep Airflow external and change only the configuration/integration needed for it to launch Spark against this platform.

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 2
The workload repository currently defines three Bundles (dev, UAT, and production), while v2's retained validator expects only main and UAT. How should v2 handle this without changing the Bundle setup?

A) Preserve all three Bundle definitions and refs exactly as they are; update only v2 validation/verification to recognize the existing contract. Run end-to-end testing only for the main/production Bundle (recommended).

B) Keep v2's two-Bundle validator contract, even though it does not match the workload repository's current three-Bundle setup.

X) Other (please describe after [Answer]: tag below)

[Answer]:B

## Question 3
How should Spark authenticate to Polaris as role-default-writer?

A) Airflow obtains a short-lived access token from Keycloak using the existing write-service-account client credentials, keeps the client secret in Airflow, and passes only the per-run token to the ephemeral Spark container. Do not log the token; Polaris continues to vend scoped RustFS credentials (recommended).

B) Mount the writer client secret into the Spark container and have Spark obtain its own token from Keycloak.

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 4
What source-change scope is allowed if the DAG factory alone cannot make the Spark workload use the Polaris token?

A) Allow the smallest necessary Spark startup/configuration changes in the workload repository, in addition to dags/dag_factory.py, while preserving Bundle definitions, refs, directories, and selection behavior (recommended for a working end-to-end flow).

B) Restrict source changes to dags/dag_factory.py only; if Spark cannot consume the token without other changes, record that as an implementation limitation.

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 5
The current Keycloak human access-token lifetime is five minutes. What should happen if a Spark workload can run longer than that?

A) Mint a fresh writer token before each Spark application submission and require each individual application to finish within the current token lifetime; do not extend token lifetime (recommended for the initial flow).

B) Support long-running Spark applications by implementing token refresh or changing the service-token lifetime; define and verify the required maximum duration.

X) Other (please describe after [Answer]: tag below)

[Answer]: X, the token ttl should be adjusted to 1 hour, ans spark should refresh it nevertheless. The setup should be similar in Jupiter

## Question 6
How should the main/production end-to-end test handle data?

A) Trigger the existing main-init_environment job only against a dedicated, newly named test table/prefix, verify the Polaris writer identity and RustFS read/write, and clean up only that test data after approval (recommended to avoid overwriting existing production data).

B) Run the existing main-init_environment job against its configured sample table as-is, including its normal overwrite behavior.

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 7
Which verification outcome should close this intent?

A) Require the main/production Bundle job to pass end-to-end using role-default-writer; verify UAT through source/config contract checks only, and record UAT runtime execution as unverified (recommended, consistent with the requested main-only test focus).

B) Require end-to-end execution of both main/production and UAT jobs before closure, despite the main-only testing constraint.

X) Other (please describe after [Answer]: tag below)

[Answer]:X only test the main branch

## Question 8: Security Extensions
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production data access).

B) No — skip SECURITY rules while retaining the explicitly required authentication and least-privilege requirements.

X) Other (please describe after [Answer]: tag below)

[Answer]:B

## Question 9: Property-Based Testing Extension
Should property-based testing rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for token/configuration and authorization logic).

B) Partial — enforce PBT rules only for pure functions and serialization round-trips.

C) No — skip PBT rules.

X) Other (please describe after [Answer]: tag below)

[Answer]:B

## Question 10: Resiliency Extensions
Should the resiliency baseline be applied to this project?

A) Yes — apply directional resilience design guidance for Airflow, token acquisition, and Spark task failure handling (recommended).

B) No — skip the resiliency baseline.

X) Other (please describe after [Answer]: tag below)

[Answer]:B
