# %% [markdown]
# # Spark authorization examples
#
# Run these direct Hive catalog queries as `user_a` and `user_b` separately.
# `user_a` is expected to read `databaseA` and be denied on `databaseB`;
# `user_b` is expected to read both. A failure is an authorization denial only
# when its category is `authorization` after the Kerberos session is established.

# %%
import os

from pyspark.sql import SparkSession

username = os.environ.get("JUPYTERHUB_USER", "unknown")
spark = (
    SparkSession.builder.appName(f"spark-authz-{username}")
    .config(
        "spark.sql.catalog.iceberg.s3.access-key-id",
        os.environ["AWS_ACCESS_KEY_ID"],
    )
    .config(
        "spark.sql.catalog.iceberg.s3.secret-access-key",
        os.environ["AWS_SECRET_ACCESS_KEY"],
    )
    .config("spark.redaction.regex", "(?i)secret|password|access[._-]?key|token")
    .config(
        "spark.redaction.string.regex",
        "(?i)secret|password|access[._-]?key|token",
    )
    .getOrCreate()
)

# Spark's Hadoop UGI starts as the local container user in local mode. Attach
# this session's own mounted Kerberos identity to UGI before the first Hive call.
ugi = spark.sparkContext._jvm.org.apache.hadoop.security.UserGroupInformation
ugi.loginUserFromKeytab(
    os.environ["KERBEROS_PRINCIPAL"],
    "/run/credentials/identity.keytab",
)

expected = {
    "user_a": {"databaseA": "allow", "databaseB": "deny"},
    "user_b": {"databaseA": "allow", "databaseB": "allow"},
}

if username not in expected:
    raise RuntimeError("Use user_a or user_b to run the test-user authorization matrix.")

# %%
def classify_failure(error):
    message = str(error).lower()
    if any(
        token in message
        for token in (
            "not authorized",
            "authorization",
            "permission denied",
            "not allowed",
            "accesscontrol",
            "insufficient privilege",
        )
    ):
        return "authorization"
    if any(token in message for token in ("gss", "kerberos", "sasl", "ticket")):
        return "kerberos"
    if any(token in message for token in ("unknown host", "connection refused", "timed out", "transport")):
        return "hive_connectivity"
    if any(token in message for token in ("table or view not found", "table not found", "no such table")):
        return "missing_object"
    if any(token in message for token in ("outofmemory", "resource", "cannot allocate")):
        return "resource"
    if any(token in message for token in ("signaturedoesnotmatch", "invalid access key", "access denied")):
        return "rustfs_credential_or_policy"
    return "unknown"


def run_case(database):
    expected_result = expected[username][database]
    table = f"iceberg.{database}.customer"
    try:
        spark.sql(f"SELECT * FROM {table} LIMIT 1").show(truncate=True)
        actual_result = "allow"
        failure_category = None
    except Exception as error:
        failure_category = classify_failure(error)
        actual_result = "deny" if failure_category == "authorization" else "error"

    print(
        {
            "username": username,
            "principal": os.environ.get("KERBEROS_PRINCIPAL", "unknown"),
            "database": database,
            "expected": expected_result,
            "actual": actual_result,
            "matches_expectation": actual_result == expected_result,
            "failure_category": failure_category,
        }
    )


# %%
run_case("databaseA")
run_case("databaseB")
