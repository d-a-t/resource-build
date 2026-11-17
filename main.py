"""Eating Well on Campus with Histamine Intolerance: a Streamlit toolkit.

Run locally:  streamlit run main.py
Add recipes:  drop a YAML file into recipes/ (see README.md) or use the
              "Add a recipe" page.
"""
from pathlib import Path
import html
import re
import urllib.parse

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
    get_food_reference_table_rows,
    get_food_subgroups,
    get_foods_by_attribute,
    load_checklists,
    load_food_reference,
    load_meal_plan,
    match_ingredient_to_food,
    pluralize,
    singularize,
)
from lib.recipes import (
    RECIPE_DIR,
    Recipe,
    calculate_recipe_cost,
    estimate_ingredient_cost,
    load_all,
    parse_yaml_text,
    swap_recipe_ingredient,
    to_yaml,
)

ROOT = Path(__file__).parent
TITLE = "Eating Well on Campus with Histamine Intolerance"

st.set_page_config(page_title=TITLE, page_icon="🥣", layout="centered")


def md(name: str) -> None:
    st.markdown((ROOT / "content" / name).read_text(encoding="utf-8"))


def disclaimer() -> None:
    with st.container(border=True):
        md("disclaimer.md")


@st.cache_data(ttl=2)
def recipes_cached():
    return load_all()


def fmt_cost(v: float) -> str:
    return f"about ${v:.2f}"


def safe_get_alternates(r: Recipe, ingredient_str: str | None = None) -> list[str]:
    """Safely retrieve alternates from a Recipe object, resilient to cached instances."""
    if hasattr(r, "get_alternates_for") and ingredient_str:
        try:
            return r.get_alternates_for(ingredient_str)
        except Exception:
            pass
    alts = getattr(r, "alternates", None) or {}
    if not ingredient_str:
        if isinstance(alts, dict):
            return list(alts.keys())
        return []
    if isinstance(alts, dict):
        if ingredient_str in alts:
            v = alts[ingredient_str]
            return v if isinstance(v, list) else [v]
        for k, v in alts.items():
            if k.lower() in ingredient_str.lower() or ingredient_str.lower() in k.lower():
                return v if isinstance(v, list) else [v]
    elif isinstance(alts, list):
        res = []
        for it in alts:
            if isinstance(it, dict):
                orig = it.get("original") or it.get("ingredient") or it.get("for") or ""
                if orig and (orig.lower() in ingredient_str.lower() or ingredient_str.lower() in orig.lower()):
                    eq = it.get("equivalent") or it.get("alternate") or it.get("substitute") or ""
                    if eq:
                        res.append(eq)
            elif isinstance(it, str):
                res.append(it)
        return res
    return []


