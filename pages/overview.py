from datetime import date

import plotly.express as px
import streamlit as st

from analytics import (
    build_full_week_frame,
    calculate_daily_macro_trend,
    calculate_goal_progress,
    calculate_macro_calorie_split,
    calculate_macro_totals,
    calculate_macros_by_meal,
    calculate_protein_by_source,
    calculate_tag_totals,
    calculate_total_protein,
    filter_entries_by_date_range,
    format_calories,
    format_grams,
    get_week_bounds,
)
from database import get_all_food_entries, get_protein_goals, initialize_database
from food_tags import TAG_DISCLAIMER


DAY_TYPES = ["Rest day", "Training day"]


def get_targets(goals, day_type):
    """Read the protein and fiber targets saved for a day type."""
    protein_target = 0.0
    fiber_target = 0.0

    if not goals.empty:
        matching_goal = goals[goals["day_type"] == day_type]
        if not matching_goal.empty:
            row = matching_goal.iloc[0]
            protein_target = float(row["daily_target_grams"] or 0.0)
            if "fiber_target_grams" in row and row["fiber_target_grams"] is not None:
                fiber_target = float(row["fiber_target_grams"] or 0.0)

    return protein_target, fiber_target


def show_macro_metrics(totals):
    """Show one metric per macro plus calories."""
    columns = st.columns(5)
    fields = [
        ("Protein", "protein_grams", format_grams),
        ("Carbs", "carbs_grams", format_grams),
        ("Fat", "fat_grams", format_grams),
        ("Fiber", "fiber_grams", format_grams),
        ("Calories", "calories", format_calories),
    ]

    for column, (label, key, formatter) in zip(columns, fields):
        with column:
            st.metric(label, formatter(totals[key]))


def create_macro_split_chart(macro_split):
    """Create a donut chart showing how calories split across macros."""
    chart = px.pie(
        macro_split,
        names="macro",
        values="calories",
        title="Calories by Macro",
        hole=0.45,
    )
    chart.update_traces(
        textinfo="label+percent",
        hovertemplate="%{label}<br>%{value:.0f} kcal<br>%{percent}<extra></extra>",
    )
    return chart


def create_source_chart(protein_by_source):
    """Create a donut chart of protein grams by source."""
    chart = px.pie(
        protein_by_source,
        names="protein_source",
        values="protein_grams",
        title="Protein by Source",
        hole=0.45,
    )
    chart.update_traces(
        textinfo="label+percent",
        hovertemplate="%{label}<br>%{value:.0f} g<br>%{percent}<extra></extra>",
    )
    return chart


def create_macros_by_meal_chart(macros_by_meal):
    """Create a grouped bar chart of macros per meal."""
    chart = px.bar(
        macros_by_meal,
        x="meal_type",
        y="grams",
        color="macro",
        barmode="group",
        title="Macros by Meal",
    )
    chart.update_traces(hovertemplate="%{x}<br>%{y:.0f} g<extra></extra>")
    chart.update_layout(xaxis_title=None, yaxis_title="Grams", legend_title=None)
    return chart


def create_tag_chart(tag_totals, title):
    """Create a bar chart counting entries per user-applied label."""
    chart = px.bar(
        tag_totals,
        x="entries",
        y="tag",
        orientation="h",
        title=title,
    )
    chart.update_traces(hovertemplate="%{y}<br>%{x} entries<extra></extra>")
    chart.update_layout(
        xaxis_title="Entries logged",
        yaxis_title=None,
        yaxis={"categoryorder": "total ascending"},
    )
    return chart


def create_week_protein_chart(week_frame, protein_target):
    """Create a bar chart of protein per day across one week."""
    chart = px.bar(
        week_frame,
        x="day_name",
        y="protein_grams",
        title="Protein by Day",
    )
    chart.update_traces(hovertemplate="%{x}<br>%{y:.0f} g<extra></extra>")

    if protein_target > 0:
        chart.add_hline(
            y=protein_target,
            line_dash="dash",
            line_color="#2e8b57",
            annotation_text="Goal",
        )

    chart.update_layout(xaxis_title=None, yaxis_title="Protein (g)")
    return chart


def create_week_macro_chart(week_frame):
    """Create a stacked bar chart of every macro across one week."""
    long_frame = week_frame.melt(
        id_vars="day_name",
        value_vars=["protein_grams", "carbs_grams", "fat_grams", "fiber_grams"],
        var_name="macro",
        value_name="grams",
    )
    long_frame["macro"] = long_frame["macro"].map(
        {
            "protein_grams": "Protein",
            "carbs_grams": "Carbs",
            "fat_grams": "Fat",
            "fiber_grams": "Fiber",
        }
    )

    chart = px.bar(
        long_frame,
        x="day_name",
        y="grams",
        color="macro",
        barmode="group",
        title="Macros by Day",
    )
    chart.update_traces(hovertemplate="%{x}<br>%{y:.0f} g<extra></extra>")
    chart.update_layout(xaxis_title=None, yaxis_title="Grams", legend_title=None)
    return chart


initialize_database()

st.title("Dashboard")
st.write("Daily and weekly summaries of what you logged.")

food_entries = get_all_food_entries()
goals = get_protein_goals()

daily_tab, weekly_tab = st.tabs(["Daily", "Weekly"])

