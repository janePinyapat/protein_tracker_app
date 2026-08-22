"""Tests for the FoodData Central client.

Every test uses a stub response, so the suite never makes a network call and
never needs an API key.
"""

import pytest

import usda_api
from usda_api import (
    DEMO_KEY,
    FoodLookupError,
    extract_nutrient,
    format_food_label,
    get_api_key,
    is_using_demo_key,
    parse_food_result,
    scale_to_portion,
    search_foods,
)


SEARCH_PAYLOAD = {
    "foods": [
        {
            "fdcId": 171284,
            "description": "Yogurt, Greek, plain, nonfat",
            "dataType": "SR Legacy",
            "foodNutrients": [
                {"nutrientId": 1003, "nutrientName": "Protein", "value": 10.3},
                {"nutrientId": 1004, "nutrientName": "Total lipid (fat)", "value": 0.4},
                {"nutrientId": 1005, "nutrientName": "Carbohydrate", "value": 3.6},
                {"nutrientId": 1008, "nutrientName": "Energy", "value": 59.0},
                {"nutrientId": 1079, "nutrientName": "Fiber", "value": 0.0},
            ],
        }
    ]
}


class StubResponse:
    def __init__(self, status_code=200, payload=None, raises=False):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self._raises = raises

    def json(self):
        if self._raises:
            raise ValueError("not json")
        return self._payload


class StubSession:
    """Stands in for the requests module."""

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.last_params = None

    def get(self, url, params=None, timeout=None):
        self.last_params = params
        if self.error:
            raise self.error
        return self.response


def test_extract_nutrient_reads_search_shape():
    nutrients = [{"nutrientId": 1003, "value": 10.3}]
    assert extract_nutrient(nutrients, 1003) == 10.3


def test_extract_nutrient_reads_nested_detail_shape():
    nutrients = [{"nutrient": {"id": 1005}, "amount": 3.6}]
    assert extract_nutrient(nutrients, 1005) == 3.6


def test_extract_nutrient_returns_none_when_absent():
    assert extract_nutrient([{"nutrientId": 1003, "value": 10.3}], 1079) is None


def test_extract_nutrient_handles_empty_list():
    assert extract_nutrient([], 1003) is None


def test_parse_food_result_maps_every_tracked_nutrient():
    parsed = parse_food_result(SEARCH_PAYLOAD["foods"][0])

    assert parsed["description"] == "Yogurt, Greek, plain, nonfat"
    assert parsed["protein_grams"] == 10.3
    assert parsed["carbs_grams"] == 3.6
    assert parsed["fat_grams"] == 0.4
    assert parsed["fiber_grams"] == 0.0
    assert parsed["calories"] == 59.0
    assert parsed["reference_grams"] == 100.0


def test_parse_food_result_tolerates_missing_nutrients():
    parsed = parse_food_result({"description": "Mystery food", "foodNutrients": []})

    assert parsed["description"] == "Mystery food"
    assert parsed["protein_grams"] is None


def test_scale_to_portion_scales_from_one_hundred_grams():
    parsed = parse_food_result(SEARCH_PAYLOAD["foods"][0])
    scaled = scale_to_portion(parsed, 200.0)

    assert scaled["protein_grams"] == 20.6
    assert scaled["calories"] == 118.0
    assert scaled["portion_grams"] == 200.0


def test_scale_to_portion_keeps_missing_values_missing():
    parsed = parse_food_result({"description": "Mystery food", "foodNutrients": []})
    scaled = scale_to_portion(parsed, 50.0)

    assert scaled["protein_grams"] is None


def test_scale_to_portion_rejects_zero_portion():
    parsed = parse_food_result(SEARCH_PAYLOAD["foods"][0])

    with pytest.raises(ValueError):
        scale_to_portion(parsed, 0)


def test_format_food_label_includes_brand_and_type():
    label = format_food_label(
        {"description": "Skyr", "brand": "Arla", "data_type": "Branded"}
    )
    assert label == "Skyr — Arla (Branded)"


