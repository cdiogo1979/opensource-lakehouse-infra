"""Trigger-time task arguments: the DAG param ``task_args``, checked and rendered without templating.

A run triggered with ``{"task_args": {"<task>": {"<argument>": "<value>"}}}`` gives
those tasks extra arguments. Each value becomes one ``--<argument>=<value>`` token
after the task's workflow ``args`` and replaces the same option there, so a value
can never become a separate option or the ``--`` separator. Nothing is rendered by
Jinja or a shell. The job's own parser still decides which options it accepts.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from .spec import _printable

PARAM = "task_args"
# The same rule as the product repositories' parser (notebooks/common/cli.py).
ARGUMENT_NAME = re.compile(r"[a-z][a-z0-9_]{0,49}")
MAX_ARGUMENTS_PER_TASK = 20
MAX_VALUE_LENGTH = 500


def option_name(name: str) -> str:
    """The command-line option for an argument name: ``scale_factor`` -> ``--scale-factor``."""
    return "--" + name.replace("_", "-")


def check_task_args(value: Any, task_names: Sequence[str]) -> list[str]:
    """Every problem with a run's ``task_args``; an empty list when it is valid.

    Args:
        value: The run's ``task_args`` param; ``None`` counts as ``{}``.
        task_names: The workflow's task names.

    Returns:
        One message per problem, naming the task and argument.
    """
    if value is None:
        return []
    if not isinstance(value, Mapping):
        return [f'{PARAM} must be an object of task names to {{"argument": "value"}} objects']
    problems = []
    for task, arguments in value.items():
        if task not in task_names:
            problems.append(f"{PARAM}: {task!r} is not a task of this workflow (tasks: {', '.join(task_names)})")
            continue
        if not isinstance(arguments, Mapping):
            problems.append(f'{PARAM}.{task}: must be an object of argument names to values, for example {{"entity": "orders"}}')
            continue
        if len(arguments) > MAX_ARGUMENTS_PER_TASK:
            problems.append(f"{PARAM}.{task}: at most {MAX_ARGUMENTS_PER_TASK} arguments")
        for name, text in arguments.items():
            if not isinstance(name, str) or not ARGUMENT_NAME.fullmatch(name):
                problems.append(f"{PARAM}.{task}: invalid argument name {name!r} (lowercase letters, digits and _, starting with a letter)")
            elif not _printable(text, MAX_VALUE_LENGTH):
                problems.append(f"{PARAM}.{task}.{name}: must be a printable string of 1 to {MAX_VALUE_LENGTH} characters")
    return problems


def task_values(value: Any, task: str) -> dict[str, str]:
    """The trigger values for one task of a checked ``task_args``; ``{}`` when it has none."""
    if not isinstance(value, Mapping):
        return {}
    arguments = value.get(task)
    return dict(arguments) if isinstance(arguments, Mapping) else {}


def effective_args(workflow_args: Sequence[str], values: Mapping[str, str]) -> list[str]:
    """The task's arguments for this run: its workflow ``args`` with the trigger values applied.

    An option given at trigger time is removed from the workflow arguments, in either
    form (``--opt value`` or ``--opt=value``), then every trigger value is appended
    as one ``--opt=value`` token.

    Args:
        workflow_args: The task's ``args`` from the workflow file.
        values: Checked trigger values for this task (argument name to string).

    Returns:
        The arguments to pass after ``--``.
    """
    replaced = {option_name(name) for name in values}
    kept, index = [], 0
    while index < len(workflow_args):
        token = workflow_args[index]
        index += 1
        if token.startswith("--") and token.partition("=")[0] in replaced:
            if "=" not in token and index < len(workflow_args) and not workflow_args[index].startswith("-"):
                index += 1  # its separate value
            continue
        kept.append(token)
    return kept + [f"{option_name(name)}={text}" for name, text in values.items()]
