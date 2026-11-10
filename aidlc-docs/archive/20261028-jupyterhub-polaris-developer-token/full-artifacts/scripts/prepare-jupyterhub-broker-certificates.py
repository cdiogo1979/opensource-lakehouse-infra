#!/usr/bin/env python3
"""Prepare or explicitly rotate the internal Hub broker CA and server cert."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS = ROOT / ".runtime/credentials"
MOUNTS = ROOT / ".runtime/container-mounts"
CA_KEY = CREDENTIALS / "jupyterhub-broker-ca-key.pem"
SERVER_CERT = CREDENTIALS / "jupyterhub-broker-server.crt"
SERVER_KEY = CREDENTIALS / "jupyterhub-broker-server-key.pem"
CA_CERT = MOUNTS / "jupyterhub-broker-ca.crt"
MATERIALS = (CA_KEY, SERVER_CERT, SERVER_KEY, CA_CERT)


def run(*args: str, capture: bool = False) -> str:
    try:
        result = subprocess.run(
            list(args), check=True, text=True, capture_output=True, timeout=30
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("Certificate tooling failed; no key material was displayed.") from error
    return result.stdout if capture else ""


def validate(paths: tuple[Path, ...] | None = None) -> None:
    paths = MATERIALS if paths is None else paths
    ca_key, server_cert, server_key, ca_cert = paths
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"Certificate material is missing or unsafe: {path.name}")
    if ca_key.stat().st_mode & 0o077 or server_key.stat().st_mode & 0o077:
        raise RuntimeError("Private certificate key permissions must be 0600.")
    if ca_cert.stat().st_mode & 0o022 or server_cert.stat().st_mode & 0o022:
        raise RuntimeError("Certificate files must not be group/world writable.")
    run("openssl", "verify", "-CAfile", str(ca_cert), str(server_cert))
    run("openssl", "x509", "-in", str(server_cert), "-checkend", "86400")
    description = run("openssl", "x509", "-in", str(server_cert), "-noout", "-ext", "subjectAltName", capture=True)
    if "DNS:jupyterhub" not in description:
        raise RuntimeError("The Hub server certificate must include DNS:jupyterhub SAN.")
    ca_constraints = run("openssl", "x509", "-in", str(ca_cert), "-noout", "-ext", "basicConstraints", capture=True)
    if "CA:TRUE" not in ca_constraints:
        raise RuntimeError("The broker trust certificate is not a certificate authority.")
    for path in (server_cert, ca_cert):
        authority_key_id = run(
            "openssl", "x509", "-in", str(path), "-noout", "-ext", "authorityKeyIdentifier", capture=True
        )
        if "Authority Key Identifier" not in authority_key_id or "No extensions" in authority_key_id:
            raise RuntimeError("Broker certificates must include an Authority Key Identifier.")
    cert_public = run("openssl", "x509", "-in", str(server_cert), "-pubkey", "-noout", capture=True)
    key_public = run("openssl", "pkey", "-in", str(server_key), "-pubout", capture=True)
    if cert_public.strip() != key_public.strip():
        raise RuntimeError("The Hub server certificate and private key do not match.")
    ca_public = run("openssl", "x509", "-in", str(ca_cert), "-pubkey", "-noout", capture=True)
    ca_key_public = run("openssl", "pkey", "-in", str(ca_key), "-pubout", capture=True)
    if ca_public.strip() != ca_key_public.strip():
        raise RuntimeError("The broker CA certificate and signing key do not match.")
    run("openssl", "pkey", "-in", str(ca_key), "-check", "-noout")


def prepare(*, rotate: bool = False) -> None:
    CREDENTIALS.mkdir(mode=0o700, parents=True, exist_ok=True)
    MOUNTS.mkdir(mode=0o700, parents=True, exist_ok=True)
    for directory in (CREDENTIALS, MOUNTS):
        if directory.is_symlink() or not directory.is_dir():
            raise RuntimeError("Protected runtime directory is unavailable.")
        directory.chmod(0o700)
    existing = [path.exists() or path.is_symlink() for path in MATERIALS]
    if any(existing) and not all(existing) and not rotate:
        raise RuntimeError("Broker certificate set is incomplete; use explicit --rotate after review.")
    if all(existing) and not rotate:
        validate()
        print("JupyterHub broker certificates are valid (values omitted).")
        return
    openssl = shutil.which("openssl")
    if not openssl:
        raise RuntimeError("OpenSSL is required to prepare broker certificates.")
    with tempfile.TemporaryDirectory(prefix="jupyterhub-broker-", dir=CREDENTIALS) as temporary:
        staging = Path(temporary)
        ca_key, ca_cert = staging / "ca-key.pem", staging / "ca.crt"
        server_key, server_csr = staging / "server-key.pem", staging / "server.csr"
        server_cert = staging / "server.crt"
        extensions = staging / "server.ext"
        extensions.write_text(
            "basicConstraints=critical,CA:FALSE\n"
            "subjectKeyIdentifier=hash\n"
            "authorityKeyIdentifier=keyid,issuer\n"
            "subjectAltName=DNS:jupyterhub\n"
            "extendedKeyUsage=serverAuth\n"
            "keyUsage=digitalSignature,keyEncipherment\n",
            encoding="ascii",
        )
        extensions.chmod(0o600)
        run(openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072", "-out", str(ca_key))
        run(
            openssl,
            "req",
            "-x509",
            "-new",
            "-key",
            str(ca_key),
            "-sha256",
            "-days",
            "1825",
            "-subj",
            "/CN=Lakehouse JupyterHub Broker CA",
            "-addext",
            "basicConstraints=critical,CA:TRUE",
            "-addext",
            "keyUsage=critical,keyCertSign,cRLSign",
            "-addext",
            "subjectKeyIdentifier=hash",
            "-addext",
            "authorityKeyIdentifier=keyid:always",
            "-out",
            str(ca_cert),
        )
        run(openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(server_key))
        run(openssl, "req", "-new", "-key", str(server_key), "-subj", "/CN=jupyterhub", "-out", str(server_csr))
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
    print("JupyterHub broker certificate set prepared (private key values omitted).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rotate", action="store_true", help="Replace the CA and server identity intentionally.")
    args = parser.parse_args()
    prepare(rotate=args.rotate)


if __name__ == "__main__":
    main()
