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
TITLE = "Georgia Tech Student Low-Histamine & Dining Toolkit"
GT_NAVY = "#003057"
GT_GOLD = "#B3A369"
GT_BUZZ_GOLD = "#EAAA00"


def inject_gt_accessibility_css() -> None:
    """Inject Georgia Tech branding and WCAG 2.1 AAA accessible styling."""
    st.markdown(
        """
        <style>
        /* ==========================================================================
           Georgia Tech Yellow Jacket Accessible Theme (WCAG 2.1 AAA Conformance)
           ========================================================================== */

        /* Accessible Skip Link (WCAG 2.4.1 Bypass Blocks) */
        .gt-skip-link {
            position: absolute !important;
            top: -70px !important;
            left: 12px !important;
            background-color: #003057 !important;
            color: #ffffff !important;
            padding: 10px 18px !important;
            z-index: 999999 !important;
            font-weight: 700 !important;
            border-radius: 4px !important;
            border: 2px solid #b3a369 !important;
            text-decoration: underline !important;
            transition: top 0.2s ease-in-out !important;
            font-size: 0.95rem !important;
        }
        .gt-skip-link:focus, .gt-skip-link:focus-visible {
            top: 12px !important;
            outline: 3px solid #b3a369 !important;
            outline-offset: 2px !important;
        }

        /* Keyboard Focus Indicator (WCAG 2.4.7 Focus Visible) */
        *:focus-visible {
            outline: 3px solid #003057 !important;
            outline-offset: 2px !important;
        }

        /* Screen reader utility (WCAG 1.3.1 Info and Relationships) */
        .sr-only {
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            padding: 0 !important;
            margin: -1px !important;
            overflow: hidden !important;
            clip: rect(0, 0, 0, 0) !important;
            white-space: nowrap !important;
            border: 0 !important;
        }

        /* Georgia Tech Header Banner */
        .gt-masthead {
            background: linear-gradient(135deg, #003057 0%, #002244 100%);
            border-bottom: 4px solid #b3a369;
            border-radius: 8px;
            padding: 18px 24px;
            margin-bottom: 24px;
            color: #ffffff;
            box-shadow: 0 2px 10px rgba(0, 48, 87, 0.18);
        }
        .gt-masthead-title {
            color: #ffffff !important;
            font-size: 1.45rem !important;
            font-weight: 800 !important;
            margin: 0 0 6px 0 !important;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .gt-masthead-sub {
            color: #f1f5f9 !important;
            font-size: 0.92rem !important;
            margin: 0 !important;
            line-height: 1.5 !important;
        }
        .gt-pill-gold {
            display: inline-block;
            background-color: #b3a369;
            color: #003057;
            font-weight: 800;
            font-size: 0.72rem;
            padding: 2px 8px;
            border-radius: 4px;
            margin-right: 6px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .gt-pill-wcag {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background-color: #002244;
            border: 1px solid #b3a369;
            color: #f8fafc;
            font-size: 0.76rem;
            padding: 4px 10px;
            border-radius: 4px;
            font-weight: 700;
        }

        /* High-contrast form controls and buttons */
        div[data-testid="stExpander"] {
            border: 1px solid #cbd5e1 !important;
            border-radius: 6px !important;
            background-color: #ffffff !important;
            margin-bottom: 12px !important;
        }
        div[data-testid="stExpander"] summary {
            font-weight: 700 !important;
            color: #0f172a !important;
            font-size: 0.95rem !important;
        }

        /* High contrast accessible links */
        a {
            color: #003057 !important;
            text-decoration: underline !important;
            text-decoration-thickness: 1.5px !important;
            font-weight: 600 !important;
        }
        a:hover {
            color: #002244 !important;
            text-decoration-thickness: 2.5px !important;
        }
        a:focus-visible {
            outline: 3px solid #003057 !important;
            outline-offset: 2px !important;
        }

        /* Base typography line-height for readability (WCAG 1.4.12) */
        p, li {
            line-height: 1.6 !important;
        }
        </style>
        <a href="#main-content" class="gt-skip-link">Skip to main content</a>
        <div id="main-content" tabindex="-1"></div>
        """,
        unsafe_allow_html=True,
    )


