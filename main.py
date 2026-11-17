"""Eating Well on Campus with Histamine Intolerance: a Streamlit toolkit.

Run locally:  streamlit run main.py
Add recipes:  drop a YAML file into recipes/ (see README.md) or use the
              "Add a recipe" page.
"""
from __future__ import annotations

from pathlib import Path
import streamlit as st

from ui import (
    TITLE,
    cached_nutrislice_menu,
    disclaimer,
    fmt_cost,
    md,
    page_add,
    page_advanced_recipes,
    page_cheap,
    page_checklists,
    page_dining,
    page_experimental_replacer,
    page_food,
    page_home,
    page_plan,
    page_recipes,
    page_resources,
    recipes_cached,
    render_recipe,
    safe_get_alternates,
)

ROOT = Path(__file__).parent

st.set_page_config(
    page_title=TITLE,
    page_icon="🐝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Georgia Tech Student Navigation Sidebar & Accessibility Hub
with st.sidebar:
    st.markdown(
        """
        <div role="region" aria-label="Georgia Tech Student Hub"
             style="background: linear-gradient(135deg, #003057 0%, #002244 100%);
                    border-left: 5px solid #b3a369; padding: 14px 16px; border-radius: 6px;
                    margin-bottom: 16px; color: #ffffff; box-shadow: 0 2px 6px rgba(0,48,87,0.2);">
            <div style="font-weight: 800; font-size: 1.05rem; color: #ffffff; display: flex; align-items: center; gap: 8px;">
                <span aria-hidden="true">🐝</span> GT Yellow Jacket Hub
            </div>
            <div style="font-size: 0.82rem; color: #f1f5f9; margin-top: 5px; line-height: 1.4;">
                Low-histamine nutrition toolkit for Georgia Tech dining halls, dorm life, and disability advocacy.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("🏛️ Campus Dining Halls", expanded=True):
        st.markdown(
            "- [Brittain Dining Hall](https://techdining.nutrislice.com/menu/brittain)\n"
            "- [North Ave Dining Hall](https://techdining.nutrislice.com/menu/north-ave-dining-hall)\n"
            "- [West Village Dining](https://techdining.nutrislice.com/menu/west-village)\n"
            "- [Tech Dining Dietitian & Allergen Info](https://dining.gatech.edu/)"
        )
    with st.expander("🏥 GT Health & Accommodations", expanded=False):
        st.markdown(
            "- [Office of Disability Services (ADAPTS)](https://disabilityservices.gatech.edu/) *(Smithgall 220)*\n"
            "- [Stamps Health Services](https://health.gatech.edu/) *(740 Ferst Dr)*\n"
            "- [Klemis Kitchen (Food Assistance)](https://studentlife.gatech.edu/klemis-kitchen)\n"
            "- [CARE & Campus Mental Health](https://care.gatech.edu/)"
        )
    with st.expander("♿ Accessibility Conformance", expanded=False):
        st.markdown(
            "**Conformance Target:** WCAG 2.1 Level AAA  \n"
            "Engineered to conform with WCAG 2.1 Level AAA and Section 508 standards: "
            "contrast ratios of 7:1+, keyboard focus visibility, ARIA landmarks, and bypass blocks."
        )

pages = [
    st.Page(page_home, title="Home", icon="🐝", url_path="home", default=True),
    st.Page(page_food, title="Food Reference", icon="📋", url_path="food"),
    st.Page(page_dining, title="Campus Dining", icon="🍽️", url_path="dining"),
    st.Page(page_cheap, title="Cheap Cooking", icon="🍳", url_path="cheap-cooking"),
    st.Page(page_recipes, title="Recipes", icon="🥣", url_path="recipes"),
    st.Page(page_plan, title="Meal Plan", icon="📅", url_path="meal-plan"),
    st.Page(page_checklists, title="Checklists & Script", icon="✅", url_path="checklists"),
    st.Page(page_add, title="Add a Recipe", icon="➕", url_path="add-recipe"),
    st.Page(page_resources, title="Resources", icon="📚", url_path="resources"),
]

st.navigation(pages).run()
