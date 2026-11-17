"""Checklists and Template page module."""
from __future__ import annotations

import streamlit as st

from lib.content import load_checklists
from ui.common import ROOT


def page_checklists() -> None:
    """Render the shopping checklist, meal prep checklist, and communication template."""
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
