from datetime import date

import streamlit as st

from database import (
    ALL_MEALS,
    ALL_SOURCES,
    ALL_TAGS,
    add_food_entry,
    delete_food_entry,
    get_all_food_entries,
    get_saved_tags,
    get_user_profile,
    initialize_database,
)
from food_photo_ai import FoodPhotoError, analyze_food_photo, get_api_key as get_anthropic_api_key
from food_tags import TAG_DISCLAIMER, TAG_HELP, build_tag_options, suggest_tags_from_entry
from livsmedelsverket_api import (
    ATTRIBUTION,
    FoodLookupError,
    fetch_food_catalog,
    fetch_food_nutrients,
    format_food_label,
    scale_to_portion,
    search_catalog,
)
from user_profile import get_priority_tags


MEAL_TYPES = ["Breakfast", "Lunch", "Dinner", "Snack", "Post-workout"]
PROTEIN_SOURCES = [
    "Meat/Poultry",
    "Fish/Seafood",
    "Eggs",
    "Dairy",
    "Legumes/Beans",
    "Plant-based/Tofu",
    "Protein powder",
    "Other",
]

EMPTY_PREFILL = {
    "description": "",
    "protein_grams": 0.0,
    "carbs_grams": 0.0,
    "fat_grams": 0.0,
    "fiber_grams": 0.0,
    "calories": 0.0,
    "meal_type": None,
}

ONE_DAY_SECONDS = 24 * 60 * 60


@st.cache_data(ttl=ONE_DAY_SECONDS, show_spinner=False)
def load_food_catalog():
    """Fetch the ~2,600-item food list once per day, not once per keystroke."""
    return fetch_food_catalog()


@st.cache_data(ttl=ONE_DAY_SECONDS, show_spinner=False)
def load_food_nutrients(nummer):
    """Fetch macro values for one food, cached per food id."""
    return fetch_food_nutrients(nummer)


def get_date_options(food_entries):
    """Create date filter options from saved food entries."""
    if food_entries.empty:
        return ["All dates"]

    dates = sorted(food_entries["log_date"].unique(), reverse=True)
    return ["All dates"] + dates


def filter_food_entries(
    food_entries, selected_date, selected_meal, selected_source, selected_tag
):
    """Filter food entries by date, meal type, protein source, and tag."""
    filtered = food_entries.copy()

    if selected_date != "All dates":
        filtered = filtered[filtered["log_date"] == selected_date]

    if selected_meal != ALL_MEALS:
        filtered = filtered[filtered["meal_type"] == selected_meal]

    if selected_source != ALL_SOURCES:
        filtered = filtered[filtered["protein_source"] == selected_source]

    if selected_tag != ALL_TAGS:
        has_tag = filtered["tags"].fillna("").apply(
            lambda tags: selected_tag in [tag.strip() for tag in tags.split(",")]
        )
        filtered = filtered[has_tag]

    return filtered


def prefill_from_lookup(parsed_food, portion_grams):
    """Copy scaled lookup numbers into the entry form."""
    scaled = scale_to_portion(parsed_food, portion_grams)

    st.session_state.prefill = {
        "description": scaled["description"] or "",
        "protein_grams": float(scaled.get("protein_grams") or 0.0),
        "carbs_grams": float(scaled.get("carbs_grams") or 0.0),
        "fat_grams": float(scaled.get("fat_grams") or 0.0),
        "fiber_grams": float(scaled.get("fiber_grams") or 0.0),
        "calories": float(scaled.get("calories") or 0.0),
    }


def prefill_from_photo_item(item):
    """Copy one AI-detected photo item into the entry form."""
    st.session_state.prefill = {
        "description": item.description,
        "protein_grams": float(item.protein_grams or 0.0),
        "carbs_grams": float(item.carbs_grams or 0.0),
        "fat_grams": float(item.fat_grams or 0.0),
        "fiber_grams": float(item.fiber_grams or 0.0),
        "calories": float(item.calories or 0.0),
    }


initialize_database()

if "prefill" not in st.session_state:
    st.session_state.prefill = dict(EMPTY_PREFILL)

if "lookup_results" not in st.session_state:
    st.session_state.lookup_results = []

if "photo_analysis" not in st.session_state:
    st.session_state.photo_analysis = None

st.title("Log Food")
st.write("Record what you ate, its macros, and any labels you want to track.")

