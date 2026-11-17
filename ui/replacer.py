"""Experimental Replacer lab module for recipe adaptations and ingredient substitutions."""
from __future__ import annotations

import html
import re

import streamlit as st

from lib.content import (
    FOOD_GROUP_COLORS,
    STATUS_COLORS,
    get_all_food_items,
    get_food_groups,
    get_foods_by_attributes,
    match_ingredient_to_food,
    pluralize,
    singularize,
)
from lib.recipes import (
    RECIPE_DIR,
    calculate_recipe_cost,
    parse_yaml_text,
    swap_recipe_ingredient,
)
from ui.common import recipes_cached, render_recipe


def page_experimental_replacer() -> None:
    """Render the Experimental Replacer workbench for swapping ingredients and adapting recipes."""
    st.subheader("🧪 Experimental Replacer")
    recipes, _ = recipes_cached()
    if not recipes:
        st.info("No recipes available to swap. Add one on the Add a Recipe page first.")
        return

    st.markdown(
        "This tool is intended primarily for **experienced cooks** who know how to adjust recipes and cooking times accordingly when swapping ingredients. "
        "Experiment with ingredient replacements to tailor recipes to your personal histamine tolerance, pantry staples, or budget. "
        "Swap ingredients either **using functional attributes** (e.g., matching starches, root vegetables, poultry, or aromatics) "
        "or **by choosing a specific ingredient** directly. The replacer calculates the updated cost per serving and generates a schema-valid recipe YAML."
    )

    EXAMPLE_PRESETS = {
        "— Build custom swap (or select an example below) —": None,
        "🍗 ➔ 🦃 Example 1: Chicken Soup ➔ Turkey & Sweet Potato Soup (Attribute: poultry)": {
            "recipe_id": "one-pot-chicken-potato-soup",
            "old_ing": "1 lb fresh chicken thighs or breasts",
            "mode": "Swap using Attributes",
            "attr": ["poultry"],
            "new_food": "Turkey",
        },
        "🥩 ➔ 🐑 Example 2: Beef Potato Hash ➔ Lamb & Sweet Potato Hash (Attributes: red meat, savory)": {
            "recipe_id": "skillet-beef-potato-hash",
            "old_ing": "1/2 lb fresh ground beef",
            "mode": "Swap using Attributes",
            "attr": ["red meat", "savory"],
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
            "attr": ["starches"],
            "new_food": "Quinoa",
        },
        "🍎 ➔ 🍐 Example 5: Apple Oatmeal ➔ Pear & Blueberry Oatmeal (Attribute: pome fruit)": {
            "recipe_id": "microwave-apple-cinnamon-oatmeal",
            "old_ing": "1/2 apple, diced",
            "mode": "Swap using Attributes",
            "attr": ["pome fruit"],
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
        if not target_attrs:
            st.warning(
                f"No culinary or nutritional attributes are recorded for '{selected_ing}'. "
                "Please choose **Swap by Specified Ingredient** to replace this item.",
                icon="⚠️",
            )
        else:
            attr_options = list(target_attrs)

            default_attrs = []
            if preset_data and preset_data.get("attr"):
                p_attr = preset_data["attr"]
                p_list = p_attr if isinstance(p_attr, list) else [p_attr]
                default_attrs = [a for a in p_list if a in attr_options]
            if not default_attrs and attr_options:
                default_attrs = [attr_options[0]]

            safe_ing_key = re.sub(r"[^a-zA-Z0-9]", "", selected_ing)
            c_att1, c_att2, c_att3 = st.columns([1.5, 0.9, 1.8])
            chosen_attrs = c_att1.multiselect(
                "Attributes to match",
                attr_options,
                default=default_attrs,
                help=f"Select one or more attributes belonging to '{matched_target['name']}': {', '.join(target_attrs)}",
                key=f"adv_attr_choice_{selected_recipe.id}_{safe_ing_key}_{preset_choice}",
            )
            match_mode = "all"
            if len(chosen_attrs) > 1:
                match_rule = c_att1.radio(
                    "Match rule",
                    ["Match ALL selected (AND)", "Match ANY selected (OR)"],
                    horizontal=True,
                    index=0,
                    key=f"adv_attr_rule_{selected_recipe.id}_{safe_ing_key}_{preset_choice}",
                )
                match_mode = "all" if "ALL" in match_rule else "any"

            pref_tol = c_att2.multiselect(
                "Tolerance",
                ["safer", "caution", "avoid"],
                default=["safer"],
                format_func=lambda s: {"safer": "🟢 SAFER", "caution": "🟡 CAUTION", "avoid": "🔴 AVOID"}.get(s, s.upper()),
                key=f"adv_attr_tol_{preset_choice}",
            )

            if not chosen_attrs:
                c_att3.info("Select at least one attribute to match.")
            else:
                raw_candidates = get_foods_by_attributes(chosen_attrs, match_mode=match_mode)
                filtered_candidates = [
                    f
                    for f in raw_candidates
                    if f["status"] in pref_tol
                    and (not matched_target or f["name"].lower() != matched_target["name"].lower())
                ]
                if not filtered_candidates:
                    if match_mode == "all" and len(chosen_attrs) > 1:
                        c_att3.warning(f"No foods found matching ALL {len(chosen_attrs)} selected attributes with selected tolerance. Try 'Match ANY' or broaden tolerance.")
                    else:
                        c_att3.warning("No foods found matching the selected attribute(s) and tolerance.")
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
        suggested_title = f"{selected_recipe.title} (with {clean_new_name.title()})"

    suggested_id = re.sub(r"[^a-z0-9]+", "-", suggested_title.lower()).strip("-")[:40]

    st.markdown("---")
    st.markdown("#### 4. Configure New Recipe Details & Pricing")
    c_meta1, c_meta2 = st.columns([1.5, 1])
    recipe_title_input = c_meta1.text_input("Modified recipe title", value=suggested_title, key=f"adv_title_{selected_recipe.id}_{preset_choice}")
    recipe_id_input = c_meta2.text_input("Recipe ID (filename)", value=suggested_id, key=f"adv_id_{selected_recipe.id}_{preset_choice}")

    # Cost override controls
    c_cost1, c_cost2 = st.columns(2)
    old_kg = matched_target.get("cost_per_kg") if matched_target else None
    new_kg = replacement_food.get("cost_per_kg")

    new_kg_input = c_cost1.number_input(
        f"Custom {clean_new_name} cost ($/kg)",
        value=float(new_kg) if new_kg is not None else 0.0,
        step=0.25,
        format="%.2f",
        key=f"adv_new_kg_{preset_choice}",
    )
    if new_kg_input > 0:
        new_kg = new_kg_input
        c_cost1.caption(f"Equivalent: ${new_kg / 2.20462:.2f}/lb")

    output_mode = st.radio(
        "Recipe generation mode",
        [
            "Direct Adaptation (creates a standalone new recipe with this ingredient replaced)",
            "Base Recipe with Alternate Option (keeps the base ingredients, adds this equivalent under 'alternates:')",
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
        diff_badge = f'<span role="status" style="background-color: #fee2e2; border: 1px solid #dc2626; color: #7f1d1d; padding: 2px 7px; border-radius: 4px; font-weight: 700; font-size: 0.8rem;">+${cost_diff:.2f}/serving</span>'
    elif cost_diff < -0.02:
        diff_badge = f'<span role="status" style="background-color: #dcfce7; border: 1px solid #16a34a; color: #14532d; padding: 2px 7px; border-radius: 4px; font-weight: 700; font-size: 0.8rem;">-${abs(cost_diff):.2f}/serving (Cheaper!)</span>'
    else:
        diff_badge = '<span role="status" style="background-color: #f8fafc; border: 1px solid #94a3b8; color: #1e293b; padding: 2px 7px; border-radius: 4px; font-weight: 600; font-size: 0.8rem;">Same cost</span>'

    rep_st_c = STATUS_COLORS.get(replacement_food["status"], {"bg": "#dcfce7", "border": "#16a34a", "text": "#14532d", "label": replacement_food["status"].upper()})
    rep_cost_str = f"${replacement_food.get('cost_per_lb', 0):.2f}/lb • ${replacement_food.get('cost_per_kg', 0):.2f}/kg"

    st.markdown(
        f'<div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px 16px; margin: 12px 0 16px 0; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px;">'
        f'<div><b>Swap:</b> <code style="color: #475569;">{html.escape(selected_ing)}</code> &nbsp;➔&nbsp; '
        f'<b style="color: #0f172a;">{html.escape(replacement_food["name"])}</b> '
        f'<span role="status" style="background-color: {rep_st_c["bg"]}; border: 1px solid {rep_st_c.get("border", "#16a34a")}; color: {rep_st_c["text"]}; padding: 1px 6px; border-radius: 4px; font-size: 0.74rem; font-weight: 700;">{rep_st_c["label"]}</span> '
        f'<span style="color: #475569; font-size: 0.84rem;">({rep_cost_str})</span></div>'
        f'<div><b>Calculated cost per serving:</b> <b>${new_cps:.2f}</b> {diff_badge} '
        f'<span style="color: #475569; font-size: 0.82rem;">(orig: ${orig_cps:.2f})</span></div>'
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


# Backward-compatible alias
page_advanced_recipes = page_experimental_replacer
