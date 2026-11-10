# End-to-End Test Instructions — s3-checkpoints (Jupyter, developer)

1. Sign in to JupyterHub as `joe-developer` and stop, then start, the server (it picks up the new mounts at spawn).
2. In a terminal of the server: `ls /run/secrets/lakehouse-checkpoints/` shows `bucket-default-dev` only.
3. In a notebook with the Lakehouse kernel:

```python
from lakehouse_spark import create_spark_session
spark = create_spark_session("checkpoint-check", catalog="lakehouse_dev")
path = "s3ckpt://bucket-default-dev/checkpoints/_jupyter_check/smoke"

def run():
    q = (spark.readStream.format("iceberg")
         .option("streaming-skip-delete-snapshots", "true").option("streaming-skip-overwrite-snapshots", "true")
         .load("lakehouse_dev.default_lhdev.bootstrap_smoke_test")
         .writeStream.format("noop").option("checkpointLocation", path).trigger(availableNow=True).start())
    q.awaitTermination()
    return q.lastProgress["batchId"], q.lastProgress["numInputRows"]

print(run(), run())   # expected: (0, <rows>) (1, 0)
jpath = spark._jvm.org.apache.hadoop.fs.Path(path)
print(jpath.getFileSystem(spark._jsc.hadoopConfiguration()).delete(jpath, True))   # True: cleanup
```
4. Expected failure case: the same stream with `s3ckpt://bucket-default-uat/checkpoints/...` fails (no key for uat in Jupyter).
