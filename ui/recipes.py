"""Recipes and Cheap Cooking pages."""
from __future__ import annotations

import streamlit as st

from lib.recipes import Recipe, calculate_recipe_cost
from ui.common import md, recipes_cached, render_recipe
from ui.replacer import page_experimental_replacer


def page_cheap() -> None:
    """Render the Cheap Cooking in a small kitchen page."""
    st.title("Cheap cooking in a small kitchen")
    md("cheap_cooking.md")


def page_recipes() -> None:
    """Render the main Recipes page with catalog browsing and the Experimental Replacer."""
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
