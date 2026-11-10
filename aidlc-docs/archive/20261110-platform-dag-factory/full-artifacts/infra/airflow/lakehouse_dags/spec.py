"""Workflow JSON v1: parse and validate a product repository's workflows (BR-1 to BR-3, BR-10).

Standard library only, so the Jenkins validator can use it without Airflow. A
product repository holds ``workflows/<name>.json`` (one DAG each), its code in
``notebooks/workload/``, and the stub ``dags/lakehouse.py`` (``STUB_TEXT``).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

API_VERSION = "lakehouse.local/workflow/v1"
WORKFLOWS_DIR = "workflows"
WORKLOAD_DIR = Path("notebooks") / "workload"
STUB_PATH = Path("dags") / "lakehouse.py"
STUB_TEXT = (
    "# Airflow DAGs for this repository, built by the lakehouse platform from workflows/*.json.\n"
    "from lakehouse_dags import load_workflows\n"
    "\n"
    "load_workflows(globals(), __file__)\n"
)
# Added to every DAG by the platform; a workflow may not list them itself.
RESERVED_TAG = "spark"

# Names never start with a dot: workflows/.<name>.json would be a hidden file.
NAME = re.compile(r"[a-zA-Z0-9_-][a-zA-Z0-9_.-]{0,99}")
TAG = re.compile(r"[a-zA-Z0-9_.:-]{1,50}")
ENTRYPOINT = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*\.py")
WORKFLOW_KEYS = {"apiVersion", "name", "schedule", "description", "tags", "tasks"}
TASK_KEYS = {"name", "entrypoint", "runs_after", "args", "retries", "retry_delay_seconds", "execution_timeout_seconds"}
MAX_TASKS = 50
MAX_TAGS = 10
MAX_ARGS = 50


@dataclass(frozen=True)
class Task:
    name: str
    entrypoint: str
    runs_after: tuple[str, ...] = ()
    args: tuple[str, ...] = ()
    retries: int | None = None
    retry_delay_seconds: int | None = None
    execution_timeout_seconds: int | None = None


@dataclass(frozen=True)
class Workflow:
    name: str
    schedule: str | None
    tasks: tuple[Task, ...]
    description: str | None = None
    tags: tuple[str, ...] = ()
    source: str = ""


@dataclass(frozen=True)
class Problem:
    path: str
    field: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.field}: {self.message}" if self.field else f"{self.path}: {self.message}"


class WorkflowError(ValueError):
    """One or more workflow problems; the message lists every one."""

    def __init__(self, problems: list[Problem]):
        self.problems = problems
        super().__init__("Invalid lakehouse workflows:\n" + "\n".join(f"  {problem}" for problem in problems))


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _printable(value: Any, limit: int) -> bool:
    return isinstance(value, str) and 0 < len(value) <= limit and value.isprintable()


class _Collector:
    def __init__(self, path: str):
        self.path = path
        self.problems: list[Problem] = []

    def add(self, field: str, message: str) -> None:
        self.problems.append(Problem(self.path, field, message))


def _integer(value: Any, field: str, low: int, high: int, out: _Collector) -> int | None:
    if not _is_int(value) or not low <= value <= high:
        out.add(field, f"must be an integer from {low} to {high}")
        return None
    return value


def _string_list(value: Any, field: str, out: _Collector) -> list[str] | None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        out.add(field, "must be a list of strings")
        return None
    return value


def _task(raw: Any, index: int, root: Path | None, out: _Collector) -> Task | None:
    where = f"tasks[{index}]"
    if not isinstance(raw, dict):
        out.add(where, "must be an object")
        return None
    before = len(out.problems)
    for key in sorted(set(raw) - TASK_KEYS):
        out.add(f"{where}.{key}", "is not a known task field")
    name = raw.get("name")
    if not isinstance(name, str) or not NAME.fullmatch(name):
        out.add(f"{where}.name", "is required: 1 to 100 of a-z A-Z 0-9 _ . -, not starting with a dot")
    entrypoint = raw.get("entrypoint")
    if not isinstance(entrypoint, str) or not ENTRYPOINT.fullmatch(entrypoint):
        out.add(f"{where}.entrypoint", "is required and must be a .py file name in notebooks/workload/")
    elif root is not None and not (root / WORKLOAD_DIR / entrypoint).is_file():
        out.add(f"{where}.entrypoint", f"notebooks/workload/{entrypoint} does not exist")
    runs_after = _string_list(raw.get("runs_after", []), f"{where}.runs_after", out)
    if runs_after is not None and len(set(runs_after)) != len(runs_after):
        out.add(f"{where}.runs_after", "lists a task more than once")
    args = _string_list(raw.get("args", []), f"{where}.args", out)
    if args is not None and (len(args) > MAX_ARGS or any(not _printable(arg, 500) for arg in args)):
        out.add(f"{where}.args", f"must hold at most {MAX_ARGS} printable strings of 1 to 500 characters")
    retries = _integer(raw["retries"], f"{where}.retries", 0, 10, out) if "retries" in raw else None
    delay = _integer(raw["retry_delay_seconds"], f"{where}.retry_delay_seconds", 0, 3600, out) if "retry_delay_seconds" in raw else None
    if "retry_delay_seconds" in raw and not (retries or 0) >= 1:
        out.add(f"{where}.retry_delay_seconds", "needs retries of at least 1")
    timeout = _integer(raw["execution_timeout_seconds"], f"{where}.execution_timeout_seconds", 1, 86400, out) if "execution_timeout_seconds" in raw else None
    if len(out.problems) != before:
        return None
    return Task(name, entrypoint, tuple(runs_after), tuple(args), retries, delay, timeout)


def _graph(tasks: list[Task], out: _Collector) -> None:
    names = [task.name for task in tasks]
    for name in sorted({name for name in names if names.count(name) > 1}):
        out.add("tasks", f"task name {name!r} is used more than once")
    known = set(names)
    for index, task in enumerate(tasks):
        for predecessor in task.runs_after:
            if predecessor == task.name:
                out.add(f"tasks[{index}].runs_after", "a task cannot run after itself")
            elif predecessor not in known:
                out.add(f"tasks[{index}].runs_after", f"names unknown task {predecessor!r}")
    if out.problems:
        return
    pending = {task.name: set(task.runs_after) for task in tasks}
    done: set[str] = set()
    while pending:
        ready = {name for name, needs in pending.items() if needs <= done}
        if not ready:
            out.add("tasks", "runs_after forms a cycle: " + ", ".join(sorted(pending)))
            return
        done |= ready
        for name in ready:
            del pending[name]


def parse_workflow(text: str, path: str, root: Path | None = None) -> tuple[Workflow | None, list[Problem]]:
    """Validate one workflow file's text; ``root`` enables the entrypoint-exists check."""
    out = _Collector(path)
    try:
        raw = json.loads(text)
    except ValueError as error:
        out.add("", f"is not valid JSON ({error.msg} at line {error.lineno})")
        return None, out.problems
    if not isinstance(raw, dict):
        out.add("", "must be a JSON object")
        return None, out.problems
    for key in sorted(set(raw) - WORKFLOW_KEYS):
        out.add(key, "is not a known workflow field")
    if raw.get("apiVersion") != API_VERSION:
        out.add("apiVersion", f"must be {API_VERSION!r}")
    name = raw.get("name")
    if not isinstance(name, str) or not NAME.fullmatch(name):
        out.add("name", "is required: 1 to 100 of a-z A-Z 0-9 _ . -, not starting with a dot")
    elif Path(path).stem != name:
        out.add("name", f"must equal the file name ({Path(path).stem!r})")
    if "schedule" not in raw:
        out.add("schedule", "is required (null for manual runs)")
    elif raw["schedule"] is not None and not _printable(raw["schedule"], 100):
        out.add("schedule", "must be null or a non-empty string of at most 100 characters")
    description = raw.get("description")
    if "description" in raw and not _printable(description, 500):
        out.add("description", "must be a printable string of 1 to 500 characters")
    tags = _string_list(raw.get("tags", []), "tags", out)
    if tags is not None:
        if len(tags) > MAX_TAGS or len(set(tags)) != len(tags) or any(not TAG.fullmatch(tag) for tag in tags):
            out.add("tags", f"must be at most {MAX_TAGS} distinct tags matching [a-zA-Z0-9_.:-]{{1,50}}")
        if RESERVED_TAG in tags:
            out.add("tags", f"{RESERVED_TAG!r} is added by the platform")
    raw_tasks = raw.get("tasks")
    tasks: list[Task] = []
    if not isinstance(raw_tasks, list) or not 1 <= len(raw_tasks) <= MAX_TASKS:
        out.add("tasks", f"is required and must hold 1 to {MAX_TASKS} tasks")
    else:
        parsed = [_task(item, index, root, out) for index, item in enumerate(raw_tasks)]
        if all(task is not None for task in parsed):
            tasks = parsed
            _graph(tasks, out)
    if out.problems:
        return None, out.problems
    return Workflow(name, raw["schedule"], tuple(tasks), description, tuple(tags), path), []


