"""Add a Recipe page module with form generation and YAML validation."""
from __future__ import annotations

import html
import streamlit as st

from lib.content import (
    STATUS_COLORS,
    get_all_food_items,
    get_food_groups,
    match_ingredient_to_food,
)
from lib.recipes import RECIPE_DIR, parse_yaml_text, to_yaml
from ui.common import recipes_cached, render_gt_header, render_recipe


def _validate_and_offer(text: str, key: str = "gen") -> None:
    """Validate recipe YAML text and offer instant preview, download, and local save."""
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
        "Download YAML file",
        text,
        file_name=f"{recipe.id}.yaml",
        mime="text/yaml",
        key=f"dl-{key}",
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


def page_add(embedded: bool = False) -> None:
    """Render the Add a Recipe form and YAML upload page or tab."""
    if not embedded:
        render_gt_header("add-recipe")
        st.title("Contribute a Low-Histamine Recipe")
    else:
        st.subheader("➕ Add a New Recipe")

    st.write(
        "Recipes are stored as structured YAML files in the `recipes/` folder. "
        "Use the interactive form below with ingredient search assistance, or paste/upload a YAML file directly."
    )
    tab_form, tab_paste = st.tabs(["📝 Fill in a Form", "📋 Paste or Upload YAML"])

    with tab_form:
        c_t1, c_t2 = st.columns([2, 1])
        with c_t1:
            title = st.text_input("Recipe Title", placeholder="e.g. Rice Cooker Chicken and Sweet Potato", key="add_recipe_title")
        with c_t2:
            rid = st.text_input("Recipe ID (letters, numbers, hyphens)", placeholder="e.g. chicken-sweet-potato-rice", key="add_recipe_id", help="Filename without .yaml extension.")

        c_c1, c_c2 = st.columns([1, 2])
        with c_c1:
            category = st.selectbox(
                "Category",
                ["basic", "advanced"],
                help="Basic: straightforward student/dorm recipes without alternates.\nAdvanced: recipes with interchangeable ingredient alternates.",
                key="add_recipe_category",
            )
        with c_c2:
            desc = st.text_input("Short description (optional)", placeholder="e.g. A fast, dorm-friendly one-pot dinner", key="add_recipe_desc")

        c1, c2, c3, c4 = st.columns(4)
        servings = c1.number_input("Servings", 1, 20, 1, key="add_recipe_servings")
        prep = c2.number_input("Prep minutes", 0, 240, 10, key="add_recipe_prep_min")
        cook = c3.number_input("Cook minutes", 0, 240, 20, key="add_recipe_cook_min")
        cost = c4.number_input("Est. cost / serving ($)", 0.0, 50.0, 2.0, 0.25, key="add_recipe_cost_inp")

        equip = st.text_area("Equipment (one per line)", placeholder="pot\nstove\nknife", key="add_recipe_equip", height=90)

        # -------------------------------------------------------------------------
        # Ingredient Searcher & Assistant
        # -------------------------------------------------------------------------
        st.markdown("#### 🥦 Ingredients (one per line)")
        st.caption(
            "Enter each ingredient with quantity on its own line (e.g. `1 lb chicken breast` or `2 medium sweet potatoes`). "
            "Use the searcher below to find reference foods, check tolerance and prices, and insert them directly."
        )

        all_foods = get_all_food_items()
        all_groups = ["All Groups"] + get_food_groups()

        with st.expander("🔍 Search & Insert Ingredients from Food Reference", expanded=True):
            col_flt, col_srch = st.columns([1, 2])
            with col_flt:
                chosen_group = st.selectbox(
                    "Filter by Food Group",
                    all_groups,
                    key="add_recipe_group_filter",
                    help="Filter available ingredients by food group.",
                )

            filtered_foods = [
                f for f in all_foods
                if chosen_group == "All Groups" or f["group"] == chosen_group
            ]

            with col_srch:
                food_display_map = {
                    f["name"]: f"{f['name']} ({f['status'].upper()}) • ${f.get('cost_per_lb', 0):.2f}/lb • {f['group']}"
                    for f in filtered_foods
                }
                food_names = list(food_display_map.keys())
                selected_food_name = st.selectbox(
                    "Search Ingredient Database",
                    options=food_names,
                    format_func=lambda n: food_display_map.get(n, n),
                    key="add_recipe_search_food",
                    help="Search or select an ingredient from the food reference database.",
                )

            # Selected food preview card
            sel_food = next((f for f in all_foods if f["name"] == selected_food_name), None)
            if sel_food:
                st_c = STATUS_COLORS.get(
                    sel_food["status"],
                    {"bg": "#dcfce7", "border": "#16a34a", "text": "#14532d", "label": sel_food["status"].upper(), "emoji": "🟢"}
                )
                cost_str = f"${sel_food.get('cost_per_lb', 0):.2f}/lb (${sel_food.get('cost_per_kg', 0):.2f}/kg)" if sel_food.get("cost_per_lb") else "Free / negligible"
                attrs_str = ", ".join(sel_food.get("attributes", [])) or "None"
                badge_html = (
                    f'<span role="status" style="background-color: {st_c["bg"]}; border: 1px solid {st_c["border"]}; '
                    f'color: {st_c["text"]}; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.78rem;">'
                    f'{st_c.get("emoji", "")} {st_c["label"]}</span>'
                )
                notes_txt = f" • *{sel_food['notes']}*" if sel_food.get("notes") else ""
                st.markdown(
                    f"<div style='background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 12px; margin-bottom: 8px; font-size: 0.88rem;'>"
                    f"<b>Selected Food:</b> {badge_html} &nbsp;<b>{html.escape(sel_food['name'])}</b> • {cost_str} • Attributes: <code>{html.escape(attrs_str)}</code>{notes_txt}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            q_c1, q_c2, q_c3 = st.columns([1.2, 1.2, 1])
            with q_c1:
                st.text_input(
                    "Quantity / Measure",
                    placeholder="e.g. 1 lb, 2 cups, 1/2 tsp",
                    key="add_recipe_qty_val",
                )
            with q_c2:
                st.text_input(
                    "Prep note (optional)",
                    placeholder="e.g. diced, minced, skinless",
                    key="add_recipe_prep_val",
                )

            def _insert_selected_ingredient():
                q = st.session_state.get("add_recipe_qty_val", "").strip()
                fn = st.session_state.get("add_recipe_search_food", "")
                pr = st.session_state.get("add_recipe_prep_val", "").strip()
                parts = []
                if q:
                    parts.append(q)
                if fn:
                    parts.append(fn)
                if pr:
                    parts.append(f"({pr})" if not pr.startswith("(") else pr)
                new_item = " ".join(parts).strip()
                if new_item:
                    cur = st.session_state.get("recipe_form_ings", "").strip()
                    st.session_state["recipe_form_ings"] = f"{cur}\n{new_item}" if cur else new_item

            with q_c3:
                st.write("&nbsp;")
                st.button("➕ Insert Ingredient", on_click=_insert_selected_ingredient, use_container_width=True)

        if "recipe_form_ings" not in st.session_state:
            st.session_state["recipe_form_ings"] = ""

        ings = st.text_area(
            "Ingredients (one per line)",
            key="recipe_form_ings",
            height=160,
            help="Type ingredients directly or use the searcher above to find and insert them.",
        )

        # Live analysis of typed ingredients
        if ings.strip():
            with st.expander("🔍 Live Ingredients Analysis & Safety Check", expanded=False):
                for line in ings.splitlines():
                    line_str = line.strip()
                    if not line_str:
                        continue
                    matched = match_ingredient_to_food(line_str)
                    if matched:
                        m_st = STATUS_COLORS.get(
                            matched["status"],
                            {"bg": "#dcfce7", "border": "#16a34a", "text": "#14532d", "label": matched["status"].upper(), "emoji": "🟢"}
                        )
                        cost_val = f"${matched['cost_per_lb']:.2f}/lb" if matched.get("cost_per_lb") else ""
                        m_badge = f'<span role="status" style="background-color: {m_st["bg"]}; border: 1px solid {m_st["border"]}; color: {m_st["text"]}; padding: 1px 6px; border-radius: 4px; font-weight: 700; font-size: 0.74rem;">{m_st.get("emoji", "")} {m_st["label"]}</span>'
                        st.markdown(
                            f"- <b>{html.escape(line_str)}</b> &nbsp;➔&nbsp; Matched: *{html.escape(matched['name'])}* {m_badge} &nbsp;<span style='color: #475569; font-size: 0.82rem;'>{cost_val}</span>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"- <b>{html.escape(line_str)}</b> &nbsp;➔&nbsp; <span style='color: #475569; font-size: 0.82rem;'>Custom / uncatalogued ingredient</span>",
                            unsafe_allow_html=True,
                        )

        steps = st.text_area("Method steps (one per line)", placeholder="Rinse and chop vegetables.\nHeat oil in pan.\nCook thoroughly.", key="add_recipe_steps", height=120)
        storage = st.text_input("Storage notes", value="Freeze single portions immediately after cooking.", key="add_recipe_storage")
        tags = st.text_input("Tags (comma-separated, optional)", placeholder="dorm-friendly, microwave, quick", key="add_recipe_tags")
        notes = st.text_input("Notes (optional)", placeholder="Optional tips or safety details", key="add_recipe_notes")

        go = st.button("✨ Generate Recipe YAML", type="primary", use_container_width=True)
        if go:
            lines = lambda s: [x.strip() for x in s.splitlines() if x.strip()]
            if not title.strip():
                st.error("Please provide a recipe title.")
                return
            if not rid.strip():
                st.error("Please provide a recipe ID.")
                return
            if not ings.strip():
                st.error("Please provide at least one ingredient.")
                return
            if not steps.strip():
                st.error("Please provide method steps.")
                return

            data = {
                "id": rid.strip(),
                "title": title.strip(),
                "category": category,
                "servings": int(servings),
                "prep_minutes": int(prep),
                "cook_minutes": int(cook),
                "cost_per_serving": float(cost),
                "equipment": lines(equip) if equip.strip() else ["pot"],
                "ingredients": lines(ings),
                "method": lines(steps),
                "storage": storage.strip() if storage.strip() else "Freeze single portions.",
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
