import asyncio

import pytest

import async_jobs
import experiment_utils
from async_jobs import _ExperimentProcessor
from dataset_utils import count_csv_rows

CSV = "id,text\n" + "".join(f"{i},row {i}\n" for i in range(1, 13))


@pytest.fixture
def dataset(tmp_path, monkeypatch):
    path = tmp_path / "answers.csv"
    path.write_text(CSV)
    for module in (async_jobs, experiment_utils):
        monkeypatch.setattr(module, "validate_dataset_file", lambda _: path)
    return "answers.csv"


async def open_dataset(dataset, sampling_config):
    processor = _ExperimentProcessor(progress=None, chunk_size=5)
    chunks, total = await processor._open_dataset(dataset, sampling_config)
    return total, sum([len(chunk) async for chunk in chunks])


@pytest.mark.parametrize(
    "sampling_config",
    [
        {"sampling_type": "all"},
        {"sampling_type": None},
        {"sampling_type": "random", "sampling_size": 4, "sampling_seed": 1},
        {"sampling_type": "random", "sampling_size": 50, "sampling_seed": 1},
        {"sampling_type": "range", "sampling_start_row": 3, "sampling_end_row": 9},
        {"sampling_type": "range", "sampling_start_row": 3, "sampling_end_row": 50},
        {"sampling_type": "range", "sampling_start_row": 4},
    ],
)
def test_total_is_the_number_of_rows_actually_run(dataset, sampling_config):
    total, run = asyncio.run(open_dataset(dataset, sampling_config))

    assert total == run


def test_counts_data_rows_only(tmp_path):
    path = tmp_path / "a.csv"
    path.write_text("id,text\n1,a\n2,b\n")

    assert count_csv_rows(path) == 2


def test_counts_records_spanning_lines_once(tmp_path):
    path = tmp_path / "a.csv"
    path.write_text('id,text\n1,"two\nlines"\n2,b\n')

    assert count_csv_rows(path) == 2


def test_ignores_blank_lines_and_bom(tmp_path):
    path = tmp_path / "a.csv"
    path.write_text("﻿id,text\n1,a\n\n2,b\n\n", encoding="utf-8")

    assert count_csv_rows(path) == 2


@pytest.mark.parametrize("content", ["", "id,text\n"])
def test_file_without_data_has_no_rows(tmp_path, content):
    path = tmp_path / "a.csv"
    path.write_text(content)

    assert count_csv_rows(path) == 0
