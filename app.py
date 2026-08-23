import streamlit as st

from database import get_user_profile, initialize_database


st.set_page_config(page_title="Protein & Recovery Tracker", layout="wide")

initialize_database()

if get_user_profile() is None:
    pages = [st.Page("pages/onboarding.py", title="Welcome")]
else:
    pages = [
        st.Page("pages/profile.py", title="Profile"),
        st.Page("pages/overview.py", title="Dashboard"),
        st.Page("pages/log_food.py", title="Log Food"),
        st.Page("pages/set_goal.py", title="Set Daily Targets"),
    ]

selected_page = st.navigation(pages)
selected_page.run()
