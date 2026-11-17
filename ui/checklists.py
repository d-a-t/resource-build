"""Checklists and Template page module."""
from __future__ import annotations

import streamlit as st

from lib.content import load_checklists
from ui.common import ROOT, render_gt_header


def page_checklists() -> None:
    """Render the shopping checklist, meal prep checklist, and communication template."""
    render_gt_header("checklists")
    st.title("Student Checklists & Communication Scripts")
    cl = load_checklists()

    c1, c2 = st.columns(2)
    with c1:
        st.header("🛒 Atlanta Student Shopping Checklist")
        st.caption("Staples for grocery runs to Atlantic Station Publix, Midtown Trader Joe's, or Howell Mill Kroger.")
        for i, item in enumerate(cl["shopping"]):
            st.checkbox(item, key=f"shop{i}")

    with c2:
        st.header("🍱 Dorm & Apartment Meal-Prep Rules")
        st.caption("Safety protocols to minimize dietary histamine accumulation in campus living.")
        for i, item in enumerate(cl["meal_prep"]):
            st.checkbox(item, key=f"prep{i}")

    st.markdown("---")
    st.header("🗣️ Talking to Dining Staff or Roommates")
    st.write(
        "Self-advocacy scripts designed for **Brittain, North Ave, and West Village** staff, "
        "as well as shared campus apartment roommates."
    )
    text = (ROOT / "content" / "template.md").read_text(encoding="utf-8")
    st.text_area("Copyable Communication Scripts (Select All to Copy)", text, height=360, help="Copy and save to your phone notes or print to hand over.")
