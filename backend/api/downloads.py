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

"""The results of batches and experiments, in one .zip file (see `results_export`)."""

from collections.abc import Sequence
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, col, select

from db import SessionDep
from results_export import build_export, stream_zip
from tables import Batch, Experiment

router = APIRouter(tags=["downloads"])

MAX_BATCHES = 50
MAX_EXPERIMENTS = 1000
# How many experiments had no results to bring: the page says so
SKIPPED_HEADER = "X-Skipped-Experiments"


def _zip_response(session: Session, experiments: Sequence[Experiment]) -> StreamingResponse:
    export = build_export(session, experiments)
    if not export.files:
        raise HTTPException(
            status_code=404,
            detail="None of these experiments has completed results yet",
        )
    ascii_name = export.filename.encode("ascii", "replace").decode().replace("?", "_")
    return StreamingResponse(
        stream_zip(export.files),
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_name}"; '
                f"filename*=UTF-8''{quote(export.filename)}"
            ),
            SKIPPED_HEADER: str(export.skipped),
        },
    )


@router.get("/batches/{batch_id}/results")
def download_batch_results(batch_id: int, session: SessionDep):
    """The results of every experiment of the batch."""
    batch = session.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    experiments = session.exec(
        select(Experiment).where(Experiment.batch_id == batch_id)
    ).all()
    return _zip_response(session, experiments)


@router.get("/results/download")
def download_results(
    session: SessionDep,
    batch_id: Annotated[list[int] | None, Query()] = None,
    experiment_id: Annotated[list[int] | None, Query()] = None,
):
    """The results of these batches (all their experiments) and of these experiments."""
    batch_ids = set(batch_id or [])
    experiment_ids = set(experiment_id or [])
    if not batch_ids and not experiment_ids:
        raise HTTPException(status_code=422, detail="Pick at least one batch or experiment")
    if len(batch_ids) > MAX_BATCHES:
        raise HTTPException(
            status_code=422, detail=f"At most {MAX_BATCHES} batches can be downloaded at once"
        )

    experiments: list[Experiment] = []
    if batch_ids:
        found = session.exec(select(Batch.id).where(col(Batch.id).in_(batch_ids))).all()
        if len(found) != len(batch_ids):
            raise HTTPException(status_code=404, detail="Batch not found")
        experiments += session.exec(
            select(Experiment).where(col(Experiment.batch_id).in_(batch_ids))
        ).all()
    if experiment_ids:
        chosen = session.exec(
            select(Experiment).where(col(Experiment.id).in_(experiment_ids))
        ).all()
        if len(chosen) != len(experiment_ids):
            raise HTTPException(status_code=404, detail="Experiment not found")
        experiments += chosen
    if len({e.id for e in experiments}) > MAX_EXPERIMENTS:
        raise HTTPException(
            status_code=422,
            detail=f"At most {MAX_EXPERIMENTS} experiments can be downloaded at once",
        )
    return _zip_response(session, experiments)
