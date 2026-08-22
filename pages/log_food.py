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
    initialize_database,
)
from food_tags import TAG_DISCLAIMER, TAG_HELP, build_tag_options
from usda_api import (
    FoodLookupError,
    format_food_label,
    get_api_key,
    is_using_demo_key,
    scale_to_portion,
    search_foods,
)


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
}


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


initialize_database()

if "prefill" not in st.session_state:
    st.session_state.prefill = dict(EMPTY_PREFILL)

if "lookup_results" not in st.session_state:
    st.session_state.lookup_results = []

st.title("Log Food")
st.write("Record what you ate, its macros, and any labels you want to track.")

with st.expander("Look up nutrition data (USDA FoodData Central)"):
    st.caption(
        "Search the USDA FoodData Central database instead of typing macros by "
        "hand. Results are per 100 g and get scaled to your portion. You can "
        "always skip this and enter the numbers yourself."
    )

    search_column, portion_column = st.columns([3, 1])

    with search_column:
        search_query = st.text_input(
            "Search foods", placeholder="e.g. greek yogurt, lentils, salmon"
        )

    with portion_column:
        portion_grams = st.number_input(
            "Portion (g)", min_value=1.0, value=100.0, step=10.0
        )

    if st.button("Search FoodData Central"):
        if not search_query.strip():
            st.warning("Enter a food to search for.")
        else:
            with st.spinner("Searching FoodData Central..."):
                try:
                    st.session_state.lookup_results = search_foods(
                        search_query, api_key=get_api_key(st.secrets)
                    )
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

        preview = scale_to_portion(chosen_food, portion_grams)

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
            prefill_from_lookup(chosen_food, portion_grams)
            st.success("Copied into the form below.")
            st.rerun()

    if is_using_demo_key(get_api_key(st.secrets)):
        st.caption(
            "Using the shared DEMO_KEY, which is rate limited. Set a "
            "USDA_API_KEY environment variable to use your own free key."
        )

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
        meal_type = st.selectbox("Meal", MEAL_TYPES)

    detail_column_one, detail_column_two = st.columns(2)

    with detail_column_one:
        protein_source = st.selectbox("Protein source", PROTEIN_SOURCES)

    with detail_column_two:
        log_date = st.date_input("Date", value=date.today())

    selected_tags = st.multiselect(
        "Your labels (optional)",
        options=build_tag_options(get_saved_tags()),
        help=TAG_HELP,
        accept_new_options=True,
    )

    submitted = st.form_submit_button("Save entry")

    if submitted:
        if not description.strip():
            st.error("Enter a food description before saving.")
        elif protein_grams <= 0 and carbs_grams <= 0 and fat_grams <= 0:
            st.error("Enter at least one macro value before saving.")
        else:
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
                tags=selected_tags,
            )
            st.session_state.prefill = dict(EMPTY_PREFILL)
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
