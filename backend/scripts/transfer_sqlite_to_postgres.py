"""
One-shot transfer of a legacy SQLite database into the PostgreSQL database.

The SQLite file is opened read-only and never modified. The target must be at
the latest migration (``alembic upgrade head``) and completely empty.

Usage (from the ``backend`` directory, inside the container):

    uv run python -m scripts.transfer_sqlite_to_postgres --source app.db --dry-run
    uv run python -m scripts.transfer_sqlite_to_postgres --source app.db

``--dry-run`` does everything, including the verification, then rolls back.

Row IDs are kept as they are: they are referenced from JSON columns
(``Analysis.runs``, ``Batch.variations``...). Sequences are realigned after the copy.
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy import Table, create_engine, func, select, text, update
from sqlalchemy.engine import Connection
from sqlmodel import SQLModel

import tables  # noqa: F401  (registers every table on SQLModel.metadata)
from config import DATABASE_URL

metadata = SQLModel.metadata

# Parents before children. ``batch`` and ``experiment`` reference each other:
# ``batch.base_experiment_id`` is filled in once ``experiment`` is copied.
COPY_ORDER = [
    "agentteam",
    "model",
    "prompt",
    "promptversion",
    "agent",
    "dataset",
    "batch",
    "experiment",
    "experimentagentconfig",
    "experimentexecution",
    "agentexecutionsnapshot",
    "analysis",
    "tag",
    "taglink",
]
DEFERRED_COLUMNS = {"batch": ["base_experiment_id"]}


def _fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def _rows(conn: Connection, table: Table) -> list[dict]:
    pk = [c for c in table.primary_key.columns]
    return [dict(r._mapping) for r in conn.execute(select(table).order_by(*pk))]


def check_target_is_empty(target: Connection) -> None:
    for name in COPY_ORDER:
        count = target.execute(select(func.count()).select_from(metadata.tables[name])).scalar_one()
        if count:
            _fail(f"target table {name!r} already has {count} rows; refusing to continue")


def load_source(source: Connection, null_dangling: bool) -> tuple[dict[str, list[dict]], list[str], list[str]]:
    """
    Read every table. SQLite did not enforce foreign keys, so some rows may
    point to nothing. Returns (rows by table, neutralised references, blocking problems).

    With ``null_dangling``, a dangling nullable column is set to NULL in the copy
    (the source is untouched). A dangling NOT NULL column is always blocking.
    """
    data = {name: _rows(source, metadata.tables[name]) for name in COPY_ORDER}
    ids = {name: {row["id"] for row in data[name]} for name in COPY_ORDER if "id" in metadata.tables[name].c}
    neutralised, blocking = [], []
    for name in COPY_ORDER:
        table = metadata.tables[name]
        for fk in table.foreign_key_constraints:
            column = fk.columns[0]
            remote = next(iter(fk.elements)).column
            for row in data[name]:
                value = row[column.name]
                if value is None or value in ids[remote.table.name]:
                    continue
                where = f"{name}.{column.name} -> {remote.table.name}.{remote.name}"
                label = f"{where}: row {_row_label(table, row)} references missing id {value}"
                if null_dangling and column.nullable:
                    row[column.name] = None
                    neutralised.append(label + " (set to NULL)")
                else:
                    blocking.append(label)
    return data, neutralised, blocking


def _row_label(table: Table, row: dict) -> str:
    return ", ".join(f"{c.name}={row[c.name]}" for c in table.primary_key.columns)


def copy_tables(data: dict[str, list[dict]], target: Connection) -> dict[str, int]:
    counts = {}
    for name in COPY_ORDER:
        table = metadata.tables[name]
        rows = data[name]
        deferred = DEFERRED_COLUMNS.get(name, [])
        if rows:
            target.execute(
                table.insert(),
                [{k: (None if k in deferred else v) for k, v in row.items()} for row in rows],
            )
        for column in deferred:
            for row in rows:
                if row[column] is not None:
                    target.execute(
                        update(table).where(table.c.id == row["id"]).values({column: row[column]})
                    )
        counts[name] = len(rows)
    return counts


def realign_sequences(target: Connection) -> None:
    for name in COPY_ORDER:
        table = metadata.tables[name]
        if "id" not in table.c or not table.c.id.primary_key or len(table.primary_key.columns) != 1:
            continue
        target.execute(
            text(
                f"SELECT setval(pg_get_serial_sequence('{name}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {name}), 1), "
                f"(SELECT MAX(id) FROM {name}) IS NOT NULL)"
            )
        )


def verify(data: dict[str, list[dict]], target: Connection) -> list[str]:
    """Compare every row of every table, value by value."""
    problems = []
    for name in COPY_ORDER:
        table = metadata.tables[name]
        src, dst = data[name], _rows(target, table)
        if len(src) != len(dst):
            problems.append(f"{name}: {len(src)} rows in source, {len(dst)} in target")
        elif src != dst:
            bad = next(i for i, (a, b) in enumerate(zip(src, dst, strict=True)) if a != b)
            diff = [k for k in src[bad] if src[bad][k] != dst[bad][k]]
            problems.append(f"{name}: row {bad} differs on columns {diff}")
    return problems


def check_result_files(source: Connection, root: Path) -> list[str]:
    table = metadata.tables["experimentexecution"]
    missing = []
    for row in source.execute(select(table.c.id, table.c.results_file_path)):
        if row.results_file_path and not (root / row.results_file_path).is_file():
            missing.append(f"execution {row.id}: {row.results_file_path}")
    return missing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--source", required=True, help="path to the legacy SQLite file")
    parser.add_argument("--results-root", default=".", help="directory results_file_path is relative to")
    parser.add_argument("--dry-run", action="store_true", help="copy and verify, then roll back")
    parser.add_argument(
        "--null-dangling",
        action="store_true",
        help="set dangling nullable references to NULL in the copy (each one is reported)",
    )
    args = parser.parse_args()

    source_path = Path(args.source).resolve()
    if not source_path.is_file():
        _fail(f"{source_path} does not exist")

    source_engine = create_engine(f"sqlite:///file:{source_path}?mode=ro&uri=true")
    target_engine = create_engine(DATABASE_URL, connect_args={"options": "-c timezone=utc"})

    with source_engine.connect() as source:
        data, neutralised, blocking = load_source(source, args.null_dangling)
        if blocking:
            print("Dangling references in the source database:")
            for line in blocking:
                print(f"  - {line}")
            _fail("use --null-dangling for nullable columns, or fix the rows; nothing was written")
        if neutralised:
            print(f"{len(neutralised)} dangling reference(s) neutralised in the copy:")
            for line in neutralised:
                print(f"  - {line}")

        missing_files = check_result_files(source, Path(args.results_root))
        if missing_files:
            print(f"WARNING: {len(missing_files)} results files are missing under {args.results_root!r}:")
            for line in missing_files[:20]:
                print(f"  - {line}")

        with target_engine.connect() as target:
            version = target.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
            if version is None:
                _fail("target is not migrated: run `alembic upgrade head` first")
            check_target_is_empty(target)
            target.rollback()  # end the read-only checks; the copy gets its own transaction

            transaction = target.begin()
            counts = copy_tables(data, target)
            realign_sequences(target)
            problems = verify(data, target)
            if problems:
                transaction.rollback()
                print("Verification failed, everything was rolled back:")
                for line in problems:
                    print(f"  - {line}")
                sys.exit(1)

            if args.dry_run:
                transaction.rollback()
                print("DRY RUN OK (rolled back). Rows that would be copied:")
            else:
                transaction.commit()
                print("Transfer committed and verified. Rows copied:")
            for name, count in counts.items():
                print(f"  {name:24s} {count}")
            print(f"Result files missing: {len(missing_files)}")


if __name__ == "__main__":
    main()
