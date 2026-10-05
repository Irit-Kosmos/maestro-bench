"""
Where a workspace keeps its files.

Everything the app stores on disk lives under ``<DATA_DIR>/workspaces/<id>/``:
datasets in ``datasets/`` and execution results in ``results/``. The database only
stores a path relative to one of those two folders, and every path read from the
database or from a request goes through ``confine``, so a workspace can never
reach another workspace's files.
"""

import re
from pathlib import Path

from config import DATA_DIR

# Names the app generates itself: a random id and one of the accepted extensions
GENERATED_NAME = re.compile(r"^[0-9a-f]{32}\.(csv|json)$")


def get_data_dir() -> Path:
    return DATA_DIR.resolve()


def workspace_dir(workspace_id: int) -> Path:
    return get_data_dir() / "workspaces" / str(int(workspace_id))


def datasets_dir(workspace_id: int) -> Path:
    return workspace_dir(workspace_id) / "datasets"


def results_dir(workspace_id: int) -> Path:
    return workspace_dir(workspace_id) / "results"


def confine(base: Path, relative: str) -> Path:
    """
    Resolve ``relative`` against ``base``, refusing anything that ends up elsewhere.

    Raises:
        ValueError: If the path is empty, absolute, or leaves ``base`` through
            ``..`` components or a symbolic link.
    """
    if not relative or "\x00" in relative:
        raise ValueError(f"Invalid path: {relative!r}")
    base = base.resolve()
    path = (base / relative).resolve()
    if base not in path.parents:
        raise ValueError(f"Invalid path: {relative!r} must stay inside its folder")
    return path
