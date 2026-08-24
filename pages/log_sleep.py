from datetime import date

import streamlit as st

from database import (
    delete_sleep_entry,
    get_all_sleep_entries,
    get_sleep_entry,
    get_wellness_goals,
    initialize_database,
    save_sleep_entry,
    save_wellness_goals,
)
from wellness import format_hours


initialize_database()

st.title("Log Sleep")
st.write(
    "Log how many hours you slept for a given date — logging the same date "
    "again updates that entry instead of adding a duplicate."
)

goals = get_wellness_goals()
sleep_target_hours = (
    goals["sleep_target_hours"] if goals and goals["sleep_target_hours"] else 0.0
)

today = date.today()
existing_today = get_sleep_entry(today.isoformat())

if existing_today:
    metric_column, target_column = st.columns(2)
    with metric_column:
        st.metric("Logged for tonight/today", format_hours(existing_today["hours_slept"]))
    if sleep_target_hours > 0:
        with target_column:
            st.metric("Target", format_hours(sleep_target_hours))

with st.form("sleep_form"):
    date_column, hours_column = st.columns(2)

    with date_column:
        log_date = st.date_input("Date", value=today)

    with hours_column:
        default_hours = existing_today["hours_slept"] if existing_today else 8.0
        hours_slept = st.number_input(
            "Hours slept", min_value=0.0, max_value=24.0, step=0.25, value=default_hours
        )

    notes = st.text_input(
        "Notes (optional)", value=(existing_today["notes"] or "") if existing_today else ""
    )

    submitted = st.form_submit_button("Save entry")

    if submitted:
        if hours_slept <= 0:
            st.error("Hours slept must be greater than zero.")
        else:
            save_sleep_entry(
                log_date.isoformat(), hours_slept, notes.strip() or None
            )
            st.success(f"Saved {format_hours(hours_slept)} for {log_date.isoformat()}.")
            st.rerun()

st.subheader("Set your sleep target")
st.write(
    "An optional daily target you set yourself — the app doesn't calculate "
    "or recommend this number."
)

with st.form("sleep_goal_form"):
    target_value = st.number_input(
        "Sleep target (hours)",
        min_value=0.0,
        max_value=24.0,
        step=0.5,
        value=float(sleep_target_hours),
    )

    submitted_goal = st.form_submit_button("Save target")

    if submitted_goal:
        save_wellness_goals(
            water_target_ml=goals["water_target_ml"] if goals else None,
            sleep_target_hours=target_value if target_value > 0 else None,
        )
        st.success("Sleep target saved.")
        st.rerun()

st.subheader("Saved entries")

sleep_entries = get_all_sleep_entries()

if sleep_entries.empty:
    st.info("No sleep logged yet.")
else:
    st.dataframe(
        sleep_entries,
        use_container_width=True,
        hide_index=True,
        column_config={
            "hours_slept": st.column_config.NumberColumn("Hours slept", format="%.2f"),
            "log_date": "Date",
            "notes": "Notes",
            "created_at": "Logged at",
        },
    )

    date_to_delete = st.selectbox(
        "Select a date to delete", sleep_entries["log_date"]
    )

    if st.button("Delete selected entry"):
        delete_sleep_entry(date_to_delete)
        st.success(f"Deleted the entry for {date_to_delete}.")
        st.rerun()
