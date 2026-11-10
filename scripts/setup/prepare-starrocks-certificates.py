#!/usr/bin/env python3
"""Create or validate the local StarRocks SQL TLS material.

The MySQL OpenID Connect client plugin only sends a Keycloak token over TLS, so
the StarRocks FE serves its MySQL port with a certificate from a local CA. The
FE reads a PKCS12 keystore; clients verify the server with the public CA file.
"""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CREDENTIALS = ROOT / ".runtime/credentials"
MOUNTS = ROOT / ".runtime/container-mounts"
CA_KEY = CREDENTIALS / "starrocks-ca-key.pem"
SERVER_CERT = CREDENTIALS / "starrocks-server.crt"
SERVER_KEY = CREDENTIALS / "starrocks-server-key.pem"
KEYSTORE_PASSWORD = CREDENTIALS / "starrocks-keystore-password"
CA_CERT = MOUNTS / "starrocks-ca.crt"
KEYSTORE = MOUNTS / "starrocks-fe-keystore.p12"
KEYSTORE_PASSWORD_MOUNT = MOUNTS / "starrocks-keystore-password"
MATERIALS = (CA_KEY, SERVER_CERT, SERVER_KEY, KEYSTORE_PASSWORD, CA_CERT, KEYSTORE)
SAN = "DNS:starrocks-fe,DNS:localhost,IP:127.0.0.1"


def run(*args: str, capture: bool = False) -> str:
    try:
        result = subprocess.run(list(args), check=True, text=True, capture_output=True, timeout=30)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("Certificate tooling failed; no key material was displayed.") from error
    return result.stdout if capture else ""


def validate() -> None:
    for path in MATERIALS:
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"StarRocks TLS material is missing or unsafe: {path.name}")
    for path in (CA_KEY, SERVER_KEY, KEYSTORE_PASSWORD):
        if path.stat().st_mode & 0o077:
            raise RuntimeError("StarRocks private key and keystore password permissions must be 0600.")
    run("openssl", "verify", "-CAfile", str(CA_CERT), str(SERVER_CERT))
    san = run("openssl", "x509", "-in", str(SERVER_CERT), "-noout", "-ext", "subjectAltName", capture=True)
    if "DNS:starrocks-fe" not in san:
        raise RuntimeError("The StarRocks certificate must include its Compose DNS SAN.")
    run("openssl", "x509", "-in", str(SERVER_CERT), "-checkend", "86400")
    run("openssl", "pkcs12", "-in", str(KEYSTORE), "-noout", "-passin", f"file:{KEYSTORE_PASSWORD}")


def stage_password_mount() -> None:
    """Copy the keystore password beside the keystore for the FE entrypoint (host-private parent)."""
    descriptor, temporary = tempfile.mkstemp(prefix=".starrocks-keystore-password.", dir=MOUNTS)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(KEYSTORE_PASSWORD.read_bytes())
    os.chmod(temporary, 0o644)
    os.replace(temporary, KEYSTORE_PASSWORD_MOUNT)


def prepare() -> None:
    for directory in (CREDENTIALS, MOUNTS):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.is_symlink() or not directory.is_dir():
            raise RuntimeError("Protected runtime directory is unavailable.")
        directory.chmod(0o700)
    existing = [path.exists() or path.is_symlink() for path in MATERIALS]
    if any(existing):
        if not all(existing):
            raise RuntimeError("StarRocks TLS material is incomplete; refusing automatic replacement.")
        validate()
        stage_password_mount()
        print("StarRocks TLS certificates are valid (values omitted).")
        return
    openssl = shutil.which("openssl")
    if openssl is None:
        raise RuntimeError("OpenSSL is required to prepare the StarRocks TLS certificates.")
    with tempfile.TemporaryDirectory(prefix="starrocks-tls-", dir=CREDENTIALS) as temporary:
        stage = Path(temporary)
        ca_key, ca_cert = stage / "ca-key.pem", stage / "ca.crt"
        server_key, server_csr, server_cert = stage / "server-key.pem", stage / "server.csr", stage / "server.crt"
        password, keystore, extensions = stage / "password", stage / "keystore.p12", stage / "server.ext"
        password.write_text(secrets.token_hex(24) + "\n", encoding="ascii")
        password.chmod(0o600)
        extensions.write_text(
            "basicConstraints=critical,CA:FALSE\n"
            "subjectKeyIdentifier=hash\n"
            "authorityKeyIdentifier=keyid,issuer\n"
            f"subjectAltName={SAN}\n"
            "extendedKeyUsage=serverAuth\n"
            "keyUsage=digitalSignature,keyEncipherment\n",
            encoding="ascii",
        )
        run(openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072", "-out", str(ca_key))
        run(openssl, "req", "-x509", "-new", "-key", str(ca_key), "-sha256", "-days", "1825", "-subj", "/CN=Lakehouse StarRocks CA", "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign,cRLSign", "-addext", "subjectKeyIdentifier=hash", "-out", str(ca_cert))
        run(openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(server_key))
        run(openssl, "req", "-new", "-key", str(server_key), "-subj", "/CN=starrocks-fe", "-out", str(server_csr))
        run(openssl, "x509", "-req", "-in", str(server_csr), "-CA", str(ca_cert), "-CAkey", str(ca_key), "-CAcreateserial", "-out", str(server_cert), "-days", "397", "-sha256", "-extfile", str(extensions))
        run(openssl, "pkcs12", "-export", "-inkey", str(server_key), "-in", str(server_cert), "-certfile", str(ca_cert), "-name", "starrocks-fe", "-passout", f"file:{password}", "-out", str(keystore))
        targets = {ca_key: CA_KEY, server_cert: SERVER_CERT, server_key: SERVER_KEY, password: KEYSTORE_PASSWORD, ca_cert: CA_CERT, keystore: KEYSTORE}
        for source, target in targets.items():
            os.replace(source, target)
            target.chmod(0o600 if target in (CA_KEY, SERVER_KEY, KEYSTORE_PASSWORD) else 0o644)
    validate()
    stage_password_mount()
    print("StarRocks TLS certificate set prepared (private key values omitted).")


if __name__ == "__main__":
    prepare()
