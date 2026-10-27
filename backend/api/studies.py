# MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
# Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
# Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlmodel import Session, col, delete, select

from auth.workspaces import WorkspaceContext, workspace_context
from batch_utils import batch_status
from db import SessionDep
from execution_stats import latest_figures
from loading import by_id, grouped_by
from schemas.studies import (
    ActivityEvent,
    ActivityItem,
    StudyAssign,
    StudyCounts,
    StudyCreate,
    StudyDetailResponse,
    StudyItemRef,
    StudyItemResponse,
    StudyItemsAdd,
    StudyKind,
    StudyMembership,
    StudyResponse,
    StudyUpdate,
)
from schemas.tags import TagResponse
from study_utils import check_items_exist, clear_item_journal, note_responses, people
from tables import (
    Analysis,
    Batch,
    Dataset,
    Experiment,
    ExperimentExecution,
    Note,
    Study,
    StudyItem,
)
from tag_utils import clear_item_tags, set_item_tags, tags_by_item
from workspace_scope import current_user_id

router = APIRouter(tags=["studies"])

ContextDep = Annotated[WorkspaceContext, Depends(workspace_context)]


# ---------------------------------------------------------------------------
# What a study gathers
# ---------------------------------------------------------------------------


@dataclass
class _Gathered:
    """What a few studies hold, loaded in a fixed number of queries.

    `links_of` lists a study's items, the most recently added first. Experiments
    are those of the studies' batches; the executions are those of every experiment
    the studies hold, directly or through a batch.
    """

    links_of: dict[int, list[StudyItem]]
    batch_experiments: dict[int, list[Experiment]]
    executions_of: dict[int, list[ExperimentExecution]]

    def experiment_ids(self, study: Study) -> set[int]:
        """The experiments of a study, each once: its own and those of its batches."""
        ids: set[int] = set()
        for link in self.links_of[study.id]:
            if link.kind == "experiment":
                ids.add(link.item_id)
            elif link.kind == "batch":
                ids.update(e.id for e in self.batch_experiments[link.item_id])
        return ids


def _gather(session: Session, studies: list[Study]) -> _Gathered:
    links_of = grouped_by(
        session,
        StudyItem,
        StudyItem.study_id,
        [s.id for s in studies],
        col(StudyItem.added_at).desc(),
        col(StudyItem.item_id).desc(),
    )
    links = [link for study in studies for link in links_of[study.id]]
    batch_experiments = grouped_by(
        session,
        Experiment,
        Experiment.batch_id,
        [link.item_id for link in links if link.kind == "batch"],
        col(Experiment.id),
    )
    experiment_ids = {link.item_id for link in links if link.kind == "experiment"}
    experiment_ids.update(
        e.id for experiments in batch_experiments.values() for e in experiments
    )
    executions_of = grouped_by(
        session,
        ExperimentExecution,
        ExperimentExecution.experiment_id,
        experiment_ids,
        col(ExperimentExecution.started_at).desc(),
    )
    return _Gathered(links_of, batch_experiments, executions_of)


def _sum(values: list[int | float]) -> int | float | None:
    return sum(values) if values else None


def _figures(experiment_ids: set[int], gathered: _Gathered) -> dict:
    """Executions, tokens and cost over experiments: the latest execution of each counts."""
    figures = [latest_figures(gathered.executions_of[i]) for i in experiment_ids]
    return {
        "execution_count": sum(f["execution_count"] for f in figures),
        "total_tokens": _sum(
            [f["total_tokens"] for f in figures if f["total_tokens"] is not None]
        ),
        "total_cost_usd": _sum(
            [f["total_cost_usd"] for f in figures if f["total_cost_usd"] is not None]
        ),
    }


def _study_responses(
    session: Session, studies: list[Study], gathered: _Gathered
) -> list[StudyResponse]:
    tags = tags_by_item(session, "study", [s.id for s in studies])
    authors = people(session, (s.created_by for s in studies))
    responses = []
    for study in studies:
        kinds = Counter(link.kind for link in gathered.links_of[study.id])
        responses.append(
            StudyResponse(
                id=study.id,
                name=study.name,
                description=study.description,
                status=study.status,
                tags=[TagResponse.model_validate(t) for t in tags.get(study.id, [])],
                author=authors.get(study.created_by) if study.created_by else None,
                counts=StudyCounts(
                    experiments=kinds["experiment"],
                    batches=kinds["batch"],
                    analyses=kinds["analysis"],
                ),
                **_figures(gathered.experiment_ids(study), gathered),
                created_at=study.created_at,
                updated_at=study.updated_at,
            )
        )
    return responses


