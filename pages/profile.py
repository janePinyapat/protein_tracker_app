import pandas as pd
import streamlit as st

from database import get_protein_goals, get_user_profile
from nutrition_targets import (
    BMI_SOURCE_NOTE,
    SOURCES_NOTE,
    calculate_bmi,
    convert_to_cm,
    convert_to_kg,
    get_bmi_category,
)
from user_profile import DIET_TYPES, PURPOSES, save_profile_and_targets


st.title("Profile")
st.write(
    "Your diet type and purpose affect which labels are suggested first "
    "when you log food — nothing is hidden. If you add your weight, the "
    "app also suggests Rest day / Training day protein and fiber targets "
    "for you, calculated from published nutrition guidelines (not a "
    "personalized medical recommendation). Adding your height too shows "
    "your BMI as general context. Saving here updates your daily targets; "
    "you can still fine-tune them anytime on the Set Daily Targets page."
)

profile = get_user_profile()
default_diet_type = profile["diet_type"] if profile else DIET_TYPES[0]
default_purposes = profile["purposes"] if profile else []
default_weight_value = profile["weight_value"] if profile else None
default_weight_unit = profile["weight_unit"] if profile else "kg"
default_height_value = profile["height_value"] if profile else None
default_height_unit = profile["height_unit"] if profile else "cm"

with st.form("profile_form"):
    diet_type = st.radio(
        "Which best describes your diet?",
        DIET_TYPES,
        index=DIET_TYPES.index(default_diet_type)
        if default_diet_type in DIET_TYPES
        else 0,
    )

    purposes = st.multiselect(
        "What are you using this tracker for?",
        options=PURPOSES,
        default=[purpose for purpose in default_purposes if purpose in PURPOSES],
    )

    weight_column, weight_unit_column = st.columns([2, 1])

    with weight_column:
        weight_value = st.number_input(
            "Your weight (optional)",
            min_value=0.0,
            step=0.5,
            value=float(default_weight_value) if default_weight_value else 0.0,
            help=(
                "Used to calculate suggested protein and fiber targets, and "
                "(with height) your BMI. Leave at 0 to skip."
            ),
        )

    with weight_unit_column:
        weight_unit = st.selectbox(
            "Weight unit",
            ["kg", "lb"],
            index=["kg", "lb"].index(default_weight_unit)
            if default_weight_unit in ["kg", "lb"]
            else 0,
        )

    height_column, height_unit_column = st.columns([2, 1])

    with height_column:
        height_value = st.number_input(
            "Your height (optional)",
            min_value=0.0,
            step=1.0,
            value=float(default_height_value) if default_height_value else 0.0,
            help="Used only to calculate BMI, alongside your weight. Leave at 0 to skip.",
        )

    with height_unit_column:
        height_unit = st.selectbox(
            "Height unit",
            ["cm", "in"],
            index=["cm", "in"].index(default_height_unit)
            if default_height_unit in ["cm", "in"]
            else 0,
        )

    submitted = st.form_submit_button("Save profile")

    if submitted:
        if not purposes:
            st.error("Pick at least one purpose.")
        else:
            protein_targets, fiber_target = save_profile_and_targets(
                diet_type,
                purposes,
                weight_value if weight_value > 0 else None,
                weight_unit,
                height_value if height_value > 0 else None,
                height_unit,
            )

            if protein_targets:
                st.success(
                    f"Profile saved. Suggested targets set — Rest day: "
                    f"{protein_targets['rest']} g protein, Training day: "
                    f"{protein_targets['training']} g protein, "
                    f"{fiber_target} g fiber (both days)."
                )
            else:
                st.success(
                    "Profile saved. Add your weight above to also get "
                    "suggested protein and fiber targets."
                )

            st.rerun()

st.subheader("Your numbers")

profile = get_user_profile()
goals = get_protein_goals()

weight_kg = convert_to_kg(
    profile["weight_value"] if profile else None,
    profile["weight_unit"] if profile else None,
)
height_cm = convert_to_cm(
    profile["height_value"] if profile else None,
    profile["height_unit"] if profile else None,
)
bmi = calculate_bmi(weight_kg, height_cm)
bmi_category = get_bmi_category(bmi)

metric_columns = st.columns(4)

with metric_columns[0]:
    st.metric(
        "Weight",
        f"{profile['weight_value']:.0f} {profile['weight_unit']}"
        if profile and profile["weight_value"]
        else "Not set",
    )

with metric_columns[1]:
    st.metric(
        "Height",
        f"{profile['height_value']:.0f} {profile['height_unit']}"
        if profile and profile["height_value"]
        else "Not set",
    )

with metric_columns[2]:
    st.metric("BMI", f"{bmi} ({bmi_category})" if bmi else "Add weight & height")

with metric_columns[3]:
    fiber_value = goals.iloc[0]["fiber_target_grams"] if not goals.empty else None
    st.metric(
        "Fiber target",
        f"{int(fiber_value)} g" if pd.notna(fiber_value) else "Not set",
    )

if bmi:
    st.caption(BMI_SOURCE_NOTE)

if not goals.empty:
    st.dataframe(
        goals[["day_type", "daily_target_grams", "fiber_target_grams"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "day_type": "Day type",
            "daily_target_grams": st.column_config.NumberColumn(
                "Protein target (g)", format="%.0f"
            ),
            "fiber_target_grams": st.column_config.NumberColumn(
                "Fiber target (g)", format="%.0f"
            ),
        },
    )
else:
    st.info("Add your weight above to get suggested protein and fiber targets.")

st.caption(SOURCES_NOTE)
