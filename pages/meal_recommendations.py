from datetime import date, timedelta

import pandas as pd
import streamlit as st

from analytics import calculate_macro_totals, calculate_remaining_targets
from database import (
    get_all_food_entries,
    get_meal_recommendations,
    get_protein_goals,
    get_recent_recommended_recipe_ids,
    get_user_profile,
    initialize_database,
    save_meal_recommendations,
)
from meal_recommendation_api import (
    DISCLAIMER,
    MEAL_TYPES,
    MealRecommendationError,
    fetch_meal_recommendations,
    get_api_key,
)


DAY_TYPES = ["Rest day", "Training day"]

# How far back to look when steering new recommendations away from repeats.
REPEAT_AVOIDANCE_DAYS = 14


def get_saved_targets(existing_goals, day_type):
    """Read the saved protein and fiber targets for a day type."""
    protein_target = 0.0
    fiber_target = 0.0

    if not existing_goals.empty:
        matching_goal = existing_goals[existing_goals["day_type"] == day_type]
        if not matching_goal.empty:
            row = matching_goal.iloc[0]
            protein_target = float(row["daily_target_grams"] or 0.0)
            if row.get("fiber_target_grams") is not None:
                fiber_target = float(row["fiber_target_grams"] or 0.0)

    return protein_target, fiber_target


def send_to_log_food(meal):
    """Prefill the Log Food form with one recommended meal and jump there."""
    st.session_state.prefill = {
        "description": meal["meal_name"],
        "protein_grams": float(meal["protein_grams"]) if pd.notna(meal["protein_grams"]) else 0.0,
        "carbs_grams": 0.0,
        "fat_grams": 0.0,
        "fiber_grams": float(meal["fiber_grams"]) if pd.notna(meal["fiber_grams"]) else 0.0,
        "calories": float(meal["calories"]) if pd.notna(meal["calories"]) else 0.0,
        "meal_type": meal["meal_type"],
    }
    st.switch_page("pages/log_food.py")


initialize_database()

st.title("Meal Recommendations")
st.write(
    "Real recipes from Spoonacular's database, matched to your diet and to "
    "help you reach today's protein and fiber target — set on the Profile "
    "page."
)

today_iso = date.today().isoformat()

current_profile = get_user_profile()
current_diet_type = current_profile["diet_type"] if current_profile else None
if current_diet_type and current_diet_type not in ("Omnivore", "Other / prefer not to say"):
    st.caption(
        f"Recommendations are filtered to match your profile's diet type: "
        f"**{current_diet_type}**. Change this on the Profile page."
    )

goals = get_protein_goals()
food_entries = get_all_food_entries()
todays_entries = food_entries[food_entries["log_date"] == today_iso]
todays_totals = calculate_macro_totals(todays_entries)

day_type = st.selectbox("Today is a...", DAY_TYPES)
protein_target, fiber_target = get_saved_targets(goals, day_type)

if protein_target <= 0:
    st.info(
        "Set a protein target on the Profile page to get meal ideas sized "
        "to what you still need today."
    )
