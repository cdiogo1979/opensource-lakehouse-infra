"""Property-based tests for the StarRocks planners (P1-P8; PBT-02, 03, 07, 08, 09)."""

from hypothesis import given, settings

from starrocks_strategies import (
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

LEVEL_PRIVILEGES = {
    "read": {("USAGE", "CATALOG"), ("SELECT", "ALL TABLES IN ALL DATABASES")},
    "write": {("USAGE", "CATALOG"), ("SELECT", "ALL TABLES IN ALL DATABASES"), ("CREATE DATABASE", "CATALOG"),
              ("CREATE TABLE", "ALL DATABASES"), ("INSERT", "ALL TABLES IN ALL DATABASES")},
    "manage": {("ALL", "CATALOG"), ("ALL", "ALL DATABASES"), ("ALL", "ALL TABLES IN ALL DATABASES")},
    "none": set(),
}


def apply_grant_plan(current, plan):
    return (set(current) | set(plan.add)) - set(plan.revoke)


def apply_user_plan(current, plan):
    state = {name: (s.plugin, set(s.roles)) for name, s in current.items()}
    for name, _roles in plan.create:
        state[name] = (reconcile.JWT_PLUGIN, set())
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


# P2 — round-trip of the JWT identity clause (PBT-02)
def test_p2_jwt_identity_round_trip():
    parsed = reconcile.parse_jwt_identity(reconcile.jwt_identity_clause())
    assert parsed == {
        "jwks_url": reconcile.JWKS_URL,
        "principal_field": "preferred_username",
        "required_issuer": "http://keycloak.localhost:8080/realms/lakehouse",
        "required_audience": "starrocks",
    }
    assert reconcile.jwt_identity_clause() == reconcile.jwt_identity_clause()


# P3 — grants equal the matrix exactly (PBT-03)
def test_p3_role_grants_match_the_matrix_exactly():
    grants = bootstrap.role_grants()
    for role in sr.MANAGED_ROLES:
        for env in sr.ENVIRONMENTS:
            actual = {(g.privilege, g.object) for g in grants if g.role == role and g.catalog == env.catalog}
            assert actual == LEVEL_PRIVILEGES[sr.CATALOG_MATRIX[role][env.name]], (role, env.name)
    analyst = {g for g in grants if g.role == "role_default_analyst"}
    assert not any(g.catalog in ("lakehouse_uat", "lakehouse_dev") for g in analyst)
    assert not any("uat" in g.object or "dev" in g.object for g in analyst)
    for g in grants:
        if g.privilege in ("DROP", "ALL") and g.catalog != sr.INTERNAL_CATALOG:
            assert sr.CATALOG_MATRIX[g.role][next(e.name for e in sr.ENVIRONMENTS if e.catalog == g.catalog)] == "manage"


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
def test_p6_user_plan_converges_and_spares_non_jwt_users(current, member_map):
    desired = reconcile.desired_users(member_map)
    plan = reconcile.plan_users(current, desired)
    after = apply_user_plan(current, plan)
    for name, roles in desired.items():
        if name in plan.conflicts:
            continue
        assert after[name][0] == reconcile.JWT_PLUGIN
        assert after[name][1] & reconcile.GRANTABLE_ROLES == set(roles)
    for name, state in current.items():
        if state.plugin != reconcile.JWT_PLUGIN:
            assert after[name] == (state.plugin, set(state.roles))
            assert name not in plan.drop
        elif name not in desired:
            assert name not in after
    assert set(plan.conflicts) == {n for n in desired if n in current and current[n].plugin != reconcile.JWT_PLUGIN}


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
    current = {n: reconcile.UserState(n, reconcile.JWT_PLUGIN, r) for n, r in desired.items()}
    assert reconcile.plan_users(current, desired).is_empty()
