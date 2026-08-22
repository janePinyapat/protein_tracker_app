"""Lookup helpers for the USDA FoodData Central API.

Nutrition numbers come from the public FoodData Central database rather than
being hardcoded in this project. The API is free but needs a key from
https://fdc.nal.usda.gov/api-key-signup.html

The key is read from, in order:

1. the ``USDA_API_KEY`` environment variable
2. ``.streamlit/secrets.toml`` (a ``usda_api_key`` entry)
3. ``DEMO_KEY``, the shared api.data.gov demo key

``DEMO_KEY`` is heavily rate limited and is only meant for a first look. No key
is stored in this repository.
"""

import os

import requests


SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
DEMO_KEY = "DEMO_KEY"
REQUEST_TIMEOUT_SECONDS = 10

# FoodData Central nutrient ids. These are stable across the dataset.
NUTRIENT_IDS = {
    "protein_grams": 1003,
    "fat_grams": 1004,
    "carbs_grams": 1005,
    "calories": 1008,
    "fiber_grams": 1079,
}

# Values in a search response are reported per 100 g of the food.
REFERENCE_GRAMS = 100.0


class FoodLookupError(Exception):
    """Raised when a food lookup cannot be completed."""


def get_api_key(secrets=None):
    """Return the FoodData Central API key to use for requests."""
    environment_key = os.environ.get("USDA_API_KEY", "").strip()
    if environment_key:
        return environment_key

    if secrets is not None:
        try:
            secret_key = str(secrets.get("usda_api_key", "")).strip()
        except Exception:
            # st.secrets raises (rather than just being falsy) when no
            # secrets.toml file exists at all, so any access is guarded.
            secret_key = ""
        if secret_key:
            return secret_key

    return DEMO_KEY


def is_using_demo_key(api_key):
    """Report whether the shared, rate-limited demo key is in use."""
    return api_key == DEMO_KEY


def extract_nutrient(food_nutrients, nutrient_id):
    """Pull one nutrient value out of a FoodData Central nutrient list.

    The search endpoint reports ``nutrientId`` at the top level while the
    detail endpoint nests it under ``nutrient``, so both shapes are accepted.
    """
    if not food_nutrients:
        return None

    for nutrient in food_nutrients:
        if not isinstance(nutrient, dict):
            continue

        current_id = nutrient.get("nutrientId")
        if current_id is None:
            nested = nutrient.get("nutrient")
            if isinstance(nested, dict):
                current_id = nested.get("id")

        if current_id != nutrient_id:
            continue

        value = nutrient.get("value")
        if value is None:
            value = nutrient.get("amount")

        if value is None:
            continue

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    return None


def parse_food_result(raw_food):
    """Turn one raw search result into the fields this app stores.

    All nutrient values are per 100 g, matching what the search endpoint
    returns.
    """
    nutrients = raw_food.get("foodNutrients", [])

    parsed = {
        "fdc_id": raw_food.get("fdcId"),
        "description": (raw_food.get("description") or "").strip(),
        "brand": (raw_food.get("brandOwner") or "").strip(),
        "data_type": raw_food.get("dataType", ""),
        "reference_grams": REFERENCE_GRAMS,
    }

    for field_name, nutrient_id in NUTRIENT_IDS.items():
        parsed[field_name] = extract_nutrient(nutrients, nutrient_id)

    return parsed


def scale_to_portion(parsed_food, portion_grams):
    """Scale per-100 g nutrient values to the portion the user actually ate."""
    if portion_grams is None or portion_grams <= 0:
        raise ValueError("portion_grams must be greater than zero")

    factor = portion_grams / parsed_food.get("reference_grams", REFERENCE_GRAMS)

    scaled = dict(parsed_food)
    scaled["portion_grams"] = portion_grams

    for field_name in NUTRIENT_IDS:
        value = parsed_food.get(field_name)
        scaled[field_name] = None if value is None else round(value * factor, 1)

    return scaled


def format_food_label(parsed_food):
    """Build a readable one-line label for a search result."""
    label = parsed_food.get("description") or "Unnamed food"

    brand = parsed_food.get("brand")
    if brand:
        label = f"{label} — {brand}"

    data_type = parsed_food.get("data_type")
    if data_type:
        label = f"{label} ({data_type})"

    return label


def search_foods(query, api_key=None, page_size=10, session=None):
    """Search FoodData Central and return parsed results.

    ``session`` exists so tests can pass a stub instead of making a network
    call. Any network or decoding problem is re-raised as ``FoodLookupError``
    so the page can show a message and fall back to manual entry.
    """
    if not query or not query.strip():
        return []

    api_key = api_key or get_api_key()
    requester = session or requests

    try:
        response = requester.get(
            SEARCH_URL,
            params={
                "query": query.strip(),
                "pageSize": page_size,
                "api_key": api_key,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except Exception as error:
        raise FoodLookupError(f"Could not reach FoodData Central: {error}") from error

    if response.status_code == 403:
        raise FoodLookupError(
            "FoodData Central rejected the API key. Check USDA_API_KEY."
        )

    if response.status_code == 429:
        raise FoodLookupError(
            "FoodData Central rate limit reached. This happens quickly on the "
            "shared demo key — add your own USDA_API_KEY to raise the limit."
        )

    if response.status_code != 200:
        raise FoodLookupError(
            f"FoodData Central returned status {response.status_code}."
        )

    try:
        payload = response.json()
    except Exception as error:
        raise FoodLookupError("FoodData Central returned an unreadable response.") from error

    return [parse_food_result(food) for food in payload.get("foods", [])]
