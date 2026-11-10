"""Property-based tests for the StarRocks planners (P1-P8; PBT-02, 03, 07, 08, 09)."""

from hypothesis import given, settings

from starrocks_strategies import (
    ROOT,
    bootstrap,
    current_grant_sets,
    environments,
    memberships,
    property_maps,
    reconcile,
    secrets,
    sr,
    user_states,
)

def level_privileges(level, database):
    """BR-3: database-scoped grants of one product role in one catalog (no CREATE DATABASE)."""
    tables, db = f"ALL TABLES IN DATABASE {database}", f"DATABASE {database}"
    return {
        "read": {("USAGE", "CATALOG"), ("SELECT", tables)},
        "write": {("USAGE", "CATALOG"), ("SELECT", tables), ("CREATE TABLE", db), ("INSERT", tables)},
        "manage": {("USAGE", "CATALOG"), ("ALL", db), ("ALL", tables)},
        "none": set(),
    }[level]


PLATFORM_ADMIN_PRIVILEGES = {("ALL", "CATALOG"), ("ALL", "ALL DATABASES"), ("ALL", "ALL TABLES IN ALL DATABASES")}
DEFAULT = sr.data_products.load_product(ROOT / "data-products/default.yaml")


def apply_grant_plan(current, plan):
    return (set(current) | set(plan.add)) - set(plan.revoke)


def apply_user_plan(current, plan):
    state = {name: (s.plugin, set(s.roles)) for name, s in current.items()}
    for name, _roles in plan.create:
        state[name] = (reconcile.LDAP_PLUGIN, set())
    for name in plan.switch:
        state[name] = (reconcile.LDAP_PLUGIN, state[name][1])
    for name, role in plan.grant:
        state[name][1].add(role)
    for name, role in plan.revoke:
        state[name][1].discard(role)
    for name in plan.drop:
        del state[name]
    return state


# P1 — round-trip of catalog properties (PBT-02)
@settings(print_blob=True)
@given(property_maps)
def test_p1_catalog_properties_round_trip(properties):
    rendered = "CREATE EXTERNAL CATALOG `x`\n" + bootstrap.render_catalog_properties(properties)
    assert bootstrap.parse_catalog_properties(rendered) == properties


@settings(print_blob=True)
@given(environments, secrets)
def test_p1_catalog_definition_round_trips_with_any_secret(env, secret):
    desired = bootstrap.catalog_definition(env, secret)
    assert bootstrap.parse_catalog_properties("CREATE EXTERNAL CATALOG x\n" + bootstrap.render_catalog_properties(desired)) == desired


# P2 — JWT users from the former token login are switched in place, never recreated (PBT-03)
@settings(print_blob=True)
@given(user_states, memberships)
def test_p2_jwt_users_are_switched_never_recreated(current, member_map):
    desired = reconcile.desired_users(member_map)
    plan = reconcile.plan_users(current, desired)
    jwt_desired = {n for n, s in current.items() if s.plugin == reconcile.JWT_PLUGIN and n in desired}
    assert set(plan.switch) == jwt_desired
    assert not {n for n, _ in plan.create} & set(current)
    assert not set(plan.switch) & set(plan.drop)


# P3 — grants equal the matrix exactly (PBT-03)
def test_p3_role_grants_match_the_matrix_exactly():
    grants = bootstrap.role_grants()
    for role in sr.data_products.ROLES:
        sr_role = f"role_default_{role}"
        for env in sr.ENVIRONMENTS:
            actual = {(g.privilege, g.object) for g in grants if g.role == sr_role and g.catalog == env.catalog}
            assert actual == level_privileges(DEFAULT.access[role][env.name], env.namespace), (role, env.name)
    for env in sr.ENVIRONMENTS:
        actual = {(g.privilege, g.object) for g in grants if g.role == "role_platform_admin" and g.catalog == env.catalog}
        assert actual == PLATFORM_ADMIN_PRIVILEGES
    analyst = {g for g in grants if g.role == "role_default_analyst"}
    assert not any(g.catalog in ("lakehouse_uat", "lakehouse_dev") for g in analyst)
    assert not any("uat" in g.object or "dev" in g.object for g in analyst)
    product_grants = {g for g in grants if g.role != "role_platform_admin"}
    assert not any(g.privilege == "CREATE DATABASE" for g in grants)
    assert not any(g.object in ("ALL DATABASES", "ALL TABLES IN ALL DATABASES") for g in product_grants)
    # CR-2: developers author MVs in dev only.
    developer = {(g.privilege, g.object) for g in grants if g.role == "role_default_developer" and g.catalog == sr.INTERNAL_CATALOG}
    assert ("CREATE MATERIALIZED VIEW", "DATABASE default_lhdev") in developer
    assert ("CREATE MATERIALIZED VIEW", "DATABASE default_lh") not in developer


