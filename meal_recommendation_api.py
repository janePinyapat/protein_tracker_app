"""Recipe suggestions for today's remaining protein/fiber target.

Uses Spoonacular's recipe database (https://spoonacular.com/food-api),
searched directly by meal type and nutrient range — no AI model involved.
The free tier here needs only a signup, never a payment: get a free key at
https://spoonacular.com/food-api/console#Dashboard, then set
SPOONACULAR_API_KEY (env var) or spoonacular_api_key in
.streamlit/secrets.toml.

Today's remaining protein/fiber is split across breakfast/lunch/dinner using
a simple fixed share (see MEAL_SHARE below) — a transparent heuristic, not
personalized meal-timing advice. Each meal is matched with Spoonacular's
``complexSearch`` endpoint: filtered by recipe type (Spoonacular has no
separate "lunch"/"dinner" category, so both map to "main course" and rely on
the protein/fiber window plus duplicate-avoidance to tell them apart), by the
user's diet type (vegetarian/vegan/pescatarian, via Spoonacular's own ``diet``
filter — never just filtered out after the fact), and by a window around
that meal's share of the remaining target.

To avoid recommending the same recipe on repeat visits, callers can pass
``exclude_recipe_ids`` (e.g. everything recommended in the last two weeks).
Candidates are paged through (via ``offset``) to find one outside that list;
if a diet+meal-type combination has too few matching recipes to avoid every
recent id, this falls back to allowing a repeat rather than returning
nothing, and says so in the returned ``notes``.

Callers can also pass ``servings`` (an exact match against Spoonacular's
``minServings``/``maxServings``), ``max_ready_time`` (Spoonacular's
``maxReadyTime``, in minutes), and ``include_ingredients`` (a list of
ingredient names, e.g. what's already in the fridge, joined into
Spoonacular's ``includeIngredients``) — all optional, and all apply the
same way to all three meals. Spoonacular's own docs don't spell out
whether ``includeIngredients`` requires every listed ingredient to appear
or just some of them, so listing more than a couple narrows results more
than it might seem like it should. Each returned meal includes
``image_url`` straight from Spoonacular's ``image`` field, for display
only (not re-hosted or downloaded).
"""

import os

import requests


BASE_URL = "https://api.spoonacular.com/recipes"
REQUEST_TIMEOUT_SECONDS = 15

MEAL_TYPES = ["Breakfast", "Lunch", "Dinner"]

# Spoonacular's recipe "type" taxonomy has no separate lunch/dinner category.
MEAL_TYPE_TO_SPOONACULAR_TYPE = {
    "Breakfast": "breakfast",
    "Lunch": "main course",
    "Dinner": "main course",
}

# This app's diet-type vocabulary (see user_profile.DIET_TYPES) mapped to
# Spoonacular's `diet` filter values. Note Spoonacular spells it
# "pescetarian". Omnivore and "Other / prefer not to say" apply no filter.
DIET_TYPE_TO_SPOONACULAR_DIET = {
    "Vegetarian": "vegetarian",
    "Vegan": "vegan",
    "Pescatarian": "pescetarian",
}

# How today's remaining protein/fiber is split across the three meals.
MEAL_SHARE = {"Breakfast": 0.25, "Lunch": 0.35, "Dinner": 0.40}

# Search window around each meal's share: how far above/below still counts
# as a match. Fiber only gets a soft floor since exact matches are rarer.
PROTEIN_WINDOW_GRAMS = 12
FIBER_FLOOR_SLACK_GRAMS = 2
CANDIDATES_PER_MEAL = 5

# How many pages of candidates to try before giving up on avoiding a repeat
# and falling back to the first page instead.
MAX_REPEAT_AVOIDANCE_PAGES = 3

DISCLAIMER = (
    "These are real recipes matched by meal type and protein/fiber content "
    "from Spoonacular's recipe database, not a personalized meal plan — "
    "check the source, and treat the listed macros as that recipe's own "
    "nutrition estimate. Not medical or dietary advice."
)


class MealRecommendationError(Exception):
    """Raised when meal recommendations can't be fetched."""


def get_api_key(secrets=None):
    """Return the Spoonacular API key to use, or None if unconfigured."""
    environment_key = os.environ.get("SPOONACULAR_API_KEY", "").strip()
    if environment_key:
        return environment_key

    if secrets is not None:
        try:
            secret_key = str(secrets.get("spoonacular_api_key", "")).strip()
        except Exception:
            # st.secrets raises (rather than just being falsy) when no
            # secrets.toml file exists at all, so any access is guarded.
            secret_key = ""
        if secret_key:
            return secret_key

    return None


