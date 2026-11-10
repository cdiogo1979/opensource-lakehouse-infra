#!/usr/bin/env python3
"""Move the lakehouse realm's local Keycloak users into the LDAP directory, once.

  scripts/operations/migrate-users-to-ldap.py --dry-run     print the plan, change nothing
  scripts/operations/migrate-users-to-ldap.py               prompt for "migrate", then run
  scripts/operations/migrate-users-to-ldap.py --yes         no prompt

Users created before the LDAP federation live in Keycloak's own database, and
their passwords cannot be copied (one-way hashes). Each user is recreated in LDAP
with a known password: bootstrap users with the documented default, product
writer users from their password file, anyone else with the default (named in
the report). Per user: write the LDAP entry, set and verify the password, then
delete the local copy, let Keycloak import the LDAP user (it gets a new ID),
restore groups and profile, and copy the Jupyter home to the volume of the new
ID. The old volume and the old Hub user are deleted after the copy is verified.
A rerun continues where it stopped. The Keycloak database is backed up first.
Passwords never appear in arguments or output.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "infra/keycloak"), str(ROOT / "infra/products")]
import data_products  # noqa: E402
import keycloak_products  # noqa: E402
import ldap_federation  # noqa: E402
import ldap_people as lp  # noqa: E402

SPEC = importlib.util.spec_from_file_location("bootstrap_realm", ROOT / "infra/keycloak/bootstrap-realm.py")
realm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(realm)

CREDENTIALS = ROOT / ".runtime/credentials"
# Each user's original record is saved here before its local copy is deleted, so
# a run that stops between deletion and restore finishes that user next time.
PENDING = ROOT / ".runtime/state/ldap-migration.json"
LDAP_CONTAINER = "lakehouse-local-ldap-1"
KEYCLOAK_DB_CONTAINER = "lakehouse-local-keycloak-db-1"
HUB_URL = f"http://127.0.0.1:{os.environ.get('JUPYTERHUB_HOST_PORT', '8000')}/hub/api"
COPY_IMAGE = "alpine:3.22@sha256:49340b346798875b5592e5d420241f2f9cfba5f47e62ebb1446a1b34734e898f"
WORK = "/tmp/lakehouse-migrate"  # inside the ldap container, mode 0700
LDAP_URL = "ldaps://ldap:636"
REALM = "lakehouse"


def log(message: str) -> None:
    print(message, flush=True)


def home_volume(subject: str) -> str:
    """The JupyterHub home volume of a Keycloak ID (as lakehouse_policy.persistent_home_volume)."""
    return f"lakehouse-jupyter-home-{hashlib.sha256(subject.encode('utf-8')).hexdigest()[:32]}"


def docker(*args: str, stdin: str | None = None, env: dict | None = None, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(["docker", *args], input=stdin, capture_output=True, text=True, timeout=300,
                            env={**os.environ, **(env or {})})
    if check and result.returncode:
        raise lp.MigrationError(f"docker {args[0]} failed (exit {result.returncode}).")
    return result


# ---- LDAP through the ldap container (LDAPS as cn=keycloak; secrets as files) ----

class Ldap:
    def __init__(self, bind_password: str) -> None:
        self.put("bind", bind_password)

    def put(self, name: str, content: str) -> None:
        docker("exec", "-i", LDAP_CONTAINER, "sh", "-c", f'umask 077; mkdir -p {WORK}; cat > {WORK}/{name}', stdin=content)

    def run(self, command: str, check: bool = False) -> subprocess.CompletedProcess:
        return docker("exec", "-e", "LDAPTLS_CACERT=/run/certs/ldap-ca.crt", LDAP_CONTAINER, "sh", "-c", command, check=check)

    def exists(self, person: lp.LdapPerson) -> bool:
        result = self.run(f'ldapsearch -LLL -x -H {LDAP_URL} -D "{ldap_federation.BIND_DN}" -y {WORK}/bind '
                          f'-s base -b "{person.dn}" dn')
        return result.returncode == 0 and "dn:" in result.stdout

    def write_entry(self, person: lp.LdapPerson) -> str:
        if self.exists(person):
            return "present"
        self.put("entry.ldif", lp.render_entry(person))
        result = self.run(f'ldapadd -x -H {LDAP_URL} -D "{ldap_federation.BIND_DN}" -y {WORK}/bind -f {WORK}/entry.ldif')
        if result.returncode not in (0, 68):  # 68: already exists
            raise lp.MigrationError(f"Writing the LDAP entry of {person.uid} failed (ldap {result.returncode}).")
        return "written"

    def set_password(self, person: lp.LdapPerson, password: str) -> None:
        self.put("user", password)
        result = self.run(f'ldappasswd -x -H {LDAP_URL} -D "{ldap_federation.BIND_DN}" -y {WORK}/bind -T {WORK}/user "{person.dn}"')
        if result.returncode:
            raise lp.MigrationError(f"Setting the LDAP password of {person.uid} failed (ldap {result.returncode}).")

    def verify_bind(self, person: lp.LdapPerson) -> bool:
        return self.run(f'ldapwhoami -x -H {LDAP_URL} -D "{person.dn}" -y {WORK}/user').returncode == 0

    def close(self) -> None:
        self.run(f"rm -rf {WORK}")


# ---- Keycloak ----

def inventory(api) -> list[lp.LocalUser]:
    users, first = [], 0
    while True:
        status, page = api.request("GET", f"/admin/realms/{REALM}/users", query={"first": first, "max": 200, "briefRepresentation": "false"})
        realm.checked(status, (200,), "List users")
        for item in page or []:
            status, groups = api.request("GET", f"/admin/realms/{REALM}/users/{item['id']}/groups")
            realm.checked(status, (200,), "List user groups")
            users.append(lp.LocalUser(
                id=item["id"], username=item["username"], enabled=bool(item.get("enabled")),
                email_verified=bool(item.get("emailVerified")), first_name=item.get("firstName") or "",
                last_name=item.get("lastName") or "", email=item.get("email") or "",
                groups=tuple(sorted(group["name"] for group in groups or [])), federated=bool(item.get("federationLink")),
            ))
        if len(page or []) < 200:
            return users
        first += 200


def passwords() -> tuple[set[str], dict[str, str], str]:
    """Bootstrap usernames, writer username -> password file contents, and the default password."""
    identities = json.loads((ROOT / "infra/keycloak/bootstrap-users.json").read_text(encoding="utf-8"))
    writers: dict[str, str] = {}
    for product in data_products.load_all():
        path = ROOT / product.writer_user.password_file
        if path.is_file() and not path.is_symlink():
            lines = path.read_text(encoding="utf-8").splitlines()
            if lines and lines[0]:
                writers[product.writer_user.username] = lines[0]
    return {u["username"] for u in identities["users"]}, writers, identities["default_password"]


def import_user(api, username: str) -> dict:
    """Look the user up again: Keycloak finds it in LDAP and imports it (new ID)."""
    status, found = api.request("GET", f"/admin/realms/{REALM}/users", query={"username": username, "exact": "true"})
    realm.checked(status, (200,), f"Import {username}")
    matches = [item for item in found or [] if item.get("username") == username]
    if len(matches) != 1 or not matches[0].get("federationLink"):
        raise lp.MigrationError(f"Keycloak did not import {username} from LDAP; its LDAP entry is in place and the run can be repeated.")
    return matches[0]


def restore(api, new: dict, user: lp.LocalUser) -> None:
    body = {
        "enabled": user.enabled, "emailVerified": user.email_verified, "requiredActions": [],
        "firstName": user.first_name, "lastName": user.last_name, "email": user.email or None,
    }
    status, _ = api.request("PUT", f"/admin/realms/{REALM}/users/{new['id']}", {k: v for k, v in body.items() if v is not None})
    realm.checked(status, (204,), f"Restore profile of {user.username}")
    for name in user.groups:
        group = keycloak_products.find_group(api, name)
        if group is None:
            raise lp.MigrationError(f"Group {name} of {user.username} no longer exists.")
        status, _ = api.request("PUT", f"/admin/realms/{REALM}/users/{new['id']}/groups/{group['id']}")
        realm.checked(status, (204,), f"Restore group {name} of {user.username}")


# ---- Jupyter homes ----

def volume_exists(name: str) -> bool:
    return docker("volume", "inspect", name, check=False).returncode == 0


def volume_stats(name: str) -> tuple[int, int]:
    result = docker("run", "--rm", "-v", f"{name}:/v:ro", COPY_IMAGE, "sh", "-c",
                    "find /v -type f | wc -l; find /v -type f -exec stat -c %s {} + | awk '{s+=$1} END {print s+0}'")
    files, size = result.stdout.split()[:2]
    return int(files), int(size)


def copy_home(old_id: str, new_id: str, hub_token: str | None, dry_run: bool) -> str:
    old, new = home_volume(old_id), home_volume(new_id)
    if not volume_exists(old):
        return "no old home"
    if dry_run:
        return f"would copy {old} -> {new}"
    docker("volume", "create", new)
    docker("run", "--rm", "-v", f"{old}:/from:ro", "-v", f"{new}:/to", COPY_IMAGE, "sh", "-c", "cp -a /from/. /to/")
    if volume_stats(old) != volume_stats(new):
        raise lp.MigrationError(f"The copied Jupyter home of {new_id} does not match the original; both volumes are kept.")
    docker("volume", "rm", old)
    hub = delete_hub_user(old_id, hub_token)
    return f"home copied and verified; old volume deleted; old Hub user {hub}"


def delete_hub_user(name: str, token: str | None) -> str:
    if token is None:
        return "left (JupyterHub token unavailable)"
    request = urllib.request.Request(f"{HUB_URL}/users/{urllib.parse.quote(name, safe='')}", method="DELETE",
                                     headers={"Authorization": f"token {token}"})
    try:
        with urllib.request.urlopen(request, timeout=20):
            return "deleted"
    except urllib.error.HTTPError as error:
        return "absent" if error.code == 404 else f"left (HTTP {error.code})"
    except (urllib.error.URLError, OSError):
        return "left (JupyterHub not reachable)"


# ---- pending records (resume after an interruption) ----

def load_pending() -> dict[str, dict]:
    if not PENDING.exists():
        return {}
    if PENDING.is_symlink() or not PENDING.is_file():
        raise lp.MigrationError("The migration state file is not a regular file.")
    return json.loads(PENDING.read_text(encoding="utf-8"))


def save_pending(pending: dict[str, dict]) -> None:
    PENDING.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = PENDING.with_name(PENDING.name + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(pending, stream, indent=1, sort_keys=True)
    os.replace(temporary, PENDING)


def record(user: lp.LocalUser) -> dict:
    return {"id": user.id, "username": user.username, "enabled": user.enabled, "email_verified": user.email_verified,
            "first_name": user.first_name, "last_name": user.last_name, "email": user.email, "groups": list(user.groups)}


def from_record(item: dict) -> lp.LocalUser:
    return lp.LocalUser(**{**item, "groups": tuple(item["groups"])})


def finish(api, user: lp.LocalUser, hub_token: str | None, pending: dict[str, dict]) -> str:
    """Import, restore, and move the home of a user whose local copy is deleted."""
    new = import_user(api, user.username)
    restore(api, new, user)
    home = copy_home(user.id, new["id"], hub_token, dry_run=False)
    pending.pop(user.username, None)
    save_pending(pending)
    return home


# ---- run ----

def preflight(api, chosen: list[lp.LocalUser], bind_password: str) -> None:
    health = docker("inspect", "-f", "{{.State.Health.Status}}", LDAP_CONTAINER, check=False).stdout.strip()
    if health != "healthy":
        raise lp.MigrationError("The ldap service is not healthy; start the stack first.")
    ldap_federation.test_connection(api, bind_password)
    for user in chosen:
        volume = home_volume(user.id)
        if docker("ps", "-q", "--filter", f"volume={volume}", check=False).stdout.strip():
            raise lp.MigrationError(f"{user.username} has a running Jupyter server; stop it first (Hub admin page).")


def backup(users: list[lp.LocalUser]) -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = ROOT / ".runtime/backups" / f"{stamp}-pre-ldap"
    target.mkdir(parents=True, mode=0o700)
    dump = docker("exec", KEYCLOAK_DB_CONTAINER, "pg_dump", "-U", "keycloak", "keycloak")
    descriptor = os.open(target / "keycloak.sql", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(dump.stdout)
    inventory_file = target / "users.json"
    inventory_file.write_text(json.dumps([{"username": u.username, "id": u.id, "groups": list(u.groups), "enabled": u.enabled} for u in users], indent=1))
    inventory_file.chmod(0o600)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)
    try:
        api = realm.KeycloakAdmin("http://127.0.0.1:8080", os.environ.get("KEYCLOAK_ADMIN_USERNAME", "admin"),
                                  realm.read_secret(CREDENTIALS / "keycloak-admin-password"))
        api.login()
        bind_password = realm.read_secret(CREDENTIALS / "ldap-keycloak-password")
        users = inventory(api)
        pending = load_pending()
        chosen, refused = lp.eligible(users)
        chosen = [user for user in chosen if user.username not in pending]
        bootstrap_users, writers, default_password = passwords()
        sources = {u.username: lp.password_source(u.username, bootstrap_users, {k: True for k in writers}) for u in chosen}
        log(f"Local users to migrate: {len(chosen)}; already in LDAP: {sum(u.federated for u in users)}; "
            f"interrupted and pending: {', '.join(sorted(pending)) or 'none'}; refused (invalid uid): {refused or 'none'}.")
        for user in chosen:
            log(f"  {user.username}: password from {sources[user.username]}; groups {', '.join(user.groups) or 'none'}; "
                f"{'enabled' if user.enabled else 'disabled'}; home {'present' if volume_exists(home_volume(user.id)) else 'none'}")
        if not chosen and not pending:
            log("Nothing to migrate.")
        if args.dry_run:
            log("Dry run: nothing was changed.")
            return 0
        token_path = CREDENTIALS / "jupyterhub-maintenance-token"
        hub_token = realm.read_secret(token_path) if token_path.is_file() else None
        for username, item in sorted(pending.items()):
            log(f"  {username}: finishing an interrupted migration; {finish(api, from_record(item), hub_token, pending)}.")
        if chosen:
            preflight(api, chosen, bind_password)
            if not args.yes:
                if not sys.stdin.isatty():
                    raise lp.MigrationError("Confirmation needed: run interactively or pass --yes.")
                if input('Type "migrate" to continue: ').strip() != "migrate":
                    log("Not confirmed; nothing was changed.")
                    return 1
            log(f"Backup of the Keycloak database and the inventory: {backup(users).relative_to(ROOT)}")
            ldap = Ldap(bind_password)
            try:
                for user in chosen:
                    person = lp.person_for(user)
                    source = sources[user.username]
                    password = default_password if source in ("bootstrap", "default") else writers[user.username]
                    state = ldap.write_entry(person)
                    ldap.set_password(person, password)
                    if not ldap.verify_bind(person):
                        raise lp.MigrationError(f"The LDAP password of {user.username} could not be verified; its Keycloak user is untouched.")
                    pending[user.username] = record(user)
                    save_pending(pending)
                    status, _ = api.request("DELETE", f"/admin/realms/{REALM}/users/{user.id}")
                    realm.checked(status, (204,), f"Delete local copy of {user.username}")
                    home = finish(api, user, hub_token, pending)
                    log(f"  {user.username}: LDAP entry {state}, password from {source}, imported, restored; {home}.")
            finally:
                ldap.close()
        client = realm.find_client(api, "starrocks")
        if client is not None:
            status, _ = api.request("DELETE", f"/admin/realms/{REALM}/clients/{client['id']}")
            realm.checked(status, (204,), "Delete the starrocks token client")
            log("Removed the retired Keycloak client 'starrocks'.")
        for command in (["infra/polaris/reconcile-keycloak-groups.py"], ["infra/starrocks/reconcile-starrocks-users.py", "--transport", "docker"]):
            result = subprocess.run([sys.executable, *command], cwd=ROOT, check=False)
            if result.returncode:
                raise lp.MigrationError(f"{command[0]} failed after the migration; rerun it once the cause is fixed.")
        reset = [u for u in chosen if sources[u.username] == lp.DEFAULT_PASSWORD_SOURCE]
        log(f"Migration completed. Users whose password is now the default: {', '.join(u.username for u in reset) or 'none'}.")
        return 0
    except (lp.MigrationError, realm.BootstrapError, ldap_federation.LdapFederationError,
            keycloak_products.KeycloakProductError, data_products.ProductError) as error:
        print(f"Migration stopped: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
