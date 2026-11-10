#!/usr/bin/env python3
"""Run the Dremio JDBC phase against a completed ETL manifest."""

import json
import os
from pathlib import Path
import sys

sys.path.insert(0, "/opt/tpch")
import load_tpch
from pyspark.sql import SparkSession


def main():
    run_id = os.environ["TPCH_RUN_ID"]
    manifest_path = Path(os.environ.get("TPCH_RESULTS_DIR", "/run/results")) / f"{run_id}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("etl_state") != "complete":
        raise RuntimeError("Dremio phase requires a completed ETL manifest")
    manifest["jdbc_state"] = "running"
    spark = None
    try:
        # No Hive catalog configuration, Kerberos material, or RustFS keys are
        # mounted in this service. Spark supplies only the JVM/JDBC driver.
        spark = SparkSession.builder.appName("TPC-H-Dremio-JDBC").getOrCreate()
        success = load_tpch.expose_in_dremio(spark, manifest)
        manifest["overall_state"] = "complete" if success else "partial"
    except Exception as error:
        manifest["jdbc_state"] = "failed"
        manifest["overall_state"] = "partial"
        manifest["diagnostics"].append(
            load_tpch.error_summary(
                error, component="Dremio JDBC", operation="expose spaces and views"
            )
        )
        print(f"ERROR: Dremio JDBC phase failed ({type(error).__name__}).", file=sys.stderr)
    finally:
        if spark is not None:
            try:
                spark.stop()
            except Exception:
                pass
        manifest["finished_at"] = load_tpch.utc_now()
        load_tpch.persist_manifest(manifest)

    print(
        f"Workload result: etl={manifest['etl_state']} "
        f"jdbc={manifest['jdbc_state']} overall={manifest['overall_state']}"
    )
    return 0 if manifest["overall_state"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
