"""Tests for the Spoonacular-based meal recommendation client.

Every network-touching test stubs the module-level ``requests`` object, so
the suite never makes a real API call, never needs a real key, and never
spends quota.
"""

import pytest

import meal_recommendation_api as mra
from meal_recommendation_api import (
    MealRecommendationError,
    describe_recipe,
    extract_nutrient,
    fetch_meal_recommendations,
    find_candidate,
    get_api_key,
    search_recipes,
    split_remaining_by_meal,
)


def make_recipe(
    recipe_id, title, protein, fiber, calories, ready=20, servings=2, source="Site",
    image="https://img.spoonacular.com/recipes/example.jpg",
):
    return {
        "id": recipe_id,
        "title": title,
        "readyInMinutes": ready,
        "servings": servings,
        "sourceUrl": f"https://example.com/{recipe_id}",
        "sourceName": source,
        "image": image,
        "nutrition": {
            "nutrients": [
                {"name": "Calories", "amount": calories, "unit": "kcal"},
                {"name": "Fat", "amount": 10.0, "unit": "g"},
                {"name": "Protein", "amount": protein, "unit": "g"},
                {"name": "Fiber", "amount": fiber, "unit": "g"},
            ]
        },
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


class StubRequestsModule:
    """Stands in for the `requests` module used inside meal_recommendation_api."""

    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [])
        self.error = error
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        if self.error:
            raise self.error
        return self.responses.pop(0)


@pytest.fixture()
def patched_requests(monkeypatch):
    def _patch(stub):
        monkeypatch.setattr(mra, "requests", stub)
        return stub

    return _patch


def results_response(recipes):
    return StubResponse(payload={"results": recipes})


# --- split_remaining_by_meal -------------------------------------------------


def test_split_remaining_by_meal_uses_fixed_shares():
    shares = split_remaining_by_meal(100.0, 20.0)

    assert shares["Breakfast"] == {"protein_grams": 25.0, "fiber_grams": 5.0}
    assert shares["Lunch"] == {"protein_grams": 35.0, "fiber_grams": 7.0}
    assert shares["Dinner"] == {"protein_grams": 40.0, "fiber_grams": 8.0}


def test_split_remaining_by_meal_floors_negative_at_zero():
    shares = split_remaining_by_meal(-10.0, -5.0)
    assert shares["Breakfast"] == {"protein_grams": 0.0, "fiber_grams": 0.0}


def test_split_remaining_by_meal_handles_none():
    shares = split_remaining_by_meal(None, None)
    assert shares["Dinner"] == {"protein_grams": 0.0, "fiber_grams": 0.0}


# --- extract_nutrient / describe_recipe --------------------------------------


def test_extract_nutrient_finds_named_value():
    nutrients = [{"name": "Protein", "amount": 26.5}, {"name": "Fiber", "amount": 4.0}]
    assert extract_nutrient(nutrients, "Protein") == 26.5


def test_extract_nutrient_returns_none_when_absent():
    assert extract_nutrient([{"name": "Fat", "amount": 5.0}], "Protein") is None


def test_extract_nutrient_handles_empty_list():
    assert extract_nutrient([], "Protein") is None


def test_describe_recipe_combines_time_and_servings():
    description = describe_recipe({"readyInMinutes": 30, "servings": 4})
    assert description == "Ready in 30 min · serves 4"


def test_describe_recipe_handles_missing_fields():
    assert describe_recipe({}) is None


# --- search_recipes -----------------------------------------------------------


def test_search_recipes_sends_expected_params_for_breakfast(patched_requests):
    stub = patched_requests(StubRequestsModule(responses=[results_response([])]))

    search_recipes("Breakfast", 10.0, 30.0, 3.0, "test-key", number=5)

    call = stub.calls[0]
    assert call["params"]["type"] == "breakfast"
    assert call["params"]["minProtein"] == 10.0
    assert call["params"]["maxProtein"] == 30.0
    assert call["params"]["minFiber"] == 3.0
    assert call["params"]["addRecipeNutrition"] == "true"
    assert call["params"]["number"] == 5
    assert call["params"]["offset"] == 0
    assert call["params"]["apiKey"] == "test-key"
    assert "diet" not in call["params"]