def split_remaining_by_meal(protein_remaining, fiber_remaining):
    """Split today's remaining protein/fiber across breakfast/lunch/dinner."""
    protein_remaining = max(protein_remaining or 0.0, 0.0)
    fiber_remaining = max(fiber_remaining or 0.0, 0.0)

    return {
        meal_type: {
            "protein_grams": protein_remaining * share,
            "fiber_grams": fiber_remaining * share,
        }
        for meal_type, share in MEAL_SHARE.items()
    }


def extract_nutrient(nutrients, name):
    """Pull one named value out of a complexSearch recipe's nutrient list."""
    for nutrient in nutrients or []:
        if nutrient.get("name") == name:
            return nutrient.get("amount")
    return None


def describe_recipe(recipe):
    """Build a short 'ready in N min' caption for a recipe.

    Deliberately omits the recipe's serving count — Spoonacular's protein/
    fiber/calorie figures are already per serving (see fetch_meal_
    recommendations' docstring), so showing "serves N" next to them read as
    if the numbers needed dividing by N, which they don't.
    """
    parts = []
    if recipe.get("readyInMinutes"):
        parts.append(f"Ready in {recipe['readyInMinutes']} min")
    return " · ".join(parts) if parts else None


def _get(url, params, api_key):
    try:
        response = requests.get(
            url, params={**params, "apiKey": api_key}, timeout=REQUEST_TIMEOUT_SECONDS
        )
    except Exception as error:
        raise MealRecommendationError(f"Could not reach Spoonacular: {error}") from error

    if response.status_code == 401:
        raise MealRecommendationError(
            "Spoonacular rejected the API key. Check SPOONACULAR_API_KEY."
        )
    if response.status_code == 402:
        raise MealRecommendationError(
            "Spoonacular's daily free quota has been used up. Try again tomorrow."
        )
    if response.status_code != 200:
        raise MealRecommendationError(
            f"Spoonacular returned status {response.status_code}."
        )

    try:
        return response.json()
    except Exception as error:
        raise MealRecommendationError(
            "Spoonacular returned an unreadable response."
        ) from error


def search_recipes(
    meal_type,
    min_protein,
    max_protein,
    min_fiber,
    api_key,
    diet=None,
    servings=None,
    max_ready_time=None,
    include_ingredients=None,
    offset=0,
    number=CANDIDATES_PER_MEAL,
):
    """Search Spoonacular for recipes of one meal type within a protein/fiber range.

    ``servings`` filters to recipes yielding exactly that many servings
    (Spoonacular's ``minServings``/``maxServings`` set to the same value).
    ``max_ready_time`` filters to recipes ready within that many minutes
    (Spoonacular's ``maxReadyTime``). ``include_ingredients`` is a list of
    ingredient names to steer results toward (Spoonacular's own
    ``includeIngredients``, comma-joined) — e.g. what's already in the
    fridge. All three are omitted from the request when not given, applying
    no filter (Spoonacular then picks automatically, same as before this
    option existed).
    """
    params = {
        "type": MEAL_TYPE_TO_SPOONACULAR_TYPE[meal_type],
        "minProtein": round(min_protein, 1),
        "maxProtein": round(max_protein, 1),
        "minFiber": round(min_fiber, 1),
        "addRecipeNutrition": "true",
        "number": number,
        "offset": offset,
    }
    if diet:
        params["diet"] = diet
    if servings:
        params["minServings"] = servings
        params["maxServings"] = servings
    if max_ready_time:
        params["maxReadyTime"] = max_ready_time
    if include_ingredients:
        params["includeIngredients"] = ",".join(include_ingredients)

    payload = _get(f"{BASE_URL}/complexSearch", params, api_key)
    return payload.get("results", [])


