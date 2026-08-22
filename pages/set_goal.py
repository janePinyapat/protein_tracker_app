import streamlit as st

from database import get_protein_goals, initialize_database, save_protein_goal


DAY_TYPES = ["Rest day", "Training day"]


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


initialize_database()

st.title("Set Daily Targets")
st.write(
    "Set your own daily protein and fiber targets for rest days and training "
    "days. These are the numbers you choose to track against — the app does "
    "not calculate or recommend them. A dietitian or doctor can help you pick "
    "targets that fit your situation."
)

existing_goals = get_protein_goals()

with st.form("set_goal_form"):
    day_type = st.selectbox("Day type", DAY_TYPES)

    default_protein, default_fiber = get_saved_targets(existing_goals, day_type)

    target_column_one, target_column_two = st.columns(2)

    with target_column_one:
        daily_target_grams = st.number_input(
            "Daily protein target (grams)",
            min_value=0.0,
            step=5.0,
            value=default_protein,
        )

    with target_column_two:
        fiber_target_grams = st.number_input(
            "Daily fiber target (grams, optional)",
            min_value=0.0,
            step=1.0,
            value=default_fiber,
        )

    submitted = st.form_submit_button("Save targets")

    if submitted:
        if daily_target_grams <= 0:
            st.error("Daily protein target must be greater than zero.")
        else:
            save_protein_goal(
                day_type,
                daily_target_grams,
                fiber_target_grams if fiber_target_grams > 0 else None,
            )
            st.success(f"Saved {day_type} targets.")
            st.rerun()

st.subheader("Saved targets")

goals = get_protein_goals()

if goals.empty:
    st.info("No targets saved yet.")
else:
    st.dataframe(
        goals[
            ["day_type", "daily_target_grams", "fiber_target_grams", "updated_at"]
        ],
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
            "updated_at": "Updated",
        },
    )
