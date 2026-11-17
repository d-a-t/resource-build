"""Common UI components, helpers, and recipe renderers."""
from __future__ import annotations

import html
from pathlib import Path
import urllib.parse
from typing import Any

import streamlit as st

from lib.content import FOOD_GROUP_COLORS, STATUS_COLORS, match_ingredient_to_food
from lib.recipes import Recipe, calculate_recipe_cost, load_all

ROOT = Path(__file__).resolve().parent.parent
TITLE = "Eating Well on Campus with Histamine Intolerance"


def md(name: str) -> None:
    """Render markdown file from the content/ directory."""
    st.markdown((ROOT / "content" / name).read_text(encoding="utf-8"))


def disclaimer() -> None:
    """Render the standard site medical and dietary disclaimer."""
    with st.container(border=True):
        md("disclaimer.md")


@st.cache_data(ttl=2)
def recipes_cached() -> tuple[list[Recipe], dict[str, list[str]]]:
    """Cache loaded recipes from recipes/ folder."""
    return load_all()


def fmt_cost(v: float) -> str:
    """Format a dollar cost."""
    return f"about ${v:.2f}"


def safe_get_alternates(r: Recipe, ingredient_str: str | None = None) -> list[str]:
    """Safely retrieve alternates from a Recipe object, resilient to cached instances."""
    if hasattr(r, "get_alternates_for") and ingredient_str:
        try:
            return r.get_alternates_for(ingredient_str)
        except Exception:
            pass
    alts = getattr(r, "alternates", None) or {}
    if not ingredient_str:
        if isinstance(alts, dict):
            return list(alts.keys())
        return []
    if isinstance(alts, dict):
        if ingredient_str in alts:
            v = alts[ingredient_str]
            return v if isinstance(v, list) else [v]
        for k, v in alts.items():
            if k.lower() in ingredient_str.lower() or ingredient_str.lower() in k.lower():
                return v if isinstance(v, list) else [v]
    elif isinstance(alts, list):
        res = []
        for it in alts:
            if isinstance(it, dict):
                orig = it.get("original") or it.get("ingredient") or it.get("for") or ""
                if orig and (orig.lower() in ingredient_str.lower() or ingredient_str.lower() in orig.lower()):
                    eq = it.get("equivalent") or it.get("alternate") or it.get("substitute") or ""
                    if eq:
                        res.append(eq)
            elif isinstance(it, str):
                res.append(it)
        return res
    return []


