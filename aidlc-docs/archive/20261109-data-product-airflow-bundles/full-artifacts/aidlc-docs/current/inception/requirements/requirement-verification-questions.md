# Requirement Verification Questions — Data Product Airflow Bundles

## Q1 How a DAG run's write credential is chosen
A) DAG-ID prefix plus a check with Airflow (Recommended)
B) DAG-ID prefix only
C) Airflow Connections read by DAG code
X) Other

[Answer]: A

## Q2 What the product file holds for Airflow
A) repo {url, prod_branch, uat_branch} + airflow.writer (Recommended)
B) repo only
X) Other

[Answer]: X — "data_product.name + airflow.writer"; clarified in C1.

## Q3 Default product's bundle names during this intent
A) Keep lakehouse-main/uat for default; new products <p>-main/-uat (Recommended)
B) Rename now (default-main/default-uat)
X) Other

[Answer]: B — rename now

## Q4 What "the bundles execute" means
A) Register and load: recreate Airflow with the new list; no DAG run (Recommended)
B) Also trigger a smoke run
X) Other

[Answer]: A

## Q5 Extensions
A) PBT partial, others off (Recommended)
B) All off
C) PBT partial + Security
X) Other

[Answer]: A