# P4 — applying the grant plan yields the matrix on managed roles only (PBT-03)
@settings(print_blob=True)
@given(current_grant_sets)
def test_p4_grant_plan_converges_and_leaves_unmanaged_roles(current):
    desired = bootstrap.role_grants()
    after = apply_grant_plan(current, bootstrap.plan_grants(current, desired))
    managed_after = {g for g in after if g.role in sr.MANAGED_ROLES}
    # Every desired grant is present, and every remaining managed grant is covered by
    # the matrix: either desired itself or implied by ALL on the same object (StarRocks
    # may report ALL as individual privileges).
    assert desired <= managed_after
    assert all(bootstrap._covered(g, desired) for g in managed_after)
    assert {g for g in after if g.role not in sr.MANAGED_ROLES} == {g for g in current if g.role not in sr.MANAGED_ROLES}


# P5 — desired users exclude service accounts and group-less users (PBT-03)
@settings(print_blob=True)
@given(memberships)
def test_p5_desired_users_follow_the_groups(member_map):
    desired = reconcile.desired_users(member_map)
    for name, roles in desired.items():
        assert not name.startswith("service-account-")
        groups = member_map[name]
        expected = {sr.GROUP_ROLES[g] for g in groups if g in sr.GROUP_ROLES}
        assert expected
        if "role-platform-admin" in groups:
            expected |= set(sr.PLATFORM_ADMIN_BUILTINS)
        assert roles == expected
    for name, groups in member_map.items():
        if not name.startswith("service-account-") and set(groups) & set(sr.GROUP_ROLES):
            assert name in desired


# P6 — applying the user plan yields the desired managed users (PBT-03)
@settings(print_blob=True)
@given(user_states, memberships)
def test_p6_user_plan_converges_and_spares_unmanaged_users(current, member_map):
    desired = reconcile.desired_users(member_map)
    plan = reconcile.plan_users(current, desired)
    after = apply_user_plan(current, plan)
    for name, roles in desired.items():
        if name in plan.conflicts:
            continue
        assert after[name][0] == reconcile.LDAP_PLUGIN
        assert after[name][1] & reconcile.GRANTABLE_ROLES == set(roles)
    for name, state in current.items():
        if state.plugin not in reconcile.MANAGED_PLUGINS:
            assert after[name] == (state.plugin, set(state.roles))
            assert name not in plan.drop
        elif name not in desired:
            assert name not in after
    assert set(plan.conflicts) == {n for n in desired if n in current and current[n].plugin not in reconcile.MANAGED_PLUGINS}


# P7 — catalog plan ignores the credential (PBT-03)
@settings(print_blob=True)
@given(environments, secrets, secrets)
def test_p7_catalog_plan_ignores_the_credential(env, secret, other):
    desired = bootstrap.catalog_definition(env, secret)
    stored = bootstrap.catalog_definition(env, other) | {bootstrap.CREDENTIAL_KEY: "******", "extra.key": "x"}
    assert bootstrap.plan_catalog(stored, desired) == "equal"
    changed = dict(stored) | {"iceberg.catalog.uri": "http://elsewhere/api/catalog"}
    assert bootstrap.plan_catalog(changed, desired) == "conflict"
    assert bootstrap.plan_catalog(None, desired) == "create"


# P8 — planning against the desired state is empty (advisory idempotence)
@settings(print_blob=True)
@given(memberships)
def test_p8_planning_the_desired_state_is_empty(member_map):
    desired_grants = bootstrap.role_grants()
    assert not bootstrap.plan_grants(desired_grants, desired_grants).add
    assert not bootstrap.plan_grants(desired_grants, desired_grants).revoke
    desired = reconcile.desired_users(member_map)
    current = {n: reconcile.UserState(n, reconcile.LDAP_PLUGIN, r) for n, r in desired.items()}
    assert reconcile.plan_users(current, desired).is_empty()
