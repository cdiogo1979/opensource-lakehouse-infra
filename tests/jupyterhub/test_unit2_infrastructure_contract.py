"""Source-level infrastructure checks for the internal broker trust boundary."""

import importlib.util
import socket
import ssl
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/setup" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


network = load_script("check-jupyter-user-network")
certificates = load_script("prepare-jupyterhub-broker-certificates")


class NetworkPreflightTests(unittest.TestCase):
    def test_accepts_nonoverlapping_subnet_and_valid_stable_address(self):
        with patch.object(network, "route_networks", return_value=[]), patch.object(
            network, "docker_networks", return_value=([], False)
        ):
            network.check("172.30.240.0/24", "172.30.240.2")

    def test_rejects_route_overlap_and_invalid_hub_address(self):
        with patch.object(network, "route_networks", return_value=[network.ipaddress.ip_network("172.30.0.0/16")]), patch.object(
            network, "docker_networks", return_value=([], False)
        ):
            with self.assertRaises(RuntimeError):
                network.check("172.30.240.0/24", "172.30.240.2")
        with self.assertRaises(RuntimeError):
            network.check("172.30.240.0/24", "172.31.0.2")


class ComposeAndCertificateContracts(unittest.TestCase):
    def test_broker_is_not_host_published_and_hub_uses_stable_address(self):
        compose = (ROOT / "compose.jupyter.yml").read_text()
        self.assertIn("ipv4_address: ${JUPYTERHUB_BROKER_BIND_IP", compose)
        self.assertIn("subnet: ${JUPYTER_USER_SUBNET", compose)
        self.assertIn("jupyterhub-broker-server-key.pem:/run/certs/jupyterhub-broker-server-key.pem:ro", compose)
        self.assertNotRegex(compose, r"8443\s*:\s*8443")

    def test_rotation_is_explicit_and_ca_key_is_not_a_compose_mount(self):
        helper = (ROOT / "scripts/setup/prepare-jupyterhub-broker-certificates.py").read_text()
        compose = (ROOT / "compose.jupyter.yml").read_text()
        self.assertIn("--rotate", helper)
        self.assertIn("DNS:jupyterhub", helper)
        self.assertNotIn("jupyterhub-broker-ca-key.pem:/", compose)

    def test_certificate_preparation_is_idempotent_and_rotation_is_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            credentials = root / "credentials"
            mounts = root / "container-mounts"
            materials = (
                credentials / "ca-key.pem",
                credentials / "server.crt",
                credentials / "server-key.pem",
                mounts / "ca.crt",
            )
            with (
                patch.object(certificates, "CREDENTIALS", credentials),
                patch.object(certificates, "MOUNTS", mounts),
                patch.object(certificates, "CA_KEY", materials[0]),
                patch.object(certificates, "SERVER_CERT", materials[1]),
                patch.object(certificates, "SERVER_KEY", materials[2]),
                patch.object(certificates, "CA_CERT", materials[3]),
                patch.object(certificates, "MATERIALS", materials),
            ):
                certificates.prepare()
                first_ca = materials[3].read_bytes()
                for certificate in (materials[1], materials[3]):
                    authority_key_id = certificates.run(
                        "openssl",
                        "x509",
                        "-in",
                        str(certificate),
                        "-noout",
                        "-ext",
                        "authorityKeyIdentifier",
                        capture=True,
                    )
                    self.assertIn("Authority Key Identifier", authority_key_id)
                    self.assertNotIn("No extensions", authority_key_id)
                certificates.prepare()
                self.assertEqual(materials[3].read_bytes(), first_ca)
                self.assertEqual(materials[0].stat().st_mode & 0o777, 0o600)
                self.assertEqual(materials[2].stat().st_mode & 0o777, 0o600)
                certificates.validate(materials)

                server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                server_context.load_cert_chain(materials[1], materials[2])
                client_context = ssl.create_default_context(cafile=str(materials[3]))
                client_socket, server_socket = socket.socketpair()
                handshake_errors = []

                def accept_tls():
                    try:
                        with server_context.wrap_socket(server_socket, server_side=True):
                            pass
                    except (OSError, ssl.SSLError) as error:
                        handshake_errors.append(error)

                server_thread = threading.Thread(target=accept_tls)
                server_thread.start()
                try:
                    with client_context.wrap_socket(client_socket, server_hostname="jupyterhub"):
                        pass
                finally:
                    client_socket.close()
                    server_socket.close()
                    server_thread.join(timeout=5)
                self.assertFalse(server_thread.is_alive())
                self.assertEqual(handshake_errors, [])

                materials[2].chmod(0o644)
                with self.assertRaises(RuntimeError):
                    certificates.validate(materials)
                materials[2].chmod(0o600)

                mismatched_key = root / "mismatched-key.pem"
                certificates.run(
                    "openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048",
                    "-out", str(mismatched_key)
                )
                mismatched_key.chmod(0o600)
                with self.assertRaises(RuntimeError):
                    certificates.validate((materials[0], materials[1], mismatched_key, materials[3]))

                self.assertIn('"-checkend", "86400"', (ROOT / "scripts/setup/prepare-jupyterhub-broker-certificates.py").read_text())
                materials[1].unlink()
                with self.assertRaises(RuntimeError):
                    certificates.validate(materials)

                certificates.prepare(rotate=True)
                self.assertNotEqual(materials[3].read_bytes(), first_ca)


if __name__ == "__main__":
    unittest.main()
