import json

import pytest
from sqlmodel import select

from api import agents, analyses, prompts, tags
from tables import Dataset, Experiment, ExperimentExecution, TagLink
from tests.conftest import api_client, scoped


@pytest.fixture
def client(engine):
    return api_client(engine, tags, prompts, analyses, agents)


def make_tag(client, name, color="gray"):
    response = client.post("/tags", json={"name": name, "color": color})
    assert response.status_code == 201, response.text
    return response.json()


ANALYSIS = {
    "name": "Graders",
    "config": {
        "truth_column": "score",
        "value_type": "numeric",
        "metrics": ["rmse"],
    },
    "runs": [],
}


def test_create_normalizes_the_name(client):
    tag = make_tag(client, "  needs   review ", "red")
    assert tag["name"] == "needs review"
    assert tag["color"] == "red"


def test_create_refuses_a_name_that_exists_ignoring_case(client):
    make_tag(client, "Extraction")
    response = client.post("/tags", json={"name": "extraction ", "color": "blue"})
    assert response.status_code == 409


def test_create_refuses_a_blank_name_and_an_unknown_color(client):
    assert client.post("/tags", json={"name": "   "}).status_code == 422
    response = client.post("/tags", json={"name": "x", "color": "chartreuse"})
    assert response.status_code == 422


def test_update_renames_and_recolors(client):
    tag = make_tag(client, "wip")
    response = client.put(f"/tags/{tag['id']}", json={"color": "amber"})
    assert response.json()["color"] == "amber"
    assert response.json()["name"] == "wip"

    response = client.put(f"/tags/{tag['id']}", json={"name": "draft"})
    assert response.json()["name"] == "draft"


def test_rename_to_another_tags_name_is_refused(client):
    make_tag(client, "prod")
    wip = make_tag(client, "wip")
    assert client.put(f"/tags/{wip['id']}", json={"name": "PROD"}).status_code == 409
    # Changing only the case of its own name is fine
    assert client.put(f"/tags/{wip['id']}", json={"name": "WIP"}).status_code == 200


def test_list_sorts_by_name(client):
    zed = make_tag(client, "zed")
    alpha = make_tag(client, "Alpha")

    listed = client.get("/tags").json()
    assert [t["id"] for t in listed] == [alpha["id"], zed["id"]]


def test_prompt_tags_are_set_replaced_and_kept(client):
    a, b = make_tag(client, "a"), make_tag(client, "b")
    prompt = client.post(
        "/prompts", json={"name": "Grader", "tag_ids": [b["id"], a["id"]]}
    ).json()
    assert [t["name"] for t in prompt["tags"]] == ["a", "b"]

    # Not sent: untouched
    client.put(f"/prompts/{prompt['id']}", json={"name": "Grader 2"})
    assert len(client.get(f"/prompts/{prompt['id']}").json()["tags"]) == 2

    # Sent: replaced
    updated = client.put(f"/prompts/{prompt['id']}", json={"tag_ids": [a["id"]]})
    assert [t["name"] for t in updated.json()["tags"]] == ["a"]

    cleared = client.put(f"/prompts/{prompt['id']}", json={"tag_ids": []})
    assert cleared.json()["tags"] == []


def test_prompt_list_carries_each_prompts_tags(client):
    a = make_tag(client, "a")
    tagged = client.post("/prompts", json={"name": "T", "tag_ids": [a["id"]]}).json()
    client.post("/prompts", json={"name": "U"})

    by_id = {p["id"]: p["tags"] for p in client.get("/prompts").json()}
    assert [t["name"] for t in by_id[tagged["id"]]] == ["a"]
    assert sorted(len(t) for t in by_id.values()) == [0, 1]


def test_unknown_tag_ids_are_refused(client):
    response = client.post("/prompts", json={"name": "P", "tag_ids": [999]})
    assert response.status_code == 422
    assert client.get("/prompts").json() == []


def test_analysis_tags_are_set_and_replaced(client):
    a, b = make_tag(client, "a"), make_tag(client, "b")
    created = client.post("/analyses", json={**ANALYSIS, "tag_ids": [a["id"]]})
    assert created.status_code == 201, created.text
    analysis = created.json()
    assert [t["name"] for t in analysis["tags"]] == ["a"]

    updated = client.put(f"/analyses/{analysis['id']}", json={"tag_ids": [b["id"]]})
    assert [t["name"] for t in updated.json()["tags"]] == ["b"]

    listed = client.get("/analyses").json()
    assert [t["name"] for t in listed[0]["tags"]] == ["b"]


def test_deleting_a_tag_takes_it_off_its_items(client, engine):
    a = make_tag(client, "a")
    prompt = client.post("/prompts", json={"name": "P", "tag_ids": [a["id"]]}).json()

    assert client.delete(f"/tags/{a['id']}").status_code == 204
    assert client.get(f"/prompts/{prompt['id']}").json()["tags"] == []
    with scoped(engine) as s:
        assert s.exec(select(TagLink)).all() == []


def test_deleting_an_item_drops_its_links_but_not_the_tag(client, engine):
    a = make_tag(client, "a")
    prompt = client.post("/prompts", json={"name": "P", "tag_ids": [a["id"]]}).json()
    analysis = client.post("/analyses", json={**ANALYSIS, "tag_ids": [a["id"]]}).json()

    client.delete(f"/prompts/{prompt['id']}")
    client.delete(f"/analyses/{analysis['id']}")

    with scoped(engine) as s:
        assert s.exec(select(TagLink)).all() == []
    assert client.get("/tags").json() == [a]


