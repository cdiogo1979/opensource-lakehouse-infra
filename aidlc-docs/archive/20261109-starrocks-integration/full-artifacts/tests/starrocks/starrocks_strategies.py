"""Hypothesis generators and module loaders for the StarRocks planners (PBT-07)."""

import importlib.util
import sys
from pathlib import Path

from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "infra/starrocks"))


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve their module through sys.modules
    spec.loader.exec_module(module)
    return module


bootstrap = load("starrocks_bootstrap", "infra/starrocks/bootstrap-starrocks.py")
reconcile = load("starrocks_reconcile", "infra/starrocks/reconcile-starrocks-users.py")
sr = bootstrap.sr

PRODUCT_GROUPS = sorted(sr.GROUP_ROLES)
OTHER_GROUPS = ["admins", "role-default-guest", "jenkins-break-glass"]

usernames = st.from_regex(r"[a-z][a-z0-9._-]{0,20}", fullmatch=True).filter(lambda n: n != "root")
service_accounts = st.from_regex(r"service-account-[a-z][a-z0-9-]{0,12}", fullmatch=True)
group_sets = st.sets(st.sampled_from(PRODUCT_GROUPS + OTHER_GROUPS), max_size=4)
memberships = st.dictionaries(st.one_of(usernames, service_accounts), group_sets, max_size=12)

# Any printable text without NUL, including quotes, backslashes, and newlines.
safe_text = st.text(st.characters(blacklist_characters="\x00", blacklist_categories=("Cs",)), max_size=40)
property_maps = st.dictionaries(safe_text.filter(bool), safe_text, max_size=8)

environments = st.sampled_from(sr.ENVIRONMENTS)
secrets = st.text(st.characters(blacklist_characters="\x00", blacklist_categories=("Cs",)), min_size=1, max_size=64)

all_grants = sorted(bootstrap.role_grants())
foreign_grants = st.builds(
    bootstrap.Grant,
    role=st.sampled_from(["custom_role", "analytics_team"]),
    privilege=st.sampled_from(["SELECT", "INSERT", "ALL"]),
    catalog=st.sampled_from(["lakehouse", "default_catalog"]),
    object=st.sampled_from(["CATALOG", "ALL TABLES IN ALL DATABASES"]),
)
extra_managed_grants = st.builds(
    bootstrap.Grant,
    role=st.sampled_from(sr.MANAGED_ROLES),
    privilege=st.sampled_from(["DROP", "DELETE", "ALTER", "INSERT", "SELECT"]),
    catalog=st.sampled_from([env.catalog for env in sr.ENVIRONMENTS]),
    object=st.sampled_from(["ALL TABLES IN ALL DATABASES", "ALL DATABASES"]),
)
current_grant_sets = st.builds(
    lambda kept, foreign, extra: set(kept) | set(foreign) | set(extra),
    st.lists(st.sampled_from(all_grants), unique=True),
    st.sets(foreign_grants, max_size=4),
    st.sets(extra_managed_grants, max_size=6),
)

role_sets = st.frozensets(st.sampled_from(sorted(reconcile.GRANTABLE_ROLES) + ["custom_role"]), max_size=4)
user_states = st.dictionaries(
    usernames,
    st.builds(lambda plugin, roles: (plugin, roles), st.sampled_from([reconcile.JWT_PLUGIN, "MYSQL_NATIVE_PASSWORD"]), role_sets),
    max_size=10,
).map(lambda raw: {name: reconcile.UserState(name, plugin, roles) for name, (plugin, roles) in raw.items()})
