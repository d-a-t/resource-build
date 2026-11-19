"""UI package for Eating Well on Campus with Histamine Intolerance."""
from __future__ import annotations

from ui.common import TITLE, disclaimer, fmt_cost, md, recipes_cached, render_recipe, safe_get_alternates
from ui.home import page_home
from ui.food import page_food
from ui.dining import page_dining, cached_nutrislice_menu
from ui.recipes import page_cheap, page_recipes
from ui.replacer import page_experimental_replacer, page_advanced_recipes
from ui.plan import page_plan
from ui.checklists import page_checklists
from ui.add_recipe import page_add
from ui.credits import page_credits
from ui.resources import page_resources

__all__ = [
    "TITLE",
    "cached_nutrislice_menu",
    "disclaimer",
    "fmt_cost",
    "md",
    "page_add",
    "page_advanced_recipes",
    "page_cheap",
    "page_checklists",
    "page_credits",
    "page_dining",
    "page_experimental_replacer",
    "page_food",
    "page_home",
    "page_plan",
    "page_recipes",
    "page_resources",
    "recipes_cached",
    "render_recipe",
    "safe_get_alternates",
]