def test_format_food_label_handles_bare_description():
    assert format_food_label({"description": "Lentils"}) == "Lentils"


def test_search_foods_returns_parsed_results():
    session = StubSession(StubResponse(payload=SEARCH_PAYLOAD))
    results = search_foods("greek yogurt", api_key="test-key", session=session)

    assert len(results) == 1
    assert results[0]["protein_grams"] == 10.3
    assert session.last_params["query"] == "greek yogurt"
    assert session.last_params["api_key"] == "test-key"


def test_search_foods_skips_request_for_blank_query():
    session = StubSession(StubResponse(payload=SEARCH_PAYLOAD))
    assert search_foods("   ", api_key="test-key", session=session) == []
    assert session.last_params is None


def test_search_foods_raises_friendly_error_on_rate_limit():
    session = StubSession(StubResponse(status_code=429))

    with pytest.raises(FoodLookupError, match="rate limit"):
        search_foods("lentils", api_key=DEMO_KEY, session=session)


def test_search_foods_raises_friendly_error_on_bad_key():
    session = StubSession(StubResponse(status_code=403))

    with pytest.raises(FoodLookupError, match="API key"):
        search_foods("lentils", api_key="bad-key", session=session)


def test_search_foods_raises_on_unexpected_status():
    session = StubSession(StubResponse(status_code=500))

    with pytest.raises(FoodLookupError, match="status 500"):
        search_foods("lentils", api_key="test-key", session=session)


def test_search_foods_raises_when_network_fails():
    session = StubSession(error=OSError("no route to host"))

    with pytest.raises(FoodLookupError, match="Could not reach"):
        search_foods("lentils", api_key="test-key", session=session)


def test_search_foods_raises_on_unreadable_body():
    session = StubSession(StubResponse(raises=True))

    with pytest.raises(FoodLookupError, match="unreadable"):
        search_foods("lentils", api_key="test-key", session=session)


def test_get_api_key_prefers_environment_variable(monkeypatch):
    monkeypatch.setenv("USDA_API_KEY", "env-key")
    assert get_api_key({"usda_api_key": "secret-key"}) == "env-key"


def test_get_api_key_falls_back_to_secrets(monkeypatch):
    monkeypatch.delenv("USDA_API_KEY", raising=False)
    assert get_api_key({"usda_api_key": "secret-key"}) == "secret-key"


def test_get_api_key_falls_back_to_demo_key(monkeypatch):
    monkeypatch.delenv("USDA_API_KEY", raising=False)
    assert get_api_key(None) == DEMO_KEY


def test_get_api_key_ignores_unreadable_secrets(monkeypatch):
    """Streamlit raises if secrets.toml is absent, which must not crash."""

    class ExplodingSecrets:
        def get(self, key, default=None):
            raise RuntimeError("no secrets file")

    monkeypatch.delenv("USDA_API_KEY", raising=False)
    assert get_api_key(ExplodingSecrets()) == DEMO_KEY


def test_get_api_key_ignores_secrets_that_raise_on_bool_check(monkeypatch):
    """st.secrets itself raises on truthiness (not just .get) when there is
    no secrets.toml at all — a bare ``if secrets:`` must not crash either."""

    class BoolExplodingSecrets:
        def __bool__(self):
            raise RuntimeError("no secrets file")

        def get(self, key, default=None):
            raise RuntimeError("no secrets file")

    monkeypatch.delenv("USDA_API_KEY", raising=False)
    assert get_api_key(BoolExplodingSecrets()) == DEMO_KEY


def test_is_using_demo_key():
    assert is_using_demo_key(DEMO_KEY)
    assert not is_using_demo_key("my-own-key")


def test_no_api_key_is_committed_in_source():
    """Guard against a real key being pasted into the module."""
    assert usda_api.DEMO_KEY == "DEMO_KEY"