def _item_responses(
    session: Session, study: Study, gathered: _Gathered
) -> list[StudyItemResponse]:
    links = gathered.links_of[study.id]

    def ids(kind: str) -> list[int]:
        return [link.item_id for link in links if link.kind == kind]

    experiments = by_id(session, Experiment, ids("experiment"))
    batches = by_id(session, Batch, ids("batch"))
    analyses = by_id(session, Analysis, ids("analysis"))
    first_of_batch = {
        batch_id: found[0]
        for batch_id, found in gathered.batch_experiments.items()
        if found
    }
    datasets = by_id(
        session,
        Dataset,
        [e.dataset_id for e in experiments.values()]
        + [e.dataset_id for e in first_of_batch.values()],
    )
    authors = people(session, (link.added_by for link in links))

    items = []
    for link in links:
        added = {
            "added_at": link.added_at,
            "added_by": authors.get(link.added_by) if link.added_by else None,
        }
        if link.kind == "experiment":
            experiment = experiments.get(link.item_id)
            if experiment is None:
                continue
            dataset = datasets.get(experiment.dataset_id)
            items.append(
                StudyItemResponse(
                    kind="experiment",
                    item_id=experiment.id,
                    name=experiment.name,
                    status=experiment.status,
                    dataset_name=dataset.name if dataset else None,
                    **_figures({experiment.id}, gathered),
                    created_at=experiment.created_at,
                    **added,
                )
            )
        elif link.kind == "batch":
            batch = batches.get(link.item_id)
            if batch is None:
                continue
            members = gathered.batch_experiments[batch.id]
            first = first_of_batch.get(batch.id)
            dataset = datasets.get(first.dataset_id) if first else None
            items.append(
                StudyItemResponse(
                    kind="batch",
                    item_id=batch.id,
                    name=batch.name,
                    status=batch_status([e.status for e in members]),
                    dataset_name=dataset.name if dataset else None,
                    experiment_count=len(members),
                    **_figures({e.id for e in members}, gathered),
                    created_at=batch.created_at,
                    **added,
                )
            )
        else:
            analysis = analyses.get(link.item_id)
            if analysis is None:
                continue
            items.append(
                StudyItemResponse(
                    kind="analysis",
                    item_id=analysis.id,
                    name=analysis.name,
                    created_at=analysis.created_at,
                    **added,
                )
            )
    return items


