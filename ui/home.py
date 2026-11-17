"""Home page module."""
from __future__ import annotations

import streamlit as st

from ui.common import TITLE, disclaimer, md


def page_home() -> None:
    """Render the Home page."""
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
