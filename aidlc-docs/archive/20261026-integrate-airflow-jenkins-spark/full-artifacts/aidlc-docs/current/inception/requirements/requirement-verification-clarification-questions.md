# Requirements Clarification — Remote Spark Credentials

You selected per-run Airflow-created containers that submit Spark applications to the existing target Spark master/worker service. You also selected the Kerberos/RustFS writer identity and credential initialization in the per-run container. In remote mode, Spark executors run in the target worker service, so their RustFS access and any required Kerberos delegation must also be defined.

## Clarification Question 1
How should the remote Spark executors obtain the writer access they need?

A) Configure the existing Spark worker service to use the writer identity as well: provision/mount the writer keytab read-only, maintain a private renewable ticket cache, and provide RustFS writer credentials through file-backed secrets. Keep the per-run driver container's writer credential setup too.

B) Use the selected writer credentials only in the per-run container and submit jobs in `local[*]` there. This changes the answer to Question 3 from B to A and does not use the target Spark master/workers for these DAG runs.

C) Keep remote execution and pass short-lived delegated Kerberos/S3 credentials from the driver to executors, without mounting the long-lived keytab/RustFS secret into the shared Spark worker. This requires supported Spark/Hadoop token delegation and renewal behavior to be designed and verified.

X) Other (please describe after [Answer]: tag below)

[Answer]:A
