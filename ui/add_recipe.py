"""Add a Recipe page module with form generation and YAML validation."""
from __future__ import annotations

import streamlit as st

from lib.recipes import RECIPE_DIR, parse_yaml_text, to_yaml
from ui.common import recipes_cached, render_gt_header, render_recipe


def _validate_and_offer(text: str, key: str = "gen") -> None:
    """Validate recipe YAML text and offer instant preview, download, and local save."""
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
        "Download YAML file",
        text,
        file_name=f"{recipe.id}.yaml",
        mime="text/yaml",
        key=f"dl-{key}",
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


def page_add() -> None:
    """Render the Add a Recipe form and YAML upload page."""
    render_gt_header("add-recipe")
    st.title("Contribute a Low-Histamine Recipe")
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
            category = st.selectbox("Category", ["basic", "advanced"], help="Basic for standard starter recipes; Advanced for adapted recipes with alternates.")
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
                "category": category,
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
