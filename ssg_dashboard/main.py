"""Top-level page orchestration."""

from datetime import datetime, timezone

import streamlit as st

from .api.tickettailor import fetch_and_store, load_from_tt_cache
from .mapping import build_canonical
from .persistence.canonical import cache_age_label, load_cache, save_cache
from .persistence.settings import load_api_key, load_capacities, load_settings
from .sections.dashboard import render_dashboard
from .sidebar import sidebar_api_panel


def main() -> None:
    if "initialized" not in st.session_state:
        st.session_state["initialized"] = True
        df, saved_at, cap = load_cache()
        if df is not None:
            st.session_state["canonical_df"] = df
            st.session_state["cache_age"]    = saved_at
            st.session_state["api_capacity"] = cap
        else:
            ok, _ = load_from_tt_cache()
            if not ok and load_api_key():
                _msg = st.empty()
                _msg.info("Auto-fetching from Ticket Tailor…")
                fetch_and_store(load_api_key())
                _msg.empty()

    st.title("🎭 SSG Ticket Sales Dashboard")

    sidebar_api_panel()

    canonical_df = st.session_state.get("canonical_df")
    raw_df       = st.session_state.get("raw_df")

    if canonical_df is None and raw_df is None:
        st.info("No data loaded — use Load cache or Refresh in the sidebar, or configure your API key in ⚙️ Settings.")
        return

    if raw_df is not None:
        with st.expander("Raw data preview", expanded=False):
            st.dataframe(raw_df.head(20), width="stretch")
            st.caption(f"{len(raw_df)} rows · {len(raw_df.columns)} columns")
    elif canonical_df is not None:
        age = cache_age_label(st.session_state.get("cache_age"))
        st.caption(f"Cached data · {len(canonical_df)} rows · {age}")

    settings            = load_settings()
    mapping             = settings.get("mapping", {})
    prices_in_cents     = settings.get("prices_in_cents", True)
    revenue_is_per_unit = settings.get("revenue_is_per_unit", False)

    if raw_df is not None:
        if not mapping.get("show") or not mapping.get("category"):
            st.warning("Column mapping not configured — go to ⚙️ Settings to set it up.")
            return
        canonical = build_canonical(raw_df, mapping, prices_in_cents, revenue_is_per_unit)
        # Auto-save so next startup skips the build step entirely
        save_cache(canonical, st.session_state.get("api_capacity", {}))
        st.session_state["canonical_df"] = canonical
        st.session_state["cache_age"]    = datetime.now(timezone.utc).isoformat()
    else:
        canonical = canonical_df

    api_cap  = st.session_state.get("api_capacity", {})
    user_cap = load_capacities()
    capacity_by_show = {**api_cap, **user_cap}

    st.divider()
    render_dashboard(canonical, capacity_by_show)
