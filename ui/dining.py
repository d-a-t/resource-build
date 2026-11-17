"""Campus Dining page module with live Tech Dining Nutrislice menu integration."""
from __future__ import annotations

import html
import streamlit as st

from lib.dining import fetch_nutrislice_menu, parse_nutrislice_url
from ui.common import disclaimer, md


@st.cache_data(ttl=600)
def cached_nutrislice_menu(school: str, menu_type: str, date_str: str, district: str = "techdining"):
    """Cache daily Nutrislice menu queries to prevent repeated network overhead."""
    return fetch_nutrislice_menu(school, menu_type, date_str, district)


def page_dining() -> None:
    """Render the Campus Dining page with live Nutrislice menu risk analysis."""
    st.title("Campus Dining & Live Daily Menu")

    tab_menu, tab_guide = st.tabs(["🍽️ Daily Nutrislice Menu Checker", "📋 Dining Hall Guide & Tips"])

    with tab_guide:
        md("dining.md")
        disclaimer()

    with tab_menu:
        st.write(
            "Analyze live daily dining hall menus from **techdining.nutrislice.com** against histamine intolerance risk. "
            "The analyzer inspects dish names, descriptions, and full recipe ingredient lists to flag high-histamine ingredients, "
            "fermented items, aged cheeses, cured meats, and histamine liberators."
        )

        default_url = "https://techdining.nutrislice.com/menu/brittain/lunch/2026-11-17"
        url_input = st.text_input(
            "Enter Tech Dining Nutrislice URL (or use quick controls below):",
            value=default_url,
            help="Paste any menu URL from techdining.nutrislice.com",
            key="dining_nutrislice_url",
        )

        parsed = parse_nutrislice_url(url_input)

        c1, c2, c3, c4 = st.columns([1.2, 1, 1, 0.8])
        school_options = {
            "brittain": "Brittain Dining Hall",
            "north-ave": "North Avenue Dining Hall",
            "west-village": "West Village Dining",
            "john-lewis-student-center": "Student Center",
        }
        school_keys = list(school_options.keys())
        school_idx = school_keys.index(parsed["school"]) if parsed["school"] in school_keys else 0
        chosen_school = c1.selectbox(
            "Dining Hall",
            school_keys,
            index=school_idx,
            format_func=lambda k: school_options.get(k, k),
            key="dining_school_select",
        )

        meal_options = ["lunch", "dinner", "breakfast"]
        meal_idx = meal_options.index(parsed["menu_type"]) if parsed["menu_type"] in meal_options else 0
        chosen_meal = c2.selectbox("Meal Period", meal_options, index=meal_idx, key="dining_meal_select")

        chosen_date = c3.text_input("Date (YYYY-MM-DD)", value=parsed["date"], key="dining_date_input")

        with c4:
            st.write("&nbsp;")
            st.button("🔄 Analyze Menu", use_container_width=True, key="dining_load_btn")

        dishes, err = cached_nutrislice_menu(chosen_school, chosen_meal, chosen_date.strip(), parsed["district"])

        if err:
            st.error(f"Could not load Nutrislice menu: {err}")
            st.info("Check your URL or date and try again. For testing, use: `https://techdining.nutrislice.com/menu/brittain/lunch/2026-11-17`.")
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

        st.caption(f"Showing **{len(filtered)}** of **{len(dishes)}** dishes for **{school_options.get(chosen_school, chosen_school)}** ({chosen_meal.title()}, {chosen_date}).")

        # Group filtered dishes by station
        by_station = {}
        for d in filtered:
            by_station.setdefault(d["station"], []).append(d)

        for station_name, s_dishes in by_station.items():
            with st.expander(f"📍 **{station_name}** ({len(s_dishes)} dishes)", expanded=True):
                for dish in s_dishes:
                    risk_badge = (
                        '<span style="background-color: #dcfce7; border: 1px solid #86efac; color: #166534; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">🟢 SAFER</span>'
                        if dish["risk"] == "safer"
                        else (
                            '<span style="background-color: #fef9c3; border: 1px solid #fde047; color: #854d0e; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">🟡 CAUTION</span>'
                            if dish["risk"] == "caution"
                            else '<span style="background-color: #fee2e2; border: 1px solid #fca5a5; color: #991b1b; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">🔴 AVOID</span>'
                        )
                    )
                    cal_str = f"&nbsp;•&nbsp; <span style='color: #64748b; font-size: 0.85rem;'>{int(dish['calories'])} kcal</span>" if dish["calories"] is not None else ""

                    reasons_html = ""
                    if dish["risk"] != "safer" and dish["reasons"]:
                        reasons_html = (
                            f"<div style='font-size: 0.84rem; color: #475569; margin-top: 3px;'>"
                            f"<b>Histamine Triggers:</b> {', '.join(dish['reasons'])}"
                            f"</div>"
                        )
                    elif dish["risk"] == "safer":
                        reasons_html = (
                            "<div style='font-size: 0.84rem; color: #166534; margin-top: 3px;'>"
                            "Fresh / simple preparation; no common histamine triggers detected."
                            "</div>"
                        )

                    st.markdown(
                        f"<div style='background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px;'>"
                        f"<div>{risk_badge} &nbsp; <b>{html.escape(dish['name'])}</b>{cal_str}</div>"
                        f"{reasons_html}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    if dish["ingredients"]:
                        with st.expander(f"View ingredient list for {dish['name']}"):
                            st.caption(dish["ingredients"])
