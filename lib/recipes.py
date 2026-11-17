"""Load and validate recipe YAML files.

Every file in recipes/*.yaml (except names starting with "_") is one recipe.
See recipes/_template.yaml for the schema and README.md for how to add one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

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

    @property
    def total_minutes(self) -> int:
        return self.prep_minutes + self.cook_minutes


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
