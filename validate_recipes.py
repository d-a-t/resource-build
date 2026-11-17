"""Check every recipe file. Run:  python validate_recipes.py
Exit code 1 if anything is wrong, so it can be used in CI."""
import sys

from lib.recipes import load_all
from lib.content import load_meal_plan

recipes, problems = load_all()
ids = {r.id for r in recipes}
for fname, errs in problems.items():
    print(f"[ERROR] {fname}")
    for e in errs:
        print(f"    - {e}")
for day in load_meal_plan():
    for meal, entry in day["meals"].items():
        rid = entry.get("recipe")
        if rid and rid not in ids:
            problems[f"meal_plan:{day['day']}:{meal}"] = [f"Unknown recipe id '{rid}'."]
            print(f"[ERROR] meal plan {day['day']} {meal}: unknown recipe id '{rid}'")
print(f"{len(recipes)} valid recipe(s), {len(problems)} problem file(s).")
sys.exit(1 if problems else 0)
