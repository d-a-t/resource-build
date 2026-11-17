# Eating Well on Campus with Histamine Intolerance (Streamlit toolkit)

## Run it
```bash
pip install -r requirements.txt
streamlit run app.py
```
To publish free, push this folder to GitHub and deploy it on Streamlit Community Cloud (main file: `app.py`).

## Project layout
| Path | What it holds |
|---|---|
| `app.py` | The site (pages, filters, Add-a-Recipe tool) |
| `recipes/*.yaml` | One recipe per file. Files starting with `_` are ignored |
| `recipes/_template.yaml` | Copy this to start a new recipe |
| `data/food_reference.yaml` | The safer / caution / avoid table |
| `data/meal_plan.yaml` | The 3-day plan; meals point to recipe ids |
| `data/checklists.yaml` | Shopping and meal-prep checklists |
| `content/*.md` | Prose for each page (edit as plain Markdown) |
| `lib/recipes.py` | Recipe loader and validator |
| `validate_recipes.py` | Command-line check for all recipes and the meal plan |

## Adding a recipe
1. Copy `recipes/_template.yaml` to `recipes/your-recipe-id.yaml` and fill it in.
2. Run `python validate_recipes.py`. It reports missing fields, wrong types, duplicate ids, and unknown recipe ids in the meal plan.
3. Refresh the site. The recipe appears on the Recipes page, with filters for equipment, tags, cost, and time.

Or use the **Add a Recipe** page: fill in a form (or paste/upload YAML), check the preview, then download the file or save it directly when running locally. On a hosted site, saved files do not persist, so download the YAML and commit it to `recipes/`.

### Recipe fields
Required: `id`, `title`, `servings`, `prep_minutes`, `cook_minutes`, `cost_per_serving`, `equipment` (list), `ingredients` (list), `method` (list), `storage`.
Optional: `description`, `tags` (list), `notes`, `verified` (true/false), `source`.

Recipes with `verified: false` show a "Draft" note. Set it to `true` once cost and food safety are checked.

## Accessibility notes
Streamlit controls much of the page markup, so run your own check (keyboard-only navigation, a screen reader, contrast). This app uses real headings, text labels instead of color, and plain tables (`st.table`), which are more screen-reader friendly than interactive grids.
