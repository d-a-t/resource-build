"""Eating Well on Campus with Histamine Intolerance: a Streamlit toolkit.

Run locally:  streamlit run main.py
Add recipes:  drop a YAML file into recipes/ (see README.md) or use the
              "Add a recipe" page.
"""
from pathlib import Path

import streamlit as st

from lib.content import (
    filter_food_items,
    get_all_attributes,
    get_all_food_items,
    get_attribute_categories,
    get_attributes_for_category,
    get_food_groups,
    get_food_reference_table_rows,
    get_food_subgroups,
    load_checklists,
    load_food_reference,
    load_meal_plan,
)
from lib.recipes import RECIPE_DIR, Recipe, load_all, parse_yaml_text, to_yaml

ROOT = Path(__file__).parent
TITLE = "Eating Well on Campus with Histamine Intolerance"

st.set_page_config(page_title=TITLE, page_icon="🥣", layout="centered")


def md(name: str) -> None:
    st.markdown((ROOT / "content" / name).read_text(encoding="utf-8"))


def disclaimer() -> None:
    with st.container(border=True):
        md("disclaimer.md")


@st.cache_data(ttl=5)
def recipes_cached():
    return load_all()


def fmt_cost(v: float) -> str:
    return f"about ${v:.2f}"


def render_recipe(r: Recipe, level_heading: bool = True) -> None:
    st.subheader(r.title)
    if r.description:
        st.write(r.description)
    if not r.verified:
        st.caption("Draft: cost and food-safety details not yet verified.")
    st.markdown(
        f"**Servings:** {r.servings}  \n"
        f"**Time:** {r.prep_minutes} min prep, {r.cook_minutes} min cook  \n"
        f"**Estimated cost per serving:** {fmt_cost(r.cost_per_serving)}  \n"
        f"**Equipment:** {', '.join(r.equipment)}  \n"
        f"**Storage:** {r.storage}"
    )
    st.markdown("**Ingredients**")
    st.markdown("\n".join(f"- {i}" for i in r.ingredients))
    st.markdown("**Method**")
    st.markdown("\n".join(f"{n}. {s}" for n, s in enumerate(r.method, 1)))
    if r.notes:
        st.markdown(f"**Note:** {r.notes}")
    if r.tags:
        st.caption("Tags: " + ", ".join(r.tags))


# ---------------------------------------------------------------- pages
def page_home():
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


def page_food():
    st.title("Food reference")
    st.write(
        "Each column has a text label, so the table does not depend on color. "
        "Lists vary by source and by person. This is a starting point "
        "*[VERIFY every row against the SIGHI food compatibility list]*. "
        "Freshness matters as much as the food itself."
    )

    all_groups = get_food_groups()
    all_attrs = get_all_attributes()

    q = st.text_input(
        "Search for a food, attribute, or note (e.g., starches, root veggies, tart, savory, chicken, tomato)",
        placeholder="Type to search foods, attributes, or notes...",
    )

    c1, c2, c3 = st.columns(3)
    selected_group = c1.selectbox("Food group", ["All"] + all_groups)
    available_subgroups = get_food_subgroups(None if selected_group == "All" else selected_group)
    selected_subgroup = c2.selectbox("Subgroup", ["All"] + available_subgroups)
    selected_statuses = c3.multiselect(
        "Tolerance level",
        options=["safer", "caution", "avoid"],
        default=["safer", "caution", "avoid"],
        format_func=lambda s: {
            "safer": "SAFER (usually tolerated)",
            "caution": "CAUTION (test slowly)",
            "avoid": "AVOID (problematic)",
        }.get(s, s.upper()),
    )

    # Organized attribute filtering by category
    attr_categories = ["All Categories"] + get_attribute_categories()
    a_col1, a_col2 = st.columns([1, 2])
    selected_attr_cat = a_col1.selectbox("Attribute category", attr_categories)

    category_attrs = get_attributes_for_category(selected_attr_cat)
    # Ensure active selections stay in options so category changes don't drop them
    current_selected = st.session_state.get("active_attrs", [])
    combined_options = sorted(set(category_attrs) | set(current_selected))

    selected_attrs = a_col2.multiselect(
        "Filter by attribute",
        options=combined_options,
        default=current_selected,
        key="active_attrs",
        help="Select attributes (e.g. starches, root veggies, tart, savory) to narrow matching foods.",
    )

    matched_items = filter_food_items(
        group_filter=selected_group,
        subgroup_filter=selected_subgroup,
        status_filters=selected_statuses,
        attribute_filters=selected_attrs,
        query=q,
    )

    all_total = len(get_all_food_items())
    st.caption(
        f"Showing **{len(matched_items)}** of **{all_total}** foods "
        f"across **{len({it['subgroup'] for it in matched_items})}** subgroup(s)."
    )

    if not matched_items:
        st.info("No matching foods found. Try adjusting your search or clearing filters.")
    else:
        tab_grouped, tab_dir = st.tabs(["Grouped Table", "Ingredient Directory"])

        with tab_grouped:
            rows = get_food_reference_table_rows(matched_items, include_attributes=False)
            st.table(rows)

        with tab_dir:
            dir_data = [
                {
                    "Ingredient": it["name"],
                    "Food Group": it["group"],
                    "Subgroup": it["subgroup"],
                    "Tolerance": {
                        "safer": "SAFER",
                        "caution": "CAUTION",
                        "avoid": "AVOID",
                    }.get(it["status"], it["status"].upper()),
                    "Attributes": ", ".join(it.get("attributes", [])),
                    "Notes": it.get("notes", "") or "—",
                }
                for it in matched_items
            ]
            st.dataframe(dir_data, use_container_width=True, hide_index=True)

    st.markdown(
        "**Rule of thumb:** cook it fresh, eat it soon, and freeze leftover portions "
        "right after cooking instead of refrigerating them for days."
    )
    disclaimer()


