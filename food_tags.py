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
    "Home cooked",
    "Low glycemic",
    "Plant-based",
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


def build_tag_options(saved_tags=None):
    """Combine the starter labels with any tags already saved by the user."""
    options = list(STARTER_TAGS)

    for tag in saved_tags or []:
        if tag and tag not in options:
            options.append(tag)

    return sorted(options, key=str.casefold)
