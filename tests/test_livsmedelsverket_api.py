"""Tests for the Livsmedelsverket (Swedish Food Agency) client.

Every test uses a stub response, so the suite never makes a network call.
Fixture data is trimmed from real responses observed from
https://dataportal.livsmedelsverket.se/livsmedel/api/v1 (food id 1594,
"Sweet wheat bread cinnamon buns homemade").
"""

import pytest

import livsmedelsverket_api
from livsmedelsverket_api import (
    FoodLookupError,
    extract_nutrient_value,
    fetch_food_catalog,
    fetch_food_nutrients,
    format_food_label,
    parse_catalog_entry,
    parse_nutrients,
    scale_to_portion,
    search_catalog,
)


CATALOG_PAYLOAD = {
    "_meta": {"totalRecords": 3, "offset": 0, "limit": 5000, "count": 3},
    "livsmedel": [
        {"nummer": 1250, "namn": "Pink salmon raw"},
        {"nummer": 1255, "namn": "Salmon farmed Norwegian fjords raw"},
        {"nummer": 1, "namn": "Beef tallow"},
    ],
}

NUTRIENT_PAYLOAD = [
    {"namn": "Protein", "euroFIRkod": "PROT", "varde": 5.8, "enhet": "g"},
    {"namn": "Fibre", "euroFIRkod": "FIBT", "varde": 2.0, "enhet": "g"},
    {"namn": "Fat, total", "euroFIRkod": "FAT", "varde": 12.7, "enhet": "g"},
    {
        "namn": "Carbohydrates, available",
        "euroFIRkod": "CHO",
        "varde": 45.4,
        "enhet": "g",
    },
    {"namn": "Energy (kJ)", "euroFIRkod": "ENERC", "varde": 1357, "enhet": "kJ"},
    {"namn": "Energy (kcal)", "euroFIRkod": "ENERC", "varde": 324, "enhet": "kcal"},
]


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
        self.last_url = None
        self.last_params = None

    def get(self, url, params=None, timeout=None):
        self.last_url = url
        self.last_params = params
        if self.error:
            raise self.error
        return self.response


def test_extract_nutrient_value_matches_code():
    assert extract_nutrient_value(NUTRIENT_PAYLOAD, "PROT") == 5.8


def test_extract_nutrient_value_disambiguates_by_unit():
    assert extract_nutrient_value(NUTRIENT_PAYLOAD, "ENERC", unit="kcal") == 324
    assert extract_nutrient_value(NUTRIENT_PAYLOAD, "ENERC", unit="kJ") == 1357


def test_extract_nutrient_value_returns_none_when_absent():
    assert extract_nutrient_value(NUTRIENT_PAYLOAD, "SUGAR") is None


def test_extract_nutrient_value_handles_empty_list():
    assert extract_nutrient_value([], "PROT") is None


def test_parse_nutrients_maps_every_tracked_macro():
    parsed = parse_nutrients(NUTRIENT_PAYLOAD)

    assert parsed["protein_grams"] == 5.8
    assert parsed["carbs_grams"] == 45.4
    assert parsed["fat_grams"] == 12.7
    assert parsed["fiber_grams"] == 2.0
    assert parsed["calories"] == 324


def test_parse_nutrients_tolerates_missing_fields():
    parsed = parse_nutrients([])

    assert parsed["protein_grams"] is None
    assert parsed["calories"] is None


def test_parse_catalog_entry_extracts_id_and_english_name():
    entry = parse_catalog_entry({"nummer": 1255, "namn": "Salmon farmed"})
    assert entry == {"nummer": 1255, "description": "Salmon farmed"}


def test_parse_catalog_entry_handles_missing_name():
    entry = parse_catalog_entry({"nummer": 9})
    assert entry["description"] == ""


def test_fetch_food_catalog_returns_parsed_entries():
    session = StubSession(StubResponse(payload=CATALOG_PAYLOAD))
    catalog = fetch_food_catalog(session=session)

    assert len(catalog) == 3
    assert catalog[0] == {"nummer": 1250, "description": "Pink salmon raw"}
    assert session.last_params["sprak"] == 2


def test_fetch_food_catalog_raises_on_bad_status():
    session = StubSession(StubResponse(status_code=500))

    with pytest.raises(FoodLookupError, match="status 500"):
        fetch_food_catalog(session=session)


def test_fetch_food_catalog_raises_when_network_fails():
    session = StubSession(error=OSError("no route to host"))

    with pytest.raises(FoodLookupError, match="Could not reach"):
        fetch_food_catalog(session=session)


def test_fetch_food_catalog_raises_on_unreadable_body():
    session = StubSession(StubResponse(raises=True))

    with pytest.raises(FoodLookupError, match="unreadable"):
        fetch_food_catalog(session=session)


def test_search_catalog_matches_case_insensitive_substring():
    catalog = [parse_catalog_entry(food) for food in CATALOG_PAYLOAD["livsmedel"]]
    matches = search_catalog("SALMON", catalog)

    assert len(matches) == 2
    assert all("salmon" in food["description"].lower() for food in matches)


def test_search_catalog_returns_empty_for_blank_query():
    catalog = [parse_catalog_entry(food) for food in CATALOG_PAYLOAD["livsmedel"]]
    assert search_catalog("   ", catalog) == []


def test_search_catalog_respects_max_results():
    catalog = [{"nummer": i, "description": "Salmon dish"} for i in range(20)]
    matches = search_catalog("salmon", catalog, max_results=5)

    assert len(matches) == 5


def test_fetch_food_nutrients_returns_parsed_macros_with_reference_grams():
    session = StubSession(StubResponse(payload=NUTRIENT_PAYLOAD))
    nutrients = fetch_food_nutrients(1594, session=session)

    assert nutrients["protein_grams"] == 5.8
    assert nutrients["calories"] == 324
    assert nutrients["reference_grams"] == 100.0
    assert "/livsmedel/1594/naringsvarden" in session.last_url


def test_fetch_food_nutrients_raises_on_bad_status():
    session = StubSession(StubResponse(status_code=404))

    with pytest.raises(FoodLookupError, match="status 404"):
        fetch_food_nutrients(1, session=session)


def test_scale_to_portion_scales_from_one_hundred_grams():
    nutrients = parse_nutrients(NUTRIENT_PAYLOAD)
    nutrients["reference_grams"] = 100.0

    scaled = scale_to_portion(nutrients, 50.0)

    assert scaled["protein_grams"] == 2.9
    assert scaled["calories"] == 162.0
    assert scaled["portion_grams"] == 50.0


def test_scale_to_portion_keeps_missing_values_missing():
    nutrients = parse_nutrients([])
    nutrients["reference_grams"] = 100.0

    scaled = scale_to_portion(nutrients, 50.0)
    assert scaled["protein_grams"] is None


def test_scale_to_portion_rejects_zero_portion():
    nutrients = parse_nutrients(NUTRIENT_PAYLOAD)
    nutrients["reference_grams"] = 100.0

    with pytest.raises(ValueError):
        scale_to_portion(nutrients, 0)


def test_format_food_label_returns_description():
    assert format_food_label({"description": "Salmon farmed"}) == "Salmon farmed"


def test_format_food_label_handles_missing_description():
    assert format_food_label({}) == "Unnamed food"


def test_no_api_key_is_needed_for_this_provider():
    """This API is keyless; guard against a key-handling regression creeping
    back in (the previous USDA client needed one)."""
    assert not hasattr(livsmedelsverket_api, "get_api_key")
    assert not hasattr(livsmedelsverket_api, "DEMO_KEY")
