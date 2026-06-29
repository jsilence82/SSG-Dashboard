"""SSG Ticket Sales Dashboard — entry point. Run with: streamlit run app.py"""

import streamlit as st

st.set_page_config(page_title="SSG Ticket Sales Dashboard", page_icon="🎭", layout="wide")

import yaml
import streamlit_authenticator as stauth

with open("auth.yaml") as f:
    _auth_config = yaml.safe_load(f)

_authenticator = stauth.Authenticate(
    _auth_config["credentials"],
    _auth_config["cookie"]["name"],
    _auth_config["cookie"]["key"],
    _auth_config["cookie"]["expiry_days"],
)

_authenticator.login()

_auth_status = st.session_state.get("authentication_status")

if _auth_status is False:
    st.error("Username or password is incorrect.")
    st.stop()
elif not _auth_status:
    st.stop()

# Authenticated — render dashboard
_authenticator.logout("Logout", "sidebar")

from ssg_dashboard.main import main
main()
