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
Full-file read and write of dataset files (CSV, and JSON lists of objects).

CSV cells are handled as strings in both directions so a save never rewrites
values (``1.10`` stays ``1.10``). Writes replace the file atomically and are
guarded by a revision, so a file changed on disk since it was read is never
silently overwritten.
"""

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any

# Datasets are loaded whole by the editor; beyond this the file is refused
MAX_ROWS = 100_000


class DatasetFileError(Exception):
    """A dataset file can't be read or written; carries the HTTP status."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def get_revision(file_path: Path) -> str:
    stat = file_path.stat()
    return f"{stat.st_mtime_ns}-{stat.st_size}"


def _too_large() -> DatasetFileError:
    return DatasetFileError(
        413, f"Dataset has more than {MAX_ROWS:,} rows, too large to open here"
    )


def _read_csv(file_path: Path) -> tuple[list[str], list[dict[str, Any]], str | None]:
    with file_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        headers = next(reader, [])
        rows: list[dict[str, Any]] = []
        has_extra_fields = False
        for record in reader:
            if not record:
                continue
            if len(rows) >= MAX_ROWS:
                raise _too_large()
            if len(record) > len(headers):
                has_extra_fields = True
            record = record[: len(headers)]
            record += [""] * (len(headers) - len(record))
            rows.append(dict(zip(headers, record, strict=True)))

    read_only_reason = None
    if len(set(headers)) != len(headers):
        read_only_reason = "This file has duplicate column names"
    elif has_extra_fields:
        read_only_reason = "Some rows have more values than the header has columns"
    return headers, rows, read_only_reason


def _read_json(file_path: Path) -> tuple[list[str], list[dict[str, Any]], str | None]:
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list) and all(isinstance(row, dict) for row in data):
        if len(data) > MAX_ROWS:
            raise _too_large()
        headers = list(dict.fromkeys(key for row in data for key in row))
        return headers, data, None
    if isinstance(data, dict):
        return list(data.keys()), [data], "This JSON file is a single object"
    return [], [], "Only JSON files holding a list of objects can be edited"


def read_dataset_rows(file_path: Path) -> dict[str, Any]:
    """Return every row of a dataset file with the metadata the editor needs."""
    ext = file_path.suffix.lower()
    revision = get_revision(file_path)

    if ext == ".csv":
        headers, rows, read_only_reason = _read_csv(file_path)
    elif ext == ".json":
        headers, rows, read_only_reason = _read_json(file_path)
    else:
        raise DatasetFileError(400, f"Unsupported file format: {ext}")

    return {
        "file_type": ext.lstrip("."),
        "headers": headers,
        "rows": rows,
        "total_rows": len(rows),
        "revision": revision,
        "read_only_reason": read_only_reason,
    }


def _atomic_write(file_path: Path, write) -> None:
    fd, tmp_name = tempfile.mkstemp(dir=file_path.parent, suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            write(f)
        tmp_path.chmod(file_path.stat().st_mode & 0o777)
        os.replace(tmp_path, file_path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def write_dataset_rows(
    file_path: Path, rows: list[dict[str, Any]], revision: str
) -> dict[str, Any]:
    """Replace the rows of a dataset file; returns its new revision and row count."""
    if get_revision(file_path) != revision:
        raise DatasetFileError(
            409, "The dataset file changed on disk. Reload it before saving."
        )
    if len(rows) > MAX_ROWS:
        raise _too_large()

    current = read_dataset_rows(file_path)
    if current["read_only_reason"]:
        raise DatasetFileError(400, current["read_only_reason"])
    headers = current["headers"]

    if current["file_type"] == "csv":

        def write(f):
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(headers)
            for row in rows:
                writer.writerow(
                    "" if row.get(h) is None else str(row[h]) for h in headers
                )
    else:

        def write(f):
            json.dump(rows, f, ensure_ascii=False, indent=2)
            f.write("\n")

    _atomic_write(file_path, write)
    return {"revision": get_revision(file_path), "total_rows": len(rows)}
