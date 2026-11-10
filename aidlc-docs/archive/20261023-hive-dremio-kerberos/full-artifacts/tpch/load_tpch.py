#!/usr/bin/env python3
"""Load the existing TPCH input set into the Hive-backed Iceberg catalog."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType,
    StructField,
    LongType,
    IntegerType,
    DecimalType,
    StringType,
    DateType,
)

CATALOG = "iceberg"
DATABASES = ("databaseA", "databaseB")
INPUT_DIR = Path(os.environ.get("TPCH_INPUT_DIR", "/opt/tpch/data"))
RESULTS_DIR = Path(os.environ.get("TPCH_RESULTS_DIR", "/run/results"))
TABLE_SCHEMAS = {
    "customer": StructType([
        StructField("c_custkey", LongType(), False),
        StructField("c_name", StringType(), False),
        StructField("c_address", StringType(), False),
        StructField("c_nationkey", LongType(), False),
        StructField("c_phone", StringType(), False),
        StructField("c_acctbal", DecimalType(15, 3), False),
        StructField("c_mktsegment", StringType(), False),
        StructField("c_comment", StringType(), False),
    ]),
    "lineitem": StructType([
        StructField("l_orderkey", LongType(), False),
        StructField("l_partkey", LongType(), False),
        StructField("l_suppkey", LongType(), False),
        StructField("l_linenumber", IntegerType(), False),
        StructField("l_quantity", DecimalType(15, 3), False),
        StructField("l_extendedprice", DecimalType(15, 3), False),
        StructField("l_discount", DecimalType(15, 3), False),
        StructField("l_tax", DecimalType(15, 3), False),
        StructField("l_returnflag", StringType(), False),
        StructField("l_linestatus", StringType(), False),
        StructField("l_shipdate", DateType(), False),
        StructField("l_commitdate", DateType(), False),
        StructField("l_receiptdate", DateType(), False),
        StructField("l_shipinstruct", StringType(), False),
        StructField("l_shipmode", StringType(), False),
        StructField("l_comment", StringType(), False),
    ]),
    "nation": StructType([
        StructField("n_nationkey", LongType(), False),
        StructField("n_name", StringType(), False),
        StructField("n_regionkey", LongType(), False),
        StructField("n_comment", StringType(), False),
    ]),
    "orders": StructType([
        StructField("o_orderkey", LongType(), False),
        StructField("o_custkey", LongType(), False),
        StructField("o_orderstatus", StringType(), False),
        StructField("o_totalprice", DecimalType(15, 3), False),
        StructField("o_orderdate", DateType(), False),
        StructField("o_orderpriority", StringType(), False),
        StructField("o_clerk", StringType(), False),
        StructField("o_shippriority", IntegerType(), False),
        StructField("o_comment", StringType(), False),
    ]),
    "part": StructType([
        StructField("p_partkey", LongType(), False),
        StructField("p_name", StringType(), False),
        StructField("p_mfgr", StringType(), False),
        StructField("p_brand", StringType(), False),
        StructField("p_type", StringType(), False),
        StructField("p_size", IntegerType(), False),
        StructField("p_container", StringType(), False),
        StructField("p_retailprice", DecimalType(15, 3), False),
        StructField("p_comment", StringType(), False),
    ]),
    "partsupp": StructType([
        StructField("ps_partkey", LongType(), False),
        StructField("ps_suppkey", LongType(), False),
        StructField("ps_availqty", IntegerType(), False),
        StructField("ps_supplycost", DecimalType(15, 3), False),
        StructField("ps_comment", StringType(), False),
    ]),
    "region": StructType([
        StructField("r_regionkey", LongType(), False),
        StructField("r_name", StringType(), False),
        StructField("r_comment", StringType(), False),
    ]),
    "supplier": StructType([
        StructField("s_suppkey", LongType(), False),
        StructField("s_name", StringType(), False),
        StructField("s_address", StringType(), False),
        StructField("s_nationkey", LongType(), False),
        StructField("s_phone", StringType(), False),
        StructField("s_acctbal", DecimalType(15, 3), False),
        StructField("s_comment", StringType(), False),
    ]),
}

# Spark's CSV datasource produces nullable fields even when a supplied schema
# marks them non-nullable; use the schema it can persist and validate exactly.
TABLE_SCHEMAS = {
    table_name: StructType([
        StructField(field.name, field.dataType, True, field.metadata)
        for field in schema.fields
    ])
    for table_name, schema in TABLE_SCHEMAS.items()
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def new_manifest():
    return {
        "run_id": os.environ.get("TPCH_RUN_ID") or str(uuid.uuid4()),
        "started_at": utc_now(),
        "effective_identity": os.environ.get("WRITE_PRINCIPAL", "write-service-account"),
        "scale_factor": os.environ.get("TPCH_SCALE_FACTOR", "1"),
        "catalog": CATALOG,
        "etl_state": "not_started",
        "jdbc_state": "not_attempted",
        "overall_state": "running",
        "databases": [],
        "dremio": {"spaces": [], "views": []},
        "diagnostics": [],
    }


def persist_manifest(manifest):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(RESULTS_DIR, 0o700)
    manifest["updated_at"] = utc_now()
    target = RESULTS_DIR / f"{manifest['run_id']}.json"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=RESULTS_DIR, delete=False
    ) as temporary:
        json.dump(manifest, temporary, indent=2, sort_keys=True)
        temporary.write("\n")
        temp_path = Path(temporary.name)
    os.chmod(temp_path, 0o600)
    temp_path.replace(target)
    print(f"Run manifest: {target}")


def read_secret(name):
    path = Path("/run/secrets") / name
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError(f"Required secret is empty: {name}")
    return value


def quote_spark_identifier(identifier):
    return "`" + identifier.replace("`", "``") + "`"


def quote_dremio_identifier(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def error_summary(error, component=None, operation=None):
    """Return a diagnostic that excludes exception text and connection secrets."""
    summary = {"type": type(error).__name__}
    if component:
        summary["component"] = component
    if operation:
        summary["operation"] = operation
    sql_state = getattr(error, "sqlState", None)
    if sql_state:
        summary["sql_state"] = str(sql_state)
    return summary


def load_and_validate_etl(spark, manifest):
    jvm = spark.sparkContext._jvm
    user_group_information = jvm.org.apache.hadoop.security.UserGroupInformation
    user_group_information.setConfiguration(
        spark.sparkContext._jsc.hadoopConfiguration()
    )
    if not user_group_information.isSecurityEnabled():
        raise RuntimeError("Hadoop Kerberos authentication is not enabled")

    expected_principal = os.environ.get("WRITE_PRINCIPAL", "write-service-account")
    cache_name = os.environ.get("KRB5CCNAME", "FILE:/run/krb5/ccache")
    cache_path = cache_name.removeprefix("FILE:")
    ticket_user = user_group_information.getUGIFromTicketCache(
        cache_path, expected_principal
    )
    if not ticket_user.hasKerberosCredentials():
        raise RuntimeError("Writer ticket cache has no Kerberos credentials")
    user_group_information.setLoginUser(ticket_user)

    manifest["effective_identity"] = user_group_information.getCurrentUser().getUserName()
    if not manifest["effective_identity"].lower().startswith(
        expected_principal.split("@")[0].lower()
    ):
        raise RuntimeError("Spark effective identity does not match the writer principal")

    source_data = {}
    for table_name, schema in TABLE_SCHEMAS.items():
        path = INPUT_DIR / f"{table_name}.tbl"
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Required TPCH input is missing or empty: {table_name}.tbl")
        # dbgen's .tbl format includes a final delimiter on each row, so parse
        # the resulting empty terminator column and drop it before writing.
        parser_schema = StructType(
            schema.fields + [StructField("_tpch_row_terminator", StringType(), True)]
        )
        parsed_df = (
            spark.read.option("delimiter", "|")
            .option("header", "false")
            .option("mode", "FAILFAST")
            .schema(parser_schema)
            .csv(str(path))
        )
        source_df = parsed_df.drop("_tpch_row_terminator")
        source_data[table_name] = (source_df, source_df.count(), schema)

    manifest["etl_state"] = "running"
    for database_name in DATABASES:
        database_record = {
            "name": database_name,
            "state": "running",
            "warehouse_prefix": f"s3a://lake/warehouse/{database_name}.db",
            "tables": [],
        }
        manifest["databases"].append(database_record)
        database_identifier = (
            f"{quote_spark_identifier(CATALOG)}."
            f"{quote_spark_identifier(database_name)}"
        )
        spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {database_identifier}")

        for table_name, (source_df, expected_count, expected_schema) in source_data.items():
            table_identifier = (
                f"{database_identifier}.{quote_spark_identifier(table_name)}"
            )
            record = {
                "name": table_name,
                "hive_identifier": f"{CATALOG}.{database_name}.{table_name}",
                "expected_schema": expected_schema.jsonValue(),
                "expected_row_count": expected_count,
                "state": "running",
            }
            database_record["tables"].append(record)

            if spark.catalog.tableExists(table_identifier):
                existing_df = spark.table(table_identifier)
                observed_count = existing_df.count()
                record["observed_row_count"] = observed_count
                record["observed_schema"] = existing_df.schema.jsonValue()
                if existing_df.schema != expected_schema or observed_count != expected_count:
                    record["state"] = "conflict"
                    raise RuntimeError(
                        f"Existing table conflicts with expected schema/count: "
                        f"{database_name}.{table_name}"
                    )
                record["state"] = "already_valid"
            else:
                source_df.writeTo(table_identifier).using("iceberg").create()
                observed_df = spark.table(table_identifier)
                observed_count = observed_df.count()
                record["observed_row_count"] = observed_count
                record["observed_schema"] = observed_df.schema.jsonValue()
                if observed_df.schema != expected_schema or observed_count != expected_count:
                    record["state"] = "conflict"
                    raise RuntimeError(
                        f"New table failed schema/count validation: "
                        f"{database_name}.{table_name}"
                    )
                record["state"] = "created"

        database_record["state"] = "complete"

    manifest["etl_state"] = "complete"


def dremio_space_names(connection):
    rows = connection.createStatement().executeQuery("SHOW SCHEMAS")
    spaces = set()
    while rows.next():
        spaces.add(rows.getString(1).lower())
    rows.close()
    return spaces


def dremio_view_names(connection, space_name):
    statement = connection.createStatement()
    escaped_space_name = space_name.replace("'", "''")
    rows = statement.executeQuery(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS "
        f"WHERE TABLE_SCHEMA = '{escaped_space_name}'"
    )
    names = set()
    while rows.next():
        names.add(rows.getString(1).lower())
    rows.close()
    statement.close()
    return names


def dremio_view_definition(connection, space_name, view_name):
    statement = connection.createStatement()
    rows = statement.executeQuery(
        f"SHOW CREATE VIEW {quote_dremio_identifier(space_name)}."
        f"{quote_dremio_identifier(view_name)}"
    )
    parts = []
    metadata = rows.getMetaData()
    while rows.next():
        parts.extend(
            str(rows.getString(index) or "")
            for index in range(1, metadata.getColumnCount() + 1)
        )
    rows.close()
    statement.close()
    return " ".join(parts)


def expose_in_dremio(spark, manifest):
    jvm = spark.sparkContext._jvm
    connection = None
    all_ok = True
    dremio = manifest["dremio"]
    # A JDBC-only retry should report its current outcome, not retain stale
    # failures from an earlier attempt in the same ETL manifest.
    dremio["spaces"] = []
    dremio["views"] = []
    hive_source = os.environ.get("DREMIO_HIVE_SOURCE", "hive")

    try:
        jvm.java.lang.Class.forName("com.dremio.jdbc.Driver")
        properties = jvm.java.util.Properties()
        properties.setProperty(
            "user", os.environ.get("DREMIO_WRITER_USER", "write-service-account")
        )
        properties.setProperty("password", read_secret("dremio-writer-password"))
        url = (
            "jdbc:dremio:direct="
            f"{os.environ.get('DREMIO_HOST', 'dremio')}:"
            f"{os.environ.get('DREMIO_JDBC_PORT', '31010')}"
        )
        connection = jvm.java.sql.DriverManager.getConnection(url, properties)
        present_spaces = dremio_space_names(connection)
    except Exception as error:  # JDBC auth/connectivity is an explicit capability gate.
        dremio["connection_state"] = "failed"
        dremio["diagnostic"] = error_summary(
            error, component="Dremio JDBC", operation="connect/list spaces"
        )
        manifest["jdbc_state"] = "failed"
        for database_name in DATABASES:
            dremio["spaces"].append({"name": database_name, "state": "failed"})
            for table_name in TABLE_SCHEMAS:
                dremio["views"].append({
                    "space": database_name,
                    "name": table_name,
                    "state": "not_attempted",
                })
        return False

    dremio["connection_state"] = "connected"
    statement = connection.createStatement()
    for database_name in DATABASES:
        space_record = {"name": database_name, "state": "running"}
        dremio["spaces"].append(space_record)
        if database_name.lower() in present_spaces:
            space_record["state"] = "already_present"
        else:
            try:
                statement.execute(f"CREATE SPACE {quote_dremio_identifier(database_name)}")
                space_record["state"] = "created"
            except Exception as error:
                space_record["state"] = "failed"
                space_record["diagnostic"] = error_summary(
                    error, component="Dremio JDBC", operation="create space"
                )
                all_ok = False
                for table_name in TABLE_SCHEMAS:
                    dremio["views"].append({
                        "space": database_name,
                        "name": table_name,
                        "state": "not_attempted",
                    })
                continue

        try:
            present_views = dremio_view_names(connection, database_name)
        except Exception as error:
            space_record["state"] = "failed"
            space_record["diagnostic"] = error_summary(
                error, component="Dremio JDBC", operation="list views"
            )
            all_ok = False
            for table_name in TABLE_SCHEMAS:
                dremio["views"].append({
                    "space": database_name,
                    "name": table_name,
                    "state": "not_attempted",
                })
            continue

        for table_name in TABLE_SCHEMAS:
            view_record = {"space": database_name, "name": table_name, "state": "running"}
            dremio["views"].append(view_record)
            target = (
                f"{quote_dremio_identifier(hive_source)}."
                f"{quote_dremio_identifier(database_name)}."
                f"{quote_dremio_identifier(table_name)}"
            )
            if table_name.lower() in present_views:
                try:
                    definition = dremio_view_definition(
                        connection, database_name, table_name
                    ).lower()
                    if all(
                        part.lower() in definition
                        for part in (hive_source, database_name, table_name)
                    ):
                        view_record["state"] = "already_valid"
                    else:
                        view_record["state"] = "conflict"
                        all_ok = False
                except Exception as error:
                    view_record["state"] = "conflict"
                    view_record["diagnostic"] = error_summary(
                        error, component="Dremio JDBC", operation="validate existing view"
                    )
                    all_ok = False
                continue

            try:
                statement.execute(
                    f"CREATE VIEW {quote_dremio_identifier(database_name)}."
                    f"{quote_dremio_identifier(table_name)} AS "
                    f"SELECT * FROM {target}"
                )
                view_record["state"] = "created"
                view_record["target"] = f"{hive_source}.{database_name}.{table_name}"
            except Exception as error:
                view_record["state"] = "failed"
                view_record["diagnostic"] = error_summary(
                    error, component="Dremio JDBC", operation="create view"
                )
                all_ok = False

    statement.close()
    connection.close()
    manifest["jdbc_state"] = "complete" if all_ok else "failed"
    return all_ok


def main():
    manifest = new_manifest()
    spark = None
    try:
        builder = SparkSession.builder.appName("TPC-H-Hive-RustFS-Loader")
        builder = builder.config(
            "spark.redaction.regex",
            "(?i)secret|password|access[._-]?key|token",
        )
        builder = builder.config(
            "spark.redaction.string.regex",
            "(?i)secret|password|access[._-]?key|token",
        )
        builder = builder.config(
            "spark.sql.catalog.iceberg.s3.access-key-id",
            read_secret("rustfs-writer-access-key"),
        )
        builder = builder.config(
            "spark.sql.catalog.iceberg.s3.secret-access-key",
            read_secret("rustfs-writer-secret-key"),
        )
        spark = builder.getOrCreate()
        load_and_validate_etl(spark, manifest)
        manifest["overall_state"] = "running"
    except Exception as error:
        manifest["etl_state"] = "failed"
        manifest["overall_state"] = "failed"
        manifest["diagnostics"].append(
            error_summary(error, component="Spark/Hive ETL", operation="load or validate")
        )
        for database in manifest["databases"]:
            if database["state"] == "running":
                database["state"] = "failed"
            for table in database["tables"]:
                if table["state"] == "running":
                    table["state"] = "failed"
        print(f"ERROR: Unit 3 workload failed ({type(error).__name__}).", file=sys.stderr)
    finally:
        if spark is not None:
            try:
                spark.stop()
            except Exception:
                pass
        # The JDBC phase runs in a separate container and receives no Kerberos
        # material. Destroy the ETL ticket before publishing the handoff manifest.
        cache_name = os.environ.get("KRB5CCNAME", "FILE:/run/krb5/ccache")
        try:
            import subprocess
            subprocess.run(
                ["kdestroy", "-c", cache_name],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
        cache_path = Path(cache_name.removeprefix("FILE:"))
        cache_path.unlink(missing_ok=True)
        if manifest["etl_state"] == "complete":
            manifest["jdbc_state"] = "not_started"
            manifest["overall_state"] = "running"
        manifest["finished_at"] = utc_now()
        persist_manifest(manifest)

    print(
        "Workload result: "
        f"etl={manifest['etl_state']} jdbc={manifest['jdbc_state']} "
        f"overall={manifest['overall_state']}"
    )
    if manifest["etl_state"] == "complete":
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
