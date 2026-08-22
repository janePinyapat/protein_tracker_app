from datetime import date

import streamlit as st

from database import (
    add_food_entry,
    create_food_log_table,
    create_protein_goals_table,
    delete_food_entry,
    get_all_food_entries,
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

ALL_MEALS = "All meals"
ALL_SOURCES = "All sources"


def get_date_options(food_entries):
    """Create date filter options from saved food entries."""
    if food_entries.empty:
        return ["All dates"]

    dates = sorted(food_entries["log_date"].unique(), reverse=True)
    return ["All dates"] + dates


def filter_food_entries(food_entries, selected_date, selected_meal, selected_source):
    """Filter food entries by date, meal type, and protein source."""
    filtered = food_entries.copy()

    if selected_date != "All dates":
        filtered = filtered[filtered["log_date"] == selected_date]

    if selected_meal != ALL_MEALS:
        filtered = filtered[filtered["meal_type"] == selected_meal]

    if selected_source != ALL_SOURCES:
        filtered = filtered[filtered["protein_source"] == selected_source]

    return filtered


create_food_log_table()
create_protein_goals_table()

st.title("Log Food")
st.write("Record what you ate and how much protein it contained.")

with st.form("log_food_form", clear_on_submit=True):
    description = st.text_input("Food description")

    form_column_one, form_column_two = st.columns(2)

    with form_column_one:
        protein_grams = st.number_input(
            "Protein (grams)", min_value=0.0, step=1.0
        )
        meal_type = st.selectbox("Meal", MEAL_TYPES)

    with form_column_two:
        calories = st.number_input(
            "Calories (optional)", min_value=0.0, step=10.0
        )
        protein_source = st.selectbox("Protein source", PROTEIN_SOURCES)

    log_date = st.date_input("Date", value=date.today())

    submitted = st.form_submit_button("Save entry")

    if submitted:
        if not description.strip():
            st.error("Enter a food description before saving.")
        elif protein_grams <= 0:
            st.error("Protein grams must be greater than zero.")
        else:
            add_food_entry(
                description=description.strip(),
                protein_grams=protein_grams,
                meal_type=meal_type,
                protein_source=protein_source,
                log_date=log_date.isoformat(),
                calories=calories if calories > 0 else None,
            )
            st.success("Food entry saved.")

st.subheader("Saved entries")

food_entries = get_all_food_entries()
date_options = get_date_options(food_entries)

filter_column_one, filter_column_two, filter_column_three = st.columns(3)

with filter_column_one:
    selected_date = st.selectbox("Filter by date", date_options)

with filter_column_two:
    selected_meal = st.selectbox("Filter by meal", [ALL_MEALS] + MEAL_TYPES)

with filter_column_three:
    selected_source = st.selectbox("Filter by source", [ALL_SOURCES] + PROTEIN_SOURCES)

filtered_entries = filter_food_entries(
    food_entries, selected_date, selected_meal, selected_source
)

if filtered_entries.empty:
    st.info("No food entries match the selected filters.")
else:
    st.dataframe(filtered_entries, use_container_width=True, hide_index=True)

    entry_to_delete = st.selectbox(
        "Select an entry id to delete",
        filtered_entries["id"],
    )

    if st.button("Delete selected entry"):
        delete_food_entry(int(entry_to_delete))
        st.success(f"Deleted entry {entry_to_delete}.")
        st.rerun()