def page_dining():
    st.title("Navigating campus dining")
    md("dining.md")


def page_cheap():
    st.title("Cheap cooking in a small kitchen")
    md("cheap_cooking.md")


def page_recipes():
    st.title("Recipes")
    recipes, problems = recipes_cached()
    if problems:
        with st.expander(f"{len(problems)} recipe file(s) have problems and are hidden"):
            for fname, errs in problems.items():
                st.markdown(f"**{fname}**")
                st.markdown("\n".join(f"- {e}" for e in errs))
    if not recipes:
        st.write("No recipes yet. Add one on the Add a Recipe page.")
        return
    st.write(
        "Costs per serving are rough estimates and need updating with real receipts. "
        "Storage means freezing portions right after cooking unless noted."
    )
    all_equipment = sorted({e for r in recipes for e in r.equipment})
    all_tags = sorted({t for r in recipes for t in r.tags})
    c1, c2 = st.columns(2)
    equip = c1.multiselect("I have (show recipes that need only these)", all_equipment)
    tags = c2.multiselect("Tags (show recipes with any of these)", all_tags)
    c3, c4 = st.columns(2)
    max_cost = c3.slider("Max cost per serving ($)", 0.0, 10.0, 10.0, 0.25)
    max_time = c4.slider("Max total minutes", 5, 120, 120, 5)

    def ok(r: Recipe) -> bool:
        if equip and not set(r.equipment) <= set(equip):
            return False
        if tags and not set(tags) & set(r.tags):
            return False
        return r.cost_per_serving <= max_cost and r.total_minutes <= max_time

    shown = [r for r in recipes if ok(r)]
    st.write(f"Showing {len(shown)} of {len(recipes)} recipes.")
    for r in shown:
        with st.container(border=True):
            render_recipe(r)


def page_plan():
    st.title("Sample 3-day meal plan")
    st.write(
        "This plan mixes the recipes with realistic campus options. Choose "
        "made-to-order or freshly prepared items in the dining hall. "
        "*[VERIFY what is available at your dining hall and market.]*"
    )
    recipes, _ = recipes_cached()
    by_id = {r.id: r for r in recipes}
    table = []
    for day in load_meal_plan():
        row = {"Day": day["day"]}
        for meal, entry in day["meals"].items():
            if "recipe" in entry:
                r = by_id.get(entry["recipe"])
                row[meal] = r.title if r else f"(missing recipe: {entry['recipe']})"
            else:
                row[meal] = entry.get("text", "")
        table.append(row)
    st.table(table)
    st.caption("Edit data/meal_plan.yaml to change this plan.")


