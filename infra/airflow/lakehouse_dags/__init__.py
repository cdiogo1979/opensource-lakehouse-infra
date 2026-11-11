"""The lakehouse platform's DAG factory for data product repositories.

A product repository's only DAG file is the stub (``spec.STUB_TEXT``)::

    from lakehouse_dags import load_workflows
    load_workflows(globals(), __file__)

Mounted read-only into the Airflow dag-processor and scheduler (and Jenkins, for
``python3 -m lakehouse_dags.validate``). Only ``load_workflows`` imports Airflow,
so ``spec``, ``identity`` and ``validate`` work without it.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, MutableMapping

from .spec import WorkflowError, load_materialized_views, load_repository


def load_workflows(namespace: MutableMapping[str, Any], stub_file: str) -> None:
    """Build one DAG per ``workflows/*.json`` of the stub's checkout into ``namespace`` (BR-9).

    Every file is validated before any DAG is built; any problem raises one
    ``WorkflowError`` listing them all, so Airflow shows it as an import error.
    """
    from .identity import identity_for

    root = Path(stub_file).resolve().parents[1]
    workflows, problems = load_repository(root)
    found, view_problems = load_materialized_views(root)
    problems += view_problems
    if problems:
        raise WorkflowError(problems)
    if not workflows and not found:
        return
    identity = identity_for(Path(stub_file))
    from .factory import build_dag, build_mv_dag

    views = {view.name: view.statement for view in found}
    dags = [build_dag(workflow, root, identity, views) for workflow in workflows]
    if views:
        dags.append(build_mv_dag(views, identity))
    for dag in dags:
        namespace["dag_" + re.sub(r"[^0-9a-zA-Z_]", "_", dag.dag_id)] = dag