def test_search_recipes_maps_lunch_and_dinner_to_main_course(patched_requests):
    stub = patched_requests(
        StubRequestsModule(responses=[results_response([]), results_response([])])
    )

    search_recipes("Lunch", 10.0, 30.0, 3.0, "test-key")
    search_recipes("Dinner", 10.0, 30.0, 3.0, "test-key")

    assert stub.calls[0]["params"]["type"] == "main course"
    assert stub.calls[1]["params"]["type"] == "main course"


def test_search_recipes_includes_diet_param_when_given(patched_requests):
    stub = patched_requests(StubRequestsModule(responses=[results_response([])]))

    search_recipes("Breakfast", 10.0, 30.0, 3.0, "test-key", diet="vegetarian")

    assert stub.calls[0]["params"]["diet"] == "vegetarian"


def test_search_recipes_includes_servings_params_when_given(patched_requests):
    stub = patched_requests(StubRequestsModule(responses=[results_response([])]))

    search_recipes("Breakfast", 10.0, 30.0, 3.0, "test-key", servings=4)

    assert stub.calls[0]["params"]["minServings"] == 4
    assert stub.calls[0]["params"]["maxServings"] == 4


def test_search_recipes_omits_servings_params_when_not_given(patched_requests):
    stub = patched_requests(StubRequestsModule(responses=[results_response([])]))

    search_recipes("Breakfast", 10.0, 30.0, 3.0, "test-key")

    assert "minServings" not in stub.calls[0]["params"]
    assert "maxServings" not in stub.calls[0]["params"]


def test_search_recipes_includes_max_ready_time_when_given(patched_requests):
    stub = patched_requests(StubRequestsModule(responses=[results_response([])]))

    search_recipes("Breakfast", 10.0, 30.0, 3.0, "test-key", max_ready_time=30)

    assert stub.calls[0]["params"]["maxReadyTime"] == 30


def test_search_recipes_omits_max_ready_time_when_not_given(patched_requests):
    stub = patched_requests(StubRequestsModule(responses=[results_response([])]))

    search_recipes("Breakfast", 10.0, 30.0, 3.0, "test-key")

    assert "maxReadyTime" not in stub.calls[0]["params"]


def test_search_recipes_passes_offset_through(patched_requests):
    stub = patched_requests(StubRequestsModule(responses=[results_response([])]))

    search_recipes("Breakfast", 10.0, 30.0, 3.0, "test-key", offset=10)

    assert stub.calls[0]["params"]["offset"] == 10


def test_search_recipes_returns_results_list(patched_requests):
    recipe = make_recipe(1, "Test Recipe", 20.0, 4.0, 300)
    patched_requests(StubRequestsModule(responses=[results_response([recipe])]))

    results = search_recipes("Breakfast", 10.0, 30.0, 3.0, "test-key")
    assert results == [recipe]


def test_search_recipes_raises_on_bad_key(patched_requests):
    patched_requests(StubRequestsModule(responses=[StubResponse(status_code=401)]))

    with pytest.raises(MealRecommendationError, match="rejected the API key"):
        search_recipes("Breakfast", 10.0, 30.0, 3.0, "bad-key")


def test_search_recipes_raises_on_quota_exceeded(patched_requests):
    patched_requests(StubRequestsModule(responses=[StubResponse(status_code=402)]))

    with pytest.raises(MealRecommendationError, match="quota"):
        search_recipes("Breakfast", 10.0, 30.0, 3.0, "test-key")


def test_search_recipes_raises_on_unexpected_status(patched_requests):
    patched_requests(StubRequestsModule(responses=[StubResponse(status_code=500)]))

    with pytest.raises(MealRecommendationError, match="status 500"):
        search_recipes("Breakfast", 10.0, 30.0, 3.0, "test-key")


def test_search_recipes_raises_on_network_error(patched_requests):
    patched_requests(StubRequestsModule(error=OSError("no route to host")))

    with pytest.raises(MealRecommendationError, match="Could not reach"):
        search_recipes("Breakfast", 10.0, 30.0, 3.0, "test-key")


def test_search_recipes_raises_on_unreadable_body(patched_requests):
    patched_requests(StubRequestsModule(responses=[StubResponse(raises=True)]))

    with pytest.raises(MealRecommendationError, match="unreadable"):
        search_recipes("Breakfast", 10.0, 30.0, 3.0, "test-key")


