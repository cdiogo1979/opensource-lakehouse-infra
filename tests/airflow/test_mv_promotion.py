"""Materialized view promotion: the MV file rules and the deploy plan (mv-promotion FR-1, FR-3, FR-4; NFR-3).

``spec`` and ``mv_deploy``'s planning use only the standard library, so these tests run on the host.
"""

import sys
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workflow_strategies  # noqa: E402,F401  (puts infra/airflow on the path)

from lakehouse_dags import mv_deploy, spec, validate  # noqa: E402

GOOD = """-- Sales per day
CREATE MATERIALIZED VIEW ${mv_database}.mv_tpch_daily
COMMENT 'Sales per day'
REFRESH ASYNC EVERY (INTERVAL 1 HOUR)
AS SELECT o_orderdate, COUNT(*) AS orders FROM ${catalog}.${namespace}.tpch_orders GROUP BY o_orderdate;
"""
PLACEMENT = mv_deploy.Placement("lakehouse_uat", "default_lhuat", "default_lhuat")


def repository(tmp_path, files):
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path


# --- The file rules (FR-1, FR-3) --------------------------------------------------------


def test_a_valid_definition_is_read_without_comments_or_the_trailing_semicolon(tmp_path):
    views, problems = spec.load_materialized_views(repository(tmp_path, {"materialized_views/tpch/mv_tpch_daily.sql": GOOD}))
    assert problems == [] and [(v.name, v.project) for v in views] == [("mv_tpch_daily", "tpch")]
    assert views[0].statement.startswith("CREATE MATERIALIZED VIEW ${mv_database}.mv_tpch_daily") and not views[0].statement.endswith(";")


@pytest.mark.parametrize(
    ("relative", "text", "message"),
    [
        ("materialized_views/tpch/mv_other.sql", GOOD, "creates 'mv_tpch_daily', but the file name says 'mv_other'"),
        ("materialized_views/tpch/mv_tpch_daily.sql", GOOD.replace(";\n", "; DROP TABLE x;\n"), "more than one statement"),
        ("materialized_views/tpch/mv_tpch_daily.sql", GOOD.replace("${namespace}", "${secret}"), "unknown placeholders ${secret}"),
        ("materialized_views/tpch/mv_tpch_daily.sql", GOOD.replace("${mv_database}.mv", "default_lh.mv"), "must hold one CREATE MATERIALIZED VIEW ${mv_database}.<name>"),
        ("materialized_views/tpch/mv__daily.sql", GOOD.replace("mv_tpch_daily", "mv__daily"), "the file name must be an MV name"),
        ("materialized_views/tpch/Mv_Daily.sql", GOOD.replace("mv_tpch_daily", "Mv_Daily"), "the file name must be an MV name"),
        ("materialized_views/tpch/notes.txt", "x", "only *.sql files belong"),
        ("materialized_views/mv_loose.sql", GOOD, "holds only subproject folders"),
    ],
)
def test_invalid_definitions_are_named(tmp_path, relative, text, message):
    _views, problems = spec.load_materialized_views(repository(tmp_path, {relative: text}))
    assert any(message in str(problem) for problem in problems), problems


def test_mv_names_are_unique_across_subprojects(tmp_path):
    root = repository(tmp_path, {"materialized_views/a/mv_tpch_daily.sql": GOOD, "materialized_views/b/mv_tpch_daily.sql": GOOD})
    views, problems = spec.load_materialized_views(root)
    assert len(views) == 1 and "MV names are unique" in str(problems[0])


def test_ci_checks_the_definitions_and_reports_them(tmp_path, capsys):
    root = repository(tmp_path, {"dags/lakehouse.py": spec.STUB_TEXT, "materialized_views/tpch/mv_tpch_daily.sql": GOOD})
    assert validate.main([str(root)]) == 0 and capsys.readouterr().out == "OK: 0 workflow(s), 1 materialized view(s)\n"
    (root / "materialized_views/tpch/mv_bad.sql").write_text("SELECT 1")
    assert validate.main([str(root)]) == 1 and "mv_bad.sql" in capsys.readouterr().out


def test_the_platform_dag_name_is_reserved(tmp_path):
    document = '{"apiVersion": "%s", "name": "deploy_materialized_views", "schedule": null, "tasks": [{"name": "t", "entrypoint": "t.py"}]}' % spec.API_VERSION
    root = repository(tmp_path, {"workflows/deploy_materialized_views.json": document, "notebooks/workload/t.py": ""})
    assert any("reserved" in str(problem) for problem in spec.load_repository(root)[1])


# --- Rendering and the marker (FR-4) ----------------------------------------------------


def test_render_fills_only_the_three_placeholders():
    rendered = mv_deploy.render(spec.parse_materialized_view(GOOD, "f", "mv_tpch_daily", "tpch")[0].statement, PLACEMENT)
    assert "default_lhuat.mv_tpch_daily" in rendered and "lakehouse_uat.default_lhuat.tpch_orders" in rendered and "${" not in rendered


