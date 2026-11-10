# Airflow Writer Identity — Requirements Clarifications

Please answer both questions by entering an option letter after [Answer]:. Other answers are recorded; these two decisions block finalizing requirements.

## Question 1
Which Bundle list is actually configured in the Airflow deployment this intent should support? The workload repository documents three entries (lakehouse-dev, lakehouse-uat, lakehouse-prod), while v2's validator accepts two (lakehouse-main and lakehouse-uat). Your previous answer selected keeping the two-entry validator, but we need to know whether that is the live list to preserve.

A) Airflow uses exactly the two entries expected by v2: lakehouse-main tracking main and lakehouse-uat tracking uat. Preserve those entries and keep the validator unchanged.

B) Airflow uses the workload repository's three entries. Preserve all three and update only v2 validation to accept them without changing their names, refs, or settings.

C) The live Airflow list differs; describe its exact Bundle names and tracking refs after [Answer]:.

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 2
You requested a one-hour service access-token lifetime and Spark-side renewal while keeping the writer client secret in Airflow. Keycloak's client-credentials grant does not issue a refresh token by default, so Spark needs a way to request a new client-credentials token. Keycloak also supports a client-level access-token lifespan override, so the one-hour setting can be limited to write-service-account rather than changing human JupyterHub token lifetimes. See the [Keycloak Server Administration Guide](https://www.keycloak.org/docs/latest/server_admin/).

A) Keep the client secret in Airflow and add a private token-renewal endpoint that the Spark job can call. Configure the one-hour access-token lifespan for write-service-account only; keep human token lifetimes unchanged (recommended).

B) Mount the writer client secret as a protected file into each ephemeral Spark container and have Spark obtain fresh client-credentials tokens directly from Keycloak. Configure the one-hour access-token lifespan for write-service-account only.

C) Configure a one-hour access token but do not renew it during a Spark application; jobs exceeding one hour may fail.

X) Other (please describe after [Answer]: tag below)

[Answer]:A
