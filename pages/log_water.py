from datetime import date

import streamlit as st

from database import (
    add_water_entry,
    delete_water_entry,
    get_all_water_entries,
    get_wellness_goals,
    initialize_database,
    save_wellness_goals,
)
from wellness import QUICK_ADD_AMOUNTS_ML, calculate_water_total, convert_to_ml, format_ml


initialize_database()

st.title("Log Water")
st.write("Track how much water you drink — log it as you go, or add a custom amount.")

today = date.today()
today_iso = today.isoformat()

water_entries = get_all_water_entries()
todays_entries = water_entries[water_entries["log_date"] == today_iso]
todays_total = calculate_water_total(todays_entries)

goals = get_wellness_goals()
water_target_ml = goals["water_target_ml"] if goals and goals["water_target_ml"] else 0.0

metric_column, progress_column = st.columns([1, 2])

with metric_column:
    st.metric("Today's total", format_ml(todays_total))

if water_target_ml > 0:
    with progress_column:
        st.progress(
            min(todays_total / water_target_ml, 1.0),
            text=f"{format_ml(todays_total)} of {format_ml(water_target_ml)} today",
        )

st.subheader("Quick add")
quick_add_columns = st.columns(len(QUICK_ADD_AMOUNTS_ML))

for column, amount in zip(quick_add_columns, QUICK_ADD_AMOUNTS_ML):
    with column:
        if st.button(f"+{amount} ml", key=f"quick_add_{amount}", use_container_width=True):
            add_water_entry(amount, today_iso)
            st.success(f"Added {amount} ml.")
            st.rerun()

with st.expander("Log a custom amount or a different date"):
    with st.form("custom_water_form"):
        amount_column, unit_column, date_column = st.columns(3)

        with amount_column:
            custom_amount = st.number_input(
                "Amount", min_value=0.0, step=50.0, value=250.0
            )

        with unit_column:
            custom_unit = st.selectbox("Unit", ["ml", "fl oz"])

        with date_column:
            custom_date = st.date_input("Date", value=today)

        submitted = st.form_submit_button("Add entry")

        if submitted:
            amount_ml = convert_to_ml(custom_amount, custom_unit)
            if not amount_ml:
                st.error("Enter an amount greater than zero.")
            else:
                add_water_entry(round(amount_ml, 1), custom_date.isoformat())
                st.success(f"Added {format_ml(amount_ml)}.")
                st.rerun()

st.subheader("Saved entries")

water_entries = get_all_water_entries()

if water_entries.empty:
    st.info("No water logged yet.")
else:
    date_options = ["All dates"] + sorted(water_entries["log_date"].unique(), reverse=True)
    selected_date = st.selectbox("Filter by date", date_options)

    filtered_entries = (
        water_entries
        if selected_date == "All dates"
        else water_entries[water_entries["log_date"] == selected_date]
    )

    st.dataframe(
        filtered_entries,
        use_container_width=True,
        hide_index=True,
        column_config={
            "amount_ml": st.column_config.NumberColumn("Amount (ml)", format="%.0f"),
            "log_date": "Date",
            "created_at": "Logged at",
        },
    )

    entry_to_delete = st.selectbox("Select an entry id to delete", filtered_entries["id"])

    if st.button("Delete selected entry"):
        delete_water_entry(int(entry_to_delete))
        st.success(f"Deleted entry {entry_to_delete}.")
        st.rerun()

st.divider()

st.subheader("Set your water target")
st.write(
    "An optional daily target you set yourself — the app doesn't calculate "
    "or recommend this number."
)

with st.form("water_goal_form"):
    target_value = st.number_input(
        "Daily water target (ml)",
        min_value=0.0,
        step=100.0,
        value=float(water_target_ml),
    )

    submitted_goal = st.form_submit_button("Save target")

    if submitted_goal:
        save_wellness_goals(
            water_target_ml=target_value if target_value > 0 else None,
            sleep_target_hours=goals["sleep_target_hours"] if goals else None,
        )
        st.success("Water target saved.")
        st.rerun()