def page_checklists():
    st.title("Checklists and template")
    cl = load_checklists()
    st.header("Shopping checklist")
    for i, item in enumerate(cl["shopping"]):
        st.checkbox(item, key=f"shop{i}")
    st.header("Meal-prep checklist")
    for i, item in enumerate(cl["meal_prep"]):
        st.checkbox(item, key=f"prep{i}")
    st.header("Talking to dining staff or a roommate")
    st.write("Copy, edit, and use this as a message or a note to hand over.")
    text = (ROOT / "content" / "template.md").read_text(encoding="utf-8")
    st.text_area("Template (select all and copy)", text, height=320)


def page_add():
    st.title("Add a recipe")
    st.write(
        "Recipes are YAML files in the `recipes/` folder. You can write one by hand "
        "(copy `recipes/_template.yaml`), paste or upload one below to check it, or "
        "fill in the form to generate one."
    )
    tab_form, tab_paste = st.tabs(["Fill in a form", "Paste or upload YAML"])

    with tab_form:
        with st.form("recipe_form"):
            title = st.text_input("Title")
            rid = st.text_input("ID (letters, numbers, hyphens)", help="Also the file name.")
            desc = st.text_input("Short description (optional)")
            c1, c2, c3, c4 = st.columns(4)
            servings = c1.number_input("Servings", 1, 20, 1)
            prep = c2.number_input("Prep min", 0, 240, 10)
            cook = c3.number_input("Cook min", 0, 240, 20)
            cost = c4.number_input("Cost / serving ($)", 0.0, 50.0, 2.0, 0.25)
            equip = st.text_area("Equipment (one per line)")
            ings = st.text_area("Ingredients (one per line)")
            steps = st.text_area("Method steps (one per line)")
            storage = st.text_input("Storage notes")
            tags = st.text_input("Tags (comma-separated, optional)")
            notes = st.text_input("Notes (optional)")
            go = st.form_submit_button("Generate YAML")
        if go:
            lines = lambda s: [x.strip() for x in s.splitlines() if x.strip()]
            data = {
                "id": rid.strip(),
                "title": title.strip(),
                "servings": int(servings),
                "prep_minutes": int(prep),
                "cook_minutes": int(cook),
                "cost_per_serving": float(cost),
                "equipment": lines(equip),
                "ingredients": lines(ings),
                "method": lines(steps),
                "storage": storage.strip(),
                "verified": False,
            }
            if desc.strip():
                data["description"] = desc.strip()
            if tags.strip():
                data["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
            if notes.strip():
                data["notes"] = notes.strip()
            st.session_state["generated"] = to_yaml(data)
        if "generated" in st.session_state:
            _validate_and_offer(st.session_state["generated"])

    with tab_paste:
        up = st.file_uploader("Upload a .yaml file", type=["yaml", "yml"])
        text = up.getvalue().decode("utf-8") if up else ""
        text = st.text_area("Or paste YAML here", text, height=300)
        if text.strip():
            _validate_and_offer(text, key="paste")


def _validate_and_offer(text: str, key: str = "gen") -> None:
    recipe, errs = parse_yaml_text(text)
    st.code(text, language="yaml")
    if errs:
        st.error("This recipe has problems:")
        st.markdown("\n".join(f"- {e}" for e in errs))
        return
    st.success("Valid recipe. Preview below.")
    render_recipe(recipe)
    existing = {p.stem for p in RECIPE_DIR.glob("*.yaml")}
    st.download_button(
        "Download YAML file", text, file_name=f"{recipe.id}.yaml",
        mime="text/yaml", key=f"dl-{key}",
    )
    if recipe.id in existing:
        st.warning(f"A file named {recipe.id}.yaml already exists, so saving is disabled.")
    elif st.button("Save to recipes folder (local use)", key=f"save-{key}"):
        try:
            (RECIPE_DIR / f"{recipe.id}.yaml").write_text(text, encoding="utf-8")
            recipes_cached.clear()
            st.success(f"Saved recipes/{recipe.id}.yaml. Check the Recipes page.")
        except OSError as exc:
            st.error(f"Could not save ({exc}). Download the file and add it to recipes/ instead.")


def page_resources():
    st.title("Resources and sources")
    md("resources.md")
    disclaimer()


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
