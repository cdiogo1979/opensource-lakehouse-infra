
import os

from pyspark.sql import SparkSession

# Standalone Hadoop Catalog example retained for reference. It is not mounted
# as a startup workload and does not implement the Hive/Unit 3 ETL flow.

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CATALOG = "iceberg"
WAREHOUSE = "s3a://lake/warehouse"

S3_ENDPOINT = "http://object-store:9000"
S3_ACCESS_KEY = os.environ["AWS_ACCESS_KEY_ID"]
S3_SECRET_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]


# ---------------------------------------------------------------------------
# Spark / Iceberg
# ---------------------------------------------------------------------------

spark = (
    SparkSession.builder
    .appName("iceberg-poc-seed")

    # Make our catalog the default catalog.
    # This overrides the "demo" catalog that comes with the Tabulario image.
    .config(
        "spark.sql.defaultCatalog",
        CATALOG,
    )

    # Iceberg Hadoop Catalog
    .config(
        f"spark.sql.catalog.{CATALOG}",
        "org.apache.iceberg.spark.SparkCatalog",
    )
    .config(
        f"spark.sql.catalog.{CATALOG}.catalog-impl",
        "org.apache.iceberg.hadoop.HadoopCatalog",
    )
    .config(
        f"spark.sql.catalog.{CATALOG}.warehouse",
        WAREHOUSE,
    )

    # -----------------------------------------------------------------------
    # RustFS / S3
    # -----------------------------------------------------------------------

    .config(
        "spark.hadoop.fs.s3a.endpoint",
        S3_ENDPOINT,
    )
    .config(
        "spark.hadoop.fs.s3a.access.key",
        S3_ACCESS_KEY,
    )
    .config(
        "spark.hadoop.fs.s3a.secret.key",
        S3_SECRET_KEY,
    )
    .config(
        "spark.hadoop.fs.s3a.path.style.access",
        "true",
    )
    .config(
        "spark.hadoop.fs.s3a.connection.ssl.enabled",
        "false",
    )
    .config(
        "spark.hadoop.fs.s3a.impl",
        "org.apache.hadoop.fs.s3a.S3AFileSystem",
    )

    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


# ---------------------------------------------------------------------------
# Create namespace
# ---------------------------------------------------------------------------

print("\n=== Creating namespace ===")

spark.sql(
    f"CREATE NAMESPACE IF NOT EXISTS {CATALOG}.demo"
)


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

print("\n=== Creating customers table ===")

spark.sql(
    f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.demo.customers (
        customer_id BIGINT,
        name STRING,
        country STRING,
        city STRING
    )
    USING iceberg
    """
)

spark.sql(
    f"""
    INSERT INTO {CATALOG}.demo.customers VALUES
        (1, 'Carlos', 'Portugal', 'Porto'),
        (2, 'Ana', 'Portugal', 'Lisbon'),
        (3, 'John', 'United Kingdom', 'London'),
        (4, 'Marie', 'France', 'Paris'),
        (5, 'Hans', 'Germany', 'Berlin')
    """
)


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

print("\n=== Creating products table ===")

spark.sql(
    f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.demo.products (
        product_id BIGINT,
        product_name STRING,
        category STRING,
        price DECIMAL(10,2)
    )
    USING iceberg
    """
)

spark.sql(
    f"""
    INSERT INTO {CATALOG}.demo.products VALUES
        (101, 'Laptop', 'Electronics', 1299.99),
        (102, 'Keyboard', 'Electronics', 89.99),
        (103, 'Coffee Machine', 'Kitchen', 249.90),
        (104, 'Running Shoes', 'Sports', 119.99),
        (105, 'Backpack', 'Accessories', 79.90)
    """
)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

print("\n=== Creating orders table ===")

spark.sql(
    f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.demo.orders (
        order_id BIGINT,
        customer_id BIGINT,
        product_id BIGINT,
        quantity INT,
        order_date DATE
    )
    USING iceberg
    """
)

spark.sql(
    f"""
    INSERT INTO {CATALOG}.demo.orders VALUES
        (1001, 1, 101, 1, DATE '2026-10-01'),
        (1002, 1, 104, 2, DATE '2026-10-02'),
        (1003, 2, 103, 1, DATE '2026-10-03'),
        (1004, 3, 102, 3, DATE '2026-10-04'),
        (1005, 4, 105, 1, DATE '2026-10-05'),
        (1006, 5, 101, 1, DATE '2026-10-06')
    """
)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

print("\n=== Namespaces ===")

spark.sql(
    f"SHOW NAMESPACES IN {CATALOG}"
).show(truncate=False)


print("\n=== Tables ===")

spark.sql(
    f"SHOW TABLES IN {CATALOG}.demo"
).show(truncate=False)


print("\n=== Customers ===")

spark.sql(
    f"SELECT * FROM {CATALOG}.demo.customers"
).show(truncate=False)


print("\n=== Products ===")

spark.sql(
    f"SELECT * FROM {CATALOG}.demo.products"
).show(truncate=False)


print("\n=== Orders ===")

spark.sql(
    f"SELECT * FROM {CATALOG}.demo.orders"
).show(truncate=False)


print("\n=== Order summary ===")

spark.sql(
    f"""
    SELECT
        c.name AS customer,
        p.product_name,
        o.quantity,
        p.price,
        o.quantity * p.price AS total
    FROM {CATALOG}.demo.orders o
    JOIN {CATALOG}.demo.customers c
        ON o.customer_id = c.customer_id
    JOIN {CATALOG}.demo.products p
        ON o.product_id = p.product_id
    ORDER BY o.order_id
    """
).show(truncate=False)


print("\n=== Iceberg POC seed completed successfully ===\n")

spark.stop()
