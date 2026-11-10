"""Shared Hypothesis generators for workflow JSON v1 (PBT-07)."""

import sys
from pathlib import Path

from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "infra/airflow"))

from lakehouse_dags import spec  # noqa: E402

names = st.from_regex(r"[a-zA-Z0-9_-][a-zA-Z0-9_.-]{0,29}", fullmatch=True)
entrypoints = st.from_regex(r"[a-z][a-z0-9_]{0,15}\.py", fullmatch=True)
tags = st.from_regex(r"[a-z][a-z0-9_.:-]{0,15}", fullmatch=True).filter(lambda tag: tag != spec.RESERVED_TAG)
arguments = st.text(st.characters(categories=("L", "N", "P", "S", "Zs")), min_size=1, max_size=40).filter(str.isprintable)
schedules = st.one_of(st.none(), st.sampled_from(["@daily", "@hourly", "0 3 * * *", "*/15 * * * *"]))


@st.composite
def tasks_graph(draw, max_tasks=8):
    """Distinct task names; each task may run after earlier tasks only, so the graph is acyclic."""
    task_names = draw(st.lists(names, min_size=1, max_size=max_tasks, unique=True))
    tasks = []
    for index, name in enumerate(task_names):
        runs_after = tuple(draw(st.lists(st.sampled_from(task_names[:index]), unique=True, max_size=3))) if index else ()
        retries = draw(st.one_of(st.none(), st.integers(0, 10)))
        delay = draw(st.one_of(st.none(), st.integers(0, 3600))) if retries else None
        tasks.append(spec.Task(
            name=name,
            entrypoint=draw(entrypoints),
            runs_after=runs_after,
            args=tuple(draw(st.lists(arguments, max_size=4))),
            retries=retries,
            retry_delay_seconds=delay,
            execution_timeout_seconds=draw(st.one_of(st.none(), st.integers(1, 86400))),
        ))
    # Shuffle declaration order: runs_after may name tasks declared later.
    return tuple(draw(st.permutations(tasks)))


@st.composite
def workflows(draw):
    name = draw(names)
    return spec.Workflow(
        name=name,
        schedule=draw(schedules),
        tasks=draw(tasks_graph()),
        description=draw(st.one_of(st.none(), arguments)),
        tags=tuple(draw(st.lists(tags, unique=True, max_size=4))),
        source=f"workflows/{name}.json",
    )


def write_repository(root: Path, workflow_list) -> Path:
    """A product repository checkout holding these workflows, their entry points, and the stub."""
    (root / "workflows").mkdir(parents=True, exist_ok=True)
    (root / "notebooks/workload").mkdir(parents=True, exist_ok=True)
    (root / "dags").mkdir(exist_ok=True)
    (root / "dags/lakehouse.py").write_text(spec.STUB_TEXT, encoding="utf-8")
    import json
    for workflow in workflow_list:
        (root / "workflows" / f"{workflow.name}.json").write_text(json.dumps(spec.to_document(workflow), indent=2), encoding="utf-8")
        for task in workflow.tasks:
            (root / "notebooks/workload" / task.entrypoint).write_text("print('ok')\n", encoding="utf-8")
    return root
