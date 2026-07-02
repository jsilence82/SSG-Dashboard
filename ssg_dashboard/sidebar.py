"""Sidebar: operational controls for TT data."""

import streamlit as st

from .api.tickettailor import load_from_tt_cache, refresh_from_api
from .i18n import t
from .persistence.canonical import cache_age_label, load_cache
from .persistence.settings import load_api_key
from .persistence.tt_cache import tt_cache_status_label


def sidebar_api_panel() -> None:
    tt_label = tt_cache_status_label()
    if tt_label:
        st.sidebar.caption(f"📦 TT raw cache: {tt_label}")

    cache_df, cache_at, _, _ = load_cache()
    if cache_df is not None:
        st.sidebar.caption(f"💾 Canonical cache: {len(cache_df)} rows · {cache_age_label(cache_at)}")

    st.sidebar.divider()

    c1, c2 = st.sidebar.columns(2)
    if c1.button(t("sidebar_load"), key="sidebar_load"):
        ok, msg = load_from_tt_cache()
        (st.sidebar.success if ok else st.sidebar.warning)(msg)
        if ok:
            st.rerun()
    if c2.button(t("sidebar_refresh"), type="primary", key="sidebar_refresh"):
        key = load_api_key()
        if key:
            with st.spinner(t("sidebar_fetching")):
                ok, msg = refresh_from_api(key)
            (st.sidebar.success if ok else st.sidebar.error)(msg)
        else:
            st.sidebar.warning(t("sidebar_no_key"))
