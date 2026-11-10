"""FAB authentication configuration for browser-based Airflow SSO."""

from __future__ import annotations

import sys
from pathlib import Path

from flask_appbuilder.security.manager import AUTH_OAUTH

CONFIG_DIR = str(Path(__file__).resolve().parent)
if CONFIG_DIR not in sys.path:
    sys.path.insert(0, CONFIG_DIR)

from airflow_oauth_security_manager import LakehouseSecurityManager  # noqa: E402


AIRFLOW_CLIENT_SECRET_FILE = Path(
    "/run/secrets/keycloak_airflow_client_secret"
)

if AIRFLOW_CLIENT_SECRET_FILE.is_symlink() or not AIRFLOW_CLIENT_SECRET_FILE.is_file():
    raise RuntimeError("The protected Airflow OIDC client secret file is unavailable.")
AIRFLOW_CLIENT_SECRET = AIRFLOW_CLIENT_SECRET_FILE.read_text(encoding="utf-8").strip()
if not AIRFLOW_CLIENT_SECRET:
    raise RuntimeError("The protected Airflow OIDC client secret file is empty.")

AUTH_TYPE = AUTH_OAUTH
AUTH_USER_REGISTRATION = True
AUTH_USER_REGISTRATION_ROLE = "Public"
AUTH_ROLES_SYNC_AT_LOGIN = True
# LakehouseSecurityManager maps Keycloak groups to these role names at sign-in
# from the data product files (apps.airflow).
AUTH_ROLES_MAPPING = {role: [role] for role in ("Admin", "User", "Viewer")}
OAUTH_PROVIDERS = [
    {
        "name": "keycloak",
        "icon": "fa-key",
        "token_key": "access_token",
        "remote_app": {
            "client_id": "airflow",
            "client_secret": AIRFLOW_CLIENT_SECRET,
            "issuer": "http://keycloak.localhost:8080/realms/lakehouse",
            "jwks_uri": "http://keycloak:8080/realms/lakehouse/protocol/openid-connect/certs",
            "id_token_signing_alg_values_supported": ["RS256"],
            "api_base_url": "http://keycloak:8080/realms/lakehouse/protocol/openid-connect/",
            "authorize_url": "http://keycloak.localhost:8080/realms/lakehouse/protocol/openid-connect/auth",
            "access_token_url": "http://keycloak:8080/realms/lakehouse/protocol/openid-connect/token",
            "client_kwargs": {"scope": "openid email profile"},
        },
    }
]
SECURITY_MANAGER_CLASS = LakehouseSecurityManager
