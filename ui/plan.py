"""Meal Plan page module."""
from __future__ import annotations

import streamlit as st

from lib.content import load_meal_plan
from ui.common import recipes_cached, render_gt_header


def page_plan() -> None:
    """Render the sample 3-day meal plan for Georgia Tech students."""
    render_gt_header("meal-plan")
    st.title("Sample 3-Day Georgia Tech Meal Plan")
    st.write(
        "This sample plan balances budget-friendly dorm meal prep with realistic Georgia Tech dining hall options "
        "(Brittain, North Ave, and West Village). Prioritize made-to-order stations or freshly prepared batches."
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
    st.caption("Plan tailored for Georgia Tech dining halls and dorm microwave/rice cooker meal prep. Configured in `data/meal_plan.yaml`.")
