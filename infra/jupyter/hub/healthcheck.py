"""Probe the browser Hub and the internal broker with certificate validation."""

import os
import socket
import ssl
from urllib.request import urlopen


with urlopen("http://127.0.0.1:8000/hub/health", timeout=3) as response:
    if response.status != 200:
        raise SystemExit(1)

context = ssl.create_default_context(cafile="/run/certs/jupyterhub-broker-ca.crt")
address = os.environ["JUPYTERHUB_BROKER_BIND_IP"]
port = int(os.environ.get("JUPYTERHUB_BROKER_PORT", "8443"))
with socket.create_connection((address, port), timeout=3) as raw_socket:
    with context.wrap_socket(raw_socket, server_hostname="jupyterhub") as tls_socket:
        tls_socket.sendall(
            b"GET /healthz HTTP/1.1\r\nHost: jupyterhub\r\nConnection: close\r\n\r\n"
        )
        status = tls_socket.recv(128).split(b"\r\n", 1)[0]
        if b" 200 " not in status:
            raise SystemExit(1)
