# Business Overview

## Business Context Diagram
```text
 people (developer, analyst, owner, platform admin)      workloads (srv-default-writer)
            |  SQL (MySQL protocol)                               |  Spark via Airflow
            v                                                     v
      +-----------+    Iceberg REST + OAuth    +---------+   vended S3   +--------+
      | StarRocks | -------------------------> | Polaris | ------------> | RustFS |
      | (planned) |                            +---------+               +--------+
      +-----------+                                 ^
            ^                                       | groups -> principal roles
            +---------- identity / roles -----> Keycloak (lakehouse realm)
```
Text alternative: StarRocks is planned as a SQL query engine. It would read the `default` product's Iceberg tables through Polaris, use Polaris-vended RustFS credentials, and take user identity and roles from the Keycloak product groups.

## Business Description
The platform provides one `default` data product in three environments: production `lakehouse`, UAT `lakehouse_uat`, and dev `lakehouse_dev`. Data is written by Spark (through Airflow, or by developers in Jupyter). There is no interactive SQL engine today. StarRocks is meant to add fast SQL over the same Iceberg tables, with access that matches the product roles already used by Polaris, RustFS, Airflow, Jenkins, and JupyterHub.

## Component Level Business Descriptions
### Legacy StarRocks (`infra/starrocks/`)
Built for the retired FreeIPA, Kerberos, and Hive Metastore stack:
- Kerberos-enabled FE and BE images (StarRocks 4.1.6)
- an LDAP group-provider role bootstrap, tested only against a disposable FE with synthetic databases
- an SQL canary and bootstrap runner aimed at the old `iceberg-poc-starrocks-fe` with a Hive-type Iceberg catalog

None of it runs in the v2 stack.

### Product bootstrap (`scripts/bootstrap-default-product.sh`)
Creates the realm, users, buckets, policies, Polaris catalogs, namespaces, grants, and smoke tables. This is the "initialization file" the request refers to. It has no StarRocks step today.
