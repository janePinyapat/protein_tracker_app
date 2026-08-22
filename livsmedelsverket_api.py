"""Lookup helpers for Livsmedelsverket's food composition database.

Livsmedelsverket (the Swedish National Food Agency) publishes a free, keyless
REST API covering roughly 2,600 Swedish foods and dishes:
https://dataportal.livsmedelsverket.se/livsmedel/swagger/index.html

Unlike USDA FoodData Central, no signup or API key is needed and there is no
documented rate limit. The trade-off is there is no server-side search
endpoint, so the food list is fetched once and matched by name locally.

Per Livsmedelsverket's terms of reuse, any use of this data must cite the
source as "Livsmedelsverkets Livsmedelsdatabasen" (CC BY 4.0).
"""

import requests


BASE_URL = "https://dataportal.livsmedelsverket.se/livsmedel/api/v1"
REQUEST_TIMEOUT_SECONDS = 15

# sprak=2 returns English food names and nutrient names; sprak=1 is Swedish.
LANGUAGE_ENGLISH = 2

# The catalog currently holds ~2,600 foods. This is fetched in one request
# (no pagination needed) with headroom for the catalog to grow.
CATALOG_FETCH_LIMIT = 5000

# All nutrient values from this API are reported per 100 g of the food.
REFERENCE_GRAMS = 100.0

# EuroFIR thesaurus codes used by this API. Each of these is unique per food
# except ENERC, which appears twice (kJ and kcal) and is disambiguated by unit.
NUTRIENT_CODES = {
    "protein_grams": "PROT",
    "carbs_grams": "CHO",
    "fat_grams": "FAT",
    "fiber_grams": "FIBT",
}
CALORIE_CODE = "ENERC"
CALORIE_UNIT = "kcal"

ATTRIBUTION = (
    "Nutrition data: Livsmedelsverkets Livsmedelsdatabasen "
    "(Swedish National Food Agency), CC BY 4.0."
)


class FoodLookupError(Exception):
    """Raised when a food lookup cannot be completed."""


def extract_nutrient_value(nutrients, euro_fir_code, unit=None):
    """Pull one nutrient value out of a naringsvarden response list."""
    if not nutrients:
        return None

    for nutrient in nutrients:
        if not isinstance(nutrient, dict):
            continue

        if nutrient.get("euroFIRkod") != euro_fir_code:
            continue

        if unit is not None and nutrient.get("enhet") != unit:
            continue

        value = nutrient.get("varde")
        if value is None:
            continue

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    return None


def parse_nutrients(nutrient_list):
    """Turn a naringsvarden response into the macro fields this app stores."""
    parsed = {
        field_name: extract_nutrient_value(nutrient_list, code)
        for field_name, code in NUTRIENT_CODES.items()
    }
    parsed["calories"] = extract_nutrient_value(
        nutrient_list, CALORIE_CODE, CALORIE_UNIT
    )
    return parsed


def parse_catalog_entry(raw_food):
    """Extract the id and English name from one food-list entry."""
    return {
        "nummer": raw_food.get("nummer"),
        "description": (raw_food.get("namn") or "").strip(),
    }


def fetch_food_catalog(session=None):
    """Fetch the full food list once, for local name matching.

    There is no search-by-name endpoint on this API, so the whole catalog
    (~2,600 items, ~1.5 MB) is fetched and filtered client-side. Callers
    should cache the result rather than calling this on every keystroke.
    """
    requester = session or requests

    try:
        response = requester.get(
            f"{BASE_URL}/livsmedel",
            params={
                "offset": 0,
                "limit": CATALOG_FETCH_LIMIT,
                "sprak": LANGUAGE_ENGLISH,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except Exception as error:
        raise FoodLookupError(
            f"Could not reach the Swedish Food Agency database: {error}"
        ) from error

    if response.status_code != 200:
        raise FoodLookupError(
            f"Swedish Food Agency database returned status {response.status_code}."
        )

    try:
        payload = response.json()
    except Exception as error:
        raise FoodLookupError(
            "Swedish Food Agency database returned an unreadable response."
        ) from error

    return [parse_catalog_entry(food) for food in payload.get("livsmedel", [])]


def search_catalog(query, catalog, max_results=15):
    """Filter an already-fetched catalog by a case-insensitive substring."""
    if not query or not query.strip():
        return []

    needle = query.strip().lower()
    matches = [food for food in catalog if needle in food["description"].lower()]
    return matches[:max_results]


def fetch_food_nutrients(nummer, session=None):
    """Fetch and parse the macro values for one food, per 100 g."""
    requester = session or requests

    try:
        response = requester.get(
            f"{BASE_URL}/livsmedel/{nummer}/naringsvarden",
            params={"sprak": LANGUAGE_ENGLISH},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except Exception as error:
        raise FoodLookupError(
            f"Could not reach the Swedish Food Agency database: {error}"
        ) from error

    if response.status_code != 200:
        raise FoodLookupError(
            f"Swedish Food Agency database returned status {response.status_code}."
        )

    try:
        payload = response.json()
    except Exception as error:
        raise FoodLookupError(
            "Swedish Food Agency database returned an unreadable response."
        ) from error

    nutrients = parse_nutrients(payload)
    nutrients["reference_grams"] = REFERENCE_GRAMS
    return nutrients


def scale_to_portion(parsed_food, portion_grams):
    """Scale per-100 g nutrient values to the portion the user actually ate."""
    if portion_grams is None or portion_grams <= 0:
        raise ValueError("portion_grams must be greater than zero")

    factor = portion_grams / parsed_food.get("reference_grams", REFERENCE_GRAMS)

    scaled = dict(parsed_food)
    scaled["portion_grams"] = portion_grams

    for field_name in list(NUTRIENT_CODES) + ["calories"]:
        value = parsed_food.get(field_name)
        scaled[field_name] = None if value is None else round(value * factor, 1)

    return scaled


def format_food_label(parsed_food):
    """Build a readable label for a search result."""
    return parsed_food.get("description") or "Unnamed food"