def test_the_marker_leads_the_comment_and_keeps_the_authors_text():
    rendered = mv_deploy.render(spec.parse_materialized_view(GOOD, "f", "mv_tpch_daily", "tpch")[0].statement, PLACEMENT)
    sql = mv_deploy.deployable(rendered, "default_lhuat.mv_tpch_daily__lakehouse_new", "abc")
    assert sql.startswith("CREATE MATERIALIZED VIEW default_lhuat.mv_tpch_daily__lakehouse_new COMMENT 'lakehouse-mv sha256=abc; Sales per day'")
    assert sql.count("COMMENT") == 1
    bare = mv_deploy.deployable("CREATE MATERIALIZED VIEW db.mv REFRESH MANUAL AS SELECT 1", "db.mv", "abc")
    assert bare == "CREATE MATERIALIZED VIEW db.mv COMMENT 'lakehouse-mv sha256=abc' REFRESH MANUAL AS SELECT 1"
    assert mv_deploy.managed_version("lakehouse-mv sha256=abc; Sales per day") == "abc" and mv_deploy.managed_version("made by hand") is None


def test_the_plan_creates_replaces_drops_and_never_touches_hand_made_views():
    work = mv_deploy.plan(
        {"new": "1", "same": "2", "changed": "3", "hand": "4"},
        {"same": "lakehouse-mv sha256=2", "changed": "lakehouse-mv sha256=old; x", "hand": "mine", "gone": "lakehouse-mv sha256=9", "other": None},
    )
    assert (work.create, work.keep, work.replace, work.foreign, work.drop) == (["new"], ["same"], ["changed"], ["hand"], ["gone"])


class FakeCursor:
    """A StarRocks MV database in memory: CREATE, SWAP and DROP of materialized views."""

    def __init__(self, existing=None, missing_tables=()):
        self.views = dict(existing or {})
        self.missing_tables = missing_tables
        self.statements = []

    def execute(self, sql, params=None):
        self.statements.append(sql)
        if sql.startswith("SELECT m.TABLE_NAME"):
            self.rows = [(name, comment) for name, comment in self.views.items()]
        elif sql.startswith("CREATE MATERIALIZED VIEW"):
            if any(table in sql for table in self.missing_tables):
                raise RuntimeError("(5502, \"Getting analyzing error. Detail message: Unknown table 'db.t'.\")")
            target = sql.split()[3].split(".", 1)[1]
            self.views[target] = sql.split("COMMENT '", 1)[1].split("'", 1)[0]
        elif sql.startswith("ALTER MATERIALIZED VIEW"):
            first, second = sql.split()[3].split(".", 1)[1], sql.split()[-1]
            self.views[first], self.views[second] = self.views[second], self.views[first]
        elif sql.startswith("DROP MATERIALIZED VIEW"):
            self.views.pop(sql.split()[-1].split(".", 1)[1], None)

    def fetchall(self):
        return self.rows


class Log:
    def __init__(self):
        self.messages = []

    def warning(self, message, *args):
        self.messages.append(message % args)


def test_apply_replaces_by_swap_and_skips_a_view_whose_table_is_missing():
    views = {"mv_a": "CREATE MATERIALIZED VIEW db.mv_a AS SELECT 2", "mv_b": "CREATE MATERIALIZED VIEW db.mv_b AS SELECT * FROM missing_t"}
    cursor = FakeCursor({"mv_a": "lakehouse-mv sha256=old", "mv_gone": "lakehouse-mv sha256=x", "mv_hand": "mine"}, missing_tables=("missing_t",))
    report = mv_deploy.apply(cursor, "db", views, Log())
    assert (report.replaced, report.skipped, report.dropped, report.failed) == (["mv_a"], ["mv_b"], ["mv_gone"], [])
    assert set(cursor.views) == {"mv_a", "mv_hand"} and mv_deploy.managed_version(cursor.views["mv_a"]) == mv_deploy.digest(views["mv_a"])
    assert "ALTER MATERIALIZED VIEW db.mv_a SWAP WITH mv_a__lakehouse_new" in cursor.statements


# --- Property: one deploy makes the managed views match the files; a second changes nothing ---

names = st.from_regex(r"mv_[a-z]{1,6}", fullmatch=True)
bodies = st.sampled_from(["SELECT 1", "SELECT 2", "SELECT 3"])


@settings(max_examples=200)
@given(st.dictionaries(names, bodies, max_size=6), st.dictionaries(names, st.one_of(bodies.map(lambda b: "managed:" + b), st.just("hand")), max_size=6))
def test_p_deploying_twice_converges_and_spares_hand_made_views(files, database):
    existing = {
        name: (f"lakehouse-mv sha256={mv_deploy.digest(f'CREATE MATERIALIZED VIEW db.{name} AS ' + state[8:])}" if state != "hand" else "hand")
        for name, state in database.items()
    }
    views = {name: f"CREATE MATERIALIZED VIEW db.{name} AS {body}" for name, body in files.items()}
    cursor = FakeCursor(existing)
    first = mv_deploy.apply(cursor, "db", views, Log())
    hand = {name for name, comment in existing.items() if comment == "hand"}
    assert {name: cursor.views[name] for name in hand} == {name: "hand" for name in hand}
    managed = {name: mv_deploy.managed_version(comment) for name, comment in cursor.views.items() if name not in hand}
    assert managed == {name: mv_deploy.digest(sql) for name, sql in views.items() if name not in hand}
    assert set(first.foreign) == hand & set(views)
    second = mv_deploy.apply(cursor, "db", views, Log())
    assert (second.created, second.replaced, second.dropped) == ([], [], [])
