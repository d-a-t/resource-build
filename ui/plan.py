"""Meal Plan page module."""
from __future__ import annotations

import streamlit as st

from lib.content import load_meal_plan
from ui.common import recipes_cached


def page_plan() -> None:
    """Render the sample 3-day meal plan."""
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
