"""Home page module tailored for Georgia Tech students."""
from __future__ import annotations

import streamlit as st

from ui.common import TITLE, disclaimer, md, render_gt_header


def page_home() -> None:
    """Render the Home page with Georgia Tech branding and accessibility features."""
    render_gt_header("home")

    st.write(
        "A low-histamine nutrition and dining toolkit designed specifically for **Georgia Tech students**, "
        "campus residents, and the Yellow Jackets who cook, dine, and plan campus events with them."
    )

    # Campus living highlights
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            '<div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-top: 4px solid #003057; border-radius: 6px; padding: 14px; height: 100%;">'
            '<h3 style="margin-top: 0; color: #003057; font-size: 1.05rem;">🏛️ Tech Dining Halls</h3>'
            '<p style="font-size: 0.88rem; color: #1e293b; margin: 0;">'
            'Live daily histamine risk evaluations for <b>Brittain</b>, <b>North Ave Dining Hall</b>, and <b>West Village</b> menus via Nutrislice API.'
            '</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            '<div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-top: 4px solid #b3a369; border-radius: 6px; padding: 14px; height: 100%;">'
            '<h3 style="margin-top: 0; color: #003057; font-size: 1.05rem;">🍳 Dorm & Apartment Hacks</h3>'
            '<p style="font-size: 0.88rem; color: #1e293b; margin: 0;">'
            'Low-cost recipes ($1.50–$3/serving) tested for microwave, rice cooker, and hot plate prep in GT housing, plus mini-fridge freezer management.'
            '</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            '<div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-top: 4px solid #003057; border-radius: 6px; padding: 14px; height: 100%;">'
            '<h3 style="margin-top: 0; color: #003057; font-size: 1.05rem;">♿ Disability Advocacy</h3>'
            '<p style="font-size: 0.88rem; color: #1e293b; margin: 0;">'
            'Self-advocacy scripts, dining staff communication notes, and official GT Office of Disability Services (ADAPTS) accommodation guides.'
            '</p>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    disclaimer()

    st.header("Why this is an access issue on campus")
    md("why_access.md")

    st.header("Explore the toolkit")
    t_c1, t_c2 = st.columns(2)
    with t_c1:
        st.markdown(
            "#### 🍽️ Campus Dining & Nutrition\n"
            "- [**Campus Dining**](/dining): Live Tech Dining menu checker with automated histamine risk categorization (`🟢 SAFER`, `🟡 CAUTION`, `🔴 AVOID`) for Brittain, North Ave, and West Village.\n"
            "- [**Food Reference**](/food): Grouped compatibility directory and searchable database with culinary attributes, pricing per lb/kg, and tolerance levels.\n"
            "- [**Meal Plan**](/meal-plan): Realistic 3-day sample plan mixing Tech Dining made-to-order stations with dorm meal prep."
        )
    with t_c2:
        st.markdown(
            "#### 🥣 Student Cooking & Advocacy\n"
            "- [**Cheap Cooking**](/cheap-cooking): Student budget staples, Atlanta grocery transit (Stinger Gold Route to Atlantic Station Publix), and dorm batch freezing.\n"
            "- [**Recipes Catalog**](/recipes): Low-histamine recipes categorized into **Basic** (starter/dorm) and **Advanced** (experimental replacer) with dynamic costs.\n"
            "- [**Checklists & Script**](/checklists): Printable grocery checklist, safe meal-prep rules, and copyable script for Tech Dining workers and roommates."
        )
