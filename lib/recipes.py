"""Load and validate recipe YAML files.

Every file in recipes/*.yaml (except names starting with "_") is one recipe.
See recipes/_template.yaml for the schema and README.md for how to add one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

import yaml

from lib.content import (
    convert_cost_kg_to_lbs,
    cost_per_kg_to_cost_per_lb,
    cost_per_lb_to_cost_per_kg,
    match_ingredient_to_food,
    pluralize,
    singularize,
)

ROOT = Path(__file__).resolve().parent.parent
RECIPE_DIR = ROOT / "recipes"

REQUIRED = {
    "id": str,
    "title": str,
    "servings": int,
    "prep_minutes": int,
    "cook_minutes": int,
    "cost_per_serving": (int, float),
    "equipment": list,
    "ingredients": list,
    "method": list,
    "storage": str,
}
OPTIONAL = {
    "description": str,
    "tags": list,
    "notes": str,
    "verified": bool,
    "source": str,
    "alternates": (dict, list),
    "category": str,
}


@dataclass
class Recipe:
    id: str
    title: str
    servings: int
    prep_minutes: int
    cook_minutes: int
    cost_per_serving: float
    equipment: list[str]
    ingredients: list[str]
    method: list[str]
    storage: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    verified: bool = False
    source: str = ""
    alternates: dict[str, list[str]] | list[dict] = field(default_factory=dict)
    category: str = ""

    def __post_init__(self):
        if not hasattr(self, "alternates") or self.alternates is None:
            self.alternates = {}
        if not hasattr(self, "category") or self.category is None:
            self.category = ""

    @property
    def is_advanced(self) -> bool:
        cat = getattr(self, "category", "") or ""
        if cat:
            return cat.strip().lower() == "advanced"
        return ("advanced-swap" in self.tags) or bool(getattr(self, "alternates", None)) or ("advanced" in self.tags)

    @property
    def display_category(self) -> str:
        return "Advanced" if self.is_advanced else "Basic"

    @property
    def total_minutes(self) -> int:
        return self.prep_minutes + self.cook_minutes

    @property
    def calculated_cost(self) -> tuple[float, float, list[dict]]:
        """Return (cost_per_serving, total_cost, itemized_breakdown)."""
        return calculate_recipe_cost(self)

    def get_alternates_for(self, ingredient_str: str) -> list[str]:
        """Return declared alternate ingredients for a given ingredient line."""
        alts = getattr(self, "alternates", None) or {}
        if not alts:
            return []
        if isinstance(alts, dict):
            if ingredient_str in alts:
                val = alts[ingredient_str]
                return val if isinstance(val, list) else [val]
            for k, v in alts.items():
                if k.lower() in ingredient_str.lower() or ingredient_str.lower() in k.lower():
                    return v if isinstance(v, list) else [v]
        elif isinstance(alts, list):
            res = []
            for item in alts:
                if isinstance(item, dict):
                    orig = item.get("original") or item.get("ingredient") or item.get("for") or ""
                    if orig and (orig.lower() in ingredient_str.lower() or ingredient_str.lower() in orig.lower()):
                        alt = item.get("equivalent") or item.get("alternate") or item.get("substitute") or ""
                        if alt:
                            res.append(alt)
                elif isinstance(item, str):
                    res.append(item)
            return res
        return []


def _name(typ) -> str:
    if isinstance(typ, tuple):
        return " or ".join(t.__name__ for t in typ)
    return typ.__name__


def validate(data: Any) -> list[str]:
    """Return a list of human-readable problems (empty list = valid)."""
    if not isinstance(data, dict):
        return ["The file must contain a YAML mapping (key: value pairs)."]
    errors: list[str] = []
    for key, typ in REQUIRED.items():
        if key not in data:
            errors.append(f"Missing required field: '{key}'.")
        elif isinstance(data[key], bool) or not isinstance(data[key], typ):
            errors.append(f"Field '{key}' has the wrong type (expected {_name(typ)}).")
    for key, typ in OPTIONAL.items():
        if key in data and not isinstance(data[key], typ):
            errors.append(f"Field '{key}' has the wrong type (expected {_name(typ)}).")
    unknown = set(data) - set(REQUIRED) - set(OPTIONAL)
    if unknown:
        errors.append(f"Unknown field(s): {', '.join(sorted(unknown))}.")
    cat = data.get("category")
    if isinstance(cat, str) and cat.strip().lower() not in ("basic", "advanced"):
        errors.append(f"'category' must be 'basic' or 'advanced' (got '{cat}').")
    for key in ("equipment", "ingredients", "method", "tags"):
        val = data.get(key)
        if isinstance(val, list):
            if key != "tags" and not val:
                errors.append(f"'{key}' must not be empty.")
            if any(not isinstance(v, str) or not v.strip() for v in val):
                errors.append(f"Every item in '{key}' must be non-empty text.")
    rid = data.get("id")
    if isinstance(rid, str) and not rid.replace("-", "").replace("_", "").isalnum():
        errors.append("'id' may only contain letters, numbers, hyphens, and underscores.")
    return errors


def parse_yaml_text(text: str) -> tuple[Recipe | None, list[str]]:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return None, [f"YAML syntax error: {exc}"]
    errors = validate(data)
    if errors:
        return None, errors
    return Recipe(**{k: data[k] for k in {**REQUIRED, **OPTIONAL} if k in data}), []


def load_all(directory: Path = RECIPE_DIR) -> tuple[list[Recipe], dict[str, list[str]]]:
    """Return (valid recipes sorted by title, {filename: [problems]})."""
    recipes: list[Recipe] = []
    problems: dict[str, list[str]] = {}
    seen: dict[str, str] = {}
    for path in sorted(directory.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        recipe, errs = parse_yaml_text(path.read_text(encoding="utf-8"))
        if recipe and recipe.id in seen:
            errs = [f"Duplicate id '{recipe.id}' (also used in {seen[recipe.id]})."]
            recipe = None
        if errs:
            problems[path.name] = errs
        elif recipe:
            seen[recipe.id] = path.name
            recipes.append(recipe)
    recipes.sort(key=lambda r: r.title.lower())
    return recipes, problems


def to_yaml(data: dict) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=88)


UNIT_WEIGHTS_KG: dict[str, float] = {
    "lb": 0.453592,
    "lbs": 0.453592,
    "pound": 0.453592,
    "pounds": 0.453592,
    "oz": 0.02835,
    "ounce": 0.02835,
    "ounces": 0.02835,
    "tbsp": 0.014,
    "tablespoon": 0.014,
    "tablespoons": 0.014,
    "tsp": 0.005,
    "teaspoon": 0.005,
    "teaspoons": 0.005,
    "cup": 0.150,
    "cups": 0.150,
    "clove": 0.005,
    "cloves": 0.005,
}

ITEM_CUP_WEIGHTS_KG: dict[str, float] = {
    "rice": 0.185,
    "oats": 0.090,
    "water": 0.240,
    "milk": 0.245,
    "flour": 0.125,
    "quinoa": 0.170,
}

ITEM_PIECE_WEIGHTS_KG: dict[str, float] = {
    "potato": 0.20,
    "potatoes": 0.20,
    "sweet potato": 0.25,
    "carrot": 0.10,
    "carrots": 0.10,
    "onion": 0.15,
    "onions": 0.15,
    "zucchini": 0.20,
    "apple": 0.15,
    "apples": 0.15,
    "pear": 0.18,
    "pears": 0.18,
    "chicken breast": 0.25,
    "egg": 0.05,
    "eggs": 0.05,
    "garlic": 0.005,
    "fillet": 0.20,
    "salmon": 0.20,
}


def parse_fraction(s: str) -> float:
    s = s.strip()
    if "/" in s:
        parts = s.split("/")
        return float(parts[0]) / float(parts[1])
    return float(s)


def parse_quantity(s: str) -> float:
    s = s.strip()
    match = re.match(r"^(\d+)\s+(\d+/\d+)$", s)
    if match:
        return float(match.group(1)) + parse_fraction(match.group(2))
    if "/" in s:
        return parse_fraction(s)
    try:
        return float(s)
    except ValueError:
        return 1.0


def estimate_ingredient_cost(ing_str: str) -> dict:
    """Calculate the estimated unit weight and cost for an ingredient line."""
    matched = match_ingredient_to_food(ing_str)
    food_name = matched["name"] if matched else "Unknown ingredient"
    food_name_lower = food_name.lower()
    cost_per_kg = matched.get("cost_per_kg") or 0.0 if matched else 0.0
    cost_per_lb = matched.get("cost_per_lb") or (cost_per_kg / 2.20462) if matched else 0.0
    status = matched.get("status", "safer") if matched else "safer"

    if "water" in food_name_lower:
        return {
            "ingredient": ing_str,
            "matched_food": food_name,
            "line_cost": 0.0,
            "weight_kg": 0.0,
            "unit_cost_kg": 0.0,
            "unit_cost_lb": 0.0,
            "status": status,
            "explanation": "Free",
        }
    if food_name_lower == "salt":
        return {
            "ingredient": ing_str,
            "matched_food": food_name,
            "line_cost": 0.02,
            "weight_kg": 0.002,
            "unit_cost_kg": cost_per_kg,
            "unit_cost_lb": cost_per_lb,
            "status": status,
            "explanation": "Pinch of salt (~$0.02)",
        }
    if "herb" in food_name_lower:
        return {
            "ingredient": ing_str,
            "matched_food": food_name,
            "line_cost": 0.20,
            "weight_kg": 0.010,
            "unit_cost_kg": cost_per_kg,
            "unit_cost_lb": cost_per_lb,
            "status": status,
            "explanation": "Fresh herb sprig (~$0.20)",
        }
    if "cinnamon" in food_name_lower and not re.search(r"\d", ing_str):
        return {
            "ingredient": ing_str,
            "matched_food": food_name,
            "line_cost": 0.05,
            "weight_kg": 0.002,
            "unit_cost_kg": cost_per_kg,
            "unit_cost_lb": cost_per_lb,
            "status": status,
            "explanation": "Dash of cinnamon (~$0.05)",
        }

    cleaned = ing_str.strip()
    qty_unit_match = re.match(r"^([\d\s/\.]+)\s*([a-zA-Z]+)?", cleaned)
    weight_kg = 0.15

    if qty_unit_match:
        qty_str = qty_unit_match.group(1).strip()
        unit_str = (qty_unit_match.group(2) or "").lower().strip()
        qty = parse_quantity(qty_str)

        if unit_str in UNIT_WEIGHTS_KG:
            if unit_str in ("cup", "cups"):
                custom_cup = None
                for k, w in ITEM_CUP_WEIGHTS_KG.items():
                    if k in food_name_lower or k in ing_str.lower():
                        custom_cup = w
                        break
                unit_wt = custom_cup if custom_cup else UNIT_WEIGHTS_KG[unit_str]
            else:
                unit_wt = UNIT_WEIGHTS_KG[unit_str]
            weight_kg = qty * unit_wt
        else:
            piece_wt = None
            for k, w in ITEM_PIECE_WEIGHTS_KG.items():
                if k in food_name_lower or k in ing_str.lower():
                    piece_wt = w
                    break
            if piece_wt:
                weight_kg = qty * piece_wt
            else:
                weight_kg = qty * 0.15
    else:
        weight_kg = 0.10

    line_cost = round(weight_kg * cost_per_kg, 2)
    if line_cost == 0.0 and cost_per_kg > 0:
        line_cost = 0.05

    weight_lb = weight_kg * 2.20462
    explanation = f"{weight_kg:.3f} kg ({weight_lb:.2f} lb) @ ${cost_per_kg:.2f}/kg (${cost_per_lb:.2f}/lb)"
    return {
        "ingredient": ing_str,
        "matched_food": food_name,
        "line_cost": line_cost,
        "weight_kg": weight_kg,
        "unit_cost_kg": cost_per_kg,
        "unit_cost_lb": cost_per_lb,
        "status": status,
        "explanation": explanation,
    }


def calculate_recipe_cost(recipe: Recipe | dict) -> tuple[float, float, list[dict]]:
    """Calculate the estimated cost per serving and total cost for a recipe.

    Returns (cost_per_serving, total_cost, itemized_breakdown).
    """
    if hasattr(recipe, "ingredients"):
        ings = recipe.ingredients
        servings = getattr(recipe, "servings", 1)
    else:
        ings = recipe.get("ingredients", [])
        servings = recipe.get("servings", 1)

    breakdown = []
    total_cost = 0.0
    for i in ings:
        item = estimate_ingredient_cost(i)
        breakdown.append(item)
        total_cost += item["line_cost"]

    servings = max(1, servings)
    cost_per_serving = round(total_cost / servings, 2)
    return cost_per_serving, round(total_cost, 2), breakdown


def swap_recipe_ingredient(
    recipe: Recipe,
    old_ingredient_str: str,
    new_food_name: str,
    old_food_name: str | None = None,
    new_cost_per_kg: float | None = None,
    old_cost_per_kg: float | None = None,
    custom_title: str | None = None,
    custom_id: str | None = None,
    as_alternate: bool = False,
) -> tuple[dict, str]:
    """Swap an ingredient in a recipe and produce an updated valid recipe dict and YAML string."""
    import re

    target_phrase = None
    if old_food_name:
        clean = re.sub(r"\(.*?\)", "", old_food_name).strip()
        if clean:
            target_phrase = clean

    clean_new = re.sub(r"\(.*?\)", "", new_food_name).strip()

    new_ingredients = []
    matched_word = None
    for ing in recipe.ingredients:
        if ing == old_ingredient_str:
            substituted = False
            if target_phrase:
                sing = singularize(target_phrase)
                plur = pluralize(sing)
                for p in (re.escape(plur), re.escape(sing), re.escape(target_phrase)):
                    pattern = re.compile(r"\b" + p + r"\b", re.IGNORECASE)
                    m = pattern.search(ing)
                    if m:
                        matched_text = m.group(0)
                        is_plural = matched_text.lower().endswith("s") and not matched_text.lower().endswith("ss")
                        repl = (
                            pluralize(clean_new.lower())
                            if (is_plural and not clean_new.lower().endswith("s"))
                            else clean_new.lower()
                        )
                        new_ing = pattern.sub(repl, ing, count=1)
                        new_ingredients.append(new_ing)
                        matched_word = target_phrase
                        substituted = True
                        break
            if not substituted:
                words = [
                    w
                    for w in re.findall(r"[a-zA-Z]+", old_ingredient_str)
                    if w.lower()
                    not in (
                        "cup",
                        "cups",
                        "tbsp",
                        "tsp",
                        "lb",
                        "lbs",
                        "oz",
                        "large",
                        "small",
                        "fresh",
                        "plain",
                        "ground",
                        "diced",
                        "sliced",
                        "cubed",
                        "grated",
                        "dry",
                        "cooked",
                        "or",
                        "and",
                    )
                ]
                for w in words:
                    pattern = re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE)
                    m = pattern.search(ing)
                    if m:
                        matched_text = m.group(0)
                        is_plural = matched_text.lower().endswith("s") and not matched_text.lower().endswith("ss")
                        repl = (
                            pluralize(clean_new.lower())
                            if (is_plural and not clean_new.lower().endswith("s"))
                            else clean_new.lower()
                        )
                        new_ing = pattern.sub(repl, ing, count=1)
                        new_ingredients.append(new_ing)
                        matched_word = w
                        substituted = True
                        break
            if not substituted:
                new_ingredients.append(f"{clean_new} (replacing {old_ingredient_str})")
                matched_word = clean_new
        else:
            new_ingredients.append(ing)

    new_method = []
    for step in recipe.method:
        new_step = step
        if matched_word and len(matched_word) > 2 and matched_word.lower() not in ("water", "salt", "oil"):
            sing_m = singularize(matched_word)
            plur_m = pluralize(sing_m)
            for p in (re.escape(plur_m), re.escape(sing_m), re.escape(matched_word)):
                pattern = re.compile(r"\b" + p + r"\b", re.IGNORECASE)
                if pattern.search(new_step):
                    def _replace_keep_case(m):
                        orig = m.group(0)
                        is_plur = orig.lower().endswith("s") and not orig.lower().endswith("ss")
                        base = pluralize(clean_new) if (is_plur and not clean_new.lower().endswith("s")) else clean_new
                        if orig.isupper():
                            return base.upper()
                        if orig[0].isupper():
                            return base.title()
                        return base.lower()

                    new_step = pattern.sub(_replace_keep_case, new_step)
                    break
        new_method.append(new_step)

    new_cost_per_serving = recipe.cost_per_serving
    if new_cost_per_kg and old_cost_per_kg and old_cost_per_kg > 0:
        cost_ratio = new_cost_per_kg / old_cost_per_kg
        new_cost_per_serving = round(recipe.cost_per_serving * cost_ratio, 2)

    if custom_title:
        title = custom_title
    elif matched_word and len(matched_word) > 2:
        sing_m = singularize(matched_word)
        plur_m = pluralize(sing_m)
        found = False
        for p in (re.escape(plur_m), re.escape(sing_m), re.escape(matched_word)):
            pattern = re.compile(r"\b" + p + r"\b", re.IGNORECASE)
            if pattern.search(recipe.title):
                title = pattern.sub(clean_new.title(), recipe.title, count=1)
                found = True
                break
        if not found:
            title = f"{recipe.title} (with {clean_new})"
    else:
        title = f"{recipe.title} (with {clean_new})"

    if custom_id:
        rid = custom_id
    else:
        clean_slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        rid = clean_slug[:40]

    data = {
        "id": rid,
        "title": title,
        "category": "advanced",
        "servings": recipe.servings,
        "prep_minutes": recipe.prep_minutes,
        "cook_minutes": recipe.cook_minutes,
        "cost_per_serving": float(recipe.cost_per_serving),
        "equipment": list(recipe.equipment),
        "ingredients": new_ingredients,
        "method": new_method,
        "storage": recipe.storage,
        "verified": False,
    }
    if as_alternate:
        # Keep original ingredients in ingredients list, add the replacement as an alternate option
        data["ingredients"] = list(recipe.ingredients)
        data["method"] = list(recipe.method)
        if custom_title:
            data["title"] = custom_title
        else:
            data["title"] = f"{recipe.title} (with {clean_new} option)"
        alts = dict(recipe.alternates) if isinstance(recipe.alternates, dict) else {}
        if old_ingredient_str not in alts:
            alts[old_ingredient_str] = []
        repl_str = None
        for orig, sub in zip(recipe.ingredients, new_ingredients):
            if orig == old_ingredient_str:
                repl_str = sub
                break
        if not repl_str:
            repl_str = f"{clean_new} (replacing {old_ingredient_str})"
        if repl_str not in alts[old_ingredient_str]:
            alts[old_ingredient_str].append(repl_str)
        data["alternates"] = alts
        data["notes"] = f"Includes alternate ingredient option for {old_ingredient_str}: {clean_new}. {recipe.notes}".strip()
    else:
        if recipe.alternates:
            data["alternates"] = recipe.alternates

    # Calculate exact cost per serving based on ingredients
    calc_serving, total_cost, _ = calculate_recipe_cost(data)
    data["cost_per_serving"] = float(calc_serving)
    if recipe.description:
        data["description"] = recipe.description
    if recipe.tags:
        data["tags"] = list(recipe.tags)
    if not as_alternate:
        if recipe.notes:
            data["notes"] = f"Swapped {old_ingredient_str} with {clean_new}. {recipe.notes}"
        else:
            data["notes"] = f"Swapped {old_ingredient_str} with {clean_new}."

    return data, to_yaml(data)
