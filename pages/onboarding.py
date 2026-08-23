import streamlit as st

from nutrition_targets import SOURCES_NOTE, WATER_SOURCE_NOTE
from user_profile import DIET_TYPES, PURPOSES, save_profile_and_targets


st.title("Welcome")
st.caption(
    "Built for women's nutrition, hydration, and recovery — targets use "
    "guidelines published for women wherever the source differentiates by sex."
)
st.write(
    "Before you start logging, tell us a bit about yourself. Diet type and "
    "purpose only change which labels are suggested first when you tag a "
    "food — every label stays available to everyone. If you add your "
    "weight, the app also suggests Rest day / Training day protein and "
    "fiber targets, and a daily water target, calculated from published "
    "guidelines — not a personalized medical recommendation. Adding height "
    "too shows your BMI as general context. Nothing here rates your food or "
    "diagnoses anything, and you can change all of it later."
)

with st.form("onboarding_form"):
    diet_type = st.radio("Which best describes your diet?", DIET_TYPES)

    purposes = st.multiselect(
        "What are you using this tracker for? (pick any that apply)",
        options=PURPOSES,
    )

    weight_column, weight_unit_column = st.columns([2, 1])

    with weight_column:
        weight_value = st.number_input(
            "Your weight (optional)",
            min_value=0.0,
            step=0.5,
            help=(
                "Used to calculate suggested protein and fiber targets, "
                "and (with height) your BMI. Leave at 0 to skip."
            ),
        )

    with weight_unit_column:
        weight_unit = st.selectbox("Weight unit", ["kg", "lb"])

    height_column, height_unit_column = st.columns([2, 1])

    with height_column:
        height_value = st.number_input(
            "Your height (optional)",
            min_value=0.0,
            step=1.0,
            help="Used only to calculate BMI, alongside your weight. Leave at 0 to skip.",
        )

    with height_unit_column:
        height_unit = st.selectbox("Height unit", ["cm", "in"])

    submitted = st.form_submit_button("Get started")

    if submitted:
        if not purposes:
            st.error("Pick at least one purpose to continue.")
        else:
            protein_targets, fiber_target, water_target_ml, _recalculated = (
                save_profile_and_targets(
                    diet_type,
                    purposes,
                    weight_value if weight_value > 0 else None,
                    weight_unit,
                    height_value if height_value > 0 else None,
                    height_unit,
                )
            )

            if protein_targets:
                st.success(
                    f"Saved! Suggested targets — Rest day: "
                    f"{protein_targets['rest']} g protein, Training day: "
                    f"{protein_targets['training']} g protein, "
                    f"{fiber_target} g fiber (both days), "
                    f"{int(water_target_ml)} ml water. Taking you to your "
                    f"dashboard..."
                )
            else:
                st.success("Saved! Taking you to your dashboard...")

            st.rerun()

st.caption(SOURCES_NOTE)
st.caption(WATER_SOURCE_NOTE)
st.caption("You can change any of this anytime from the Profile page in the sidebar.")