def render_recipe(r: Recipe, level_heading: bool = True) -> None:
    """Render a single recipe card with category badge, live costs, and ingredients."""
    is_adv = getattr(r, "is_advanced", False)
    category_badge = (
        '<span style="background-color: #f5f3ff; border: 1px solid #c4b5fd; color: #5b21b6; '
        'padding: 2px 8px; border-radius: 4px; font-size: 0.76rem; font-weight: 700;">'
        '🟣 ADVANCED RECIPE</span>'
        if is_adv
        else '<span style="background-color: #f0fdf4; border: 1px solid #86efac; color: #166534; '
        'padding: 2px 8px; border-radius: 4px; font-size: 0.76rem; font-weight: 700;">'
        '🟢 BASIC RECIPE</span>'
    )
    st.markdown(f'<div style="margin-bottom: 6px;">{category_badge}</div>', unsafe_allow_html=True)
    st.subheader(r.title)
    if r.description:
        st.write(r.description)
    if not r.verified:
        st.caption("Draft: cost and food-safety details not yet verified.")

    # Dynamically calculate recipe cost from ingredients
    calc_cps, total_cost, breakdown = calculate_recipe_cost(r)
    servings_label = f"{r.servings} serving" if r.servings == 1 else f"{r.servings} servings"

    st.markdown(
        f"**Servings:** {r.servings}  \n"
        f"**Time:** {r.prep_minutes} min prep, {r.cook_minutes} min cook  \n"
        f"**Estimated cost per serving:** **${calc_cps:.2f}** "
        f'<span style="color: #64748b; font-size: 0.88rem;">(calculated: ${total_cost:.2f} total / {servings_label})</span>  \n'
        f"**Equipment:** {', '.join(r.equipment)}  \n"
        f"**Storage:** {r.storage}",
        unsafe_allow_html=True,
    )
    st.markdown("**Ingredients**")
    ing_lines = []
    for i in r.ingredients:
        m = match_ingredient_to_food(i)
        alts = safe_get_alternates(r, i)
        alt_html = ""
        if alts:
            alt_badges = " ".join(
                f'<span style="background-color: #f1f5f9; border: 1px solid #cbd5e1; color: #475569; padding: 1px 6px; border-radius: 4px; font-size: 0.76rem;">{html.escape(a)}</span>'
                for a in alts
            )
            alt_html = f'<br><span style="margin-left: 18px; font-size: 0.78rem; color: #64748b;">⇄ <b>YAML Alternates:</b> {alt_badges}</span>'

        if m:
            st_c = STATUS_COLORS.get(m["status"], {"bg": "#dcfce7", "text": "#166534", "label": m["status"].upper()})
            cost_parts = []
            if m.get("cost_per_lb") is not None:
                cost_parts.append(f"${m['cost_per_lb']:.2f}/lb")
            if m.get("cost_per_kg") is not None:
                cost_parts.append(f"${m['cost_per_kg']:.2f}/kg")
            cost_str = " • ".join(cost_parts)
            cost_display = f'<span style="color: #64748b; font-size: 0.84rem;">({cost_str})</span>' if cost_str else ""
            encoded_name = urllib.parse.quote(m["name"])
            link_html = (
                f'<a href="/food?food={encoded_name}&tab=dir" target="_self" '
                f'title="View {html.escape(m["name"])} in Food Reference" '
                f'style="color: inherit; text-decoration: underline; text-decoration-color: #cbd5e1; font-weight: 500;">{html.escape(i)}</a>'
            )
            badge_html = f'<span style="background-color: {st_c["bg"]}; color: {st_c["text"]}; padding: 1px 6px; border-radius: 4px; font-size: 0.74rem; font-weight: 700; margin-left: 5px;">{st_c["label"]}</span>'
            ing_lines.append(f"- {link_html} {badge_html} {cost_display}{alt_html}")
        else:
            ing_lines.append(f"- {html.escape(i)}{alt_html}")
    st.markdown("\n".join(ing_lines), unsafe_allow_html=True)

    with st.expander(f"💰 View calculated cost breakdown (${calc_cps:.2f}/serving)"):
        cost_rows = [
            {
                "Ingredient": item["ingredient"],
                "Matched Food": item["matched_food"],
                "Unit Price": (
                    f"${item['unit_cost_lb']:.2f}/lb (${item['unit_cost_kg']:.2f}/kg)"
                    if item["unit_cost_kg"] > 0
                    else "Free"
                ),
                "Weight / Count": (
                    f"{item['weight_kg']*2.20462:.2f} lb ({item['weight_kg']:.3f} kg)"
                    if item["weight_kg"] > 0
                    else "—"
                ),
                "Est. Cost": f"${item['line_cost']:.2f}",
            }
            for item in breakdown
        ]
        st.dataframe(cost_rows, use_container_width=True, hide_index=True)
        st.caption(
            f"Total calculated cost: ${total_cost:.2f} ÷ {r.servings} serving(s) = "
            f"**${calc_cps:.2f} per serving**."
        )

    st.markdown("**Method**")
    st.markdown("\n".join(f"{n}. {s}" for n, s in enumerate(r.method, 1)))
    if r.notes:
        st.markdown(f"**Note:** {r.notes}")
    if r.tags:
        st.caption("Tags: " + ", ".join(r.tags))
