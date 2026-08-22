import streamlit as st


st.set_page_config(page_title="Protein & Recovery Tracker", layout="wide")

pages = [
    st.Page("pages/overview.py", title="Overview"),
    st.Page("pages/log_food.py", title="Log Food"),
    st.Page("pages/set_goal.py", title="Set Protein Goal"),
]

selected_page = st.navigation(pages)
selected_page.run()