def to_document(workflow: Workflow) -> dict[str, Any]:
    """The JSON form of a workflow, omitting defaults (inverse of ``parse_workflow``)."""
    document: dict[str, Any] = {"apiVersion": API_VERSION, "name": workflow.name, "schedule": workflow.schedule}
    if workflow.description is not None:
        document["description"] = workflow.description
    if workflow.tags:
        document["tags"] = list(workflow.tags)
    tasks = []
    for task in workflow.tasks:
        item: dict[str, Any] = {"name": task.name, "entrypoint": task.entrypoint}
        if task.runs_after:
            item["runs_after"] = list(task.runs_after)
        if task.args:
            item["args"] = list(task.args)
        for key in ("retries", "retry_delay_seconds", "execution_timeout_seconds"):
            if getattr(task, key) is not None:
                item[key] = getattr(task, key)
        tasks.append(item)
    document["tasks"] = tasks
    return document


def workflow_files(root: Path) -> list[Path]:
    directory = root / WORKFLOWS_DIR
    return sorted(directory.iterdir()) if directory.is_dir() else []


def load_repository(root: Path) -> tuple[list[Workflow], list[Problem]]:
    """Every workflow of a repository checkout, or the problems that block them."""
    workflows: list[Workflow] = []
    problems: list[Problem] = []
    for path in workflow_files(root):
        relative = path.relative_to(root).as_posix()
        if path.name.startswith(".") or path.name == "__pycache__":
            continue
        if not path.is_file() or path.suffix != ".json":
            problems.append(Problem(relative, "", "only *.json workflow files belong in workflows/"))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            problems.append(Problem(relative, "", "cannot be read as UTF-8 text"))
            continue
        workflow, found = parse_workflow(text, relative, root)
        problems += found
        if workflow is not None:
            workflows.append(workflow)
    return workflows, problems


def check_repository(root: Path) -> tuple[list[Workflow], list[Problem]]:
    """The CI check: the workflows, the exact stub, and nothing else in dags/ (BR-10)."""
    workflows, problems = load_repository(root)
    stub = root / STUB_PATH
    if not stub.is_file():
        problems.append(Problem(STUB_PATH.as_posix(), "", "is missing; copy the platform stub"))
    elif stub.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n") != STUB_TEXT:
        problems.append(Problem(STUB_PATH.as_posix(), "", "differs from the platform stub; restore its exact text"))
    dags = root / "dags"
    if dags.is_dir():
        for path in sorted(dags.rglob("*")):
            if "__pycache__" in path.parts or path.is_dir() or path == stub:
                continue
            problems.append(Problem(path.relative_to(root).as_posix(), "", "only the stub belongs in dags/ (declare DAGs in workflows/*.json)"))
    return workflows, sorted(problems, key=lambda problem: (problem.path, problem.field, problem.message))