with st.expander("Log food from a photo (AI-assisted)"):
    st.caption(
        "Take or upload a photo and Claude will try to identify the food and "
        "estimate its macros. This is a visual guess from a general-purpose "
        "AI model, not a lab measurement — always review the numbers below "
        "before using them, and adjust anything that looks off."
    )

    photo_source = st.radio(
        "Photo source", ["Take a photo", "Upload a photo"], horizontal=True
    )

    if photo_source == "Take a photo":
        photo = st.camera_input("Take a photo of your food")
    else:
        photo = st.file_uploader(
            "Upload a food photo", type=["jpg", "jpeg", "png", "webp"]
        )

    if photo is not None:
        st.image(photo, caption="Photo to analyze", width=250)

        if st.button("Analyze photo with AI"):
            with st.spinner("Asking Claude what's in this photo..."):
                try:
                    st.session_state.photo_analysis = analyze_food_photo(
                        photo.getvalue(),
                        photo.type,
                        api_key=get_anthropic_api_key(st.secrets),
                    )
                except FoodPhotoError as error:
                    st.session_state.photo_analysis = None
                    st.error(str(error))
                    st.caption(
                        "You can still enter macros manually in the form below."
                    )

    analysis = st.session_state.photo_analysis

    if analysis:
        if analysis.notes:
            st.info(analysis.notes)

        for index, item in enumerate(analysis.items):
            with st.container(border=True):
                st.markdown(f"**{item.description}** — {item.portion_estimate}")

                item_columns = st.columns(5)
                item_fields = [
                    ("Protein", item.protein_grams, "g"),
                    ("Carbs", item.carbs_grams, "g"),
                    ("Fat", item.fat_grams, "g"),
                    ("Fiber", item.fiber_grams, "g"),
                    ("Calories", item.calories, "kcal"),
                ]

                for column, (label, value, unit) in zip(item_columns, item_fields):
                    with column:
                        st.metric(label, "—" if value is None else f"{value:.0f} {unit}")

                if st.button("Use this item", key=f"use_photo_item_{index}"):
                    prefill_from_photo_item(item)
                    st.success("Copied into the form below.")
                    st.rerun()

    st.caption(
        "AI estimates only — not medical, nutrition, or dietary advice. "
        "Always double-check against the food itself."
    )

with st.expander("Look up nutrition data (Swedish Food Agency database)"):
    st.caption(
        "Search Livsmedelsverkets Livsmedelsdatabasen (the Swedish National "
        "Food Agency's food composition database) instead of typing macros "
        "by hand. No sign-up needed. Results are per 100 g and get scaled "
        "to your portion. Food names and dishes are mostly Swedish in "
        "origin. You can always skip this and enter the numbers yourself."
    )

    search_column, portion_column = st.columns([3, 1])

    with search_column:
        search_query = st.text_input(
            "Search foods", placeholder="e.g. salmon, lentils, yogurt"
        )

    with portion_column:
        portion_grams = st.number_input(
            "Portion (g)", min_value=1.0, value=100.0, step=10.0
        )

    if st.button("Search Swedish Food Database"):
        if not search_query.strip():
            st.warning("Enter a food to search for.")
        else:
            with st.spinner("Searching the food database..."):
                try:
                    catalog = load_food_catalog()
                    matches = search_catalog(search_query, catalog)
                    st.session_state.lookup_results = matches
                    if not matches:
                        st.info("No matches found. Try a different search term.")
                except FoodLookupError as error:
                    st.session_state.lookup_results = []
                    st.error(str(error))
                    st.caption(
                        "You can still enter macros manually in the form below."
                    )

    results = st.session_state.lookup_results

    if results:
        labels = [format_food_label(food) for food in results]
        chosen_label = st.selectbox("Search results", labels)
        chosen_food = results[labels.index(chosen_label)]

        try:
            nutrients = load_food_nutrients(chosen_food["nummer"])
        except FoodLookupError as error:
            nutrients = None
            st.error(str(error))

        if nutrients:
            combined_food = dict(chosen_food)
            combined_food.update(nutrients)
            preview = scale_to_portion(combined_food, portion_grams)

            preview_columns = st.columns(5)
            preview_fields = [
                ("Protein", "protein_grams", "g"),
                ("Carbs", "carbs_grams", "g"),
                ("Fat", "fat_grams", "g"),
                ("Fiber", "fiber_grams", "g"),
                ("Calories", "calories", "kcal"),
            ]

            for column, (label, field, unit) in zip(preview_columns, preview_fields):
                value = preview.get(field)
                with column:
                    st.metric(label, "—" if value is None else f"{value:.0f} {unit}")

            st.caption(f"Values shown for a {portion_grams:.0f} g portion.")

            if st.button("Use these numbers"):
                prefill_from_lookup(combined_food, portion_grams)
                st.success("Copied into the form below.")
                st.rerun()

    st.caption(ATTRIBUTION)

prefill = st.session_state.prefill

