"""Vocabulary and tag-personalization rules for the user's profile.

The profile (diet type + purpose) is captured once during onboarding and can
be edited any time from the Profile page. It is used for exactly one thing:
reordering which tag suggestions appear first when logging food. It never
hides a tag, restricts what can be logged, or changes a macro/goal
calculation — every starter tag stays available to everyone regardless of
profile.
"""

DIET_TYPES = [
    "Omnivore",
    "Vegetarian",
    "Vegan",
    "Pescatarian",
    "Other / prefer not to say",
]

PURPOSES = [
    "PCOS management",
    "Strength training / muscle recovery",
    "General health tracking",
    "Other",
]

# Starter tags (see food_tags.STARTER_TAGS) promoted to the top of the tag
# picker for a given diet type or purpose. This is a suggested order only.
DIET_TAG_PRIORITY = {
    "Vegan": ["Plant-based"],
    "Vegetarian": ["Plant-based", "Dairy"],
    "Pescatarian": ["Plant-based"],
}

PURPOSE_TAG_PRIORITY = {
    "PCOS management": ["Low glycemic", "High fiber", "Added sugar", "Refined carbs"],
    "Strength training / muscle recovery": [
        "High protein",
        "Pre-workout",
        "Post-workout",
        "Home cooked",
    ],
}


def get_priority_tags(diet_type, purposes):
    """Tags to suggest first, in order, for this profile.

    Duplicates across diet type and purpose are kept only once, in the order
    first encountered.
    """
    priority = []

    for tag in DIET_TAG_PRIORITY.get(diet_type, []):
        if tag not in priority:
            priority.append(tag)

    for purpose in purposes or []:
        for tag in PURPOSE_TAG_PRIORITY.get(purpose, []):
            if tag not in priority:
                priority.append(tag)

    return priority
