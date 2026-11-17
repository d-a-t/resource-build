"""Campus Dining page module with live Tech Dining Nutrislice menu integration."""
from __future__ import annotations

import datetime
import html
import streamlit as st

from lib.dining import AVAILABLE_DINING_HALLS, fetch_nutrislice_menu, parse_nutrislice_url
from ui.common import disclaimer, md, render_gt_header


@st.cache_data(ttl=600)
def cached_nutrislice_menu(school: str, menu_type: str, date_str: str, district: str = "techdining"):
    """Cache daily Nutrislice menu queries to prevent repeated network overhead."""
    return fetch_nutrislice_menu(school, menu_type, date_str, district)


def page_dining() -> None:
    """Render the Campus Dining page with live Nutrislice menu risk analysis."""
    render_gt_header("dining")
    st.title("Campus Dining & Live Daily Menus")

    tab_menu, tab_guide = st.tabs(["🍽️ Daily Nutrislice Menu Checker", "📋 GT Dining Hall Guide & Tips"])

    with tab_guide:
        md("dining.md")
        disclaimer()

    with tab_menu:
        st.write(
            "Analyze live daily dining hall menus from **techdining.nutrislice.com** against histamine intolerance risk. "
            "The analyzer inspects dish names, descriptions, and full recipe ingredient lists to flag high-histamine ingredients, "
            "fermented items, aged cheeses, cured meats, and histamine liberators."
        )

        st.markdown("#### 🏛️ Campus Dining Locations")
        st.caption(
            "Select an available dining hall or paste its URL directly. Available locations:\n"
            "- [Brittain](https://techdining.nutrislice.com/menu/brittain)\n"
            "- [North Ave Dining Hall](https://techdining.nutrislice.com/menu/north-ave-dining-hall)\n"
            "- [West Village](https://techdining.nutrislice.com/menu/west-village)"
        )

        avail_hall_keys = list(AVAILABLE_DINING_HALLS.keys())
        default_hall_key = "brittain"

        if "dining_nutrislice_url" not in st.session_state:
            st.session_state["dining_nutrislice_url"] = AVAILABLE_DINING_HALLS[default_hall_key]["url"]

        def _on_hall_select_change() -> None:
            chosen = st.session_state.get("dining_hall_choice")
            if chosen in AVAILABLE_DINING_HALLS:
                st.session_state["dining_nutrislice_url"] = AVAILABLE_DINING_HALLS[chosen]["url"]

        col_hall, col_url = st.columns([1.2, 1.8])
        with col_hall:
            chosen_school_key = st.selectbox(
                "Select Available Dining Hall",
                options=avail_hall_keys,
                format_func=lambda k: AVAILABLE_DINING_HALLS[k]["name"],
                key="dining_hall_choice",
                on_change=_on_hall_select_change,
            )

        with col_url:
            url_input = st.text_input(
                "Nutrislice URL (paste or edit)",
                key="dining_nutrislice_url",
                help="Available URLs:\n- https://techdining.nutrislice.com/menu/brittain\n- https://techdining.nutrislice.com/menu/north-ave-dining-hall\n- https://techdining.nutrislice.com/menu/west-village",
            )

        parsed = parse_nutrislice_url(url_input)
        school = parsed["school"] if parsed["school"] in AVAILABLE_DINING_HALLS else chosen_school_key

        c1, c2, c3 = st.columns([1, 1.2, 0.8])
        meal_options = ["lunch", "dinner", "breakfast"]
        meal_idx = meal_options.index(parsed["menu_type"]) if parsed["menu_type"] in meal_options else 0
        chosen_meal = c1.selectbox("Meal Period", meal_options, index=meal_idx, key="dining_meal_select")

        # Parse date from URL or default to 2026-11-17
        try:
            default_date_val = datetime.date.fromisoformat(parsed["date"])
        except (ValueError, TypeError):
            default_date_val = datetime.date(2026, 11, 17)

        # Sync date picker if URL input changed the date
        if st.session_state.get("_last_parsed_url_date") != parsed["date"]:
            st.session_state["_last_parsed_url_date"] = parsed["date"]
            st.session_state["dining_date_picker"] = default_date_val

        chosen_date_obj = c2.date_input(
            "Date (Calendar Dropdown)",
            value=default_date_val,
            key="dining_date_picker",
            help="Click to open the interactive calendar drop down and select a menu date.",
        )

        if isinstance(chosen_date_obj, (datetime.date, datetime.datetime)):
            chosen_date_str = chosen_date_obj.strftime("%Y-%m-%d")
        elif isinstance(chosen_date_obj, (list, tuple)) and chosen_date_obj:
            chosen_date_str = chosen_date_obj[0].strftime("%Y-%m-%d")
        else:
            chosen_date_str = str(chosen_date_obj)

        with c3:
            st.write("&nbsp;")
            st.button("🔄 Analyze Menu", use_container_width=True, key="dining_load_btn")

        hall_info = AVAILABLE_DINING_HALLS.get(school, AVAILABLE_DINING_HALLS[default_hall_key])
        canonical_url = f"{hall_info['url']}/{chosen_meal}/{chosen_date_str}"
        st.caption(f"Currently viewing: **{hall_info['name']}** • [{canonical_url}]({canonical_url})")

        dishes, err = cached_nutrislice_menu(school, chosen_meal, chosen_date_str, parsed["district"])

        if err:
            st.error(f"Could not load Nutrislice menu: {err}")
            st.info(
                "Check your URL or date and try again. Available dining hall URLs:\n"
                "- `https://techdining.nutrislice.com/menu/brittain`\n"
                "- `https://techdining.nutrislice.com/menu/north-ave-dining-hall`\n"
                "- `https://techdining.nutrislice.com/menu/west-village`"
            )
            return

        if not dishes:
            st.warning("No dishes found on the menu for this date and meal period.")
            return

        # Metrics overview
        n_safer = sum(1 for d in dishes if d["risk"] == "safer")
        n_caution = sum(1 for d in dishes if d["risk"] == "caution")
        n_avoid = sum(1 for d in dishes if d["risk"] == "avoid")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Dishes Analyzed", len(dishes))
        m2.metric("🟢 SAFER Choices", n_safer)
        m3.metric("🟡 CAUTION Items", n_caution)
        m4.metric("🔴 AVOID (High Risk)", n_avoid)

        # Filters
        st.markdown("---")
        cf1, cf2, cf3 = st.columns([1.2, 1, 1.5])
        all_stations = ["All Stations"] + sorted({d["station"] for d in dishes})
        selected_station = cf1.selectbox("Filter by Station", all_stations, key="dining_station_filter")

        risk_filter = cf2.selectbox(
            "Filter by Histamine Risk",
            ["All Risk Levels", "🟢 SAFER only", "🟡 CAUTION only", "🔴 AVOID only"],
            key="dining_risk_filter",
        )

        search_q = cf3.text_input(
            "Search dish or ingredient",
            placeholder="Type chicken, burger, cucumber, salad...",
            key="dining_dish_search",
        )

        # Filter dishes
        filtered = []
        for d in dishes:
            if selected_station != "All Stations" and d["station"] != selected_station:
                continue
            if risk_filter == "🟢 SAFER only" and d["risk"] != "safer":
                continue
            if risk_filter == "🟡 CAUTION only" and d["risk"] != "caution":
                continue
            if risk_filter == "🔴 AVOID only" and d["risk"] != "avoid":
                continue
            if search_q:
                q = search_q.strip().lower()
                in_name = q in d["name"].lower()
                in_station = q in d["station"].lower()
                in_ings = q in d["ingredients"].lower()
                if not (in_name or in_station or in_ings):
                    continue
            filtered.append(d)

        st.caption(f"Showing **{len(filtered)}** of **{len(dishes)}** dishes for **{hall_info['name']}** ({chosen_meal.title()}, {chosen_date_str}).")

        # Group filtered dishes by station
        by_station = {}
        for d in filtered:
            by_station.setdefault(d["station"], []).append(d)

        for station_name, s_dishes in by_station.items():
            with st.expander(f"📍 **{station_name}** ({len(s_dishes)} dishes)", expanded=True):
                for dish in s_dishes:
                    risk_badge = (
                        '<span role="status" aria-label="Histamine risk: SAFER. Fresh preparation without high histamine triggers." '
                        'style="background-color: #dcfce7; border: 1px solid #16a34a; color: #14532d; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">🟢 SAFER</span>'
                        if dish["risk"] == "safer"
                        else (
                            '<span role="status" aria-label="Histamine risk: CAUTION. Contains moderate histamine triggers or liberators." '
                            'style="background-color: #fef3c7; border: 1px solid #d97706; color: #78350f; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">🟡 CAUTION</span>'
                            if dish["risk"] == "caution"
                            else '<span role="status" aria-label="Histamine risk: AVOID. High histamine, aged, cured, or fermented ingredients." '
                            'style="background-color: #fee2e2; border: 1px solid #dc2626; color: #7f1d1d; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">🔴 AVOID</span>'
                        )
                    )
                    cal_str = f"&nbsp;•&nbsp; <span style='color: #475569; font-size: 0.85rem;'>{int(dish['calories'])} kcal</span>" if dish["calories"] is not None else ""

                    reasons_html = ""
                    if dish["risk"] != "safer" and dish["reasons"]:
                        reasons_html = (
                            f"<div style='font-size: 0.84rem; color: #334155; margin-top: 4px;'>"
                            f"<b>Histamine Triggers:</b> {', '.join(dish['reasons'])}"
                            f"</div>"
                        )
                    elif dish["risk"] == "safer":
                        reasons_html = (
                            "<div style='font-size: 0.84rem; color: #14532d; margin-top: 4px; font-weight: 500;'>"
                            "Fresh / simple preparation; no common histamine triggers detected."
                            "</div>"
                        )

                    st.markdown(
                        f"<div style='background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px 14px; margin-bottom: 8px;'>"
                        f"<div>{risk_badge} &nbsp; <b style='color: #0f172a;'>{html.escape(dish['name'])}</b>{cal_str}</div>"
                        f"{reasons_html}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    if dish["ingredients"]:
                        with st.expander(f"View ingredient list for {dish['name']}"):
                            st.caption(dish["ingredients"])
