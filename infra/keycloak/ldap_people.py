"""Pure model of the LDAP people tree and of the one-time user migration (BR-4).

No I/O: ``migrate-users-to-ldap.py`` performs the steps planned here. Entries use
Keycloak's default mappers (uid, cn = first name, sn = last name, mail) so the
users Keycloak imports look exactly like the users it creates itself.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass

SUFFIX = "dc=lakehouse,dc=local"
PEOPLE = f"ou=people,{SUFFIX}"
OBJECT_CLASSES = ("top", "person", "organizationalPerson", "inetOrgPerson")
UID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}$")
SERVICE_ACCOUNT_PREFIX = "service-account-"
DEFAULT_PASSWORD_SOURCE = "default"

# Per user, in this order; deletions only after the matching verification (P2).
STEPS = (
    "write_entry",
    "set_password",
    "verify_bind",
    "delete_local",
    "import",
    "restore",
    "copy_home",
    "verify_home",
    "delete_old_home",
    "delete_old_hub_user",
)


@dataclass(frozen=True)
class LdapPerson:
    uid: str
    cn: str
    sn: str
    mail: str | None = None

    @property
    def dn(self) -> str:
        return f"uid={self.uid},{PEOPLE}"

    def attributes(self) -> dict[str, list[str]]:
        attributes = {"objectClass": list(OBJECT_CLASSES), "uid": [self.uid], "cn": [self.cn], "sn": [self.sn]}
        if self.mail:
            attributes["mail"] = [self.mail]
        return attributes


@dataclass(frozen=True)
class LocalUser:
    id: str
    username: str
    enabled: bool = True
    email_verified: bool = False
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    groups: tuple[str, ...] = ()
    federated: bool = False


class MigrationError(Exception):
    """A refusal or failure naming the user and step; never a password."""


def valid_uid(username: str) -> bool:
    return bool(UID_PATTERN.fullmatch(username))


def person_for(user: LocalUser) -> LdapPerson:
    """The entry for a user; empty names fall back to the username (inetOrgPerson needs cn and sn)."""
    if not valid_uid(user.username):
        raise MigrationError(f"Username {user.username!r} is not a valid LDAP uid.")
    return LdapPerson(
        uid=user.username,
        cn=user.first_name.strip() or user.username,
        sn=user.last_name.strip() or user.username,
        mail=user.email.strip() or None,
    )


# ---- LDIF (RFC 2849) ----

_SAFE_INIT = re.compile(r"[\x01-\x09\x0b\x0c\x0e-\x1f\x21-\x39\x3b\x3d-\x7f]")
_SAFE_CHAR = re.compile(r"[\x01-\x09\x0b\x0c\x0e-\x7f]*")


def _safe(value: str) -> bool:
    """A SAFE-STRING that also keeps trailing spaces, which some tools strip."""
    if value == "":
        return True
    return bool(_SAFE_INIT.fullmatch(value[0]) and _SAFE_CHAR.fullmatch(value) and not value.endswith(" "))


def _line(attribute: str, value: str) -> str:
    if _safe(value):
        return f"{attribute}: {value}"
    return f"{attribute}:: {base64.b64encode(value.encode('utf-8')).decode('ascii')}"


def render_entry(person: LdapPerson) -> str:
    lines = [_line("dn", person.dn)]
    for attribute, values in person.attributes().items():
        lines += [_line(attribute, value) for value in values]
    return "\n".join(lines) + "\n"


def parse_ldif(text: str) -> tuple[str, dict[str, list[str]]]:
    """(dn, attributes) of a single LDIF entry, with folded lines and base64 values."""
    unfolded: list[str] = []
    for raw in text.splitlines():
        if raw.startswith(" ") and unfolded:
            unfolded[-1] += raw[1:]
        elif raw and not raw.startswith("#"):
            unfolded.append(raw)
    dn = None
    attributes: dict[str, list[str]] = {}
    for line in unfolded:
        name, _, rest = line.partition(":")
        if rest.startswith(":"):
            value = base64.b64decode(rest[1:].strip()).decode("utf-8")
        else:
            value = rest[1:] if rest.startswith(" ") else rest
        if name == "dn":
            dn = value
        else:
            attributes.setdefault(name, []).append(value)
    if dn is None:
        raise MigrationError("LDIF entry has no dn.")
    return dn, attributes


# ---- passwords and plans ----

def password_source(username: str, bootstrap_users: set[str], writer_files: dict[str, bool]) -> str:
    """bootstrap, then writer-file (when the file exists and is not empty), then default (P5)."""
    if username in bootstrap_users:
        return "bootstrap"
    if writer_files.get(username):
        return "writer-file"
    return DEFAULT_PASSWORD_SOURCE


def eligible(users: list[LocalUser]) -> tuple[list[LocalUser], list[str]]:
    """(users to migrate, refused usernames): local, not service accounts, valid uid (P3)."""
    chosen, refused = [], []
    for user in users:
        if user.federated or user.username.startswith(SERVICE_ACCOUNT_PREFIX):
            continue
        if not valid_uid(user.username):
            refused.append(user.username)
            continue
        chosen.append(user)
    return sorted(chosen, key=lambda u: u.username), sorted(refused)


def plan_migration(users: list[LocalUser]) -> list[tuple[str, str]]:
    """(username, step) in execution order; empty once every user is federated (P6)."""
    chosen, _ = eligible(users)
    return [(user.username, step) for user in chosen for step in STEPS]