def render_recipe(r: Recipe, level_heading: bool = True) -> None:
    is_adv = getattr(r, "is_advanced", False)
    category_badge = (
        '<span style="background-color: #f5f3ff; border: 1px solid #c4b5fd; color: #5b21b6; '
        'padding: 2px 8px; border-radius: 4px; font-size: 0.76rem; font-weight: 700;">'
        '🟣 ADVANCED RECIPE</span>'
        if is_adv
        else '<span style="background-color: #f0fdf4; border: 1px solid #86efac; color: #166534; '
        'padding: 2px 8px; border-radius: 4px; font-size: 0.76rem; font-weight: 700;">'
        '🟢 BASIC RECIPE</span>'
    )
    st.markdown(f'<div style="margin-bottom: 6px;">{category_badge}</div>', unsafe_allow_html=True)
    st.subheader(r.title)
    if r.description:
        st.write(r.description)
    if not r.verified:
        st.caption("Draft: cost and food-safety details not yet verified.")

    # Dynamically calculate recipe cost from ingredients
    calc_cps, total_cost, breakdown = calculate_recipe_cost(r)
    servings_label = f"{r.servings} serving" if r.servings == 1 else f"{r.servings} servings"

    st.markdown(
        f"**Servings:** {r.servings}  \n"
        f"**Time:** {r.prep_minutes} min prep, {r.cook_minutes} min cook  \n"
        f"**Estimated cost per serving:** **${calc_cps:.2f}** "
        f'<span style="color: #64748b; font-size: 0.88rem;">(calculated: ${total_cost:.2f} total / {servings_label})</span>  \n'
        f"**Equipment:** {', '.join(r.equipment)}  \n"
        f"**Storage:** {r.storage}",
        unsafe_allow_html=True,
    )
    st.markdown("**Ingredients**")
    ing_lines = []
    for i in r.ingredients:
        m = match_ingredient_to_food(i)
        alts = safe_get_alternates(r, i)
        alt_html = ""
        if alts:
            alt_badges = " ".join(
                f'<span style="background-color: #f1f5f9; border: 1px solid #cbd5e1; color: #475569; padding: 1px 6px; border-radius: 4px; font-size: 0.76rem;">{html.escape(a)}</span>'
                for a in alts
            )
            alt_html = f'<br><span style="margin-left: 18px; font-size: 0.78rem; color: #64748b;">⇄ <b>YAML Alternates:</b> {alt_badges}</span>'

        if m:
            st_c = STATUS_COLORS.get(m["status"], {"bg": "#dcfce7", "text": "#166534", "label": m["status"].upper()})
            cost_parts = []
            if m.get("cost_per_lb") is not None:
                cost_parts.append(f"${m['cost_per_lb']:.2f}/lb")
            if m.get("cost_per_kg") is not None:
                cost_parts.append(f"${m['cost_per_kg']:.2f}/kg")
            cost_str = " • ".join(cost_parts)
            cost_display = f'<span style="color: #64748b; font-size: 0.84rem;">({cost_str})</span>' if cost_str else ""
            encoded_name = urllib.parse.quote(m["name"])
            link_html = (
                f'<a href="/food?food={encoded_name}&tab=dir" target="_self" '
                f'title="View {html.escape(m["name"])} in Food Reference" '
                f'style="color: inherit; text-decoration: underline; text-decoration-color: #cbd5e1; font-weight: 500;">{html.escape(i)}</a>'
            )
            badge_html = f'<span style="background-color: {st_c["bg"]}; color: {st_c["text"]}; padding: 1px 6px; border-radius: 4px; font-size: 0.74rem; font-weight: 700; margin-left: 5px;">{st_c["label"]}</span>'
            ing_lines.append(f"- {link_html} {badge_html} {cost_display}{alt_html}")
        else:
            ing_lines.append(f"- {html.escape(i)}{alt_html}")
    st.markdown("\n".join(ing_lines), unsafe_allow_html=True)

    with st.expander(f"💰 View calculated cost breakdown (${calc_cps:.2f}/serving)"):
        cost_rows = [
            {
                "Ingredient": item["ingredient"],
                "Matched Food": item["matched_food"],
                "Unit Price": (
                    f"${item['unit_cost_lb']:.2f}/lb (${item['unit_cost_kg']:.2f}/kg)"
                    if item["unit_cost_kg"] > 0
                    else "Free"
                ),
                "Weight / Count": (
                    f"{item['weight_kg']*2.20462:.2f} lb ({item['weight_kg']:.3f} kg)"
                    if item["weight_kg"] > 0
                    else "—"
                ),
                "Est. Cost": f"${item['line_cost']:.2f}",
            }
            for item in breakdown
        ]
        st.dataframe(cost_rows, use_container_width=True, hide_index=True)
        st.caption(
            f"Total calculated cost: ${total_cost:.2f} ÷ {r.servings} serving(s) = "
            f"**${calc_cps:.2f} per serving**."
        )

    st.markdown("**Method**")
    st.markdown("\n".join(f"{n}. {s}" for n, s in enumerate(r.method, 1)))
    if r.notes:
        st.markdown(f"**Note:** {r.notes}")
    if r.tags:
        st.caption("Tags: " + ", ".join(r.tags))


# ---------------------------------------------------------------- pages
def page_home():
    st.title(TITLE)
    st.write(
        "A low-histamine toolkit for Georgia Tech students and the people who "
        "cook, dine, and plan events with them."
    )
    st.info("DRAFT for workshopping. Items marked [VERIFY] still need a source check.")
    disclaimer()
    st.header("Why this is an access issue")
    md("why_access.md")
    st.header("What's in this toolkit")
    st.markdown(
        "- **Food Reference:** safer, caution, and avoid foods\n"
        "- **Campus Dining:** questions to ask and how to request accommodations\n"
        "- **Cheap Cooking:** staples, batch cooking, dorm-friendly methods\n"
        "- **Recipes:** filter by equipment, time, cost, and tags\n"
        "- **Meal Plan:** a sample 3-day plan\n"
        "- **Checklists and Template:** shopping, meal prep, and a script for dining staff\n"
        "- **Add a Recipe:** grow the collection with a YAML file"
    )


def page_food():
    st.title("Food reference")
    st.write(
        "Each column has a text label and distinct color badge. "
        "Lists vary by source and by person. This is a starting point "
        "*[VERIFY every row against the SIGHI food compatibility list]*. "
        "Freshness matters as much as the food itself."
    )

    all_groups = get_food_groups()
    all_attrs = get_all_attributes()

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


