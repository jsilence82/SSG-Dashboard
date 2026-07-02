"""Settings tab: TT API, PayPal API, and column mapping."""

import streamlit as st

from ..api.paypal import pp_get_token
from ..api.tickettailor import load_from_tt_cache, refresh_from_api, tt_ping
from ..config import CANONICAL_FIELDS
from ..mapping import mapping_ui
from ..persistence.paypal_cache import cache_status_label, clear_paypal_cache
from ..i18n import t
from ..persistence.settings import (
    _is_production,
    load_api_key,
    load_paypal_settings,
    load_settings,
    save_api_key,
    save_language,
    save_mapping_settings,
    save_paypal_settings,
)
from ..persistence.tt_cache import tt_cache_status_label


def render_settings() -> None:
    raw_df   = st.session_state.get("raw_df")
    settings = load_settings()

    st.subheader(t("settings_language_header"))
    current_lang = st.session_state.get("lang", "en")
    lang = st.radio(
        t("language_label"),
        options=["en", "de"],
        format_func=lambda x: "English" if x == "en" else "Deutsch",
        index=0 if current_lang == "en" else 1,
        horizontal=True,
        key="lang_radio",
    )
    if lang != current_lang:
        st.session_state["lang"] = lang
        save_language(lang)
        st.rerun()

    st.divider()
    st.subheader("🎟 Ticket Tailor")

    key = load_api_key()
    if key:
        masked = key[:4] + "•" * max(4, len(key) - 8) + key[-4:]
        st.success(f"✓ API key configured — current: `{masked}`")
    else:
        st.warning("No API key configured.")

    if not _is_production():
        new_key = st.text_input(
            "New API key" if not key else "Replace API key (leave blank to keep current)",
            type="password",
            key="tt_key_input_settings",
        )
        if st.button("💾 Save key", disabled=(not new_key and not key), key="save_tt_key"):
            if new_key:
                try:
                    save_api_key(new_key)
                    st.success("API key saved.")
                    st.rerun()
                except KeyError as e:
                    st.error(str(e))
            else:
                st.warning("Enter a new key to replace the existing one.")
    else:
        st.info("Credentials are managed via Streamlit secrets. Use the Streamlit Cloud dashboard to update them.")

    tt_label = tt_cache_status_label()
    if tt_label:
        st.caption(f"📦 TT raw cache: {tt_label}")
    else:
        st.caption("📭 No TT raw cache — use Refresh to fetch and save locally.")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🔍 Test connection", key="tt_test_settings"):
            if key:
                ok, msg = tt_ping(key)
                (st.success if ok else st.error)(msg)
            else:
                st.warning("No API key configured.")
    with c2:
        if st.button("📂 Load from cache", key="tt_load_settings"):
            ok, msg = load_from_tt_cache()
            (st.success if ok else st.warning)(msg)
            if ok:
                st.rerun()
    with c3:
        if st.button("🔄 Refresh from API", type="primary", key="tt_refresh_settings"):
            if key:
                with st.spinner("Fetching from Ticket Tailor…"):
                    ok, msg = refresh_from_api(key)
                (st.success if ok else st.error)(msg)
            else:
                st.warning("Configure an API key first.")

    st.divider()

    st.subheader("💳 PayPal")

    st.info(
        "**Prerequisite — Transaction Search permission:** "
        "Your PayPal REST API app must have the *Transaction Search* feature enabled. "
        "Go to developer.paypal.com → My Apps & Credentials → select your app → "
        "scroll to Live (or Sandbox) features → tick **Transaction Search** → Save."
    )

    saved_cid, saved_secret, saved_sandbox = load_paypal_settings()

    if not _is_production():
        pp_client = st.text_area("Client ID", value=saved_cid, height=80, key="pp_client_settings")

        show_secret = st.checkbox("Show Client Secret", value=False, key="pp_show_secret")
        if show_secret:
            pp_secret = st.text_area("Client Secret", value=saved_secret, height=80, key="pp_secret_settings")
        else:
            pp_secret = st.text_input("Client Secret", value=saved_secret, type="password", key="pp_secret_settings")

        pp_sandbox = st.checkbox("Use Sandbox", value=saved_sandbox, key="pp_sandbox_settings")

        ca, cb = st.columns(2)
        with ca:
            if st.button("💾 Save PayPal credentials", key="save_pp_settings"):
                try:
                    save_paypal_settings(pp_client, pp_secret, pp_sandbox)
                    st.success("PayPal credentials saved.")
                except KeyError as e:
                    st.error(str(e))
        with cb:
            if st.button("🔌 Test & get token", key="test_pp_settings"):
                cid = pp_client.strip() or saved_cid
                sec = pp_secret.strip() or saved_secret
                ok, result = pp_get_token(cid, sec, pp_sandbox)
                if ok:
                    st.session_state["paypal_token"]   = result
                    st.session_state["paypal_sandbox"] = pp_sandbox
                    env = "Sandbox" if pp_sandbox else "Live"
                    st.success(f"✓ Token obtained ({env}) — PayPal connected.")
                else:
                    st.error(f"✗ {result}")
    else:
        st.info("Credentials are managed via Streamlit secrets. Use the Streamlit Cloud dashboard to update them.")
        if st.button("🔌 Test & get token", key="test_pp_settings"):
            ok, result = pp_get_token(saved_cid, saved_secret, saved_sandbox)
            if ok:
                st.session_state["paypal_token"]   = result
                st.session_state["paypal_sandbox"] = saved_sandbox
                env = "Sandbox" if saved_sandbox else "Live"
                st.success(f"✓ Token obtained ({env}) — PayPal connected.")
            else:
                st.error(f"✗ {result}")

    pp_label = cache_status_label()
    if pp_label:
        st.caption(f"📦 PayPal cache: {pp_label}")

    token_ready = bool(st.session_state.get("paypal_token"))
    if token_ready:
        env_label = "Sandbox" if st.session_state.get("paypal_sandbox") else "Live"
        st.caption(f"✓ PayPal connected · {env_label} (token active for this session)")

    st.divider()

    st.subheader("📐 Column Mapping")

    key_prefix = st.session_state.get("raw_source", "api")

    if raw_df is not None:
        mapping = mapping_ui(raw_df, key_prefix=key_prefix, saved=settings)
    else:
        st.caption("No raw data loaded — editing saved column names. Changes apply on next fetch or upload.")
        saved_map     = settings.get("mapping", {})
        saved_columns = settings.get("raw_columns", [])
        mapping       = {}
        mc1, mc2      = st.columns(2)
        for i, (field, label) in enumerate(CANONICAL_FIELDS.items()):
            required = field in ("show", "category")
            with (mc1 if i % 2 == 0 else mc2):
                if saved_columns:
                    opts    = saved_columns if required else ["(none)"] + saved_columns
                    default = saved_map.get(field)
                    if default not in opts:
                        default = opts[0] if required else "(none)"
                    choice  = st.selectbox(label, opts, index=opts.index(default),
                                           key=f"mapping_cache_{field}")
                    mapping[field] = None if choice == "(none)" else choice
                else:
                    val = st.text_input(label, value=saved_map.get(field) or "",
                                        placeholder="(none)", key=f"mapping_text_{field}")
                    mapping[field] = val.strip() or None

    opt1, opt2 = st.columns(2)
    with opt1:
        prices_in_cents = st.checkbox(
            "Revenue in cents (Ticket Tailor convention)",
            value=settings.get("prices_in_cents", True),
            key="prices_in_cents_setting")
    with opt2:
        revenue_is_per_unit = st.checkbox(
            "Revenue is per-ticket price, not row total",
            value=settings.get("revenue_is_per_unit", bool((mapping or {}).get("quantity"))),
            key="revenue_per_unit_setting",
            help="Tick for rows like '30 Adult tickets at €14'.")

    if st.button("💾 Save mappings", key="save_mappings_settings"):
        if mapping and mapping.get("show") and mapping.get("category"):
            save_mapping_settings(
                mapping, prices_in_cents, revenue_is_per_unit,
                raw_columns=list(raw_df.columns) if raw_df is not None else None,
            )
            st.success("Mappings saved.")
        else:
            st.warning("Set Show and Category first.")
