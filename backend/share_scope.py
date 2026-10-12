"""
What a public link lets its holder read.

A link covers its item and what lies strictly below it, nothing else:

- an experiment: its executions;
- a batch: its experiments, and their executions (not the experiment it was derived from);
- an analysis: the executions it compares (not their experiments);
- a study: what it gathers, each item as above.

The scope is worked out in a session confined to the workspace of the link, so a row of
another workspace is never in it.
"""

import json
from collections.abc import Iterable
from dataclasses import dataclass

from sqlmodel import Session, SQLModel, col, select

from tables import (
    Analysis,
    Batch,
    Experiment,
    ExperimentExecution,
    Study,
    StudyItem,
)

ROOT_TABLES: dict[str, type[SQLModel]] = {
    "study": Study,
    "batch": Batch,
    "experiment": Experiment,
    "analysis": Analysis,
}


@dataclass(frozen=True)
class Scope:
    """The ids a link reaches, by kind."""

    root_found: bool
    studies: frozenset[int]
    batches: frozenset[int]
    experiments: frozenset[int]
    analyses: frozenset[int]
    executions: frozenset[int]

    def ids(self, kind: str) -> frozenset[int]:
        return {
            "study": self.studies,
            "batch": self.batches,
            "experiment": self.experiments,
            "analysis": self.analyses,
            "execution": self.executions,
        }[kind]


def _existing(session: Session, table: type[SQLModel], ids: Iterable[int]) -> set[int]:
    wanted = set(ids)
    if not wanted:
        return set()
    return set(session.exec(select(table.id).where(col(table.id).in_(wanted))).all())


def _run_executions(analyses: Iterable[Analysis]) -> set[int]:
    return {
        run["execution_id"]
        for analysis in analyses
        for run in json.loads(analysis.runs)
        if isinstance(run, dict) and isinstance(run.get("execution_id"), int)
    }


def scope_of(session: Session, kind: str, item_id: int) -> Scope:
    """The scope of a link to this item, in a session confined to the link's workspace."""
    root = session.get(ROOT_TABLES[kind], item_id)

    gathered: dict[str, set[int]] = {"experiment": set(), "batch": set(), "analysis": set()}
    studies: set[int] = set()
    if root is not None and kind == "study":
        studies.add(item_id)
        for item_kind, gathered_id in session.exec(
            select(StudyItem.kind, StudyItem.item_id).where(StudyItem.study_id == item_id)
        ).all():
            gathered[item_kind].add(gathered_id)
    elif root is not None:
        gathered[kind].add(item_id)

    batches = _existing(session, Batch, gathered["batch"])
    experiments = _existing(session, Experiment, gathered["experiment"])
    if batches:
        experiments |= set(
            session.exec(
                select(Experiment.id).where(col(Experiment.batch_id).in_(batches))
            ).all()
        )
    analyses = (
        list(
            session.exec(
                select(Analysis).where(col(Analysis.id).in_(gathered["analysis"]))
            ).all()
        )
        if gathered["analysis"]
        else []
    )

    executions: set[int] = set()
    if experiments:
        executions |= set(
            session.exec(
                select(ExperimentExecution.id).where(
                    col(ExperimentExecution.experiment_id).in_(experiments)
                )
            ).all()
        )
    executions |= _existing(session, ExperimentExecution, _run_executions(analyses))

    return Scope(
        root_found=root is not None,
        studies=frozenset(studies),
        batches=frozenset(batches),
        experiments=frozenset(experiments),
        analyses=frozenset(a.id for a in analyses),
        executions=frozenset(executions),
    )