def find_candidate(
    meal_type,
    min_protein,
    max_protein,
    min_fiber,
    api_key,
    diet,
    exclude_ids,
    used_ids,
    servings=None,
    max_ready_time=None,
    include_ingredients=None,
):
    """Find a recipe for one meal, preferring one outside ``exclude_ids``.

    Pages through results (via ``offset``) looking for a match that isn't in
    ``exclude_ids`` (recently recommended) or ``used_ids`` (already picked
    for another meal in this same run). If the candidate pool is too small
    to avoid every recent id, falls back to the first page rather than
    returning nothing — still excluding ``used_ids`` so this run never picks
    the same recipe twice. Returns ``(recipe_or_none, was_forced_repeat)``.
    """
    offset = 0
    first_page = None

    for _ in range(MAX_REPEAT_AVOIDANCE_PAGES):
        candidates = search_recipes(
            meal_type,
            min_protein,
            max_protein,
            min_fiber,
            api_key,
            diet=diet,
            servings=servings,
            max_ready_time=max_ready_time,
            include_ingredients=include_ingredients,
            offset=offset,
        )
        if offset == 0:
            first_page = candidates
        if not candidates:
            break

        pick = next(
            (
                candidate
                for candidate in candidates
                if candidate.get("id") not in used_ids and candidate.get("id") not in exclude_ids
            ),
            None,
        )
        if pick is not None:
            return pick, False

        offset += len(candidates)

    if first_page:
        pick = next(
            (candidate for candidate in first_page if candidate.get("id") not in used_ids),
            None,
        )
        if pick is not None:
            return pick, True

    return None, False


def fetch_meal_recommendations(
    protein_remaining,
    fiber_remaining,
    diet_type=None,
    exclude_recipe_ids=None,
    api_key=None,
    servings=None,
    max_ready_time=None,
    include_ingredients=None,
):
    """Find one Spoonacular recipe each for breakfast, lunch, and dinner,
    sized to a share of today's remaining protein/fiber target.

    ``diet_type`` is this app's own vocabulary (e.g. "Vegetarian") — mapped
    internally to Spoonacular's ``diet`` filter, so results are excluded by
    Spoonacular itself rather than fetched and then discarded.
    ``exclude_recipe_ids`` are recipe ids to steer away from repeating (see
    ``find_candidate``). ``servings``, ``max_ready_time``, and
    ``include_ingredients`` apply the same way to all three meals (see
    ``search_recipes``) — all optional, and each is simply omitted from the
    Spoonacular request when not given.

    Returns ``{"meals": [...], "notes": ...}``.
    """
    api_key = api_key if api_key is not None else get_api_key()
    if not api_key:
        raise MealRecommendationError(
            "No Spoonacular API key configured. Set the SPOONACULAR_API_KEY "
            "environment variable, or add spoonacular_api_key to "
            ".streamlit/secrets.toml, to get meal suggestions."
        )

    diet = DIET_TYPE_TO_SPOONACULAR_DIET.get(diet_type)
    exclude_ids = set(exclude_recipe_ids or [])
    shares = split_remaining_by_meal(protein_remaining, fiber_remaining)

    meals = []
    used_ids = set()
    repeated_meal_types = []

    for meal_type in MEAL_TYPES:
        target = shares[meal_type]
        min_protein = max(target["protein_grams"] - PROTEIN_WINDOW_GRAMS, 0)
        max_protein = target["protein_grams"] + PROTEIN_WINDOW_GRAMS
        min_fiber = max(target["fiber_grams"] - FIBER_FLOOR_SLACK_GRAMS, 0)

        pick, was_repeat = find_candidate(
            meal_type,
            min_protein,
            max_protein,
            min_fiber,
            api_key,
            diet,
            exclude_ids,
            used_ids,
            servings=servings,
            max_ready_time=max_ready_time,
            include_ingredients=include_ingredients,
        )
        if pick is None:
            continue

        used_ids.add(pick["id"])
        if was_repeat:
            repeated_meal_types.append(meal_type)

        nutrients = (pick.get("nutrition") or {}).get("nutrients", [])

        meals.append(
            {
                "meal_type": meal_type,
                "recipe_id": pick.get("id"),
                "meal_name": pick.get("title") or "Untitled recipe",
                "description": describe_recipe(pick),
                "estimated_protein_grams": extract_nutrient(nutrients, "Protein"),
                "estimated_fiber_grams": extract_nutrient(nutrients, "Fiber"),
                "estimated_calories": extract_nutrient(nutrients, "Calories"),
                "source_title": pick.get("sourceName") or pick.get("title"),
                "source_url": pick.get("sourceUrl"),
                "image_url": pick.get("image"),
            }
        )

    if not meals:
        raise MealRecommendationError(
            "No matching recipes were found for today's target. Try "
            "refreshing, or adjust your target on the form below."
        )

    notes_parts = []
    if len(meals) < len(MEAL_TYPES):
        missing = ", ".join(
            sorted(set(MEAL_TYPES) - {meal["meal_type"] for meal in meals})
        )
        notes_parts.append(f"No matching recipe found for: {missing}.")
    if repeated_meal_types:
        notes_parts.append(
            f"Not enough new matches for {', '.join(repeated_meal_types)}, so "
            "it repeats a recent recommendation."
        )

    return {"meals": meals, "notes": " ".join(notes_parts)}
