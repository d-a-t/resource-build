"""Resources and Sources page module."""
from __future__ import annotations

import streamlit as st

from ui.common import disclaimer, md


def page_resources() -> None:
    """Render the Resources and sources page."""
    st.title("Resources and sources")
    md("resources.md")
    disclaimer()