# --- find_candidate -----------------------------------------------------------


def test_find_candidate_returns_first_match_when_nothing_excluded(patched_requests):
    recipe = make_recipe(1, "Recipe A", 20.0, 4.0, 300)
    patched_requests(StubRequestsModule(responses=[results_response([recipe])]))

    pick, was_repeat = find_candidate(
        "Breakfast", 10.0, 30.0, 3.0, "test-key", None, exclude_ids=set(), used_ids=set()
    )

    assert pick["id"] == 1
    assert was_repeat is False


def test_find_candidate_pages_past_excluded_recipes(patched_requests):
    page_one = [make_recipe(1, "Recipe A", 20.0, 4.0, 300)]
    page_two = [make_recipe(2, "Recipe B", 20.0, 4.0, 300)]
    stub = patched_requests(
        StubRequestsModule(responses=[results_response(page_one), results_response(page_two)])
    )

    pick, was_repeat = find_candidate(
        "Breakfast", 10.0, 30.0, 3.0, "test-key", None, exclude_ids={1}, used_ids=set()
    )

    assert pick["id"] == 2
    assert was_repeat is False
    # Second call should have paged past the first page's single result.
    assert stub.calls[1]["params"]["offset"] == 1


def test_find_candidate_falls_back_to_repeat_when_pool_exhausted(patched_requests):
    only_recipe = [make_recipe(1, "Only Recipe", 20.0, 4.0, 300)]
    # Three pages tried (MAX_REPEAT_AVOIDANCE_PAGES), each returns the same
    # single already-excluded recipe until offset moves past total results.
    patched_requests(
        StubRequestsModule(
            responses=[
                results_response(only_recipe),
                results_response([]),
            ]
        )
    )

    pick, was_repeat = find_candidate(
        "Breakfast", 10.0, 30.0, 3.0, "test-key", None, exclude_ids={1}, used_ids=set()
    )

    assert pick["id"] == 1
    assert was_repeat is True


def test_find_candidate_never_returns_a_used_id_even_as_fallback(patched_requests):
    only_recipe = [make_recipe(1, "Only Recipe", 20.0, 4.0, 300)]
    patched_requests(
        StubRequestsModule(responses=[results_response(only_recipe), results_response([])])
    )

    pick, was_repeat = find_candidate(
        "Breakfast", 10.0, 30.0, 3.0, "test-key", None, exclude_ids=set(), used_ids={1}
    )

    assert pick is None


def test_find_candidate_returns_none_when_no_candidates_at_all(patched_requests):
    patched_requests(StubRequestsModule(responses=[results_response([])]))

    pick, was_repeat = find_candidate(
        "Breakfast", 10.0, 30.0, 3.0, "test-key", None, exclude_ids=set(), used_ids=set()
    )

    assert pick is None
    assert was_repeat is False


# --- fetch_meal_recommendations ------------------------------------------------


def test_fetch_meal_recommendations_requires_api_key(monkeypatch):
    monkeypatch.delenv("SPOONACULAR_API_KEY", raising=False)

    with pytest.raises(MealRecommendationError, match="No Spoonacular API key"):
        fetch_meal_recommendations(80.0, 15.0, api_key=None)


def test_fetch_meal_recommendations_builds_three_meals(patched_requests):
    responses = [
        results_response([make_recipe(1, "Breakfast Recipe", 20.0, 4.0, 300)]),
        results_response([make_recipe(2, "Lunch Recipe", 28.0, 7.0, 450)]),
        results_response([make_recipe(3, "Dinner Recipe", 32.0, 8.0, 520)]),
    ]
    patched_requests(StubRequestsModule(responses=responses))

    payload = fetch_meal_recommendations(100.0, 20.0, api_key="test-key")

    assert [meal["meal_type"] for meal in payload["meals"]] == [
        "Breakfast",
        "Lunch",
        "Dinner",
    ]
    assert payload["meals"][0]["meal_name"] == "Breakfast Recipe"
    assert payload["meals"][0]["recipe_id"] == 1
    assert payload["meals"][0]["estimated_protein_grams"] == 20.0
    assert payload["meals"][0]["estimated_fiber_grams"] == 4.0
    assert payload["meals"][0]["estimated_calories"] == 300
    assert payload["meals"][0]["source_url"] == "https://example.com/1"
    assert payload["meals"][0]["description"] == "Ready in 20 min · serves 2"
    assert payload["meals"][0]["image_url"] == "https://img.spoonacular.com/recipes/example.jpg"
    assert payload["notes"] == ""