def page_dining():
    st.title("Navigating campus dining")
    md("dining.md")


def page_cheap():
    st.title("Cheap cooking in a small kitchen")
    md("cheap_cooking.md")


def page_recipes():
    st.title("Recipes")
    tab_browse, tab_replacer = st.tabs(["Browse Recipes", "Experimental Replacer"])

    with tab_browse:
        recipes, problems = recipes_cached()
        if problems:
            with st.expander(f"{len(problems)} recipe file(s) have problems and are hidden"):
                for fname, errs in problems.items():
                    st.markdown(f"**{fname}**")
                    st.markdown("\n".join(f"- {e}" for e in errs))
        if not recipes:
            st.write("No recipes yet. Add one on the Add a Recipe page.")
        else:
            st.write(
                "Costs per serving are dynamically calculated from canonical ingredient costs and quantities. "
                "Storage means freezing portions right after cooking unless noted. "
                "Click on any ingredient to view its safety profile, cost, and culinary attributes in Food Reference."
            )
            n_base = sum(1 for r in recipes if not getattr(r, "is_advanced", False))
            n_adv = sum(1 for r in recipes if getattr(r, "is_advanced", False))
            filter_options = [
                f"All Recipes ({len(recipes)})",
                f"Basic Recipes ({n_base})",
                f"Advanced Recipes ({n_adv})",
            ]
            recipe_filter = st.radio(
                "Filter recipe catalog",
                filter_options,
                horizontal=True,
                key="browse_catalog_filter",
            )
            search_query = st.text_input(
                "Search recipes by name, ingredient, or alternate",
                placeholder="Type recipe title, ingredient, or alternate (e.g. turkey, sweet potato, soup, quinoa, salmon)...",
                key="browse_recipe_search",
            )
            all_equipment = sorted({e for r in recipes for e in r.equipment})
            all_tags = sorted({t for r in recipes for t in r.tags})
            c1, c2 = st.columns(2)
            equip = c1.multiselect("I have (show recipes that need only these)", all_equipment, key="browse_equip")
            tags = c2.multiselect("Tags (show recipes with any of these)", all_tags, key="browse_tags")
            c3, c4 = st.columns(2)
            max_cost = c3.slider("Max calculated cost per serving ($)", 0.0, 10.0, 10.0, 0.25, key="browse_cost")
            max_time = c4.slider("Max total minutes", 5, 120, 120, 5, key="browse_time")

            def ok(r: Recipe) -> bool:
                is_adv = getattr(r, "is_advanced", False)
                if recipe_filter.startswith("Basic Recipes") and is_adv:
                    return False
                if recipe_filter.startswith("Advanced Recipes") and not is_adv:
                    return False
                if search_query:
                    sq = search_query.strip().lower()
                    title_match = sq in r.title.lower()
                    ing_match = any(sq in ing.lower() for ing in r.ingredients)
                    alts_val = getattr(r, "alternates", None)
                    alt_match = bool(
                        alts_val
                        and any(
                            sq in str(v).lower()
                            for v in (alts_val.values() if isinstance(alts_val, dict) else alts_val)
                        )
                    )
                    if not (title_match or ing_match or alt_match):
                        return False
                if equip and not set(r.equipment) <= set(equip):
                    return False
                if tags and not set(tags) & set(r.tags):
                    return False
                calc_cps, _, _ = calculate_recipe_cost(r)
                return calc_cps <= max_cost and r.total_minutes <= max_time

            shown = [r for r in recipes if ok(r)]
            st.write(f"Showing {len(shown)} of {len(recipes)} recipes.")
            for r in shown:
                with st.container(border=True):
                    render_recipe(r)

    with tab_replacer:
        page_experimental_replacer()