with daily_tab:
    filter_column_one, filter_column_two = st.columns(2)

    with filter_column_one:
        selected_date = st.date_input("Date", value=date.today())

    with filter_column_two:
        selected_day_type = st.selectbox("Day type", DAY_TYPES)

    protein_target, fiber_target = get_targets(goals, selected_day_type)

    todays_entries = food_entries[
        food_entries["log_date"] == selected_date.isoformat()
    ]
    totals = calculate_macro_totals(todays_entries)
    progress = calculate_goal_progress(
        calculate_total_protein(todays_entries), protein_target
    )

    show_macro_metrics(totals)

    if protein_target <= 0:
        st.info("Set a protein goal on the Set Daily Targets page to see progress.")
    else:
        st.progress(
            min(progress["progress_percent"] / 100, 1.0),
            text=(
                f"Protein: {format_grams(progress['total_protein_grams'])} of "
                f"{format_grams(protein_target)} "
                f"({format_grams(max(progress['remaining_grams'], 0.0))} to go)"
            ),
        )

    if fiber_target > 0:
        st.progress(
            min(totals["fiber_grams"] / fiber_target, 1.0),
            text=(
                f"Fiber: {format_grams(totals['fiber_grams'])} of "
                f"{format_grams(fiber_target)}"
            ),
        )

    if todays_entries.empty:
        st.info("No food logged for this date yet.")
    else:
        chart_column_one, chart_column_two = st.columns(2)

        with chart_column_one:
            macro_split = calculate_macro_calorie_split(todays_entries)
            if macro_split.empty:
                st.info("Add macro values to see the calorie split.")
            else:
                st.plotly_chart(
                    create_macro_split_chart(macro_split), use_container_width=True
                )

        with chart_column_two:
            protein_by_source = calculate_protein_by_source(todays_entries)
            if protein_by_source.empty:
                st.info("No protein sources logged for this date.")
            else:
                st.plotly_chart(
                    create_source_chart(protein_by_source), use_container_width=True
                )

        macros_by_meal = calculate_macros_by_meal(todays_entries)
        if not macros_by_meal.empty:
            st.plotly_chart(
                create_macros_by_meal_chart(macros_by_meal),
                use_container_width=True,
            )

        daily_tag_totals = calculate_tag_totals(todays_entries)
        if daily_tag_totals.empty:
            st.caption("No labels applied to this date's entries yet.")
        else:
            st.plotly_chart(
                create_tag_chart(daily_tag_totals, "Your Labels Today"),
                use_container_width=True,
            )

with weekly_tab:
    week_column_one, week_column_two = st.columns(2)

    with week_column_one:
        week_reference = st.date_input(
            "Any date in the week", value=date.today(), key="week_reference"
        )

    with week_column_two:
        week_day_type = st.selectbox("Compare against", DAY_TYPES, key="week_day_type")

    week_start, week_end = get_week_bounds(week_reference)
    week_protein_target, week_fiber_target = get_targets(goals, week_day_type)

    st.caption(
        f"Week of {week_start.strftime('%d %b %Y')} to "
        f"{week_end.strftime('%d %b %Y')} (Monday to Sunday)."
    )

    week_entries = filter_entries_by_date_range(food_entries, week_start, week_end)
    week_totals = calculate_macro_totals(week_entries)
    week_daily_totals = calculate_daily_macro_trend(week_entries)
    days_logged = len(week_daily_totals)

    if days_logged == 0:
        st.info("Nothing logged during this week yet.")
    else:
        days_meeting_goal = 0
        if week_protein_target > 0:
            days_meeting_goal = int(
                (week_daily_totals["protein_grams"] >= week_protein_target).sum()
            )

        summary_column_one, summary_column_two, summary_column_three = st.columns(3)

        with summary_column_one:
            st.metric("Days logged", f"{days_logged} of 7")

        with summary_column_two:
            average_protein = week_totals["protein_grams"] / days_logged
            st.metric("Average protein per logged day", format_grams(average_protein))

        with summary_column_three:
            if week_protein_target > 0:
                st.metric("Days at or above goal", f"{days_meeting_goal} of {days_logged}")
            else:
                st.metric("Days at or above goal", "No goal set")

        st.subheader("Week totals")
        show_macro_metrics(week_totals)

        st.subheader("Daily averages (across logged days)")
        average_totals = {
            key: value / days_logged for key, value in week_totals.items()
        }
        show_macro_metrics(average_totals)

        if week_fiber_target > 0:
            average_fiber = week_totals["fiber_grams"] / days_logged
            st.caption(
                f"Average fiber is {format_grams(average_fiber)} against a "
                f"{format_grams(week_fiber_target)} daily target."
            )

        week_frame = build_full_week_frame(week_daily_totals, week_start)

        st.plotly_chart(
            create_week_protein_chart(week_frame, week_protein_target),
            use_container_width=True,
        )
        st.plotly_chart(
            create_week_macro_chart(week_frame), use_container_width=True
        )

        week_tag_totals = calculate_tag_totals(week_entries)
        if week_tag_totals.empty:
            st.caption("No labels applied to this week's entries yet.")
        else:
            st.plotly_chart(
                create_tag_chart(week_tag_totals, "Your Labels This Week"),
                use_container_width=True,
            )

            st.dataframe(
                week_tag_totals,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "tag": "Label",
                    "entries": st.column_config.NumberColumn("Entries", format="%d"),
                    "protein_grams": st.column_config.NumberColumn(
                        "Protein (g)", format="%.0f"
                    ),
                    "carbs_grams": st.column_config.NumberColumn(
                        "Carbs (g)", format="%.0f"
                    ),
                    "fat_grams": st.column_config.NumberColumn("Fat (g)", format="%.0f"),
                    "fiber_grams": st.column_config.NumberColumn(
                        "Fiber (g)", format="%.0f"
                    ),
                },
            )

st.caption(TAG_DISCLAIMER)
