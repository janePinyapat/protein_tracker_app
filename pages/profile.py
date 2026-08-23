import streamlit as st

from database import get_user_profile
from nutrition_targets import SOURCES_NOTE
from user_profile import DIET_TYPES, PURPOSES, save_profile_and_targets


st.title("Profile")
st.write(
    "Your diet type and purpose affect which labels are suggested first "
    "when you log food — nothing is hidden. If you add your weight, the "
    "app also suggests Rest day / Training day protein and fiber targets "
    "for you, calculated from published nutrition guidelines (not a "
    "personalized medical recommendation). Saving here updates those "
    "targets; you can still fine-tune them anytime on the Set Daily "
    "Targets page."
)

profile = get_user_profile()
default_diet_type = profile["diet_type"] if profile else DIET_TYPES[0]
default_purposes = profile["purposes"] if profile else []
default_weight_value = profile["weight_value"] if profile else None
default_weight_unit = profile["weight_unit"] if profile else "kg"

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

    weight_column, unit_column = st.columns([2, 1])

    with weight_column:
        weight_value = st.number_input(
            "Your weight (optional)",
            min_value=0.0,
            step=0.5,
            value=float(default_weight_value) if default_weight_value else 0.0,
            help=(
                "Used only to calculate suggested protein and fiber targets "
                "below. Leave at 0 to skip and keep your current targets."
            ),
        )

    with unit_column:
        weight_unit = st.selectbox(
            "Unit",
            ["kg", "lb"],
            index=["kg", "lb"].index(default_weight_unit)
            if default_weight_unit in ["kg", "lb"]
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

st.caption(SOURCES_NOTE)
