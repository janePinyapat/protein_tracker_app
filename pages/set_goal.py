import streamlit as st

from database import create_protein_goals_table, get_protein_goals, save_protein_goal


DAY_TYPES = ["Rest day", "Training day"]


create_protein_goals_table()

st.title("Set Protein Goal")
st.write(
    "Set a daily protein target for rest days and training days. "
    "Recovery and PCOS-related protein needs are often higher on "
    "training days."
)

existing_goals = get_protein_goals()

with st.form("set_goal_form"):
    day_type = st.selectbox("Day type", DAY_TYPES)

    default_target = 0.0
    if not existing_goals.empty:
        matching_goal = existing_goals[existing_goals["day_type"] == day_type]
        if not matching_goal.empty:
            default_target = float(matching_goal.iloc[0]["daily_target_grams"])

    daily_target_grams = st.number_input(
        "Daily protein target (grams)",
        min_value=0.0,
        step=5.0,
        value=default_target,
    )

    submitted = st.form_submit_button("Save goal")

    if submitted:
        if daily_target_grams <= 0:
            st.error("Daily protein target must be greater than zero.")
        else:
            save_protein_goal(day_type, daily_target_grams)
            st.success(f"Saved {day_type} target: {daily_target_grams:.0f} g")
            st.rerun()

st.subheader("Saved goals")

goals = get_protein_goals()

if goals.empty:
    st.info("No protein goals saved yet.")
else:
    st.dataframe(
        goals[["day_type", "daily_target_grams", "updated_at"]],
        use_container_width=True,
        hide_index=True,
    )
