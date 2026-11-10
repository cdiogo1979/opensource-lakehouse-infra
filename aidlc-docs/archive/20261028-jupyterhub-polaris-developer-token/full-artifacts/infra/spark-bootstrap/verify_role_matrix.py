"""Exercise Polaris and vended RustFS access for one temporary role per run."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

KEYCLOAK_TOKEN_URI = "http://keycloak:8080/realms/lakehouse/protocol/openid-connect/token"
POLARIS_URI = "http://polaris:8181/api/catalog"
INPUT = Path("/run/secrets/role-matrix-clients.json")
PRODUCT = {
    "lakehouse": ("default_lh", "prod", "bucket-default"),
    "lakehouse_uat": ("default_lhuat", "uat", "bucket-default-uat"),
    "lakehouse_dev": ("default_lhdev", "dev", "bucket-default-dev"),
}
READABLE = {
    "developer": frozenset({"prod", "uat", "dev"}),
    "analyst": frozenset({"prod"}),
    "owner": frozenset({"prod", "uat", "dev"}),
    "writer": frozenset({"prod", "uat", "dev"}),
}
WRITABLE = {
    "developer": frozenset({"dev"}),
    "analyst": frozenset(),
    "owner": frozenset({"prod", "uat", "dev"}),
    "writer": frozenset({"prod", "uat", "dev"}),
}
ROLES = tuple(READABLE)
ENVIRONMENTS = frozenset({"prod", "uat", "dev"})
MUTATIONS = frozenset({"write", "create", "alter", "drop", "append", "overwrite", "delete"})


def role_can_access(roles: set[str] | frozenset[str], environment: str, operation: str) -> bool:
    """Evaluate the explicit role/environment matrix; unknown inputs deny."""
    if not isinstance(roles, (set, frozenset)):
        return False
    if not isinstance(environment, str) or not isinstance(operation, str):
        return False
    if environment not in ENVIRONMENTS or (operation != "read" and operation not in MUTATIONS):
        return False
    grants = READABLE if operation == "read" else WRITABLE
    return any(
        isinstance(role, str) and environment in grants.get(role, ())
        for role in roles
    )


def valid_path_segment(value: str) -> bool:
    """Accept one simple Unicode alphanumeric/underscore/hyphen path segment."""
    if not isinstance(value, str) or not value or value in {".", ".."} or not value[0].isalnum():
        return False
    return all(character.isalnum() or character in "_-" for character in value)


def expected_table_location(catalog: str, namespace: str, table: str) -> str:
    """Return the exact approved bucket/catalog/database/table URI."""
    if not isinstance(catalog, str) or catalog not in PRODUCT:
        raise ValueError("Unknown catalog")
    expected_namespace, _, bucket = PRODUCT[catalog]
    if namespace != expected_namespace:
        raise ValueError("Namespace does not match its catalog")
    if not all(valid_path_segment(part) for part in (catalog, namespace, table)):
        raise ValueError("Invalid storage path segment")
    return f"s3://{bucket}/{catalog}/{namespace}/{table}"


def location_matches(location: str, catalog: str, namespace: str, table: str) -> bool:
    """Require the observed location to equal the one authorized table path."""
    try:
        expected = expected_table_location(catalog, namespace, table)
        parsed = urllib.parse.urlsplit(location)
        port = parsed.port
    except (TypeError, ValueError):
        return False
    if parsed.scheme != "s3" or parsed.query or parsed.fragment or parsed.username or parsed.password:
        return False
    if port is not None or parsed.netloc != expected.removeprefix("s3://").split("/", 1)[0]:
        return False
    path = parsed.path.rstrip("/")
    return f"s3://{parsed.netloc}{path}" == expected


def sql_name(*parts: str) -> str:
    return ".".join(f"`{part.replace('`', '``')}`" for part in parts)


def token_for(client_id: str, secret: str) -> str:
    payload = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": secret,
    }).encode()
    request = urllib.request.Request(
        KEYCLOAK_TOKEN_URI,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        token = json.loads(response.read()).get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Identity provider returned no access token.")
    return token


def spark_session(token: str, role: str) -> SparkSession:
    from pyspark.sql import SparkSession

    builder = (
        SparkSession.builder.appName(f"default-product-role-matrix-{role}")
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.defaultCatalog", "lakehouse")
        .config("spark.redaction.regex", "(?i)secret|password|token|access[.]?key|credential")
        .config("spark.sql.redaction.options.regex", "(?i)secret|password|token|access[.]?key|credential")
    )
    for catalog in PRODUCT:
        prefix = f"spark.sql.catalog.{catalog}"
        for suffix, value in {
            "": "org.apache.iceberg.spark.SparkCatalog",
            ".type": "rest",
            ".uri": POLARIS_URI,
            ".io-impl": "org.apache.iceberg.aws.s3.S3FileIO",
            ".token": token,
            ".token-refresh-enabled": "false",
            ".warehouse": catalog,
            ".header.Polaris-Realm": "lakehouse",
            ".header.X-Iceberg-Access-Delegation": "vended-credentials",
        }.items():
            builder = builder.config(prefix + suffix, value)
    session = builder.getOrCreate()
    session.sparkContext.setLogLevel("ERROR")
    return session


def main() -> None:
    mode = os.environ.get("ROLE_MATRIX_MODE", "test")
    role = os.environ.get("ROLE_MATRIX_ROLE", "")
    if mode not in {"test", "cleanup"} or (mode == "test" and role not in ROLES):
        raise RuntimeError("Role-matrix mode or role is invalid.")
    if INPUT.is_symlink() or not INPUT.is_file():
        raise RuntimeError("Protected temporary role credentials are unavailable.")
    identities = json.loads(INPUT.read_text(encoding="utf-8"))
    base_id = int(identities["probe_id_base"])
    token_role = "writer" if mode == "cleanup" else role
    identity = identities[token_role]
    token = token_for(identity["client_id"], identity["client_secret"])
    spark = spark_session(token, f"{mode}-{token_role}")
    failures: list[str] = []
    try:
        if mode == "test":
            role_index = ROLES.index(role)
            for env_index, (catalog, (namespace, environment, _bucket)) in enumerate(PRODUCT.items()):
                table = sql_name(catalog, namespace, "bootstrap_smoke_test")
                can_read = environment in READABLE[role]
                try:
                    rows = spark.sql(f"SELECT id, environment FROM {table}").collect()
                    read_succeeded = True
                    baseline_visible = (1, environment) in {
                        (row["id"], row["environment"]) for row in rows
                    }
                except Exception:
                    read_succeeded = False
                    baseline_visible = False
                read_matches = (read_succeeded and baseline_visible) if can_read else not read_succeeded
                if not read_matches:
                    failures.append(f"read/{environment}: expected {'allow' if can_read else 'deny'}, got {'allow' if read_succeeded else 'deny'}")
                if can_read and read_succeeded:
                    location_rows = spark.sql(f"DESCRIBE TABLE EXTENDED {table}").collect()
                    location = next(
                        (row["data_type"] for row in location_rows if row["col_name"].strip().lower() == "location"),
                        None,
                    )
                    if not location or not location_matches(location, catalog, namespace, "bootstrap_smoke_test"):
                        failures.append(f"location/{environment}: table location does not match the approved bucket/catalog/database/table layout")

                can_write = environment in WRITABLE[role]
                probe_id = base_id + role_index * 10 + env_index
                try:
                    spark.sql(f"INSERT INTO {table} VALUES ({probe_id}, 'role-matrix-probe')")
                    write_ok = True
                except Exception:
                    write_ok = False
                if write_ok != can_write:
                    failures.append(f"write/{environment}: expected {'allow' if can_write else 'deny'}, got {'allow' if write_ok else 'deny'}")
            if failures:
                print(f"ROLE_MATRIX_FAILURE: {role}: " + "; ".join(failures))
                raise SystemExit(1)
            print(f"ROLE_MATRIX_RESULT: {role} permissions matched across prod/dev/UAT.")
        else:
            ids = [base_id + ROLES.index(name) * 10 + env for name in ROLES for env in range(len(PRODUCT))]
            for catalog, (namespace, environment, _bucket) in PRODUCT.items():
                table = sql_name(catalog, namespace, "bootstrap_smoke_test")
                id_list = ",".join(str(value) for value in ids)
                spark.sql(f"DELETE FROM {table} WHERE id IN ({id_list})")
                rows = spark.sql(f"SELECT id, environment FROM {table}").collect()
                if [(row["id"], row["environment"]) for row in rows] != [(1, environment)]:
                    failures.append(f"{environment}: smoke table did not return to its original single row")
            if failures:
                print("ROLE_MATRIX_FAILURE: cleanup: " + "; ".join(failures))
                raise SystemExit(1)
            print("ROLE_MATRIX_CLEANUP: all smoke tables returned to their original single row.")
    finally:
        spark.stop()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as error:
        print(f"ROLE_MATRIX_FAILURE: unexpected verification error ({type(error).__name__}).")
        raise SystemExit(1) from None
