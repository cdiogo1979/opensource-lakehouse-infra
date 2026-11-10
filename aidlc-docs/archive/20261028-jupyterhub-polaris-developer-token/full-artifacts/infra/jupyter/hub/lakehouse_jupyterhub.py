"""JupyterHub entry point that owns the in-process broker TLS listener."""

from __future__ import annotations

import os

from jupyterhub.app import JupyterHub
from tornado.httpserver import HTTPServer

from lakehouse_token_broker import LakehouseTokenBroker, broker_application, broker_ssl_context


class LakehouseJupyterHub(JupyterHub):
    """Run the internal token broker on the same event loop/process as Hub."""

    async def start(self):
        await super().start()
        bind_address = os.environ["JUPYTERHUB_BROKER_BIND_IP"]
        bind_port = int(os.environ.get("JUPYTERHUB_BROKER_PORT", "8443"))
        cert_path = "/run/certs/jupyterhub-broker-server.crt"
        key_path = "/run/certs/jupyterhub-broker-server-key.pem"
        ca_path = "/run/certs/jupyterhub-broker-ca.crt"
        for path in (cert_path, key_path, ca_path):
            if os.path.islink(path) or not os.path.isfile(path):
                raise RuntimeError("JupyterHub broker TLS material is missing or unsafe.")
        broker = LakehouseTokenBroker(self)
        self._lakehouse_token_broker = broker
        self._lakehouse_broker_server = HTTPServer(
            broker_application(broker),
            ssl_options=broker_ssl_context(cert_path, key_path),
            max_body_size=2048,
            idle_connection_timeout=10,
            xheaders=False,
        )
        self._lakehouse_broker_server.listen(bind_port, address=bind_address)
        self.log.info("Internal token broker listening on configured user-network address.")

    async def cleanup(self):
        server = getattr(self, "_lakehouse_broker_server", None)
        if server is not None:
            server.stop()
            await server.close_all_connections()
        await super().cleanup()


if __name__ == "__main__":
    LakehouseJupyterHub.launch_instance()
