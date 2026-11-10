#!/usr/bin/env python3
"""Create or validate the local LDAP TLS material.

The directory accepts only LDAPS. Keycloak and the StarRocks FE verify its
certificate against a local CA, staged as `.runtime/container-mounts/ldap-ca.crt`.
The server key and certificate are staged read-only for the `ldap` container.
`--rotate` replaces the whole set (restart ldap, Keycloak, and StarRocks after).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CREDENTIALS = ROOT / ".runtime/credentials"
MOUNTS = ROOT / ".runtime/container-mounts"
CA_KEY = CREDENTIALS / "ldap-ca-key.pem"
SERVER_KEY = CREDENTIALS / "ldap-server-key.pem"
SERVER_CERT = CREDENTIALS / "ldap-server.crt"
CA_CERT = MOUNTS / "ldap-ca.crt"
SERVER_CERT_MOUNT = MOUNTS / "ldap-server.crt"
SERVER_KEY_MOUNT = MOUNTS / "ldap-server-key.pem"
MATERIALS = (CA_KEY, SERVER_KEY, SERVER_CERT, CA_CERT)
SAN = "DNS:ldap"


def run(*args: str, capture: bool = False) -> str:
    try:
        result = subprocess.run(list(args), check=True, text=True, capture_output=True, timeout=30)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("Certificate tooling failed; no key material was displayed.") from error
    return result.stdout if capture else ""


def validate() -> None:
    for path in MATERIALS:
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"LDAP TLS material is missing or unsafe: {path.name}")
    for path in (CA_KEY, SERVER_KEY):
        if path.stat().st_mode & 0o077:
            raise RuntimeError("LDAP private key permissions must be 0600.")
    run("openssl", "verify", "-CAfile", str(CA_CERT), str(SERVER_CERT))
    san = run("openssl", "x509", "-in", str(SERVER_CERT), "-noout", "-ext", "subjectAltName", capture=True)
    if SAN not in san:
        raise RuntimeError("The LDAP certificate must include its Compose DNS SAN.")
    run("openssl", "x509", "-in", str(SERVER_CERT), "-checkend", "86400")


def stage(source: Path, target: Path) -> None:
    """Copy into the host-private mount directory for the ldap container."""
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=MOUNTS)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(source.read_bytes())
    os.chmod(temporary, 0o644)
    os.replace(temporary, target)


def generate() -> None:
    openssl = shutil.which("openssl")
    if openssl is None:
        raise RuntimeError("OpenSSL is required to prepare the LDAP TLS certificates.")
    with tempfile.TemporaryDirectory(prefix="ldap-tls-", dir=CREDENTIALS) as temporary:
        work = Path(temporary)
        ca_key, ca_cert = work / "ca-key.pem", work / "ca.crt"
        server_key, server_csr, server_cert, extensions = work / "server-key.pem", work / "server.csr", work / "server.crt", work / "server.ext"
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
        run(openssl, "req", "-x509", "-new", "-key", str(ca_key), "-sha256", "-days", "1825", "-subj", "/CN=Lakehouse LDAP CA",
            "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign,cRLSign",
            "-addext", "subjectKeyIdentifier=hash", "-out", str(ca_cert))
        run(openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(server_key))
        run(openssl, "req", "-new", "-key", str(server_key), "-subj", "/CN=ldap", "-out", str(server_csr))
        run(openssl, "x509", "-req", "-in", str(server_csr), "-CA", str(ca_cert), "-CAkey", str(ca_key), "-CAcreateserial",
            "-out", str(server_cert), "-days", "397", "-sha256", "-extfile", str(extensions))
        for source, target in {ca_key: CA_KEY, server_key: SERVER_KEY, server_cert: SERVER_CERT, ca_cert: CA_CERT}.items():
            os.replace(source, target)
            target.chmod(0o600 if target in (CA_KEY, SERVER_KEY) else 0o644)


def prepare(rotate: bool = False) -> None:
    for directory in (CREDENTIALS, MOUNTS):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.is_symlink() or not directory.is_dir():
            raise RuntimeError("Protected runtime directory is unavailable.")
        directory.chmod(0o700)
    existing = [path.exists() or path.is_symlink() for path in MATERIALS]
    if rotate or not any(existing):
        generate()
        state = "prepared" if not rotate else "rotated"
    elif not all(existing):
        raise RuntimeError("LDAP TLS material is incomplete; refusing automatic replacement (use --rotate).")
    else:
        state = "valid"
    validate()
    stage(SERVER_CERT, SERVER_CERT_MOUNT)
    stage(SERVER_KEY, SERVER_KEY_MOUNT)
    print(f"LDAP TLS certificates are {state} (key values omitted).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rotate", action="store_true")
    prepare(parser.parse_args().rotate)
