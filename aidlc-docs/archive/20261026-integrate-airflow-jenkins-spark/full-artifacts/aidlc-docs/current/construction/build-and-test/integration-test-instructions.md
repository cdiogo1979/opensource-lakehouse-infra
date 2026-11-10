# Integration Test Instructions — Unit 1 Spark Writer Runtime

## Prior Kerberos Spark smoke test

The archived Unit 1 Foundation Build and Test record previously ran Spark SQL in local mode with a pre-authenticated Kerberos ticket cache. It listed Hive namespaces, created a temporary namespace, verified it in the metastore, and removed it. The same read/write metadata smoke test was repeated here on the derived image, together with a sample Iceberg table read.

Run this in an isolated, removable Compose container. It uses existing file-backed secrets without printing their values and does not stop or recreate the normal `spark` service:

```bash
docker compose --profile workload run --rm --no-deps --entrypoint /bin/bash spark -lc '
set -euo pipefail
umask 077
kinit -c "$KRB5CCNAME" -kt "$SPARK_WRITER_KEYTAB" "$SPARK_WRITER_PRINCIPAL"
klist -s -c "$KRB5CCNAME"
{
  printf "[default]\naws_access_key_id="
  tr -d "\r\n" </run/secrets/rustfs-writer-access-key
  printf "\naws_secret_access_key="
  tr -d "\r\n" </run/secrets/rustfs-writer-secret-key
  printf "\n"
} > "$AWS_SHARED_CREDENTIALS_FILE"
chmod 600 "$AWS_SHARED_CREDENTIALS_FILE"
export AWS_PROFILE=default AWS_EC2_METADATA_DISABLED=true
/opt/spark/bin/spark-sql --master "local[1]" -e "SHOW NAMESPACES IN iceberg"
/opt/spark/bin/spark-sql --master "local[1]" -e "SELECT COUNT(*) FROM iceberg.databaseA.customer"
ns="spark_writer_smoke_$(date +%s)"
/opt/spark/bin/spark-sql --master "local[1]" -e "CREATE NAMESPACE iceberg.$ns"
/opt/spark/bin/spark-sql --master "local[1]" -e "SHOW NAMESPACES IN iceberg"
/opt/spark/bin/spark-sql --master "local[1]" -e "DROP NAMESPACE iceberg.$ns"
'
```

Expected results: Kerberos validation succeeds; `databasea` and `databaseb` appear; the sample query returns 150000; the temporary namespace appears after creation and is removed by the final command. The credentials file and ticket cache are held in the run container's private tmpfs and removed with the container.

## Remaining supervised-service integration checks

The isolated smoke test above does **not** exercise `infra/spark/entrypoint.sh` or a standalone Spark worker. Before reporting Unit 1 fully verified, schedule a Spark service restart after confirming no user notebook or Spark work will be interrupted, then verify:

1. `docker compose ps spark` reports healthy.
2. The Spark master JSON reports at least one alive worker and advertises `spark://spark:7077`.
3. A remote Spark application submitted to that master completes an Iceberg read/write as `write-service-account`.
4. Renewal failure/recovery, worker decommission and re-registration, signal cleanup, and diagnostic redaction behave as designed.

The old running container was left untouched during this Build and Test. At inspection time, its Spark master reported zero workers and zero active apps/drivers; those observations are not proof of the new supervisor's behavior.
