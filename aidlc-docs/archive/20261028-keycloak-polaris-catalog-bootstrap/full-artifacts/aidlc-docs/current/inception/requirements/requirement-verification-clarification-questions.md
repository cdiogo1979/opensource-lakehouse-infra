# Requirements Follow-up Clarifications

Your answers to the original requirements questions have been recorded. These follow-ups resolve scope and provisioning details before the requirements document is finalized.

## Question 20 — Kerberos removal and deferred client integrations
You selected removal of MIT Kerberos and also chose to defer client integrations beyond the initial platform-admin journey. The initial journey still includes a short-lived Spark job to create and verify the three test tables.

A) Remove the MIT KDC/keytabs and Kerberos configuration in this intent; use OAuth for the bootstrap Spark job, while leaving Airflow, JupyterHub, and StarRocks out of the initial Compose journey and deferring their future integrations (Recommended interpretation)

B) Include OAuth migration and verification for Spark, JupyterHub, Airflow, and StarRocks now, before removing Kerberos

C) Keep the MIT KDC available but do not start it in the initial journey; migrate clients in a later intent

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 21 — Initial platform-admin identity
The CLI creates the product resources, but an authorized operator needs initial administrative access to Keycloak and the bootstrap process. How should that first platform-admin identity be established?

A) Create/provision a dedicated initial platform-admin account through a protected, one-time bootstrap secret; do not reuse the built-in realm administrator for routine product work (Recommended)

B) Use the Keycloak built-in realm administrator directly for the first product creation and ongoing administration

C) Create the account manually in the Keycloak UI before running the product bootstrap CLI

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 22 — Should the creating platform admin receive the product-owner role?
The product owner role is distinct from Keycloak realm administration and RustFS root. Should the operator who creates `default` also be granted the product-level owner role?

A) Yes, assign the creating platform admin to `role-default-owner` for the new product (Recommended)

B) No, create the owner group but leave membership empty until an owner is assigned separately

C) Let the platform admin choose owner members during the CLI invocation

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 23 — Iceberg object location within each bucket
Each environment has its own bucket. What base path should the product bootstrap configure for Iceberg data?

A) Use a product namespace prefix within each bucket, such as `s3://bucket-default/default_lh/`, `s3://bucket-default-dev/default_lhdev/`, and `s3://bucket-default-uat/default_lhuat/` (Recommended)

B) Use the bucket root as the catalog base location, with Polaris managing object layout beneath it

C) Require the platform admin to provide an explicit base path for each environment

X) Other (please describe after [Answer]: tag below)

[Answer]:A