def page_experimental_replacer() -> None:
    st.subheader("🧪 Experimental Replacer")
    recipes, _ = recipes_cached()
    if not recipes:
        st.info("No recipes available to swap. Add one on the Add a Recipe page first.")
        return

    st.markdown(
        "Experiment with ingredient replacements to tailor any recipe to your histamine tolerance, pantry ingredients, or budget. "
        "Swap an ingredient either **using functional attributes** (e.g., matching starches, root vegetables, poultry, tart, or aromatics) "
        "or **by choosing a specific ingredient** directly. The replacer calculates the updated cost per serving and generates a fully compliant recipe YAML."
    )

    EXAMPLE_PRESETS = {
        "— Build custom swap (or select an example below) —": None,
        "🍗 ➔ 🦃 Example 1: Chicken Soup ➔ Turkey & Sweet Potato Soup (Attribute: poultry)": {
            "recipe_id": "one-pot-chicken-potato-soup",
            "old_ing": "1 lb fresh chicken thighs or breasts",
            "mode": "Swap using Attributes",
            "attr": "poultry",
            "new_food": "Turkey",
        },
        "🥩 ➔ 🐑 Example 2: Beef Potato Hash ➔ Lamb & Sweet Potato Hash (Attribute: red meat)": {
            "recipe_id": "skillet-beef-potato-hash",
            "old_ing": "1/2 lb fresh ground beef",
            "mode": "Swap using Attributes",
            "attr": "red meat",
            "new_food": "Lamb",
        },
        "🍗 ➔ 🐟 Example 3: Chicken Rice ➔ Flash-Frozen Salmon Rice (Ingredient: Meat and fish)": {
            "recipe_id": "rice-cooker-chicken-carrot-rice",
            "old_ing": "1 chicken breast, diced small",
            "mode": "Swap by Specified Ingredient",
            "group": "Meat and fish",
            "new_food": "Salmon (gutted and frozen within minutes of catch)",
        },
        "🍚 ➔ 🌾 Example 4: Fried Rice ➔ Quinoa Veggie Bowl (Attribute: starches)": {
            "recipe_id": "veggie-fried-rice",
            "old_ing": "1 1/2 cups freshly cooked rice",
            "mode": "Swap using Attributes",
            "attr": "starches",
            "new_food": "Quinoa",
        },
        "🍎 ➔ 🍐 Example 5: Apple Oatmeal ➔ Pear & Blueberry Oatmeal (Attribute: fruit)": {
            "recipe_id": "microwave-apple-cinnamon-oatmeal",
            "old_ing": "1/2 apple, diced",
            "mode": "Swap using Attributes",
            "attr": "fruit",
            "new_food": "Pears",
        },
    }

    preset_choice = st.selectbox(
        "⚡ Try an example advanced swap (or customize your own below):",
        list(EXAMPLE_PRESETS.keys()),
        key="adv_example_preset",
    )
    preset_data = EXAMPLE_PRESETS.get(preset_choice)

    def find_idx(items, predicate, default=0):
        for idx, it in enumerate(items):
            if predicate(it):
                return idx
        return default

    # 1. Base Recipe selection
    default_recipe_idx = 0
    if preset_data:
        default_recipe_idx = find_idx(recipes, lambda r: r.id == preset_data["recipe_id"], 0)

    c_rec, c_ing = st.columns([1, 1])
    selected_recipe = c_rec.selectbox(
        "1. Select base recipe",
        recipes,
        index=default_recipe_idx,
        format_func=lambda r: f"{r.title} (${calculate_recipe_cost(r)[0]:.2f}/serv)",
        key=f"adv_recipe_select_{preset_choice}",
    )

    # 2. Ingredient selection
    default_ing_idx = 0
    if preset_data and preset_data.get("old_ing") in selected_recipe.ingredients:
        default_ing_idx = selected_recipe.ingredients.index(preset_data["old_ing"])

    selected_ing = c_ing.selectbox(
        "2. Select ingredient to swap out",
        selected_recipe.ingredients,
        index=default_ing_idx,
        key=f"adv_ing_select_{selected_recipe.id}_{preset_choice}",
    )

    matched_target = match_ingredient_to_food(selected_ing)
    if matched_target:
        tgt_grp_c = FOOD_GROUP_COLORS.get(
            matched_target["group"],
            {"bg": "#f1f5f9", "border": "#cbd5e1", "text": "#334155"},
        )
        tgt_st_c = STATUS_COLORS.get(
            matched_target["status"],
            {"bg": "#f1f5f9", "border": "#cbd5e1", "text": "#334155", "label": matched_target["status"].upper()},
        )
        tgt_cost_lb = f"${matched_target['cost_per_lb']:.2f}/lb" if matched_target.get("cost_per_lb") is not None else ""
        tgt_cost_kg = f"${matched_target['cost_per_kg']:.2f}/kg" if matched_target.get("cost_per_kg") is not None else ""
        tgt_cost_str = " • ".join(filter(None, [tgt_cost_lb, tgt_cost_kg])) or "—"
        tgt_attrs_html = " ".join(
            f'<span style="background-color: #f1f5f9; border: 1px solid #cbd5e1; color: #475569; padding: 1px 6px; border-radius: 4px; font-size: 0.78rem; margin-right: 4px;">{html.escape(a)}</span>'
            for a in matched_target.get("attributes", [])
        ) or "None"

        st.markdown(
            f'<div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 14px; margin: 8px 0 16px 0;">'
            f'<span style="font-weight: 600; color: #0f172a;">Detected Food:</span> '
            f'<span style="font-weight: 700; color: #1e293b; margin-left: 4px;">{html.escape(matched_target["name"])}</span> &nbsp;'
            f'<span style="background-color: {tgt_grp_c["bg"]}; border: 1px solid {tgt_grp_c["border"]}; color: {tgt_grp_c["text"]}; padding: 1px 6px; border-radius: 4px; font-size: 0.78rem; font-weight: 600;">{html.escape(matched_target["group"])}</span> '
            f'<span style="background-color: {tgt_st_c["bg"]}; border: 1px solid {tgt_st_c["border"]}; color: {tgt_st_c["text"]}; padding: 1px 6px; border-radius: 4px; font-size: 0.78rem; font-weight: 700;">{tgt_st_c["label"]}</span> &nbsp;'
            f'<span style="color: #64748b; font-size: 0.85rem;">Cost: {tgt_cost_str}</span><br>'
            f'<div style="margin-top: 4px;"><b style="font-size: 0.82rem; color: #475569;">Attributes:</b> {tgt_attrs_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # 3. Swap Method
    default_mode_idx = 1 if (preset_data and preset_data.get("mode") == "Swap by Specified Ingredient") else 0
    swap_mode = st.radio(
        "3. Choose swap method",
        ["Swap using Attributes", "Swap by Specified Ingredient"],
        index=default_mode_idx,
        horizontal=True,
        key=f"adv_swap_mode_{preset_choice}",
    )

    replacement_food = None

    if swap_mode == "Swap using Attributes":
        target_attrs = matched_target.get("attributes", []) if matched_target else []
        all_attrs = get_all_attributes()
        attr_options = target_attrs + [a for a in all_attrs if a not in target_attrs]

        default_attr_idx = 0
        if preset_data and preset_data.get("attr") in attr_options:
            default_attr_idx = attr_options.index(preset_data["attr"])

        c_att1, c_att2, c_att3 = st.columns([1.2, 1, 1.8])
        chosen_attr = c_att1.selectbox(
            "Attribute to match",
            attr_options,
            index=default_attr_idx,
            help="Select a culinary or nutritional property to find comparable alternatives",
            key=f"adv_attr_choice_{selected_recipe.id}_{preset_choice}",
        )
        pref_tol = c_att2.multiselect(
            "Tolerance",
            ["safer", "caution", "avoid"],
            default=["safer"],
            format_func=lambda s: {"safer": "🟢 SAFER", "caution": "🟡 CAUTION", "avoid": "🔴 AVOID"}.get(s, s.upper()),
            key=f"adv_attr_tol_{preset_choice}",
        )
        raw_candidates = get_foods_by_attribute(chosen_attr)
        filtered_candidates = [
            f
            for f in raw_candidates
            if f["status"] in pref_tol
            and (not matched_target or f["name"].lower() != matched_target["name"].lower())
        ]
        if not filtered_candidates:
            c_att3.warning(f"No '{chosen_attr}' foods found with selected tolerance.")
        else:
            default_rep_idx = 0
            if preset_data and preset_data.get("new_food"):
                default_rep_idx = find_idx(
                    filtered_candidates,
                    lambda f: f["name"].lower() == preset_data["new_food"].lower(),
                    0,
                )
            replacement_food = c_att3.selectbox(
                "Replacement food",
                filtered_candidates,
                index=default_rep_idx,
                format_func=lambda f: f"{f['name']} ({f['status'].upper()}) - ${f.get('cost_per_lb', 0):.2f}/lb • ${f.get('cost_per_kg', 0):.2f}/kg",
                key=f"adv_attr_replacement_{preset_choice}",
            )

    else:
        c_grp1, c_grp2, c_grp3 = st.columns([1.2, 1, 1.8])
        groups = ["All"] + get_food_groups()
        default_grp_idx = 0
        if preset_data and preset_data.get("group") in groups:
            default_grp_idx = groups.index(preset_data["group"])
        elif matched_target and matched_target["group"] in groups:
            default_grp_idx = groups.index(matched_target["group"])
        chosen_grp = c_grp1.selectbox("Food group", groups, index=default_grp_idx, key=f"adv_spec_group_{preset_choice}")
        pref_tol = c_grp2.multiselect(
            "Tolerance",
            ["safer", "caution", "avoid"],
            default=["safer"],
            format_func=lambda s: {"safer": "🟢 SAFER", "caution": "🟡 CAUTION", "avoid": "🔴 AVOID"}.get(s, s.upper()),
            key=f"adv_spec_tol_{preset_choice}",
        )
        candidates = [
            f
            for f in get_all_food_items()
            if (chosen_grp == "All" or f["group"] == chosen_grp)
            and f["status"] in pref_tol
            and (not matched_target or f["name"].lower() != matched_target["name"].lower())
        ]
        if not candidates:
            c_grp3.warning("No foods found matching selected group and tolerance.")
        else:
            default_rep_idx = 0
            if preset_data and preset_data.get("new_food"):
                default_rep_idx = find_idx(
                    candidates,
                    lambda f: f["name"].lower() == preset_data["new_food"].lower(),
                    0,
                )
            replacement_food = c_grp3.selectbox(
                "Replacement food",
                candidates,
                index=default_rep_idx,
                format_func=lambda f: f"{f['name']} ({f['group']}) [{f['status'].upper()}] - ${f.get('cost_per_lb', 0):.2f}/lb • ${f.get('cost_per_kg', 0):.2f}/kg",
                key=f"adv_spec_replacement_{preset_choice}",
            )

    if not replacement_food:
        st.info("Select a replacement food above to generate the modified recipe.")
        return

    clean_new_name = re.sub(r"\(.*?\)", "", replacement_food["name"]).strip()
    matched_word = None
    if matched_target:
        clean_tgt = re.sub(r"\(.*?\)", "", matched_target["name"]).strip()
        sing_t = singularize(clean_tgt)
        plur_t = pluralize(sing_t)
        for p in (re.escape(plur_t), re.escape(sing_t), re.escape(clean_tgt)):
            pattern = re.compile(r"\b" + p + r"\b", re.IGNORECASE)
            if pattern.search(selected_recipe.title):
                matched_word = p
                break

    if matched_word:
        pattern = re.compile(r"\b" + matched_word + r"\b", re.IGNORECASE)
        suggested_title = pattern.sub(clean_new_name.title(), selected_recipe.title, count=1)
    else:
        suggested_title = f"{selected_recipe.title} (with {clean_new_name})"

    suggested_slug = re.sub(r"[^a-z0-9]+", "-", suggested_title.lower()).strip("-")[:40]

    col_t1, col_t2 = st.columns([2, 1])
    recipe_title_input = col_t1.text_input(
        "Recipe title",
        value=suggested_title,
        key=f"adv_title_val_{selected_recipe.id}_{clean_new_name}_{preset_choice}",
    )
    recipe_id_input = col_t2.text_input(
        "Recipe ID (slug for YAML file)",
        value=suggested_slug,
        key=f"adv_id_val_{selected_recipe.id}_{clean_new_name}_{preset_choice}",
        help="Allowed: letters, numbers, hyphens, underscores. Used as <id>.yaml",
    )

    old_kg = matched_target.get("cost_per_kg") if matched_target else None
    new_kg = replacement_food.get("cost_per_kg")

    output_mode = st.radio(
        "Recipe YAML format",
        [
            "Tailored Variation (replaces ingredient directly in recipe)",
            "Base Recipe with Alternate Equivalent (keeps base ingredient & adds to 'alternates:' field)",
        ],
        key=f"adv_output_mode_{selected_recipe.id}_{preset_choice}",
    )
    is_as_alternate = output_mode.startswith("Base Recipe with Alternate")

    swapped_dict, yaml_output = swap_recipe_ingredient(
        recipe=selected_recipe,
        old_ingredient_str=selected_ing,
        new_food_name=replacement_food["name"],
        old_food_name=matched_target["name"] if matched_target else None,
        new_cost_per_kg=new_kg,
        old_cost_per_kg=old_kg,
        custom_title=recipe_title_input.strip() if recipe_title_input.strip() else None,
        custom_id=recipe_id_input.strip() if recipe_id_input.strip() else None,
        as_alternate=is_as_alternate,
    )

    # Dynamic cost calculation comparison
    orig_cps, orig_total, _ = calculate_recipe_cost(selected_recipe)
    new_cps, new_total, swapped_breakdown = calculate_recipe_cost(swapped_dict)
    cost_diff = round(new_cps - orig_cps, 2)

    if cost_diff > 0.02:
        diff_badge = f'<span style="background-color: #fee2e2; color: #991b1b; padding: 2px 7px; border-radius: 4px; font-weight: 700; font-size: 0.8rem;">+${cost_diff:.2f}/serving</span>'
    elif cost_diff < -0.02:
        diff_badge = f'<span style="background-color: #dcfce7; color: #166534; padding: 2px 7px; border-radius: 4px; font-weight: 700; font-size: 0.8rem;">-${abs(cost_diff):.2f}/serving (Cheaper!)</span>'
    else:
        diff_badge = '<span style="background-color: #f1f5f9; color: #475569; padding: 2px 7px; border-radius: 4px; font-weight: 600; font-size: 0.8rem;">Same cost</span>'

    rep_st_c = STATUS_COLORS.get(replacement_food["status"], {"bg": "#dcfce7", "text": "#166534", "label": replacement_food["status"].upper()})
    rep_cost_str = f"${replacement_food.get('cost_per_lb', 0):.2f}/lb • ${replacement_food.get('cost_per_kg', 0):.2f}/kg"

    st.markdown(
        f'<div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px 16px; margin: 12px 0 16px 0; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px;">'
        f'<div><b>Swap:</b> <code style="color: #64748b;">{html.escape(selected_ing)}</code> &nbsp;➔&nbsp; '
        f'<b style="color: #0f172a;">{html.escape(replacement_food["name"])}</b> '
        f'<span style="background-color: {rep_st_c["bg"]}; color: {rep_st_c["text"]}; padding: 1px 6px; border-radius: 4px; font-size: 0.74rem; font-weight: 700;">{rep_st_c["label"]}</span> '
        f'<span style="color: #64748b; font-size: 0.84rem;">({rep_cost_str})</span></div>'
        f'<div><b>Calculated cost per serving:</b> <b>${new_cps:.2f}</b> {diff_badge} '
        f'<span style="color: #64748b; font-size: 0.82rem;">(orig: ${orig_cps:.2f})</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    parsed_swapped, errors = parse_yaml_text(yaml_output)

    if errors:
        st.error("Generated recipe failed schema validation:")
        for err in errors:
            st.markdown(f"- {err}")
        return

    st.success(f"Recipe YAML schema verified and valid! Calculated cost: **${new_cps:.2f}/serving** (${new_total:.2f} total).")

    prev_tab, yaml_tab = st.tabs(["Recipe Preview", "Generated YAML Code"])
    with prev_tab:
        with st.container(border=True):
            render_recipe(parsed_swapped)

    with yaml_tab:
        st.code(yaml_output, language="yaml")

    c_dl, c_sv = st.columns([1, 1])
    c_dl.download_button(
        "📥 Download Recipe YAML",
        data=yaml_output,
        file_name=f"{parsed_swapped.id}.yaml",
        mime="text/yaml",
        key=f"adv_download_btn_{preset_choice}",
    )

    existing_slugs = {p.stem for p in RECIPE_DIR.glob("*.yaml")}
    if parsed_swapped.id in existing_slugs:
        c_sv.warning(f"A recipe file named '{parsed_swapped.id}.yaml' already exists. Change Recipe ID to save as a new recipe.")
    else:
        if c_sv.button("💾 Save to recipes/ folder (local use)", key=f"adv_save_local_btn_{preset_choice}"):
            try:
                (RECIPE_DIR / f"{parsed_swapped.id}.yaml").write_text(yaml_output, encoding="utf-8")
                recipes_cached.clear()
                st.success(f"Saved recipes/{parsed_swapped.id}.yaml! Check the Browse Recipes tab.")
            except OSError as exc:
                st.error(f"Could not save ({exc}). Download the file and place it in recipes/ instead.")


page_advanced_recipes = page_experimental_replacer


def page_plan():
    st.title("Sample 3-day meal plan")
    st.write(
        "This plan mixes the recipes with realistic campus options. Choose "
        "made-to-order or freshly prepared items in the dining hall. "
        "*[VERIFY what is available at your dining hall and market.]*"
    )
    recipes, _ = recipes_cached()
    by_id = {r.id: r for r in recipes}
    table = []
    for day in load_meal_plan():
        row = {"Day": day["day"]}
        for meal, entry in day["meals"].items():
            if "recipe" in entry:
                r = by_id.get(entry["recipe"])
                row[meal] = r.title if r else f"(missing recipe: {entry['recipe']})"
            else:
                row[meal] = entry.get("text", "")
        table.append(row)
    st.table(table)
    st.caption("Edit data/meal_plan.yaml to change this plan.")


def page_checklists():
    st.title("Checklists and template")
    cl = load_checklists()
    st.header("Shopping checklist")
    for i, item in enumerate(cl["shopping"]):
        st.checkbox(item, key=f"shop{i}")
    st.header("Meal-prep checklist")
    for i, item in enumerate(cl["meal_prep"]):
        st.checkbox(item, key=f"prep{i}")
    st.header("Talking to dining staff or a roommate")
    st.write("Copy, edit, and use this as a message or a note to hand over.")
    text = (ROOT / "content" / "template.md").read_text(encoding="utf-8")
    st.text_area("Template (select all and copy)", text, height=320)


def page_add():
    st.title("Add a recipe")
    st.write(
        "Recipes are YAML files in the `recipes/` folder. You can write one by hand "
        "(copy `recipes/_template.yaml`), paste or upload one below to check it, or "
        "fill in the form to generate one."
    )
    tab_form, tab_paste = st.tabs(["Fill in a form", "Paste or upload YAML"])

    with tab_form:
        with st.form("recipe_form"):
            title = st.text_input("Title")
            rid = st.text_input("ID (letters, numbers, hyphens)", help="Also the file name.")
            category = st.selectbox("Category", ["basic", "advanced"], help="Basic for standard starter recipes; Advanced for adapted recipes with alternates.")
            desc = st.text_input("Short description (optional)")
            c1, c2, c3, c4 = st.columns(4)
            servings = c1.number_input("Servings", 1, 20, 1)
            prep = c2.number_input("Prep min", 0, 240, 10)
            cook = c3.number_input("Cook min", 0, 240, 20)
            cost = c4.number_input("Cost / serving ($)", 0.0, 50.0, 2.0, 0.25)
            equip = st.text_area("Equipment (one per line)")
            ings = st.text_area("Ingredients (one per line)")
            steps = st.text_area("Method steps (one per line)")
            storage = st.text_input("Storage notes")
            tags = st.text_input("Tags (comma-separated, optional)")
            notes = st.text_input("Notes (optional)")
            go = st.form_submit_button("Generate YAML")
        if go:
            lines = lambda s: [x.strip() for x in s.splitlines() if x.strip()]
            data = {
                "id": rid.strip(),
                "title": title.strip(),
                "category": category,
                "servings": int(servings),
                "prep_minutes": int(prep),
                "cook_minutes": int(cook),
                "cost_per_serving": float(cost),
                "equipment": lines(equip),
                "ingredients": lines(ings),
                "method": lines(steps),
                "storage": storage.strip(),
                "verified": False,
            }
            if desc.strip():
                data["description"] = desc.strip()
            if tags.strip():
                data["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
            if notes.strip():
                data["notes"] = notes.strip()
            st.session_state["generated"] = to_yaml(data)
        if "generated" in st.session_state:
            _validate_and_offer(st.session_state["generated"])

    with tab_paste:
        up = st.file_uploader("Upload a .yaml file", type=["yaml", "yml"])
        text = up.getvalue().decode("utf-8") if up else ""
        text = st.text_area("Or paste YAML here", text, height=300)
        if text.strip():
            _validate_and_offer(text, key="paste")


def _validate_and_offer(text: str, key: str = "gen") -> None:
    recipe, errs = parse_yaml_text(text)
    st.code(text, language="yaml")
    if errs:
        st.error("This recipe has problems:")
        st.markdown("\n".join(f"- {e}" for e in errs))
        return
    st.success("Valid recipe. Preview below.")
    render_recipe(recipe)
    existing = {p.stem for p in RECIPE_DIR.glob("*.yaml")}
    st.download_button(
        "Download YAML file", text, file_name=f"{recipe.id}.yaml",
        mime="text/yaml", key=f"dl-{key}",
    )
    if recipe.id in existing:
        st.warning(f"A file named {recipe.id}.yaml already exists, so saving is disabled.")
    elif st.button("Save to recipes folder (local use)", key=f"save-{key}"):
        try:
            (RECIPE_DIR / f"{recipe.id}.yaml").write_text(text, encoding="utf-8")
            recipes_cached.clear()
            st.success(f"Saved recipes/{recipe.id}.yaml. Check the Recipes page.")
        except OSError as exc:
            st.error(f"Could not save ({exc}). Download the file and add it to recipes/ instead.")


def page_resources():
    st.title("Resources and sources")
    md("resources.md")
    disclaimer()


pages = [
    st.Page(page_home, title="Home", url_path="home", default=True),
    st.Page(page_food, title="Food Reference", url_path="food"),
    st.Page(page_dining, title="Campus Dining", url_path="dining"),
    st.Page(page_cheap, title="Cheap Cooking", url_path="cheap-cooking"),
    st.Page(page_recipes, title="Recipes", url_path="recipes"),
    st.Page(page_plan, title="Meal Plan", url_path="meal-plan"),
    st.Page(page_checklists, title="Checklists and Template", url_path="checklists"),
    st.Page(page_add, title="Add a Recipe", url_path="add-recipe"),
    st.Page(page_resources, title="Resources", url_path="resources"),
]
st.navigation(pages).run()
