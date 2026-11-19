"""Credits and Open Source Acknowledgments page module."""
from __future__ import annotations

import streamlit as st

from ui.common import md, render_gt_header


def page_credits() -> None:
    """Render the Credits and Open Source Acknowledgments page."""
    render_gt_header("credits")
    st.title("Credits & Acknowledgments")
    md("credits.md")
