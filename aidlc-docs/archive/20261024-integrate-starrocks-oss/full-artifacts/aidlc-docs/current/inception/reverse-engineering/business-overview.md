# Business Overview

## Business Context

This local lakehouse PoC demonstrates a shared Iceberg data lake: Spark produces sample tables; Hive Metastore stores catalog metadata; RustFS stores table objects; notebooks and the planned analytical engine query the shared data. The adjacent Airflow/Jenkins project can orchestrate Spark jobs.

## Business Transactions

- **Ingest sample data**: Generate TPCH input and use Spark as `write-service-account` to create/populate Iceberg tables through Hive Metastore into RustFS.
- **Explore data**: Use Jupyter Spark sessions to query Iceberg tables under configured user credentials.
- **Serve SQL analytics (proposed)**: Add StarRocks OSS to query Iceberg tables through HMS and RustFS. This is the new intent; it is not yet approved as a detailed requirement or implemented.
- **Orchestrate ingestion (adjacent project)**: Airflow triggers containerized Spark jobs; the existing sample configuration still refers to Nessie and placeholder object-store credentials.

## Business Terms

- **HMS**: Hive Metastore catalog endpoint and metadata database.
- **Iceberg**: Table format/catalog metadata describing data files and snapshots.
- **RustFS**: S3-compatible object store holding table data and Iceberg metadata files.
- **StarRocks**: Proposed MPP analytical SQL engine, separate from the catalog and storage.
