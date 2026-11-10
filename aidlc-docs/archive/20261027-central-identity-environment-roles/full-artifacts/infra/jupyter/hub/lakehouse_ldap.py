import ssl

import ldap3
from ldap3.utils.conv import escape_filter_chars


ROLE_GROUPS = ("lakehouse-developers", "lakehouse-analysts")
WRITER_GROUP = "lakehouse-writers"
ADMIN_LOGIN = "administrator"


def _text(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="strict")
    return str(value)


def _active_user(connection, username, user_base):
    safe_username = escape_filter_chars(username)
    ok = connection.search(
        user_base,
        f"(&(uid={safe_username})(objectClass=*))",
        search_scope=ldap3.SUBTREE,
        attributes=["uid", "nsAccountLock"],
        size_limit=2,
    )
    if not ok or len(connection.entries) != 1:
        raise RuntimeError("Directory user lookup was not unique and successful.")
    entry = connection.entries[0]
    lock_value = entry.entry_attributes_as_dict.get("nsAccountLock", [])
    if lock_value and _text(lock_value[0]).strip().lower() in {"true", "1", "yes"}:
        raise PermissionError("Directory account is locked.")
    return entry.entry_dn


def _member_of(connection, username_dn, group_base, group_cn):
    group_dn = f"cn={group_cn},{group_base}"
    ok = connection.search(
        group_dn,
        "(objectClass=*)",
        search_scope=ldap3.BASE,
        attributes=["cn", "member"],
        size_limit=2,
    )
    if not ok or len(connection.entries) != 1 or "member" not in connection.entries[0]:
        raise RuntimeError("Directory role lookup failed or returned incomplete data.")
    members = {_text(member).casefold() for member in connection.entries[0].member.values}
    return username_dn.casefold() in members


def current_role(
    username,
    host,
    user_base,
    group_base,
    reader_dn,
    reader_password,
    ca_file,
):
    tls = ldap3.Tls(validate=ssl.CERT_REQUIRED, ca_certs_file=ca_file)
    server = ldap3.Server(
        host,
        port=636,
        use_ssl=True,
        tls=tls,
        connect_timeout=5,
    )
    connection = ldap3.Connection(
        server,
        user=reader_dn,
        password=reader_password,
        auto_bind=True,
        receive_timeout=5,
        raise_exceptions=True,
    )
    try:
        user_dn = _active_user(connection, username, user_base)
        developer = _member_of(connection, user_dn, group_base, ROLE_GROUPS[0])
        analyst = _member_of(connection, user_dn, group_base, ROLE_GROUPS[1])
        writer = _member_of(connection, user_dn, group_base, WRITER_GROUP)
        if writer or username == "write-service-account":
            raise PermissionError("Writer/service identities cannot spawn notebook servers.")
        if username == ADMIN_LOGIN:
            if developer or analyst:
                raise PermissionError("Platform administrator has conflicting data roles.")
            return "admin"
        roles = [role for role, member in (("developer", developer), ("analyst", analyst)) if member]
        if len(roles) != 1:
            raise PermissionError("User must have exactly one supported data role.")
        return roles[0]
    finally:
        connection.unbind()
