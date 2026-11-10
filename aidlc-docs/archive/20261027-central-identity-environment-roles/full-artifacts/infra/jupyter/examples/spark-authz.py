# %% [markdown]
# # JupyterHub Spark identity check
#
# Run this in a notebook as `developer-user`, `analyst-user`, or
# `administrator`. Spark/Hadoop must load the session's own keytab into Hadoop
# UserGroupInformation before the first Hive Metastore operation. A native
# `kinit` ticket alone does not initialize Hadoop's Java Subject.

# %%
import os

from pyspark.sql import SparkSession

username = os.environ["JUPYTERHUB_USER"]
principal = os.environ["KERBEROS_PRINCIPAL"]
expected_principals = {
    "developer-user": "developer-user@LAKEHOUSE.LOCAL",
    "analyst-user": "analyst-user@LAKEHOUSE.LOCAL",
    "administrator": "admin@LAKEHOUSE.LOCAL",
}
if username not in expected_principals or principal != expected_principals[username]:
    raise RuntimeError("The notebook identity does not match its configured Spark principal.")

spark = (
    SparkSession.builder.appName(f"lakehouse-{username}")
    .config("spark.redaction.regex", "(?i)secret|password|access[._-]?key|token")
    .config(
        "spark.redaction.string.regex",
        "(?i)secret|password|access[._-]?key|token",
    )
    .getOrCreate()
)

ugi = spark.sparkContext._jvm.org.apache.hadoop.security.UserGroupInformation
ugi.loginUserFromKeytab(principal, "/run/credentials/identity.keytab")
if not ugi.getLoginUser().hasKerberosCredentials():
    raise RuntimeError("Hadoop did not load the notebook's Kerberos identity.")

# This metadata query confirms the Hive catalog connection without reading any
# existing table data. Object access is enforced separately by RustFS policies.
database_count = len(spark.sql("SHOW DATABASES IN iceberg").collect())
print({"user": username, "principal": principal, "visible_database_count": database_count})

# Optionally set LAKEHOUSE_SAMPLE_TABLE to a table you are authorized to read.
sample_table = os.environ.get("LAKEHOUSE_SAMPLE_TABLE")
if sample_table:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.")
    if not sample_table or any(character not in allowed for character in sample_table):
        raise ValueError("LAKEHOUSE_SAMPLE_TABLE must be a qualified SQL identifier.")
    spark.sql(f"SELECT * FROM {sample_table} LIMIT 10").show(truncate=True)
