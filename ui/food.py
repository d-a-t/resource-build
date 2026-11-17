"""Food Reference page module."""
from __future__ import annotations

import html
import streamlit as st

from lib.content import (
    FOOD_GROUP_COLORS,
    STATUS_COLORS,
    filter_food_items,
    get_all_attributes,
    get_all_food_items,
    get_attribute_categories,
    get_attributes_for_category,
    get_food_groups,
    get_food_reference_html_table,
    get_food_subgroups,
)
from ui.common import disclaimer


def page_food() -> None:
    """Render the interactive Food Reference table and ingredient directory."""
    st.title("Food reference")
    st.write(
        "Each column has a text label and distinct color badge. "
        "Lists vary by source and by person. This is a starting point "
        "*[VERIFY every row against the SIGHI food compatibility list]*. "
        "Freshness matters as much as the food itself."
    )

    all_groups = get_food_groups()

    # Query param detection for redirection from food box clicks
    focused_food = st.query_params.get("food", "").strip()
    tab_param = st.query_params.get("tab", "").strip()

    # View mode state management
    if "food_view_mode" not in st.session_state:
        st.session_state["food_view_mode"] = "Ingredient Directory" if (focused_food or tab_param == "dir") else "Grouped Table"
    elif focused_food and st.session_state.get("_last_focused_food") != focused_food:
        st.session_state["food_view_mode"] = "Ingredient Directory"
    st.session_state["_last_focused_food"] = focused_food

    q = st.text_input(
        "Search for a food, attribute, or note (e.g., starches, root veggies, tart, savory, chicken, tomato)",
        placeholder="Type to search foods, attributes, or notes...",
    )

    c1, c2, c3 = st.columns(3)
    selected_group = c1.selectbox("Food group", ["All"] + all_groups)
    available_subgroups = get_food_subgroups(None if selected_group == "All" else selected_group)
    selected_subgroup = c2.selectbox("Subgroup", ["All"] + available_subgroups)
    selected_statuses = c3.multiselect(
        "Tolerance level",
        options=["safer", "caution", "avoid"],
        default=["safer", "caution", "avoid"],
        format_func=lambda s: {
            "safer": "🟢 SAFER (usually tolerated)",
            "caution": "🟡 CAUTION (test slowly)",
            "avoid": "🔴 AVOID (problematic)",
        }.get(s, s.upper()),
    )

    # Organized attribute filtering by category
    attr_categories = ["All Categories"] + get_attribute_categories()
    a_col1, a_col2 = st.columns([1, 2])
    selected_attr_cat = a_col1.selectbox("Attribute category", attr_categories)

    category_attrs = get_attributes_for_category(selected_attr_cat)
    # Ensure active selections stay in options so category changes don't drop them
    current_selected = st.session_state.get("active_attrs", [])
    combined_options = sorted(set(category_attrs) | set(current_selected))

    selected_attrs = a_col2.multiselect(
        "Filter by attribute",
        options=combined_options,
        default=current_selected,
        key="active_attrs",
        help="Select attributes (e.g. starches, root veggies, tart, savory) to narrow matching foods.",
    )

    matched_items = filter_food_items(
        group_filter=selected_group,
        subgroup_filter=selected_subgroup,
        status_filters=selected_statuses,
        attribute_filters=selected_attrs,
        query=q,
    )

    all_total = len(get_all_food_items())
    st.caption(
        f"Showing **{len(matched_items)}** of **{all_total}** foods "
        f"across **{len({it['subgroup'] for it in matched_items})}** subgroup(s)."
    )

    if not matched_items:
        st.info("No matching foods found. Try adjusting your search or clearing filters.")
        st.markdown(
            "**Rule of thumb:** cook it fresh, eat it soon, and freeze leftover portions "
            "right after cooking instead of refrigerating them for days."
        )
        disclaimer()
        return

    # View selector
    view_options = ["Grouped Table", "Ingredient Directory"]
    active_idx = 0 if st.session_state["food_view_mode"] == "Grouped Table" else 1
    selected_view = st.radio(
        "View mode",
        options=view_options,
        index=active_idx,
        horizontal=True,
        key="food_view_radio",
        label_visibility="collapsed",
    )
    st.session_state["food_view_mode"] = selected_view

    if selected_view == "Grouped Table":
        # Legend for tolerance tags
        st.markdown(
            '<div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin: 8px 0 10px 0; font-size: 0.88rem;">'
            '<span style="font-weight: 600; color: #475569;">Tolerance tags:</span>'
            '<span style="background-color: #dcfce7; border: 1px solid #86efac; color: #166534; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.82rem;">SAFER</span>'
            '<span style="background-color: #fef3c7; border: 1px solid #fde047; color: #854d0e; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.82rem;">CAUTION</span>'
            '<span style="background-color: #fee2e2; border: 1px solid #fca5a5; color: #991b1b; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.82rem;">AVOID</span>'
            '<span style="color: #64748b; font-size: 0.84rem; margin-left: 6px;">💡 Click any food box to jump to its ingredient details</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Legend for food groups
        group_pills = " ".join(
            f'<span style="background-color: {colors["bg"]}; border: 1px solid {colors["border"]}; color: {colors["text"]}; padding: 2px 7px; border-radius: 4px; font-size: 0.78rem; font-weight: 600; margin-right: 4px; display: inline-block;">{grp}</span>'
            for grp, colors in FOOD_GROUP_COLORS.items()
        )
        st.markdown(f'<div style="margin-bottom: 12px; font-size: 0.82rem; color: #64748b;"><b style="color: #475569;">Food group colors:</b> {group_pills}</div>', unsafe_allow_html=True)

        # Render HTML table with individually boxed and colored food chips
        st.markdown(get_food_reference_html_table(matched_items), unsafe_allow_html=True)

    else:
        # Ingredient Directory view
        if focused_food:
            banner_col1, banner_col2, banner_col3 = st.columns([3, 1.2, 1.2])
            banner_col1.info(f"Viewing category details for: **{focused_food}** (clicked from Grouped Table)")
            if banner_col2.button("← Grouped Table", key="back_to_grouped_btn"):
                st.query_params.clear()
                st.session_state["food_view_mode"] = "Grouped Table"
                st.session_state["_last_focused_food"] = ""
                st.rerun()
            if banner_col3.button("Show all foods", key="clear_focus_btn"):
                st.query_params.clear()
                st.session_state["_last_focused_food"] = ""
                st.rerun()

            # Highlighted food card for focused item
            matching_focused = [it for it in get_all_food_items() if it["name"].lower() == focused_food.lower()]
            if matching_focused:
                target = matching_focused[0]
                grp_c = FOOD_GROUP_COLORS.get(target["group"], {"bg": "#f1f5f9", "border": "#cbd5e1", "text": "#334155"})
                st_c = STATUS_COLORS.get(target["status"], {"bg": "#f1f5f9", "border": "#cbd5e1", "text": "#334155", "label": target["status"].upper()})

                cost_str = f"<b>Cost:</b> ${target['cost_per_kg']:.2f}/kg"
                if target.get("cost_per_lb") is not None:
                    cost_str += f" (${target['cost_per_lb']:.2f}/lb)"

                attrs_html = " ".join(
                    f'<span style="background-color: #f1f5f9; border: 1px solid #cbd5e1; color: #334155; padding: 2px 7px; border-radius: 4px; font-size: 0.8rem; margin-right: 4px;">{a}</span>'
                    for a in target.get("attributes", [])
                ) or "None"
                notes_line = f"<br><b>Notes:</b> {html.escape(target['notes'])}" if target.get("notes") else ""

                card_html = (
                    f'<div style="background: #ffffff; border: 2px solid {st_c["border"]}; border-radius: 8px; padding: 14px 18px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);">'
                    f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">'
                    f'<span style="font-size: 1.25rem; font-weight: 700; color: #0f172a;">{html.escape(target["name"])}</span>'
                    f'<div>'
                    f'<span style="background-color: {grp_c["bg"]}; border: 1px solid {grp_c["border"]}; color: {grp_c["text"]}; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; margin-right: 6px;">{html.escape(target["group"])}</span>'
                    f'<span style="background-color: {st_c["bg"]}; border: 1px solid {st_c["border"]}; color: {st_c["text"]}; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 700;">{st_c["label"]}</span>'
                    f'</div>'
                    f'</div>'
                    f'<div style="font-size: 0.9rem; color: #475569; line-height: 1.6;">'
                    f'<b>Subgroup:</b> {html.escape(target["subgroup"])} &nbsp;|&nbsp; {cost_str}<br>'
                    f'<b>Attributes:</b> {attrs_html}{notes_line}'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)

        # Full searchable directory table (focused on item if selected, or all items)
        display_items = (
            [it for it in matched_items if it["name"].lower() == focused_food.lower()]
            if focused_food
            else matched_items
        )
        dir_data = [
            {
                "Ingredient": it["name"],
                "Food Group": it["group"],
                "Subgroup": it["subgroup"],
                "Tolerance": {
                    "safer": "🟢 SAFER",
                    "caution": "🟡 CAUTION",
                    "avoid": "🔴 AVOID",
                }.get(it["status"], it["status"].upper()),
                "Cost / kg": f"${it['cost_per_kg']:.2f}" if it.get("cost_per_kg") is not None else "—",
                "Cost / lb": f"${it['cost_per_lb']:.2f}" if it.get("cost_per_lb") is not None else "—",
                "Attributes": ", ".join(it.get("attributes", [])),
                "Notes": it.get("notes", "") or "—",
            }
            for it in display_items
        ]
        st.dataframe(dir_data, use_container_width=True, hide_index=True)

    st.markdown(
        "**Rule of thumb:** cook it fresh, eat it soon, and freeze leftover portions "
        "right after cooking instead of refrigerating them for days."
    )
    disclaimer()
