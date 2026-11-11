"""Verify an Iceberg availableNow stream with an s3ckpt:// checkpoint (s3-checkpoints FR-6).

  spark-submit verify_checkpoint_stream.py first  <run-id>   batch 0 reads the smoke table
  spark-submit verify_checkpoint_stream.py resume <run-id>   a new session resumes with no rows, then cleans up

Uses lakehouse_spark's catalog and checkpoint settings (ResolvingFileIO, S3A, the mounted
dev key), with the writer's static token instead of a broker, as create_smoke_tables.py does.
No key or token is printed.
"""

import re
import sys

import lakehouse_spark as ls
from create_smoke_tables import PASSWORD_FILE, SECRET_FILE, writer_token
from pyspark.sql import SparkSession

CATALOG = "lakehouse_dev"
SOURCE = "lakehouse_dev.default_lhdev.bootstrap_smoke_test"
BUCKET = "bucket-default-dev"
OTHER_BUCKET = "bucket-default-uat"


def session():
    token = writer_token(SECRET_FILE.read_text(encoding="utf-8").splitlines()[0], PASSWORD_FILE.read_text(encoding="utf-8").strip())
    settings = ls.catalog_settings(CATALOG)
    settings.update(ls.checkpoint_settings(ls.checkpoint_key_files(), "us-east-1"))
    prefix = f"spark.sql.catalog.{CATALOG}"
    settings.update({prefix + ".rest.auth.type": "oauth2", prefix + ".token": token, prefix + ".token-refresh-enabled": "false"})
    builder = SparkSession.builder.appName("verify-checkpoint-stream")
    for key, value in settings.items():
        builder = builder.config(key, value)
    spark = builder.getOrCreate()
    ls._quiet_known_warnings(spark)
    return spark


def stream(spark, checkpoint):
    query = (spark.readStream.format("iceberg")
             .option("streaming-skip-delete-snapshots", "true").option("streaming-skip-overwrite-snapshots", "true")
             .load(SOURCE).writeStream.format("noop").option("checkpointLocation", checkpoint)
             .trigger(availableNow=True).start())
    query.awaitTermination()
    return query.lastProgress or {}


def files(spark, checkpoint):
    path = spark._jvm.org.apache.hadoop.fs.Path(checkpoint)
    fs = path.getFileSystem(spark._jsc.hadoopConfiguration())
    names, found = [], fs.listFiles(path, True)
    while found.hasNext():
        names.append(str(found.next().getPath())[len(checkpoint):])
    return fs, path, sorted(names)


def main(phase, run_id):
    if phase not in ("first", "resume") or not re.fullmatch(r"[a-z0-9-]{8,40}", run_id):
        raise SystemExit("usage: verify_checkpoint_stream.py {first|resume} <run-id>")
    checkpoint = f"s3ckpt://{BUCKET}/checkpoints/_verify/{run_id}"
    spark = session()
    try:
        progress = stream(spark, checkpoint)
        if phase == "first":
            if progress.get("batchId") != 0:
                raise SystemExit(f"FAIL first run: batch {progress.get('batchId')}, expected 0")
            print(f"OK first run: batch 0, {progress.get('numInputRows')} rows")
            return
        if progress.get("numInputRows") != 0:
            raise SystemExit(f"FAIL resume: {progress.get('numInputRows')} rows reprocessed")
        fs, path, names = files(spark, checkpoint)
        if "/sources/0/offsets/0" not in names or "/commits/0" not in names:
            raise SystemExit(f"FAIL resume: checkpoint files {names}")
        print(f"OK resume: batch {progress.get('batchId')}, 0 rows; checkpoint files {names}")
        try:
            stream(spark, f"s3ckpt://{OTHER_BUCKET}/checkpoints/_verify/{run_id}")
            raise SystemExit(f"FAIL fail-closed: a checkpoint in {OTHER_BUCKET} worked without its key")
        except Exception as error:  # noqa: BLE001 - any failure is the expected outcome (SystemExit passes through)
            print(f"OK fail-closed: a checkpoint in {OTHER_BUCKET} without its key is refused ({type(error).__name__})")
        print(f"OK cleanup: checkpoint deleted ({fs.delete(path, True)})")
    finally:
        spark.stop()


if __name__ == "__main__":
    main(*sys.argv[1:3])
