import pytest

from batch_utils import (
    VariationError,
    batch_status,
    count_points,
    expand_variations,
    is_base_point,
    normalize_variations,
    parse_point,
    prompt_variable_names,
    serialize_point,
    unmapped_variables,
)


def axis(step, field, *values):
    return {"step_key": str(step), "field": field, "values": list(values)}


class TestExpandVariations:
    def test_single_axis_gives_one_point_per_value(self):
        points = expand_variations([axis(1, "model_id", 10, 11, 12)])
        assert points == [
            {"1": {"model_id": 10}},
            {"1": {"model_id": 11}},
            {"1": {"model_id": 12}},
        ]

    def test_axes_form_a_cartesian_product(self):
        variations = [axis(1, "model_id", 10, 11), axis(1, "prompt_version_id", 5, 6, 7)]
        points = expand_variations(variations)
        assert len(points) == count_points(variations) == 6
        assert {"1": {"model_id": 11, "prompt_version_id": 6}} in points

    def test_first_axis_varies_slowest(self):
        points = expand_variations(
            [axis(1, "model_id", 10, 11), axis(1, "temperature", 0, 1)]
        )
        assert [p["1"]["model_id"] for p in points] == [10, 10, 11, 11]

    def test_axes_on_different_agents_stay_separate(self):
        points = expand_variations(
            [axis(1, "model_id", 10, 11), axis(2, "model_id", 20)]
        )
        assert points == [
            {"1": {"model_id": 10}, "2": {"model_id": 20}},
            {"1": {"model_id": 11}, "2": {"model_id": 20}},
        ]


class TestNormalizeVariations:
    def test_drops_duplicate_values_keeping_order(self):
        result = normalize_variations([axis(1, "model_id", 3, 1, 3, 2, 1)])
        assert result[0]["values"] == [3, 1, 2]

    def test_requires_a_variation(self):
        with pytest.raises(VariationError):
            normalize_variations([])

    def test_rejects_unknown_field(self):
        with pytest.raises(VariationError, match="cannot be varied"):
            normalize_variations([axis(1, "max_tokens", 100)])

    def test_rejects_same_agent_field_twice(self):
        with pytest.raises(VariationError, match="more than once"):
            normalize_variations(
                [axis(1, "model_id", 1), axis(1, "model_id", 2)]
            )

    def test_the_steps_of_one_agent_are_separate_axes(self):
        result = normalize_variations(
            [axis("1", "model_id", 1, 2), axis("1#2", "model_id", 3, 4)]
        )
        assert [v["step_key"] for v in result] == ["1", "1#2"]
        assert [v["agent_id"] for v in result] == [1, 1]
        assert expand_variations(result)[0] == {
            "1": {"model_id": 1},
            "1#2": {"model_id": 3},
        }

    def test_an_axis_without_a_step_is_the_first_step_of_its_agent(self):
        result = normalize_variations(
            [{"agent_id": 7, "field": "model_id", "values": [1]}]
        )
        assert result[0]["step_key"] == "7"

    def test_rejects_a_step_that_is_not_one(self):
        with pytest.raises(VariationError, match="Invalid step"):
            normalize_variations([axis("x#2", "model_id", 1)])

    def test_rejects_negative_temperature(self):
        with pytest.raises(VariationError, match="Temperature"):
            normalize_variations([axis(1, "temperature", -0.5)])

    def test_zero_temperature_is_valid(self):
        assert normalize_variations([axis(1, "temperature", 0, 0.7)])

    def test_temperature_can_be_the_model_default(self):
        result = normalize_variations([axis(1, "temperature", None, 0.7)])
        assert result[0]["values"] == [None, 0.7]

    def test_only_temperature_accepts_the_model_default(self):
        with pytest.raises(VariationError, match="needs a value"):
            normalize_variations([axis(1, "model_id", None, 3)])


class TestIsBasePoint:
    base = {("1", "model_id"): 10, ("1", "temperature"): None}

    def test_every_axis_at_its_base_value(self):
        assert is_base_point({"1": {"model_id": 10, "temperature": None}}, self.base)

    def test_one_axis_elsewhere_is_not_the_base(self):
        assert not is_base_point({"1": {"model_id": 10, "temperature": 0.7}}, self.base)
        assert not is_base_point({"1": {"model_id": 11, "temperature": None}}, self.base)

    def test_zero_is_not_the_model_default(self):
        assert not is_base_point({"1": {"model_id": 10, "temperature": 0}}, self.base)


class TestPointSerialization:
    def test_round_trip_keeps_the_step_keys(self):
        point = {"3": {"model_id": 9}, "3#2": {"temperature": 0.2}}
        assert parse_point(serialize_point(point)) == point

    @pytest.mark.parametrize("raw", [None, "", "not json"])
    def test_unreadable_point_is_empty(self, raw):
        assert parse_point(raw) == {}


class TestPromptCompatibility:
    def test_variable_names_from_list_or_object(self):
        assert prompt_variable_names('["a", "b"]') == {"a", "b"}
        assert prompt_variable_names('{"a": "desc", "b": ""}') == {"a", "b"}

    @pytest.mark.parametrize("raw", [None, "", "oops", "3"])
    def test_variable_names_tolerate_bad_input(self, raw):
        assert prompt_variable_names(raw) == set()

    def test_reports_variables_without_a_mapping(self):
        mappings = [
            {"variable": "answer", "source": "dataset", "sourceColumn": "text"},
            {"variable": "extra"},  # no source: not provided
        ]
        assert unmapped_variables({"answer", "extra", "ref"}, mappings) == {
            "extra",
            "ref",
        }

    def test_agent_without_mappings_accepts_any_prompt(self):
        assert unmapped_variables({"anything"}, None) == set()
        assert unmapped_variables({"anything"}, []) == set()


class TestBatchStatus:
    @pytest.mark.parametrize(
        ("statuses", "expected"),
        [
            ([], "pending"),
            (["completed", "completed"], "completed"),
            (["completed", "running"], "running"),
            (["pending", "completed"], "pending"),
            (["completed", "failed"], "partial"),
            (["failed", "failed"], "failed"),
            (["completed", "cancelled"], "partial"),
            (["failed", "cancelled"], "failed"),
            (["cancelled", "cancelled"], "cancelled"),
        ],
    )
    def test_overall_status(self, statuses, expected):
        assert batch_status(statuses) == expected