def _detail(session: Session, study: Study) -> StudyDetailResponse:
    gathered = _gather(session, [study])
    base = _study_responses(session, [study], gathered)[0]
    return StudyDetailResponse(
        **base.model_dump(), items=_item_responses(session, study, gathered)
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get(session: Session, study_id: int) -> Study:
    study = session.get(Study, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    return study


def _archived(study: Study) -> HTTPException:
    return HTTPException(
        status_code=409, detail=f'Study "{study.name}" is archived: it is read-only'
    )


def _get_writable(session: Session, study_id: int) -> Study:
    study = _get(session, study_id)
    if study.status == "archived":
        raise _archived(study)
    return study


def _checked_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="A study needs a name")
    return cleaned


def _touch(study: Study) -> None:
    study.updated_at = datetime.now(UTC)


def _add_items(session: Session, study: Study, refs: list[StudyItemRef]) -> None:
    """Put items in the study, leaving out those already there. Nothing is committed."""
    wanted: dict[str, set[int]] = {}
    for ref in refs:
        wanted.setdefault(ref.kind, set()).add(ref.item_id)
    for kind, item_ids in wanted.items():
        check_items_exist(session, kind, item_ids)

    present = set(
        session.exec(
            select(StudyItem.kind, StudyItem.item_id).where(
                StudyItem.study_id == study.id
            )
        ).all()
    )
    user_id = current_user_id(session)
    for kind, item_ids in wanted.items():
        for item_id in sorted(item_ids):
            if (kind, item_id) not in present:
                session.add(
                    StudyItem(
                        study_id=study.id, kind=kind, item_id=item_id, added_by=user_id
                    )
                )
    if wanted:
        _touch(study)
        session.add(study)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/studies", response_model=list[StudyResponse])
def list_studies(session: SessionDep):
    """Every study, the most recently touched first."""
    studies = list(
        session.exec(
            select(Study).order_by(col(Study.updated_at).desc(), col(Study.id).desc())
        ).all()
    )
    return _study_responses(session, studies, _gather(session, studies))


@router.get("/studies/memberships", response_model=list[StudyMembership])
def list_memberships(kind: StudyKind, session: SessionDep):
    """Which studies each item of a kind is in, to show on lists and to pick from."""
    rows = session.exec(
        select(StudyItem.study_id, StudyItem.item_id)
        .where(StudyItem.kind == kind)
        .order_by(col(StudyItem.study_id), col(StudyItem.item_id))
    ).all()
    return [StudyMembership(study_id=s, item_id=i) for s, i in rows]


@router.post("/studies/assign", status_code=204)
def assign_studies(data: StudyAssign, session: SessionDep):
    """Put items in several studies, take them out, or both, in one go.

    A study in both lists gets the items. An archived study is read-only.
    """
    check_items_exist(session, data.kind, data.item_ids)
    items = set(data.item_ids)
    to_add = set(data.add)
    to_remove = set(data.remove) - to_add

    studies = by_id(session, Study, to_add | to_remove)
    if missing := (to_add | to_remove) - studies.keys():
        raise HTTPException(
            status_code=422, detail=f"Unknown studies: {sorted(missing)}"
        )
    for study in studies.values():
        if study.status == "archived":
            raise _archived(study)

    if to_remove:
        session.exec(
            delete(StudyItem).where(
                StudyItem.kind == data.kind,
                col(StudyItem.item_id).in_(items),
                col(StudyItem.study_id).in_(to_remove),
            )
        )
    if to_add:
        present = set(
            session.exec(
                select(StudyItem.study_id, StudyItem.item_id).where(
                    StudyItem.kind == data.kind,
                    col(StudyItem.item_id).in_(items),
                    col(StudyItem.study_id).in_(to_add),
                )
            ).all()
        )
        user_id = current_user_id(session)
        for study_id in sorted(to_add):
            for item_id in sorted(items):
                if (study_id, item_id) not in present:
                    session.add(
                        StudyItem(
                            study_id=study_id,
                            kind=data.kind,
                            item_id=item_id,
                            added_by=user_id,
                        )
                    )
    for study in studies.values():
        _touch(study)
        session.add(study)
    session.commit()


@router.post("/studies", response_model=StudyDetailResponse, status_code=201)
def create_study(data: StudyCreate, session: SessionDep):
    study = Study(name=_checked_name(data.name), description=data.description)
    session.add(study)
    session.flush()
    set_item_tags(session, "study", study.id, data.tag_ids)
    _add_items(session, study, data.items)
    session.commit()
    session.refresh(study)
    return _detail(session, study)


@router.get("/studies/{study_id}", response_model=StudyDetailResponse)
def get_study(study_id: int, session: SessionDep):
    return _detail(session, _get(session, study_id))


@router.put("/studies/{study_id}", response_model=StudyDetailResponse)
def update_study(study_id: int, data: StudyUpdate, session: SessionDep):
    """Rename, describe, tag or change the status of a study.

    An archived study only changes its status, to leave the archive.
    """
    study = _get(session, study_id)
    if study.status == "archived" and data.status in (None, "archived"):
        raise _archived(study)

    if data.name is not None:
        study.name = _checked_name(data.name)
    if "description" in data.model_fields_set:
        study.description = data.description
    if data.status is not None:
        study.status = data.status
    if data.tag_ids is not None:
        set_item_tags(session, "study", study.id, data.tag_ids)
    _touch(study)
    session.add(study)
    session.commit()
    session.refresh(study)
    return _detail(session, study)


@router.delete("/studies/{study_id}", status_code=204)
def delete_study(study_id: int, session: SessionDep):
    """Delete a study with its notes. What it gathered is left as it is."""
    study = _get(session, study_id)
    clear_item_tags(session, "study", study.id)
    session.exec(delete(StudyItem).where(StudyItem.study_id == study.id))
    clear_item_journal(session, "study", study.id)
    session.delete(study)
    session.commit()


@router.post("/studies/{study_id}/items", response_model=StudyDetailResponse)
def add_items(study_id: int, data: StudyItemsAdd, session: SessionDep):
    study = _get_writable(session, study_id)
    _add_items(session, study, data.items)
    session.commit()
    session.refresh(study)
    return _detail(session, study)


@router.delete("/studies/{study_id}/items/{kind}/{item_id}", status_code=204)
def remove_item(study_id: int, kind: StudyKind, item_id: int, session: SessionDep):
    """Take an item out of a study. The item itself, and its notes, stay."""
    study = _get_writable(session, study_id)
    link = session.get(StudyItem, (study_id, kind, item_id))
    if not link:
        raise HTTPException(status_code=404, detail="This item is not in the study")
    session.delete(link)
    _touch(study)
    session.add(study)
    session.commit()


@router.get("/studies/{study_id}/activity", response_model=list[ActivityEvent])
def study_activity(
    study_id: int,
    session: SessionDep,
    context: ContextDep,
    limit: Annotated[int, Query(ge=1, le=300)] = 100,
):
    """The timeline of a study, newest first.

    It is worked out from what the study already holds: the moments items were added,
    the experiments that completed, and the notes about the study and about its items.
    An item taken out of the study leaves the timeline.
    """
    study = _get(session, study_id)
    gathered = _gather(session, [study])
    links = gathered.links_of[study.id]

    def ids(kind: str) -> list[int]:
        return [link.item_id for link in links if link.kind == kind]

    experiments = by_id(session, Experiment, ids("experiment"))
    batches = by_id(session, Batch, ids("batch"))
    analyses = by_id(session, Analysis, ids("analysis"))
    names = {
        "study": {study.id: study.name},
        "experiment": {i: e.name for i, e in experiments.items()},
        "batch": {i: b.name for i, b in batches.items()},
        "analysis": {i: a.name for i, a in analyses.items()},
    }
    # The experiments of the study's batches are part of its story too
    batch_members = [e for found in gathered.batch_experiments.values() for e in found]
    for experiment in batch_members:
        names["experiment"].setdefault(experiment.id, experiment.name)
    authors = people(session, (link.added_by for link in links))

    events: list[ActivityEvent] = []
    for link in links:
        name = names[link.kind].get(link.item_id)
        if name is None:
            continue
        events.append(
            ActivityEvent(
                type="item_added",
                at=link.added_at,
                actor=authors.get(link.added_by) if link.added_by else None,
                item=ActivityItem(kind=link.kind, item_id=link.item_id, name=name),
            )
        )
    held = {e.id: e for e in [*experiments.values(), *batch_members]}
    events.extend(
        ActivityEvent(
            type="experiment_completed",
            at=experiment.completed_at,
            item=ActivityItem(
                kind="experiment", item_id=experiment.id, name=experiment.name
            ),
        )
        for experiment in held.values()
        if experiment.completed_at is not None
    )

    # The study's own notes, and those of the items it holds (not of a batch's experiments)
    about = [and_(Note.kind == "study", Note.item_id == study.id)]
    about += [
        and_(Note.kind == kind, col(Note.item_id).in_(item_ids))
        for kind in ("experiment", "batch", "analysis")
        if (item_ids := ids(kind))
    ]
    notes = list(
        session.exec(
            select(Note)
            .where(or_(*about))
            .order_by(col(Note.created_at).desc(), col(Note.id).desc())
            .limit(limit)
        ).all()
    )
    for note, response in zip(
        notes, note_responses(session, notes, context), strict=True
    ):
        name = names[note.kind].get(note.item_id)
        if name is None:
            continue
        events.append(
            ActivityEvent(
                type="note",
                at=note.created_at,
                actor=response.author,
                item=ActivityItem(kind=note.kind, item_id=note.item_id, name=name),
                note=response,
            )
        )

    events.sort(key=lambda event: event.at, reverse=True)
    return events[:limit]
