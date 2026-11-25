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

"""
The results of several experiments in one .zip file.

Each experiment brings the results file of its latest completed execution, as it is
on disk, in the folder of its batch:

    grid_batch-12/
      elaastic_exp-129.json
      mohler_exp-128.json
    experiments/            (the experiments that are in no batch)
      solo_exp-7.json

The paths are found while the database session is open; the zip is then written as
it is sent, a piece of file at a time.
"""

import re
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlmodel import Session, col, select

from results_files import results_path
from tables import Batch, Experiment, ExperimentExecution

LOOSE_FOLDER = "experiments"
CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class Export:
    filename: str
    # (path in the zip, file on disk)
    files: list[tuple[str, Path]]
    # Experiments without a completed execution that has its results file
    skipped: int


def slug(name: str, fallback: str) -> str:
    """`Mistral Large 4` → `mistral-large-4`: safe in a file name, on any system."""
    cleaned = re.sub(r"[^\w]+", "-", name.lower()).strip("-_")
    return cleaned[:80].rstrip("-_") or fallback


def batch_folder(batch: Batch) -> str:
    return f"{slug(batch.name, 'batch')}_batch-{batch.id}"


def experiment_file(experiment: Experiment, batch: Batch | None) -> str:
    # A batch names its experiments `<batch> · <variant>`: the folder already says the batch
    name = experiment.name
    if batch is not None and name.startswith(f"{batch.name} · "):
        name = name.removeprefix(f"{batch.name} · ")
    return f"{slug(name, 'experiment')}_exp-{experiment.id}.json"


def latest_results(
    session: Session, experiment_ids: list[int]
) -> dict[int, Path]:
    """The results file of each experiment's latest completed execution, when it is on disk."""
    executions = session.exec(
        select(ExperimentExecution)
        .where(col(ExperimentExecution.experiment_id).in_(experiment_ids))
        .where(ExperimentExecution.status == "completed")
        .where(col(ExperimentExecution.results_file_path).is_not(None))
        .order_by(col(ExperimentExecution.started_at).desc(), col(ExperimentExecution.id).desc())
    ).all()
    found: dict[int, Path] = {}
    for execution in executions:
        if execution.experiment_id in found:
            continue
        path = results_path(execution)
        if path is not None and path.is_file():
            found[execution.experiment_id] = path
    return found


def build_export(session: Session, experiments: Iterable[Experiment]) -> Export:
    """What the zip of these experiments holds, and how it is called."""
    experiments = sorted(
        {int(e.id): e for e in experiments if e.id is not None}.values(),
        key=lambda e: (e.batch_id is None, e.batch_id or 0, e.id),
    )
    batch_ids = {e.batch_id for e in experiments if e.batch_id is not None}
    batches = (
        {
            int(b.id): b
            for b in session.exec(select(Batch).where(col(Batch.id).in_(batch_ids))).all()
            if b.id is not None
        }
        if batch_ids
        else {}
    )
    results = latest_results(session, [int(e.id) for e in experiments])

    files = []
    for experiment in experiments:
        path = results.get(int(experiment.id))
        if path is None:
            continue
        batch = batches.get(experiment.batch_id) if experiment.batch_id else None
        folder = batch_folder(batch) if batch else LOOSE_FOLDER
        files.append((f"{folder}/{experiment_file(experiment, batch)}", path))

    # Everything from one batch: the zip is named after it
    in_batches = {e.batch_id for e in experiments}
    only = next(iter(in_batches)) if len(in_batches) == 1 else None
    if only is not None and only in batches:
        filename = f"{batch_folder(batches[only])}.zip"
    else:
        filename = f"maestro-results_{datetime.now(UTC):%Y-%m-%d}.zip"
    return Export(filename=filename, files=files, skipped=len(experiments) - len(files))


class _Pipe:
    """A file object that zipfile writes into, and that the response empties."""

    def __init__(self) -> None:
        self.chunks: list[bytes] = []
        self.position = 0

    def write(self, data: bytes) -> int:
        self.chunks.append(bytes(data))
        self.position += len(data)
        return len(data)

    def tell(self) -> int:
        return self.position

    def flush(self) -> None:
        pass

    def drain(self) -> bytes:
        data = b"".join(self.chunks)
        self.chunks.clear()
        return data


def stream_zip(files: list[tuple[str, Path]]) -> Iterator[bytes]:
    """The zip of `files`, written as it is read, so a large export is never held in memory."""
    pipe = _Pipe()
    with zipfile.ZipFile(pipe, "w", compression=zipfile.ZIP_DEFLATED) as archive:  # type: ignore[arg-type]
        for name, path in files:
            info = zipfile.ZipInfo(name, date_time=_date_time(path))
            info.compress_type = zipfile.ZIP_DEFLATED
            with archive.open(info, "w", force_zip64=True) as entry, open(path, "rb") as source:
                while chunk := source.read(CHUNK_SIZE):
                    entry.write(chunk)
                    if data := pipe.drain():
                        yield data
            if data := pipe.drain():
                yield data
    if data := pipe.drain():
        yield data


def _date_time(path: Path) -> tuple[int, int, int, int, int, int]:
    moment = datetime.fromtimestamp(path.stat().st_mtime, UTC)
    # Zip dates start in 1980
    return max(moment, datetime(1980, 1, 1, tzinfo=UTC)).timetuple()[:6]  # type: ignore[return-value]