def render_gt_header(current_page: str = "") -> None:
    """Render the accessible Georgia Tech Yellow Jacket masthead banner."""
    inject_gt_accessibility_css()
    st.markdown(
        """
        <header role="banner" class="gt-masthead" aria-label="Georgia Tech Student Toolkit Header">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div>
                    <h1 class="gt-masthead-title">
                        <span aria-hidden="true">🐝</span> Georgia Tech Student Low-Histamine & Dining Toolkit
                    </h1>
                    <p class="gt-masthead-sub">
                        <span class="gt-pill-gold">Yellow Jackets</span>
                        Campus Dining (Brittain, North Ave, West Village) • Dorm Cooking • Student Budgeting • Disability Access
                    </p>
                </div>
            </div>
        </header>
        """,
        unsafe_allow_html=True,
    )


def md(name: str) -> None:
    """Render markdown file from the content/ directory."""
    st.markdown((ROOT / "content" / name).read_text(encoding="utf-8"))


def disclaimer() -> None:
    """Render the standard site medical and dietary disclaimer with accessible semantics."""
    with st.container(border=True):
        st.markdown(
            '<div role="note" aria-label="Medical and Dietary Disclaimer">'
            '<h4 style="margin-top: 0; color: #003057; display: flex; align-items: center; gap: 6px;">'
            '<span>⚠️</span> Medical & Dietary Disclaimer</h4>'
            '</div>',
            unsafe_allow_html=True,
        )
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
        '<span role="status" aria-label="Recipe complexity: Advanced recipe with ingredient alternates" '
        'style="background-color: #f3e8ff; border: 1px solid #9333ea; color: #4c1d95; '
        'padding: 3px 10px; border-radius: 4px; font-size: 0.76rem; font-weight: 700;">'
        '🟣 ADVANCED RECIPE</span>'
        if is_adv
        else '<span role="status" aria-label="Recipe complexity: Basic recipe with simple preparation" '
        'style="background-color: #f0fdf4; border: 1px solid #16a34a; color: #14532d; '
        'padding: 3px 10px; border-radius: 4px; font-size: 0.76rem; font-weight: 700;">'
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
        f'<span style="color: #475569; font-size: 0.88rem;">(calculated: ${total_cost:.2f} total / {servings_label})</span>  \n'
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
                f'<span style="background-color: #f8fafc; border: 1px solid #94a3b8; color: #1e293b; padding: 1px 6px; border-radius: 4px; font-size: 0.76rem; font-weight: 500;">{html.escape(a)}</span>'
                for a in alts
            )
            alt_html = f'<br><span style="margin-left: 18px; font-size: 0.78rem; color: #475569;">⇄ <b>YAML Alternates:</b> {alt_badges}</span>'

        if m:
            st_c = STATUS_COLORS.get(m["status"], {"bg": "#dcfce7", "border": "#16a34a", "text": "#14532d", "label": m["status"].upper(), "emoji": "🟢"})
            cost_parts = []
            if m.get("cost_per_lb") is not None:
                cost_parts.append(f"${m['cost_per_lb']:.2f}/lb")
            if m.get("cost_per_kg") is not None:
                cost_parts.append(f"${m['cost_per_kg']:.2f}/kg")
            cost_str = " • ".join(cost_parts)
            cost_display = f'<span style="color: #475569; font-size: 0.84rem;">({cost_str})</span>' if cost_str else ""
            encoded_name = urllib.parse.quote(m["name"])
            link_html = (
                f'<a href="/food?food={encoded_name}&tab=dir" target="_self" '
                f'title="View {html.escape(m["name"])} in Food Reference" '
                f'style="color: #003057; text-decoration: underline; font-weight: 600;">{html.escape(i)}</a>'
            )
            badge_aria = st_c.get("aria_label", f"Tolerance level: {st_c['label']}")
            badge_html = (
                f'<span role="status" aria-label="{html.escape(badge_aria)}" '
                f'style="background-color: {st_c["bg"]}; border: 1px solid {st_c["border"]}; color: {st_c["text"]}; '
                f'padding: 1px 6px; border-radius: 4px; font-size: 0.74rem; font-weight: 700; margin-left: 5px;">'
                f'{st_c.get("emoji", "")} {st_c["label"]}</span>'
            )
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