def test_fetch_meal_recommendations_passes_servings_and_max_ready_time_through(
    patched_requests,
):
    responses = [
        results_response([make_recipe(1, "Breakfast Recipe", 20.0, 4.0, 300)]),
        results_response([make_recipe(2, "Lunch Recipe", 28.0, 7.0, 450)]),
        results_response([make_recipe(3, "Dinner Recipe", 32.0, 8.0, 520)]),
    ]
    stub = patched_requests(StubRequestsModule(responses=responses))

    fetch_meal_recommendations(
        100.0, 20.0, api_key="test-key", servings=3, max_ready_time=20
    )

    assert all(call["params"]["minServings"] == 3 for call in stub.calls)
    assert all(call["params"]["maxServings"] == 3 for call in stub.calls)
    assert all(call["params"]["maxReadyTime"] == 20 for call in stub.calls)


def test_fetch_meal_recommendations_passes_diet_filter_through(patched_requests):
    responses = [
        results_response([make_recipe(1, "Breakfast Recipe", 20.0, 4.0, 300)]),
        results_response([make_recipe(2, "Lunch Recipe", 28.0, 7.0, 450)]),
        results_response([make_recipe(3, "Dinner Recipe", 32.0, 8.0, 520)]),
    ]
    stub = patched_requests(StubRequestsModule(responses=responses))

    fetch_meal_recommendations(100.0, 20.0, diet_type="Vegetarian", api_key="test-key")

    assert all(call["params"].get("diet") == "vegetarian" for call in stub.calls)


def test_fetch_meal_recommendations_maps_pescatarian_to_pescetarian(patched_requests):
    responses = [
        results_response([make_recipe(1, "Breakfast Recipe", 20.0, 4.0, 300)]),
        results_response([make_recipe(2, "Lunch Recipe", 28.0, 7.0, 450)]),
        results_response([make_recipe(3, "Dinner Recipe", 32.0, 8.0, 520)]),
    ]
    stub = patched_requests(StubRequestsModule(responses=responses))

    fetch_meal_recommendations(100.0, 20.0, diet_type="Pescatarian", api_key="test-key")

    assert all(call["params"].get("diet") == "pescetarian" for call in stub.calls)


def test_fetch_meal_recommendations_applies_no_diet_filter_for_omnivore(patched_requests):
    responses = [
        results_response([make_recipe(1, "Breakfast Recipe", 20.0, 4.0, 300)]),
        results_response([make_recipe(2, "Lunch Recipe", 28.0, 7.0, 450)]),
        results_response([make_recipe(3, "Dinner Recipe", 32.0, 8.0, 520)]),
    ]
    stub = patched_requests(StubRequestsModule(responses=responses))

    fetch_meal_recommendations(100.0, 20.0, diet_type="Omnivore", api_key="test-key")

    assert all("diet" not in call["params"] for call in stub.calls)


def test_fetch_meal_recommendations_excludes_recent_recipe_ids(patched_requests):
    responses = [
        results_response(
            [make_recipe(1, "Old Breakfast", 20.0, 4.0, 300), make_recipe(2, "New Breakfast", 20.0, 4.0, 300)]
        ),
        results_response([make_recipe(3, "Lunch Recipe", 28.0, 7.0, 450)]),
        results_response([make_recipe(4, "Dinner Recipe", 32.0, 8.0, 520)]),
    ]
    patched_requests(StubRequestsModule(responses=responses))

    payload = fetch_meal_recommendations(
        100.0, 20.0, exclude_recipe_ids=[1], api_key="test-key"
    )

    assert payload["meals"][0]["meal_name"] == "New Breakfast"


