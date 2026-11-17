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

st.set_page_config(page_title=TITLE, page_icon="🥣", layout="centered")

pages = [
    st.Page(page_home, title="Home", url_path="home", default=True),
    st.Page(page_food, title="Food Reference", url_path="food"),
    st.Page(page_dining, title="Campus Dining", url_path="dining"),
    st.Page(page_cheap, title="Cheap Cooking", url_path="cheap-cooking"),
    st.Page(page_recipes, title="Recipes", url_path="recipes"),
    st.Page(page_plan, title="Meal Plan", url_path="meal-plan"),
    st.Page(page_checklists, title="Checklists and Template", url_path="checklists"),
    st.Page(page_add, title="Add a Recipe", url_path="add-recipe"),
    st.Page(page_resources, title="Resources", url_path="resources"),
]

st.navigation(pages).run()
