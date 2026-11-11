"""Trigger-time task arguments: checking and rendering ``task_args`` (airflow-task-params FR-2, FR-3; NFR-2, NFR-4).

``lakehouse_dags.task_args`` uses only the standard library, so these tests run on the host.
"""

import sys
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workflow_strategies  # noqa: E402,F401  (puts infra/airflow on the path, as for test_workflow_spec.py)

from lakehouse_dags.task_args import MAX_ARGUMENTS_PER_TASK, check_task_args, effective_args, option_name, task_values

TASKS = ["tpch_region_db_brz_load", "tpch_region_load"]


def test_no_or_empty_task_args_is_valid_and_changes_nothing():
    assert check_task_args(None, TASKS) == [] and check_task_args({}, TASKS) == []
    assert effective_args(["--entity", "region"], task_values(None, "tpch_region_load")) == ["--entity", "region"]


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("--entity orders", "task_args must be an object"),
        ({"tpch_orders_load": {"entity": "orders"}}, "'tpch_orders_load' is not a task of this workflow (tasks: tpch_region_db_brz_load, tpch_region_load)"),
        ({"tpch_region_load": ["--x"]}, "task_args.tpch_region_load: must be an object of argument names"),
        ({"tpch_region_load": {"Lookback": "1"}}, "invalid argument name 'Lookback'"),
        ({"tpch_region_load": {"silver-lookback-days": "1"}}, "invalid argument name 'silver-lookback-days'"),
        ({"tpch_region_load": {"silver_lookback_days": 7}}, "task_args.tpch_region_load.silver_lookback_days: must be a printable string of 1 to 500"),
        ({"tpch_region_load": {"note": ""}}, "must be a printable string"),
        ({"tpch_region_load": {"note": "a\nb"}}, "must be a printable string"),
        ({"tpch_region_load": {"note": "x" * 501}}, "must be a printable string"),
        ({"tpch_region_load": {f"a{i}": "1" for i in range(MAX_ARGUMENTS_PER_TASK + 1)}}, f"at most {MAX_ARGUMENTS_PER_TASK} arguments"),
    ],
)
def test_invalid_task_args_are_named(value, message):
    assert any(message in problem for problem in check_task_args(value, TASKS))


def test_every_problem_is_reported_together():
    problems = check_task_args({"nope": {}, "tpch_region_load": {"a": 1, "B": "x"}}, TASKS)
    assert len(problems) == 3


def test_a_trigger_value_replaces_the_option_in_either_form_and_keeps_the_rest():
    workflow = ["--entity", "region", "--scale-factor=0.01", "--flag", "--note", "-x"]
    assert effective_args(workflow, {"entity": "orders", "scale_factor": "1"}) == ["--flag", "--note", "-x", "--entity=orders", "--scale-factor=1"]
    assert effective_args(workflow, {"silver_lookback_days": "7"}) == [*workflow, "--silver-lookback-days=7"]


def test_a_value_stays_one_token_even_when_it_looks_like_options():
    assert effective_args([], {"note": "-- --entity evil"}) == ["--note=-- --entity evil"]


def test_values_reach_only_their_task():
    run = {"tpch_region_load": {"silver_lookback_days": "7"}}
    assert task_values(run, "tpch_region_load") == {"silver_lookback_days": "7"}
    assert task_values(run, "tpch_region_db_brz_load") == {}


# --- Property: rendering then parsing (the product parser's rules) gives the trigger values ----------

names = st.from_regex(r"[a-z][a-z0-9]{0,8}(_[a-z0-9]{1,4})?", fullmatch=True)
texts = st.text(st.characters(categories=("L", "N", "P", "S", "Zs")), min_size=1, max_size=30).filter(str.isprintable)


def parse(tokens):
    """The product repositories' rule (notebooks/common/cli.py): --opt=value or --opt value; an option twice is an error."""
    values, index = {}, 0
    while index < len(tokens):
        option, has_value, value = tokens[index].partition("=")
        index += 1
        if not has_value:
            value = tokens[index]
            index += 1
        assert option not in values, f"{option} given twice"
        values[option] = value
    return values


@settings(max_examples=200)
@given(st.dictionaries(names, texts.filter(lambda t: not t.startswith("-")), max_size=6), st.dictionaries(names, texts, max_size=6), st.booleans())
def test_p_trigger_values_win_once_and_workflow_values_stay(workflow_values, trigger_values, equals_form):
    workflow = []
    for name, text in workflow_values.items():
        workflow += [f"{option_name(name)}={text}"] if equals_form else [option_name(name), text]
    assert check_task_args({"t": trigger_values}, ["t"]) == []
    parsed = parse(effective_args(workflow, trigger_values))
    expected = {option_name(n): t for n, t in workflow_values.items()} | {option_name(n): t for n, t in trigger_values.items()}
    assert parsed == expected
