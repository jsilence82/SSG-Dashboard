"""SSG Ticket Sales Dashboard — entry point. Run with: streamlit run app.py"""

import streamlit as st

st.set_page_config(page_title="SSG Ticket Sales Dashboard", page_icon="🎭", layout="wide")

from ssg_dashboard.main import main

if __name__ == "__main__":
    main()
