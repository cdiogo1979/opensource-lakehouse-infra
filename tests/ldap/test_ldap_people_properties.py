"""Property-based tests for the LDAP people model and the migration plan (PBT partial)."""

from hypothesis import given, settings, strategies as st

from ldap_strategies import lp, people, user_lists, usernames


# P1 — render then parse an LDAP entry gives the same entry (PBT-02)
@settings(print_blob=True)
@given(people)
def test_p1_ldif_round_trip(person):
    dn, attributes = lp.parse_ldif(lp.render_entry(person))
    assert dn == person.dn
    assert attributes == person.attributes()


# P2 — no deletion before the matching verification, for every user (PBT-03)
@settings(print_blob=True)
@given(user_lists)
def test_p2_verification_precedes_deletion(users):
    plan = lp.plan_migration(users)
    for username in {name for name, _ in plan}:
        steps = [step for name, step in plan if name == username]
        assert steps.index("verify_bind") < steps.index("delete_local")
        assert steps.index("verify_home") < steps.index("delete_old_home") < steps.index("delete_old_hub_user")
        assert steps == list(lp.STEPS)


# P3 — every eligible local user exactly once; never federated or service accounts (PBT-03)
@settings(print_blob=True)
@given(user_lists)
def test_p3_plan_covers_eligible_users_exactly_once(users):
    planned = [name for name, step in lp.plan_migration(users) if step == "write_entry"]
    expected = sorted(u.username for u in users if not u.federated and not u.username.startswith("service-account-") and lp.valid_uid(u.username))
    assert planned == expected
    _, refused = lp.eligible(users)
    assert set(refused) == {u.username for u in users if not u.federated and not u.username.startswith("service-account-") and not lp.valid_uid(u.username)}


# P5 — the password source follows the precedence bootstrap > writer file > default (PBT-03)
@settings(print_blob=True)
@given(usernames, st.sets(usernames, max_size=4), st.dictionaries(usernames, st.booleans(), max_size=4))
def test_p5_password_source_precedence(username, bootstrap, writers):
    source = lp.password_source(username, bootstrap, writers)
    if username in bootstrap:
        assert source == "bootstrap"
    elif writers.get(username):
        assert source == "writer-file"
    else:
        assert source == lp.DEFAULT_PASSWORD_SOURCE


# P6 (advisory, PBT-04) — once every user is federated, the plan is empty
@settings(print_blob=True)
@given(user_lists)
def test_p6_completed_migration_plans_nothing(users):
    migrated = [lp.LocalUser(**{**u.__dict__, "federated": True}) for u in users]
    assert lp.plan_migration(migrated) == []


def test_entries_need_names_and_fall_back_to_the_username():
    person = lp.person_for(lp.LocalUser(id="1", username="anna"))
    assert (person.cn, person.sn, person.mail) == ("anna", "anna", None)
    assert lp.render_entry(lp.LdapPerson("x", " leading", "José")).count("::") == 2
