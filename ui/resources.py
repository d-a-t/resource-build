"""Resources and Sources page module."""
from __future__ import annotations

import streamlit as st

from ui.common import disclaimer, md, render_gt_header


def page_resources() -> None:
    """Render the Georgia Tech Campus Resources and scholarly citations page."""
    render_gt_header("resources")
    st.title("Campus Resources & Scholarly Literature")
    md("resources.md")
    st.markdown("---")
    st.info(
        "Looking for project credits, open source libraries, and AI engineering acknowledgments? "
        "Visit the dedicated [Credits page](/credits)."
    )
    disclaimer()
