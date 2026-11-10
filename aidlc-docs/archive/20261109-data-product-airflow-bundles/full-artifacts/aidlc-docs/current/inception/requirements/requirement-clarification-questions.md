# Requirement Clarification Questions — Data Product Airflow Bundles

## C1 Meaning of "data_product.name + airflow.writer"
[Answer]: "i meant the data product "name" as defined in the yml file not the repo name". Bundle names and DAG-ID prefixes come from the product's `name` in its YAML file. The repository is configured in a `repo` block (URL, prod branch, UAT branch), as in the original request, together with `airflow.writer`.

## C2 The workload-repository change (with Q3 B)
A) I prepare a patch for opensource-lakehouse; you review and push it (Recommended)
B) You implement it from a documented contract

[Answer]: A