with st.form("log_food_form", clear_on_submit=False):
    description = st.text_input("Food description", value=prefill["description"])

    macro_column_one, macro_column_two = st.columns(2)

    with macro_column_one:
        protein_grams = st.number_input(
            "Protein (grams)",
            min_value=0.0,
            step=1.0,
            value=prefill["protein_grams"],
        )
        carbs_grams = st.number_input(
            "Carbs (grams)", min_value=0.0, step=1.0, value=prefill["carbs_grams"]
        )
        fiber_grams = st.number_input(
            "Fiber (grams)", min_value=0.0, step=1.0, value=prefill["fiber_grams"]
        )

    with macro_column_two:
        fat_grams = st.number_input(
            "Fat (grams)", min_value=0.0, step=1.0, value=prefill["fat_grams"]
        )
        calories = st.number_input(
            "Calories (optional)",
            min_value=0.0,
            step=10.0,
            value=prefill["calories"],
        )
        meal_type = st.selectbox(
            "Meal",
            MEAL_TYPES,
            index=MEAL_TYPES.index(prefill["meal_type"])
            if prefill.get("meal_type") in MEAL_TYPES
            else 0,
        )

    detail_column_one, detail_column_two = st.columns(2)

    with detail_column_one:
        protein_source = st.selectbox("Protein source", PROTEIN_SOURCES)

    with detail_column_two:
        log_date = st.date_input("Date", value=date.today())

    profile = get_user_profile()
    priority_tags = get_priority_tags(
        profile["diet_type"] if profile else None,
        profile["purposes"] if profile else None,
    )

    selected_tags = st.multiselect(
        "Your labels (optional)",
        options=build_tag_options(get_saved_tags(), priority_tags=priority_tags),
        help=TAG_HELP,
        accept_new_options=True,
    )
    st.caption(
        "A few labels are also added automatically from what you enter above "
        "(e.g. \"High protein\" at 20g+, \"Dairy\" for yogurt/cheese in the "
        "description) — you'll see exactly which ones after saving."
    )

    submitted = st.form_submit_button("Save entry")

    if submitted:
        if not description.strip():
            st.error("Enter a food description before saving.")
        elif protein_grams <= 0 and carbs_grams <= 0 and fat_grams <= 0:
            st.error("Enter at least one macro value before saving.")
        else:
            suggested_tags = suggest_tags_from_entry(
                description.strip(),
                protein_grams,
                fiber_grams,
                meal_type,
                protein_source,
            )
            auto_added_tags = [tag for tag in suggested_tags if tag not in selected_tags]
            final_tags = list(selected_tags) + auto_added_tags

            add_food_entry(
                description=description.strip(),
                protein_grams=protein_grams,
                meal_type=meal_type,
                protein_source=protein_source,
                log_date=log_date.isoformat(),
                calories=calories if calories > 0 else None,
                carbs_grams=carbs_grams,
                fat_grams=fat_grams,
                fiber_grams=fiber_grams,
                tags=final_tags,
            )
            st.session_state.prefill = dict(EMPTY_PREFILL)

            if auto_added_tags:
                st.success(
                    f"Food entry saved. Auto-added labels based on what you "
                    f"entered: {', '.join(auto_added_tags)}."
                )
            else:
                st.success("Food entry saved.")

            st.rerun()

st.caption(TAG_DISCLAIMER)

st.subheader("Saved entries")

food_entries = get_all_food_entries()
date_options = get_date_options(food_entries)
tag_options = [ALL_TAGS] + get_saved_tags()

filter_column_one, filter_column_two = st.columns(2)
filter_column_three, filter_column_four = st.columns(2)

with filter_column_one:
    selected_date = st.selectbox("Filter by date", date_options)

with filter_column_two:
    selected_meal = st.selectbox("Filter by meal", [ALL_MEALS] + MEAL_TYPES)

with filter_column_three:
    selected_source = st.selectbox("Filter by source", [ALL_SOURCES] + PROTEIN_SOURCES)

with filter_column_four:
    selected_tag = st.selectbox("Filter by label", tag_options)

filtered_entries = filter_food_entries(
    food_entries, selected_date, selected_meal, selected_source, selected_tag
)

if filtered_entries.empty:
    st.info("No food entries match the selected filters.")
else:
    st.dataframe(
        filtered_entries,
        use_container_width=True,
        hide_index=True,
        column_config={
            "protein_grams": st.column_config.NumberColumn("Protein (g)", format="%.1f"),
            "carbs_grams": st.column_config.NumberColumn("Carbs (g)", format="%.1f"),
            "fat_grams": st.column_config.NumberColumn("Fat (g)", format="%.1f"),
            "fiber_grams": st.column_config.NumberColumn("Fiber (g)", format="%.1f"),
            "calories": st.column_config.NumberColumn("Calories", format="%.0f"),
            "description": "Food",
            "meal_type": "Meal",
            "protein_source": "Source",
            "log_date": "Date",
            "tags": "Labels",
        },
    )

    entry_to_delete = st.selectbox(
        "Select an entry id to delete",
        filtered_entries["id"],
    )

    if st.button("Delete selected entry"):
        delete_food_entry(int(entry_to_delete))
        st.success(f"Deleted entry {entry_to_delete}.")
        st.rerun()
