import json

import results_files
from tables import ExperimentExecution
from tests.conftest import TEST_WORKSPACE_ID


def execution_with(path: str | None, workspace_id=TEST_WORKSPACE_ID):
    return ExperimentExecution(
        experiment_id=1,
        dataset_snapshot="{}",
        results_file_path=path,
        workspace_id=workspace_id,
    )


def test_a_relative_path_resolves_inside_the_workspace_results_folder(results_dir):
    file = results_dir / "run.json"
    file.write_text(json.dumps({"rows": []}))

    assert results_files.results_path(execution_with("run.json")) == file


def test_no_stored_path_means_no_file(results_dir):
    assert results_files.results_path(execution_with(None)) is None


def test_paths_outside_the_results_folder_are_refused(results_dir, data_dir):
    outside = results_dir.parent / "secret.json"
    outside.write_text("{}")

    for path in (
        "../secret.json",
        "../../1/secret.json",
        "sub/../../secret.json",
        str(outside),
        "/etc/passwd",
        "",
    ):
        assert results_files.results_path(execution_with(path)) is None, path


def test_a_workspace_cannot_reach_the_results_of_another(results_dir, data_dir):
    other = data_dir / "workspaces" / "2" / "results"
    other.mkdir(parents=True)
    (other / "run.json").write_text(json.dumps({"rows": [{}]}))

    for path in ("../../2/results/run.json", str(other / "run.json")):
        assert results_files.results_path(execution_with(path)) is None, path
    # ...while the owner of that file reads it normally
    assert (
        results_files.results_path(execution_with("run.json", workspace_id=2))
        == other / "run.json"
    )


def test_a_symbolic_link_out_of_the_folder_is_refused(results_dir):
    secret = results_dir.parent / "secret.json"
    secret.write_text("{}")
    (results_dir / "link.json").symlink_to(secret)

    assert results_files.results_path(execution_with("link.json")) is None


def test_the_row_count_ignores_a_path_outside_the_results_folder(results_dir):
    (results_dir.parent / "secret.json").write_text(json.dumps({"rows": [{}, {}]}))

    assert results_files.execution_row_count(execution_with("../secret.json")) is None