def test_a_tag_is_shared_between_kinds(client):
    a = make_tag(client, "paper")
    prompt = client.post("/prompts", json={"name": "P", "tag_ids": [a["id"]]}).json()
    analysis = client.post("/analyses", json={**ANALYSIS, "tag_ids": [a["id"]]}).json()
    assert prompt["tags"] == [a]
    assert analysis["tags"] == [a]


def test_analysis_runs_still_round_trip(client, engine):
    with scoped(engine) as s:
        dataset = Dataset(name="answers", file_path="answers.csv")
        s.add(dataset)
        s.flush()
        experiment = Experiment(name="Run", dataset_id=dataset.id)
        s.add(experiment)
        s.flush()
        execution = ExperimentExecution(experiment_id=experiment.id, dataset_snapshot="{}")
        s.add(execution)
        s.commit()
        execution_id = execution.id

    response = client.post(
        "/analyses",
        json={**ANALYSIS, "runs": [{"execution_id": execution_id, "agent_name": "g"}]},
    )
    assert json.loads(response.text)["runs"][0]["execution_id"] == execution_id


def test_assign_adds_and_removes_tags_on_several_items(client):
    a, b, c = make_tag(client, "a"), make_tag(client, "b"), make_tag(client, "c")
    one = client.post(
        "/prompts", json={"name": "1", "tag_ids": [a["id"], b["id"]]}
    ).json()
    two = client.post("/prompts", json={"name": "2", "tag_ids": [b["id"]]}).json()
    three = client.post("/prompts", json={"name": "3"}).json()

    response = client.post(
        "/tags/assign",
        json={
            "kind": "prompt",
            "item_ids": [one["id"], two["id"]],
            "add": [c["id"]],
            "remove": [b["id"]],
        },
    )
    assert response.status_code == 204, response.text

    names = {
        p["name"]: [t["name"] for t in p["tags"]] for p in client.get("/prompts").json()
    }
    assert names == {"1": ["a", "c"], "2": ["c"], "3": []}
    assert three["id"]  # untouched


def test_assign_twice_does_not_duplicate_links(client, engine):
    a = make_tag(client, "a")
    prompt = client.post("/prompts", json={"name": "P", "tag_ids": [a["id"]]}).json()
    body = {"kind": "prompt", "item_ids": [prompt["id"]], "add": [a["id"]]}
    assert client.post("/tags/assign", json=body).status_code == 204
    assert client.post("/tags/assign", json=body).status_code == 204
    with scoped(engine) as s:
        assert len(s.exec(select(TagLink)).all()) == 1


def test_assign_works_on_analyses(client):
    a = make_tag(client, "a")
    analysis = client.post("/analyses", json=ANALYSIS).json()
    client.post(
        "/tags/assign",
        json={"kind": "analysis", "item_ids": [analysis["id"]], "add": [a["id"]]},
    )
    assert [
        t["name"] for t in client.get(f"/analyses/{analysis['id']}").json()["tags"]
    ] == ["a"]


def test_assign_refuses_unknown_items_and_tags_without_changing_anything(client):
    a = make_tag(client, "a")
    prompt = client.post("/prompts", json={"name": "P"}).json()

    unknown_item = client.post(
        "/tags/assign",
        json={"kind": "prompt", "item_ids": [prompt["id"], 999], "add": [a["id"]]},
    )
    assert unknown_item.status_code == 422
    unknown_tag = client.post(
        "/tags/assign",
        json={"kind": "prompt", "item_ids": [prompt["id"]], "add": [999]},
    )
    assert unknown_tag.status_code == 422
    assert client.get(f"/prompts/{prompt['id']}").json()["tags"] == []
    assert (
        client.post("/tags/assign", json={"kind": "prompt", "item_ids": []}).status_code
        == 422
    )


def make_agent(client, **fields):
    response = client.post("/agents", json={"name": "A", **fields})
    assert response.status_code == 201, response.text
    return response.json()


def test_agent_tags_are_set_replaced_and_kept(client):
    a, b = make_tag(client, "a"), make_tag(client, "b")
    agent = make_agent(client, tag_ids=[a["id"]])
    assert [t["name"] for t in agent["tags"]] == ["a"]

    renamed = client.put(f"/agents/{agent['id']}", json={"name": "B"}).json()
    assert [t["name"] for t in renamed["tags"]] == ["a"]  # left out: kept

    replaced = client.put(f"/agents/{agent['id']}", json={"tag_ids": [b["id"]]}).json()
    assert [t["name"] for t in replaced["tags"]] == ["b"]

    listed = client.get("/agents").json()
    assert [t["name"] for t in listed[0]["tags"]] == ["b"]


def test_assign_works_on_agents(client, engine):
    a = make_tag(client, "a")
    agent = make_agent(client)
    client.post(
        "/tags/assign",
        json={"kind": "agent", "item_ids": [agent["id"]], "add": [a["id"]]},
    )
    assert [t["name"] for t in client.get(f"/agents/{agent['id']}").json()["tags"]] == [
        "a"
    ]

    client.delete(f"/agents/{agent['id']}")
    with scoped(engine) as s:
        assert s.exec(select(TagLink)).all() == []
