"""Contracts for the LDAP directory, the Keycloak federation, and the migration (FR-1, FR-2, FR-5)."""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "infra/keycloak")]

import ldap_federation as lf  # noqa: E402

DOCKERFILE = (ROOT / "infra/ldap/Dockerfile").read_text()
ENTRYPOINT = (ROOT / "infra/ldap/ldap-entrypoint.sh").read_text()
TEMPLATE = (ROOT / "infra/ldap/slapd.conf.template").read_text()
CORE = (ROOT / "compose.core.yml").read_text()
LDAP_SERVICE = CORE[CORE.index("  ldap:\n"):CORE.index("  keycloak:\n")]
MIGRATION = (ROOT / "scripts/operations/migrate-users-to-ldap.py").read_text()


def test_image_is_pinned_to_the_probed_packages():
    assert re.search(r"FROM alpine:3\.22@sha256:[0-9a-f]{64}", DOCKERFILE)
    for package in ("openldap", "openldap-back-mdb", "openldap-clients", "openldap-passwd-argon2"):
        assert f"{package}=2.6.8-r0" in DOCKERFILE


def test_ldaps_only_argon2_and_least_privilege_acls():
    assert 'exec slapd -d 0 -f "$CONF" -h "ldaps:/// ldapi:///"' in ENTRYPOINT and "ldap:///" not in ENTRYPOINT.replace("ldaps:///", "").replace("ldapi:///", "")
    assert "password-hash {ARGON2}" in TEMPLATE and "rootpw @ADMIN_HASH@" in TEMPLATE
    assert 'by dn.exact="cn=keycloak,ou=services,dc=lakehouse,dc=local" write' in TEMPLATE
    assert "by anonymous auth" in TEMPLATE and TEMPLATE.rstrip().endswith("access to * by * none")
    assert "TLSProtocolMin 3.3" in TEMPLATE


def test_secrets_come_from_files_and_are_never_arguments():
    assert "slappasswd -o module-load=argon2.so -h '{ARGON2}' -T" in ENTRYPOINT
    assert " -s " not in ENTRYPOINT and " -w " not in ENTRYPOINT
    assert "slapmodify" in ENTRYPOINT  # the bind password file stays the source of truth


def test_compose_service_has_no_host_port_and_mounts_secrets_read_only():
    assert "ports:" not in LDAP_SERVICE and "environment:" not in LDAP_SERVICE
    for mount in ("ldap-admin-password:/run/secrets/ldap_admin_password:ro", "ldap-keycloak-password:/run/secrets/ldap_keycloak_password:ro",
                  "ldap-server-key.pem:/run/certs/ldap-server-key.pem:ro", "ldap-data:/var/lib/openldap/data"):
        assert mount in LDAP_SERVICE
    keycloak = CORE[CORE.index("  keycloak:\n"):CORE.index("  polaris-db:\n")]
    assert "ldap-ca.crt:/run/certs/ldap-ca.crt:ro" in keycloak and "ldap:\n        condition: service_healthy" in keycloak
    assert "name: lakehouse-local_ldap-data" in CORE
    reset = (ROOT / "scripts/operations/reset-lakehouse.py").read_text()
    assert '"ldap-data"' in reset


def test_keycloak_trusts_the_ldap_ca():
    runtime = (ROOT / "scripts/setup/prepare-runtime.py").read_text()
    assert "truststore-paths=/run/certs/ldap-ca.crt" in runtime
    assert "prepare-ldap-certificates.py" in runtime


def test_federation_settings_are_writable_ldaps_with_password_modify():
    assert lf.MANAGED["editMode"] == "WRITABLE" and lf.MANAGED["connectionUrl"] == "ldaps://ldap:636"
    assert lf.MANAGED["usePasswordModifyExtendedOp"] == "true" and lf.MANAGED["uuidLDAPAttribute"] == "entryUUID"
    component = lf.desired_component("realm-id", "bind-secret")
    assert component["config"]["bindCredential"] == ["bind-secret"] and component["parentId"] == "realm-id"


def test_federation_plan_creates_accepts_updates_and_refuses_conflicts():
    assert lf.plan(None) == ("create", [])
    equal = {"config": {key: [value] for key, value in lf.MANAGED.items()}}
    assert lf.plan(equal) == ("equal", [])
    drift = {"config": {**equal["config"], "connectionUrl": ["ldap://old:389"]}}
    assert lf.plan(drift) == ("update", ["connectionUrl"])
    conflict = {"config": {**equal["config"], "usersDn": ["ou=staff,dc=x"]}}
    with pytest.raises(lf.LdapFederationError, match="usersDn"):
        lf.plan(conflict)


def test_realm_bootstrap_ensures_federation_before_groups_and_users():
    source = (ROOT / "infra/keycloak/bootstrap-realm.py").read_text()
    federation = source.index("ldap_federation.ensure_and_test(")
    assert federation < source.index("keycloak_products.apply_product(") < source.index("create_missing_bootstrap_user(api, user")
    assert "starrocks_login_client_configuration" not in source and "ensure_audience_mapper" not in source


def test_migration_deletes_a_local_user_only_after_its_ldap_password_is_verified():
    body = MIGRATION[MIGRATION.index("for user in chosen:\n                    person"):]
    assert body.index("ldap.verify_bind(person)") < body.index("save_pending(pending)") < body.index('api.request("DELETE"')
    assert "--dry-run" in MIGRATION and "backup(users)" in MIGRATION and "pg_dump" in MIGRATION


def test_migration_never_passes_passwords_as_arguments():
    ldap_commands = re.findall(r"ldap\w+ [^\n]*", MIGRATION)
    assert ldap_commands and all(" -w " not in command for command in ldap_commands)
    assert "-y {WORK}/bind" in MIGRATION and "-T {WORK}/user" in MIGRATION
    assert "allow_abbrev=False" in MIGRATION


def test_migration_resumes_users_interrupted_after_deletion():
    assert "PENDING = ROOT / \".runtime/state/ldap-migration.json\"" in MIGRATION
    assert MIGRATION.index("for username, item in sorted(pending.items())") < MIGRATION.index("preflight(api, chosen, bind_password)")
