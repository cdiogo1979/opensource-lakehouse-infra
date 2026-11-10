"""Focused contracts for the Unit 2 broker client and Spark token handoff."""

import base64
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "infra/jupyter/singleuser"))
import lakehouse_broker_client as client  # noqa: E402
import lakehouse_spark as spark_factory  # noqa: E402


def make_jwt(expiry: int) -> str:
    def encode(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")

    return f"{encode({'alg': 'none'})}.{encode({'exp': expiry})}.signature"


class BrokerClientTests(unittest.TestCase):
    def response(self, token, expiry=None):
        return json.dumps(
            {"access_token": token, "expires_at": expiry if expiry is not None else 5000}
        ).encode()

    def test_broker_uses_https_ca_and_hub_token_then_returns_exact_jwt(self):
        jwt = make_jwt(5000)

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _size):
                return self.body

        response = Response()
        response.body = self.response(jwt)
        tls_context = type("TlsContext", (), {"check_hostname": True, "verify_mode": 2})()
        with patch.object(client.ssl, "create_default_context", return_value=tls_context), patch.object(
            client, "urlopen", return_value=response
        ) as open_url:
            result = client.request_user_token(
                broker_url="https://jupyterhub:8443/api/v1/token",
                ca_path=__file__,
                hub_api_token="hub-server-token",
                clock=lambda: 1000,
            )
        request = open_url.call_args.args[0]
        timeout = open_url.call_args.kwargs["timeout"]
        context = open_url.call_args.kwargs["context"]
        self.assertEqual(result.access_token, jwt)
        self.assertEqual(result.expires_at, 5000)
        self.assertEqual(request.get_header("Authorization"), "Bearer hub-server-token")
        self.assertEqual(timeout, 5.0)
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, 2)

    def test_broker_rejects_short_expiry_or_mismatched_expiry(self):
        jwt = make_jwt(1060)
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def read(self, _size): return json.dumps({"access_token": jwt, "expires_at": 1061}).encode()

        with patch.object(client.ssl, "create_default_context", return_value=object()), patch.object(
            client, "urlopen", return_value=Response()
        ):
            with self.assertRaises(client.BrokerClientError):
                client.request_user_token(ca_path=__file__, hub_api_token="hub", clock=lambda: 1000)

    def test_client_never_includes_response_body_in_failures(self):
        from urllib.error import URLError

        with patch.object(client.ssl, "create_default_context", return_value=object()), patch.object(
            client, "urlopen", side_effect=URLError("private bearer response")
        ):
            with self.assertRaises(client.BrokerClientError) as raised:
                client.request_user_token(ca_path=__file__, hub_api_token="secret-token")
        self.assertNotIn("private bearer response", str(raised.exception))
        self.assertNotIn("secret-token", str(raised.exception))


class SparkFactoryTests(unittest.TestCase):
    def test_exact_access_jwt_configures_all_catalogs_and_refresh_is_disabled(self):
        jwt = make_jwt(5000)
        config = {}

        class Builder:
            def appName(self, _name): return self
            def config(self, key, value):
                config[key] = value
                return self
            def getOrCreate(self): return "spark-session"

        fake_sql = types.ModuleType("pyspark.sql")
        fake_sql.SparkSession = types.SimpleNamespace(builder=Builder())
        fake_pyspark = types.ModuleType("pyspark")
        fake_pyspark.SparkContext = types.SimpleNamespace(_active_spark_context=None)
        with patch.object(spark_factory, "request_user_token", return_value=client.BrokerToken(jwt, 5000)), patch.dict(
            sys.modules, {"pyspark": fake_pyspark, "pyspark.sql": fake_sql}
        ):
            result = spark_factory.create_spark_session()
        self.assertEqual(result, "spark-session")
        self.assertEqual(config["spark.sql.defaultCatalog"], "lakehouse")
        for catalog in ("lakehouse", "lakehouse_uat", "lakehouse_dev"):
            prefix = f"spark.sql.catalog.{catalog}"
            self.assertEqual(config[prefix + ".token"], jwt)
            self.assertEqual(config[prefix + ".token-refresh-enabled"], "false")
            self.assertEqual(config[prefix + ".type"], "rest")
            self.assertEqual(config[prefix + ".warehouse"], catalog)
            self.assertEqual(config[prefix + ".header.X-Iceberg-Access-Delegation"], "vended-credentials")
        self.assertIn("token", config["spark.redaction.regex"])

    def test_factory_rejects_unapproved_default_catalog_without_requesting_token(self):
        fake_pyspark = types.ModuleType("pyspark")
        fake_pyspark.SparkContext = types.SimpleNamespace(_active_spark_context=None)
        with patch.dict(os.environ, {"LAKEHOUSE_POLARIS_CATALOG": "unknown_catalog"}), patch.object(
            spark_factory, "request_user_token"
        ) as request_token, patch.dict(sys.modules, {"pyspark": fake_pyspark}):
            with self.assertRaises(RuntimeError):
                spark_factory.create_spark_session()
        request_token.assert_not_called()

    def test_factory_rejects_existing_spark_context_before_requesting_token(self):
        fake_sql = types.ModuleType("pyspark.sql")
        fake_pyspark = types.ModuleType("pyspark")
        fake_pyspark.SparkContext = types.SimpleNamespace(_active_spark_context=object())
        with patch.object(spark_factory, "request_user_token") as request_token, patch.dict(
            sys.modules, {"pyspark": fake_pyspark, "pyspark.sql": fake_sql}
        ):
            with self.assertRaises(RuntimeError):
                spark_factory.create_spark_session()
        request_token.assert_not_called()


if __name__ == "__main__":
    unittest.main()
