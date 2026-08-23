"""Shared vocabulary for the labels a user can attach to a food entry.

These are descriptive labels the user applies themselves, not a rating. The
app never scores a food, ranks one tag above another, or suggests what anyone
should eat — it only counts and charts back the labels that were entered.

The starter list below is a convenience, not a recommendation. Users can type
their own tags, and any tag they save shows up alongside these.
"""

# Descriptive starter labels drawn from terms that come up in PCOS and
# recovery nutrition conversations. Ordering is alphabetical, not a ranking.
STARTER_TAGS = [
    "Added sugar",
    "Dairy",
    "Eating out",
    "Gluten",
    "High fiber",
    "High protein",
    "Home cooked",
    "Low glycemic",
    "Plant-based",
    "Post-workout",
    "Pre-workout",
    "Processed",
    "Refined carbs",
    "Whole grain",
]

TAG_DISCLAIMER = (
    "Tags are your own labels. This app does not rate foods, rank tags, or "
    "give nutrition or medical advice — it only totals and charts what you "
    "entered. For guidance on PCOS or recovery nutrition, talk to a "
    "registered dietitian or your doctor."
)

TAG_HELP = (
    "Pick any labels that describe this food to you, or type your own. "
    "You can apply more than one."
)


# Per-serving thresholds used to auto-suggest the two macro-based starter
# tags. These are simple, fixed numbers describing the amount logged, not a
# nutrition claim or a judgment that more or less is better. 5 g fiber
# matches the amount common "high fiber" food-labeling thresholds use;
# 20 g protein is a common per-meal reference point in sports nutrition.
HIGH_PROTEIN_THRESHOLD_GRAMS = 20
HIGH_FIBER_THRESHOLD_GRAMS = 5

# Keyword -> tag: matched as a case-insensitive substring of the food
# description. A description can match more than one tag. Deliberately
# narrow and literal (no attempt to guess cuisine, cooking method, or
# glycemic index) so a suggestion is never asserting something the
# description didn't actually say.
DESCRIPTION_KEYWORD_TAGS = {
    "Dairy": ["yogurt", "yoghurt", "cheese", "milk", "skyr", "cream"],
    "Plant-based": ["tofu", "tempeh", "lentil", "chickpea", "seitan", "edamame"],
    "Whole grain": ["whole grain", "whole wheat", "brown rice", "oats", "oatmeal", "quinoa"],
    "Gluten": ["bread", "pasta", "noodle", "wheat", "bagel", "cracker"],
    "Added sugar": ["sugar", "syrup", "honey", "candy", "soda", "cake", "cookie", "dessert", "chocolate"],
    "Eating out": ["restaurant", "takeout", "take-out", "delivery", "drive-thru", "drive through"],
    "Processed": ["protein bar", "protein shake", "frozen meal", "fast food"],
}

# Fields already picked from a dropdown map straight to a tag — no guessing.
PROTEIN_SOURCE_TAGS = {
    "Plant-based/Tofu": ["Plant-based"],
    "Legumes/Beans": ["Plant-based"],
    "Dairy": ["Dairy"],
    "Protein powder": ["Processed"],
}

MEAL_TYPE_TAGS = {
    "Post-workout": ["Post-workout"],
}


def suggest_tags_from_entry(
    description="",
    protein_grams=0.0,
    fiber_grams=0.0,
    meal_type=None,
    protein_source=None,
):
    """Suggest descriptive labels from what was entered when logging a food.

    Purely descriptive — matched from the exact text/fields entered (keyword
    match on the description, direct lookup for meal type and protein
    source) or a fixed gram threshold for the two macro tags. Never infers
    anything the entry didn't say (no cuisine, cooking method, or glycemic
    index guessing), and never implies the amount logged is good or bad.
    Returned in a stable, de-duplicated order.
    """
    suggested = []

    def add(tag):
        if tag not in suggested:
            suggested.append(tag)

    description_text = (description or "").lower()
    for tag, keywords in DESCRIPTION_KEYWORD_TAGS.items():
        if any(keyword in description_text for keyword in keywords):
            add(tag)

    for tag in PROTEIN_SOURCE_TAGS.get(protein_source, []):
        add(tag)

    for tag in MEAL_TYPE_TAGS.get(meal_type, []):
        add(tag)

    if protein_grams and protein_grams >= HIGH_PROTEIN_THRESHOLD_GRAMS:
        add("High protein")

    if fiber_grams and fiber_grams >= HIGH_FIBER_THRESHOLD_GRAMS:
        add("High fiber")

    return suggested


def build_tag_options(saved_tags=None, priority_tags=None):
    """Combine the starter labels with any tags already saved by the user.

    ``priority_tags`` (e.g. from the user's profile) moves matching tags to
    the front of the list. It only reorders — every tag stays available to
    everyone regardless of profile, and options not in ``priority_tags``
    keep their normal alphabetical order after it.
    """
    options = list(STARTER_TAGS)

    for tag in saved_tags or []:
        if tag and tag not in options:
            options.append(tag)

    priority = [tag for tag in (priority_tags or []) if tag in options]
    remaining = sorted(
        (tag for tag in options if tag not in priority), key=str.casefold
    )

    return priority + remaining
