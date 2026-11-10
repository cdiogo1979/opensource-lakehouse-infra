"""Shared Hypothesis generators for the LDAP people model and the migration (PBT-07)."""

import sys
from pathlib import Path

from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "infra/keycloak")]

import ldap_people as lp  # noqa: E402

# Valid uids, including the boundary lengths (1 and 63 characters).
usernames = st.from_regex(r"[a-z0-9][a-z0-9._-]{0,62}", fullmatch=True)
invalid_usernames = st.one_of(
    st.from_regex(r"[A-Z][a-z]{1,8}", fullmatch=True),
    st.from_regex(r"[a-z]{1,8} [a-z]{1,8}", fullmatch=True),
    st.just("-leading"),
)
service_accounts = st.from_regex(r"service-account-[a-z][a-z0-9-]{0,12}", fullmatch=True)
# Names in any script, with LDIF-special leading and trailing characters.
names = st.one_of(
    st.just(""),
    st.text(st.characters(blacklist_categories=("Cs", "Cc"), blacklist_characters="\x00"), min_size=1, max_size=30),
    st.sampled_from([" Ana", "Ana ", ":colon", "<angle", "José", "李", "O'Brien", "Anne-Marie"]),
)
emails = st.one_of(st.just(""), st.from_regex(r"[a-z0-9._-]{1,12}@[a-z0-9-]{1,10}\.(local|com)", fullmatch=True))
group_sets = st.lists(st.sampled_from(["role-default-owner", "role-default-developer", "role-default-analyst",
                                       "role-default-writer", "role-platform-admin", "role-sales-analyst"]),
                      unique=True, max_size=3).map(tuple)


@st.composite
def local_users(draw, username=usernames):
    return lp.LocalUser(
        id=draw(st.uuids()).hex,
        username=draw(username),
        enabled=draw(st.booleans()),
        email_verified=draw(st.booleans()),
        first_name=draw(names),
        last_name=draw(names),
        email=draw(emails),
        groups=draw(group_sets),
        federated=draw(st.booleans()),
    )


user_lists = st.lists(st.one_of(local_users(), local_users(service_accounts), local_users(invalid_usernames)),
                      max_size=12, unique_by=lambda u: u.username)
people = local_users().map(lambda user: lp.person_for(user))