def test_fetch_meal_recommendations_notes_forced_repeats(patched_requests):
    only_recipe = [make_recipe(1, "Only Breakfast", 20.0, 4.0, 300)]
    responses = [
        results_response(only_recipe),
        results_response([]),  # exhausts paging for breakfast, forces repeat
        results_response([make_recipe(2, "Lunch Recipe", 28.0, 7.0, 450)]),
        results_response([make_recipe(3, "Dinner Recipe", 32.0, 8.0, 520)]),
    ]
    patched_requests(StubRequestsModule(responses=responses))

    payload = fetch_meal_recommendations(
        100.0, 20.0, exclude_recipe_ids=[1], api_key="test-key"
    )

    assert payload["meals"][0]["meal_name"] == "Only Breakfast"
    assert "Breakfast" in payload["notes"]


def test_fetch_meal_recommendations_skips_meals_with_no_matches(patched_requests):
    responses = [
        results_response([make_recipe(1, "Breakfast Recipe", 20.0, 4.0, 300)]),
        results_response([]),  # no lunch match at all
        results_response([make_recipe(3, "Dinner Recipe", 32.0, 8.0, 520)]),
    ]
    patched_requests(StubRequestsModule(responses=responses))

    payload = fetch_meal_recommendations(100.0, 20.0, api_key="test-key")

    assert [meal["meal_type"] for meal in payload["meals"]] == ["Breakfast", "Dinner"]
    assert "Lunch" in payload["notes"]


def test_fetch_meal_recommendations_raises_when_nothing_matches(patched_requests):
    responses = [results_response([]) for _ in range(3)]
    patched_requests(StubRequestsModule(responses=responses))

    with pytest.raises(MealRecommendationError, match="No matching recipes"):
        fetch_meal_recommendations(100.0, 20.0, api_key="test-key")


def test_fetch_meal_recommendations_avoids_duplicate_recipe_across_meals(
    patched_requests,
):
    # Same top candidate (id=1) shows up first for both Breakfast and Lunch
    # searches; Lunch should fall through to the second candidate (id=2).
    responses = [
        results_response([make_recipe(1, "Recipe A", 20.0, 4.0, 300)]),
        results_response(
            [make_recipe(1, "Recipe A", 20.0, 4.0, 300), make_recipe(2, "Recipe B", 25.0, 6.0, 400)]
        ),
        results_response([make_recipe(3, "Recipe C", 30.0, 7.0, 500)]),
    ]
    patched_requests(StubRequestsModule(responses=responses))

    payload = fetch_meal_recommendations(100.0, 20.0, api_key="test-key")

    names = [meal["meal_name"] for meal in payload["meals"]]
    assert names == ["Recipe A", "Recipe B", "Recipe C"]


def test_fetch_meal_recommendations_handles_missing_nutrition_gracefully(
    patched_requests,
):
    recipe_without_nutrition = {"id": 1, "title": "Mystery Recipe"}
    responses = [
        results_response([recipe_without_nutrition]),
        results_response([]),
        results_response([]),
    ]
    patched_requests(StubRequestsModule(responses=responses))

    payload = fetch_meal_recommendations(100.0, 20.0, api_key="test-key")

    assert payload["meals"][0]["estimated_protein_grams"] is None
    assert payload["meals"][0]["description"] is None


# --- get_api_key ----------------------------------------------------------------


def test_get_api_key_prefers_environment_variable(monkeypatch):
    monkeypatch.setenv("SPOONACULAR_API_KEY", "env-key")
    assert get_api_key({"spoonacular_api_key": "secret-key"}) == "env-key"


def test_get_api_key_falls_back_to_secrets(monkeypatch):
    monkeypatch.delenv("SPOONACULAR_API_KEY", raising=False)
    assert get_api_key({"spoonacular_api_key": "secret-key"}) == "secret-key"


def test_get_api_key_returns_none_when_unconfigured(monkeypatch):
    monkeypatch.delenv("SPOONACULAR_API_KEY", raising=False)
    assert get_api_key(None) is None


def test_get_api_key_ignores_secrets_that_raise_on_bool_check(monkeypatch):
    """st.secrets raises on truthiness (not just .get) when there is no
    secrets.toml at all — a bare ``if secrets:`` must not crash either."""

    class BoolExplodingSecrets:
        def __bool__(self):
            raise RuntimeError("no secrets file")

        def get(self, key, default=None):
            raise RuntimeError("no secrets file")

    monkeypatch.delenv("SPOONACULAR_API_KEY", raising=False)
    assert get_api_key(BoolExplodingSecrets()) is None
