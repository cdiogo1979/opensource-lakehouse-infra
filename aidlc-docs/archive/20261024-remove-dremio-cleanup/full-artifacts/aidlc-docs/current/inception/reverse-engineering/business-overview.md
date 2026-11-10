# Reverse Engineering — Business Overview

This PoC demonstrates a local lakehouse workflow: bootstrap component identities; use Spark as `write-service-account` to write TPCH Iceberg tables into RustFS with Hive Metastore catalog metadata; query those tables through Spark/Jupyter and Dremio; and separately attempt to expose Hive objects as Dremio Spaces/views over JDBC.

The new intent removes Dremio and cleans project contents. The likely resulting workflow is identity/bootstrap → Spark ETL → Hive catalog and RustFS data → Spark/Jupyter query. The user has not yet confirmed whether Jupyter, Spark, TPCH workload, or their local data should remain, so that target is a proposal only.
