#!/usr/bin/env python3
"""Create or validate the local Airflow token-broker CA and server certificate."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CREDENTIALS = ROOT / ".runtime/credentials"
MOUNTS = ROOT / ".runtime/container-mounts"
CA_KEY = CREDENTIALS / "airflow-token-broker-ca-key.pem"
SERVER_CERT = CREDENTIALS / "airflow-token-broker-server.crt"
SERVER_KEY = CREDENTIALS / "airflow-token-broker-server-key.pem"
CA_CERT = MOUNTS / "airflow-token-broker-ca.crt"
MATERIALS = (CA_KEY, SERVER_CERT, SERVER_KEY, CA_CERT)


def run(*args: str, capture: bool = False) -> str:
    try:
        result = subprocess.run(list(args), check=True, text=True, capture_output=True, timeout=30)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("Certificate tooling failed; no key material was displayed.") from error
    return result.stdout if capture else ""


def validate(paths: tuple[Path, ...] = MATERIALS) -> None:
    ca_key, server_cert, server_key, ca_cert = paths
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"Certificate material is missing or unsafe: {path.name}")
    if ca_key.stat().st_mode & 0o077 or server_key.stat().st_mode & 0o077:
        raise RuntimeError("Private certificate key permissions must be 0600.")
    run("openssl", "verify", "-CAfile", str(ca_cert), str(server_cert))
    san = run("openssl", "x509", "-in", str(server_cert), "-noout", "-ext", "subjectAltName", capture=True)
    if "DNS:airflow-token-broker" not in san:
        raise RuntimeError("The Airflow broker certificate must include its Compose DNS SAN.")
    cert_public = run("openssl", "x509", "-in", str(server_cert), "-pubkey", "-noout", capture=True)
    key_public = run("openssl", "pkey", "-in", str(server_key), "-pubout", capture=True)
    if cert_public.strip() != key_public.strip():
        raise RuntimeError("The Airflow broker certificate and private key do not match.")
    run("openssl", "x509", "-in", str(server_cert), "-checkend", "86400")


def prepare() -> None:
    for directory in (CREDENTIALS, MOUNTS):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.is_symlink() or not directory.is_dir():
            raise RuntimeError("Protected runtime directory is unavailable.")
        directory.chmod(0o700)
    existing = [path.exists() or path.is_symlink() for path in MATERIALS]
    if any(existing):
        if not all(existing):
            raise RuntimeError("Airflow broker certificate set is incomplete; refusing automatic replacement.")
        validate()
        print("Airflow token-broker certificates are valid (values omitted).")
        return
    openssl = shutil.which("openssl")
    if openssl is None:
        raise RuntimeError("OpenSSL is required to prepare the Airflow token-broker certificates.")
    with tempfile.TemporaryDirectory(prefix="airflow-broker-", dir=CREDENTIALS) as temporary:
        stage = Path(temporary)
        ca_key, ca_cert = stage / "ca-key.pem", stage / "ca.crt"
        server_key, server_csr, server_cert = stage / "server-key.pem", stage / "server.csr", stage / "server.crt"
        extensions = stage / "server.ext"
        extensions.write_text(
            "basicConstraints=critical,CA:FALSE\n"
            "subjectKeyIdentifier=hash\n"
            "authorityKeyIdentifier=keyid,issuer\n"
            "subjectAltName=DNS:airflow-token-broker\n"
            "extendedKeyUsage=serverAuth\n"
            "keyUsage=digitalSignature,keyEncipherment\n",
            encoding="ascii",
        )
        extensions.chmod(0o600)
        run(openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072", "-out", str(ca_key))
        run(openssl, "req", "-x509", "-new", "-key", str(ca_key), "-sha256", "-days", "1825", "-subj", "/CN=Lakehouse Airflow Broker CA", "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign,cRLSign", "-addext", "subjectKeyIdentifier=hash", "-out", str(ca_cert))
        run(openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(server_key))
        run(openssl, "req", "-new", "-key", str(server_key), "-subj", "/CN=airflow-token-broker", "-out", str(server_csr))
        run(openssl, "x509", "-req", "-in", str(server_csr), "-CA", str(ca_cert), "-CAkey", str(ca_key), "-CAcreateserial", "-out", str(server_cert), "-days", "397", "-sha256", "-extfile", str(extensions))
        for path in (ca_key, server_key):
            path.chmod(0o600)
        server_cert.chmod(0o644)
        ca_cert.chmod(0o644)
        validate((ca_key, server_cert, server_key, ca_cert))
        for source, target in zip((ca_key, server_cert, server_key, ca_cert), MATERIALS, strict=True):
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.replace(source, target)
            target.chmod(0o600 if target in (CA_KEY, SERVER_KEY) else 0o644)
    print("Airflow token-broker certificate set prepared (private key values omitted).")


if __name__ == "__main__":
    prepare()