else:
    remaining = calculate_remaining_targets(
        protein_target,
        fiber_target,
        todays_totals["protein_grams"],
        todays_totals["fiber_grams"],
    )

    metric_columns = st.columns(3)
    with metric_columns[0]:
        st.metric("Protein remaining today", f"{remaining['protein_grams']:.0f} g")
    with metric_columns[1]:
        st.metric("Fiber remaining today", f"{remaining['fiber_grams']:.0f} g")
    with metric_columns[2]:
        st.metric("Target", f"{protein_target:.0f} g / {fiber_target:.0f} g")

    cached = get_meal_recommendations(today_iso)
    already_close = (
        remaining["protein_grams"] <= 5
        and remaining["fiber_grams"] <= 5
        and not cached.empty
    )

    if already_close:
        st.success("You're already close to today's target — nice work.")

    st.caption("Recipe search options — applied to all three meals")
    search_option_columns = st.columns(2)
    with search_option_columns[0]:
        desired_servings = st.number_input(
            "Servings", min_value=1, max_value=12, value=2, step=1
        )
    with search_option_columns[1]:
        max_cook_minutes = st.number_input(
            "Max cook time (minutes)",
            min_value=0,
            max_value=240,
            value=45,
            step=5,
            help="0 means no limit.",
        )

    button_label = (
        "Refresh today's meal ideas" if not cached.empty else "Get today's meal ideas"
    )

    if st.button(button_label):
        with st.spinner("Searching Spoonacular for matching recipes..."):
            try:
                profile = get_user_profile()
                diet_type = profile["diet_type"] if profile else None

                since_date = (
                    date.today() - timedelta(days=REPEAT_AVOIDANCE_DAYS - 1)
                ).isoformat()
                exclude_recipe_ids = get_recent_recommended_recipe_ids(since_date)

                payload = fetch_meal_recommendations(
                    remaining["protein_grams"],
                    remaining["fiber_grams"],
                    diet_type=diet_type,
                    exclude_recipe_ids=exclude_recipe_ids,
                    api_key=get_api_key(st.secrets),
                    servings=desired_servings,
                    max_ready_time=max_cook_minutes if max_cook_minutes > 0 else None,
                )
                meals_to_save = [
                    {
                        "meal_type": meal.get("meal_type"),
                        "recipe_id": meal.get("recipe_id"),
                        "meal_name": meal.get("meal_name") or "Untitled meal",
                        "description": meal.get("description"),
                        "protein_grams": meal.get("estimated_protein_grams"),
                        "fiber_grams": meal.get("estimated_fiber_grams"),
                        "calories": meal.get("estimated_calories"),
                        "source_title": meal.get("source_title"),
                        "source_url": meal.get("source_url"),
                        "image_url": meal.get("image_url"),
                    }
                    for meal in payload["meals"]
                    if meal.get("meal_type") in MEAL_TYPES
                ]
                if meals_to_save:
                    save_meal_recommendations(today_iso, meals_to_save)
                if payload.get("notes"):
                    st.warning(payload["notes"])
                st.rerun()
            except MealRecommendationError as error:
                st.error(str(error))
                st.caption(
                    "You can still log food manually on the Log Food page."
                )

    cached = get_meal_recommendations(today_iso)

    if not cached.empty:
        st.caption("Click refresh above for new ideas.")

        for _, meal in cached.iterrows():
            with st.container(border=True):
                st.markdown(f"**{meal['meal_type']}: {meal['meal_name']}**")

                if meal.get("image_url"):
                    st.image(meal["image_url"])

                if meal["description"]:
                    st.write(meal["description"])

                meal_metric_columns = st.columns(3)
                with meal_metric_columns[0]:
                    st.metric(
                        "Protein",
                        f"{meal['protein_grams']:.0f} g"
                        if pd.notna(meal["protein_grams"])
                        else "—",
                    )
                with meal_metric_columns[1]:
                    st.metric(
                        "Fiber",
                        f"{meal['fiber_grams']:.0f} g"
                        if pd.notna(meal["fiber_grams"])
                        else "—",
                    )
                with meal_metric_columns[2]:
                    st.metric(
                        "Calories",
                        f"{meal['calories']:.0f}"
                        if pd.notna(meal["calories"])
                        else "—",
                    )

                if meal["source_url"]:
                    st.caption(
                        f"Source: [{meal['source_title'] or meal['source_url']}]"
                        f"({meal['source_url']})"
                    )

                if st.button(
                    f"Log this {meal['meal_type'].lower()}",
                    key=f"log_meal_{meal['meal_type']}",
                ):
                    send_to_log_food(meal)

        st.caption(DISCLAIMER)
    else:
        st.info("Click the button above to get today's meal ideas.")
