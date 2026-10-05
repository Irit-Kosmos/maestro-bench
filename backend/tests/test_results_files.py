import json

import results_files
from tables import ExperimentExecution


def execution_with(path: str | None) -> ExperimentExecution:
    return ExperimentExecution(
        experiment_id=1, dataset_snapshot="{}", results_file_path=path
    )


def test_a_relative_path_resolves_inside_the_data_directory(data_dir):
    (data_dir / "results").mkdir()
    file = data_dir / "results" / "run.json"
    file.write_text(json.dumps({"rows": []}))

    assert results_files.results_path(execution_with("results/run.json")) == file


def test_no_stored_path_means_no_file(data_dir):
    assert results_files.results_path(execution_with(None)) is None


def test_paths_outside_the_results_directory_are_refused(data_dir):
    outside = data_dir / "secret.json"
    outside.write_text("{}")

    for path in (
        "../secret.json",
        "results/../secret.json",
        "secret.json",
        str(outside),
        "/etc/passwd",
    ):
        assert results_files.results_path(execution_with(path)) is None, path


def test_the_row_count_ignores_a_path_outside_the_results_directory(data_dir):
    (data_dir / "secret.json").write_text(json.dumps({"rows": [{}, {}]}))

    assert results_files.execution_row_count(execution_with("secret.json")) is None
